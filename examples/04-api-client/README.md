# Example 04 — REST API Client

Shows how to drive a running PhantomOrchestra server from Python
using `httpx` for REST and `websockets` for real-time streaming.

## What It Demonstrates

- Checking server health
- Creating a session via `POST /api/v1/sessions`
- Polling session state via `GET /api/v1/sessions/{id}`
- Streaming signals via WebSocket
- Cleaning up with `DELETE /api/v1/sessions/{id}`

## Prerequisites

```bash
# Terminal 1 — start the server
export PHANTOM_API_KEY="your-key"
poetry run phantom serve

# Terminal 2 — run the client
cd examples/04-api-client
pip install httpx websockets
python main.py
```

## WebSocket Streaming

The `stream_session()` coroutine (at the bottom of `main.py`)
shows how to receive every signal in real time. Swap the polling
loop for a call to `stream_session(sid)` to see live output.

## Expected Output

```
Server version : 0.1.0
Uptime (s)     : 3.4

Creating session...
Session ID : 3f8a2c1d-...
State      : running
  state=running  iterations=1
  state=running  iterations=2
  state=complete  iterations=3

Final state : complete
Iterations  : 3
Session removed.
```
