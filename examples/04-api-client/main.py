"""Example 04: REST API Client.

Shows how to interact with a running PhantomOrchestra server
using httpx for REST calls and websockets for real-time streaming.

Prerequisites:
  Start the server first:
    poetry run phantom serve

  Then run this example:
    python main.py
"""

import asyncio
import json
import sys


async def main() -> None:
    try:
        import httpx
    except ImportError:
        print("Install httpx: pip install httpx", file=sys.stderr)
        sys.exit(1)

    base = "http://localhost:3000/api/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        resp = await client.get(f"{base}/health/")
        resp.raise_for_status()
        health = resp.json()
        print(f"Server version : {health['version']}")
        print(f"Uptime (s)     : {health['uptime_seconds']:.1f}")

        # 2. Create a session
        print("\nCreating session...")
        resp = await client.post(
            f"{base}/sessions",
            json={
                "task": "Print the current date and time",
                "max_iterations": 5,
            },
        )
        resp.raise_for_status()
        session = resp.json()
        sid = session["session_id"]
        print(f"Session ID : {sid}")
        print(f"State      : {session['state']}")

        # 3. Poll until complete (or use WebSocket below instead)
        for _ in range(20):
            await asyncio.sleep(1.0)
            resp = await client.get(f"{base}/sessions/{sid}")
            resp.raise_for_status()
            data = resp.json()
            state = data["state"]
            iters = data["iterations"]
            print(f"  state={state}  iterations={iters}")
            if state in ("complete", "failed", "stopped"):
                break

        # 4. Final state
        resp = await client.get(f"{base}/sessions/{sid}")
        final = resp.json()
        print(f"\nFinal state : {final['state']}")
        print(f"Iterations  : {final['iterations']}")

        # 5. Clean up
        await client.delete(f"{base}/sessions/{sid}")
        print("Session removed.")


async def stream_session(session_id: str) -> None:
    """Alternative: stream signals via WebSocket."""
    try:
        import websockets
    except ImportError:
        print(
            "Install websockets: pip install websockets",
            file=sys.stderr,
        )
        return

    uri = (
        f"ws://localhost:3000/api/v1/sessions/{session_id}/ws"
    )
    print(f"Connecting to {uri}")

    async with websockets.connect(uri) as ws:  # type: ignore[attr-defined]
        async for raw in ws:
            data = json.loads(raw)
            sig_type = data.get("signal_type", "unknown")
            content = str(data.get("content", ""))[:120]
            print(f"[{sig_type:20s}] {content}")

            if sig_type == "state_transition":
                if "complete" in content or "failed" in content:
                    break


if __name__ == "__main__":
    asyncio.run(main())
