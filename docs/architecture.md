# Architecture

PhantomOrchestra is an event-driven AI task orchestration platform.
Every component communicates through a central pub/sub bus called the
`SignalChannel`. No component calls another directly — they only emit
and subscribe to typed `Signal` objects.

## System Overview

```
┌──────────────────────────────────────────────────────────┐
│                  Conductor  (FastAPI)                    │
│   REST /api/v1/*          WebSocket /api/v1/*/ws         │
└────────────────────────┬─────────────────────────────────┘
                         │ SessionManager
         ┌───────────────▼──────────────────┐
         │           SignalChannel           │
         │   pub/sub bus  +  SignalDepot     │
         │         (persistence)             │
         └──┬─────────────┬────────────────┬┘
            │             │                │
     ┌──────▼──────┐ ┌────▼─────┐  ┌──────▼──────┐
     │  Director   │ │  Stage   │  │   Memory    │
     │(controller) │ │(runtime) │  │  (recall)   │
     └──────┬──────┘ └──────────┘  └─────────────┘
            │
     ┌──────▼──────┐
     │  Performer  │  ◄──  VoiceProvider (LLM)
     │  (AI agent) │
     └─────────────┘
```

## Modules

### `phantom/score/` — Configuration

Pydantic v2 models that define the full configuration schema:

| Class | Purpose |
|-------|---------|
| `OrchestraConfig` | Master config; holds all sub-configs |
| `VoiceConfig` | LLM provider settings (model, key, retries) |
| `PerformerConfig` | Agent capability flags |
| `StageConfig` | Execution environment settings |

`loader.py` searches four locations for `config.toml` in order:
explicit path → `$PHANTOM_CONFIG_PATH` → `~/.phantom/config.toml`
→ `./config.toml`, then applies `PHANTOM_*` environment variable
overrides on top.

### `phantom/signal/` — Event System

The signal system is the backbone of the platform.

**`Signal`** (base class) — every event in the system. Carries an
auto-assigned integer ID, ISO timestamp, `SignalSource`, and optional
`cause` (parent signal ID).

**`Directive`** (subclass of Signal) — represents an *action* the
performer wants to take. Subtypes: `RunCommandDirective`,
`ReadFileDirective`, `WriteFileDirective`, `EditFileDirective`,
`MessageDirective`, `CompleteDirective`, `DelegateDirective`.

**`Report`** (subclass of Signal) — represents an *observation*
returned by the environment. Subtypes: `CommandOutputReport`,
`FileReadReport`, `FileWriteReport`, `FaultReport`,
`StateTransitionReport`.

**`SignalDepot`** — persists each signal as a JSON file named by its
zero-padded ID (e.g. `00000042.json`) under a session-scoped path in
the `Repository`.

**`SignalChannel`** — thread-safe pub/sub bus. Subscribers register a
callback under a `ChannelSubscriber` enum value. When `broadcast()` is
called, the channel assigns the signal's ID and timestamp, persists it
via the depot, then fans out to all subscribers via per-subscriber
`ThreadPoolExecutor` instances. Secrets registered via `mask_secrets()`
are recursively replaced in signal content before fan-out.

### `phantom/voice/` — LLM Abstraction

`VoiceProvider` wraps `litellm.completion`. It translates
`Message` objects into the LiteLLM wire format, executes with
configurable exponential-backoff retries, extracts tool calls from
the response, and accumulates `UsageMetrics`.

`VoiceRegistry` lazily instantiates `VoiceProvider` objects on first
access, keyed by the name used in `OrchestraConfig.voices`.

### `phantom/performer/` — AI Agent Core

**`Performer`** (abstract) — base class with a class-level registry.
Concrete performers implement `decide(scene) -> Directive`.

**`CodeActPerformer`** — the default implementation. On each call to
`decide()` it builds a message list (system prompt + conversation
history), calls the LLM, appends the response to history, then parses
the response into a `Directive`. It supports both tool-call responses
(dispatched via a name→constructor table) and markdown code fences
(`\`\`\`bash` → `RunCommandDirective`).

**`Scene`** — immutable-ish state bag for one session: conversation
history, all emitted directives and reports, iteration counter, budget
tracking, and current `PerformerState`.

**`Director`** — subscribes to the `SignalChannel` as
`ChannelSubscriber.DIRECTOR`. On each incoming `Report`, it appends
the content to history and calls `_step()`. `_step()` calls
`performer.decide(scene)`, increments the iteration counter, and
broadcasts the resulting `Directive`. When a `CompleteDirective`
arrives it transitions the scene to `COMPLETE`.

### `phantom/stage/` — Execution Environment

**`Stage`** (abstract) — defines `initialize()`, `teardown()`,
`execute_command()`, `read_file()`, and `write_file()`. The base class
provides a `dispatch(directive)` router that delegates to the right
method.

**`LocalStage`** — runs commands with `asyncio.create_subprocess_shell`
in the host process. All file paths are resolved through
`_resolve_path()`, which prevents traversal outside the workspace.

**`ContainerStage`** — spins up a Docker container per session
(`docker run --detach`), executes commands via `docker exec`, and
tears down with `docker rm -f` on `teardown()`.

### `phantom/conductor/` — REST + WebSocket API

`create_app()` returns a fully-configured FastAPI application:

- `POST /api/v1/sessions` — creates a session, wires the full pipeline
  (depot → channel → performer → stage → director), fires off the
  director as a background task, returns `SessionResponse`.
- `GET /api/v1/sessions/{id}` — returns current scene state.
- `POST /api/v1/sessions/{id}/messages` — resumes a paused session.
- `DELETE /api/v1/sessions/{id}` — stops and removes a session.
- `WS /api/v1/sessions/{id}/ws` — `WebSocketRelay` subscribes to the
  channel and forwards every signal as JSON.

### `phantom/vault/` — Storage

`Repository` (abstract) defines `persist`, `retrieve`, `enumerate`,
`remove`. Two implementations ship:

- `LocalRepository` — writes to the host filesystem with atomic
  rename (`os.replace`) for thread safety and path-traversal
  protection via `os.path.realpath`.
- `MemoryRepository` — dict-backed, useful for testing.

## Signal Lifecycle

```
1. Director calls performer.decide(scene)
2. Performer returns a Directive
3. Director calls channel.broadcast(directive, source=PERFORMER)
4. Channel assigns id=N, timestamp=now(), persists to depot
5. Channel fans out to all subscribers in parallel:
   - Stage subscriber receives directive, executes it
   - Conductor subscriber forwards to WebSocket clients
6. Stage calls channel.broadcast(report, source=ENVIRONMENT)
7. Channel persists report, fans out again
8. Director subscriber receives report, appends to history
9. Director calls _step() → goto 1
```

## Extension Points

| What to extend | How |
|---------------|-----|
| Custom AI agent | Subclass `Performer`, call `Performer.register()` |
| Custom runtime | Subclass `Stage`, add case to `factory.py` |
| Custom storage | Subclass `Repository`, add case to `vault/factory.py` |
| Additional API routes | Add `APIRouter` and include in `app.py` |
| Additional signal types | Subclass `Directive` or `Report`, register in `codec.py` |
