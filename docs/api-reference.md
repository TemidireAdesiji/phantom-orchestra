# REST API Reference

Base URL: `http://localhost:3000/api/v1`

Interactive docs (Swagger UI): `http://localhost:3000/docs`

## Authentication

The open-source build ships without authentication. Production
deployments should place a reverse proxy (nginx, Caddy) with TLS
and an auth layer in front of the Conductor.

## Sessions

### Create Session

```
POST /api/v1/sessions
```

Start a new task execution session.

**Request body:**

```json
{
  "task": "Write a function that reverses a linked list",
  "performer_name": "default",
  "voice_name": null,
  "workspace_dir": null,
  "max_iterations": 100,
  "max_budget_usd": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task` | string | yes | Task description (1–10000 chars) |
| `performer_name` | string | no | Registered performer name |
| `voice_name` | string | no | Named voice/LLM config to use |
| `workspace_dir` | string | no | Override workspace directory |
| `max_iterations` | integer | no | Stop after N iterations (1–500) |
| `max_budget_usd` | number | no | USD cost cap |

**Response `201 Created`:**

```json
{
  "session_id": "3f8a2c1d-...",
  "state": "running",
  "iterations": 0,
  "budget_spent_usd": 0.0,
  "outputs": {},
  "message": null
}
```

**Example:**

```bash
curl -X POST http://localhost:3000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"task": "List files in the workspace", "max_iterations": 5}'
```

---

### List Sessions

```
GET /api/v1/sessions
```

Returns all active sessions.

**Response `200 OK`:**

```json
[
  {
    "session_id": "3f8a2c1d-...",
    "state": "running",
    "iterations": 3,
    "created_at": 1704067200.0
  }
]
```

---

### Get Session

```
GET /api/v1/sessions/{session_id}
```

Returns the current state of a session.

**Response `200 OK`:** Same shape as Create Session response.

**Response `404 Not Found`:**

```json
{"detail": "Session not found: 3f8a2c1d-..."}
```

---

### Send Message

```
POST /api/v1/sessions/{session_id}/messages
```

Send a follow-up message to a paused or running session.

**Request body:**

```json
{"content": "Now also add type hints to the function"}
```

**Response `200 OK`:** Updated `SessionResponse`.

---

### Stop Session

```
DELETE /api/v1/sessions/{session_id}
```

Stops execution and releases all resources for the session.

**Response `204 No Content`**

---

## Health

### Health Check

```
GET /api/v1/health/
```

**Response `200 OK`:**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 142.7
}
```

---

## WebSocket — Real-time Signal Stream

```
WS /api/v1/sessions/{session_id}/ws
```

Connect to receive every `Signal` broadcast on the session's channel
as it happens.

**Incoming messages (server → client):**

Each message is a JSON object with at minimum:

```json
{
  "signal_type": "run_command",
  "content": "ls -la",
  "source": "performer",
  "id": 4,
  "timestamp": "2024-01-01T12:00:00.123456"
}
```

Common `signal_type` values:

| Value | Description |
|-------|-------------|
| `run_command` | Shell command directive |
| `read_file` | File read directive |
| `write_file` | File write directive |
| `send_message` | Agent message to user |
| `complete` | Task completion directive |
| `command_output` | Shell command result |
| `file_read` | File read result |
| `file_write` | File write result |
| `state_transition` | Agent state changed |
| `fault` | Error report |

**Outgoing messages (client → server):**

Send a user message to a running session:

```json
{"type": "message", "content": "Please also handle edge cases"}
```

**Example (wscat):**

```bash
wscat -c ws://localhost:3000/api/v1/sessions/3f8a2c1d-.../ws
```

---

## Error Responses

All errors follow FastAPI's standard format:

```json
{"detail": "Human-readable error message"}
```

| Status | Meaning |
|--------|---------|
| `400` | Malformed request |
| `404` | Session not found |
| `422` | Validation error (missing required field, out-of-range value) |
| `500` | Internal server error |
