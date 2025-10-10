# Development Guide

## Prerequisites

- Python 3.11 or 3.12
- [Poetry](https://python-poetry.org/docs/#installation) 1.8+
- Docker Desktop or Docker Engine (for ContainerStage tests)
- Git 2.x

## Initial Setup

```bash
git clone https://github.com/phantom-orchestra/phantom-orchestra.git
cd phantom-orchestra

# Install all dependencies including dev tools
poetry install --with dev

# Install git hooks (ruff, format check, secret detection)
poetry run pre-commit install

# Set up local configuration
cp config.template.toml config.toml
# Edit config.toml: set voice.api_key, or export PHANTOM_API_KEY
```

## Running the Server Locally

```bash
# Start with default config
poetry run phantom serve

# Custom host/port
poetry run phantom serve --host 127.0.0.1 --port 8080

# Point at a specific config file
poetry run phantom serve --config /path/to/config.toml
```

The API docs are available at `http://localhost:3000/docs`.

## Running a Task from the CLI

```bash
poetry run phantom run "Create a hello_world.py file"

# With a specific model
PHANTOM_MODEL=gpt-4o poetry run phantom run "Describe the workspace"

# Limit iterations
poetry run phantom run "Analyse this directory" --max-iterations 10
```

## Running Tests

```bash
# All unit tests (fast, no network)
make test

# Unit tests with HTML coverage report
make test-cov
open htmlcov/index.html

# A single test module
poetry run pytest tests/unit/signal/ -v

# Integration tests (requires network for real LLM calls if unmocked)
poetry run pytest tests/integration -v

# One specific test
poetry run pytest tests/unit/vault/test_local_vault.py::test_persist_and_retrieve -v
```

## Linting and Formatting

```bash
# Check for issues
make lint

# Auto-fix and reformat
make format

# Type checking
make type-check
```

All of these run automatically as pre-commit hooks and in CI.

## Adding a Dependency

```bash
# Runtime dependency
poetry add some-package

# Dev-only dependency
poetry add --group dev some-dev-tool
```

Always commit `pyproject.toml`. A `poetry.lock` file is optional for
libraries but recommended for applications.

## Project Layout Quick Reference

```
phantom/
  score/       Configuration models and loader
  signal/      Event system (directives, reports, channel, depot)
  voice/       LLM abstraction (provider, registry, messages)
  performer/   AI agent core (base, codeact, director, scene)
  stage/       Execution environments (local, docker)
  conductor/   FastAPI server (app, session manager, websocket)
  vault/       Storage backends (local, memory)
  toolkit/     Shared utilities (logging, async helpers)
  main.py      CLI entry point
tests/
  unit/        Fast, no-network tests mirroring phantom/ layout
  integration/ Full pipeline tests with mocked LLM
docs/          Architecture, config, API, development guides
examples/      Runnable standalone examples
containers/    Dockerfiles
.github/       CI workflows
```

## Common Development Tasks

### Add a New Signal Type

1. Create a dataclass in `phantom/signal/directive/` or
   `phantom/signal/report/` subclassing `Directive` or `Report`.
2. Add a `directive_type` / `report_type` string field.
3. Register it in `phantom/signal/codec.py` dispatch tables.
4. Export from `phantom/signal/__init__.py`.
5. Add tests in `tests/unit/signal/`.

### Add a New Performer

1. Subclass `phantom.performer.base.Performer`.
2. Implement `decide(scene) -> Directive`.
3. Call `Performer.register("MyName", MyPerformer)` at module level.
4. Import the module in `phantom/performer/__init__.py`.
5. Add tests in `tests/unit/performer/`.

### Add a New REST Endpoint

1. Create or extend a router in `phantom/conductor/routes/`.
2. Add request/response Pydantic models in `phantom/conductor/models.py`.
3. Include the router in `phantom/conductor/app.py`.
4. Add tests in `tests/unit/conductor/`.

## Debugging Tips

- Set `PHANTOM_LOG_LEVEL=DEBUG` for verbose structured logs.
- Set `voice.log_completions = true` in config to dump every LLM
  request/response to the `completions/` folder.
- The `SignalDepot` stores every signal as JSON under
  `file_store_path/<session_id>/`. Inspect these files to replay
  exactly what happened in a session.
- Use `poetry run pytest -s` to see live log output during tests.
