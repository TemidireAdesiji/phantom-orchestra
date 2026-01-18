"""Example 01: Hello World.

Demonstrates the simplest possible PhantomOrchestra session:
run a single task programmatically using a mock LLM response
so no API key is required.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

# Allow running from the examples directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phantom.main import run_task  # noqa: E402
from phantom.signal.report.control import PerformerState  # noqa: E402
from phantom.voice.message import Message  # noqa: E402


def _make_mock_voice():
    """Return a mock that produces a scripted two-turn conversation."""
    call_count = 0

    def fake_complete(messages, tools=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First turn: run a command
            return Message.assistant(
                content="I will print a greeting.\n\n"
                "```bash\necho 'Hello from PhantomOrchestra!'\n```"
            )
        # Second turn: declare success
        return Message.assistant(
            content="The task is complete. Task complete.",
        )

    return fake_complete


async def main() -> None:
    mock_complete = _make_mock_voice()

    with patch(
        "phantom.voice.provider.VoiceProvider.complete",
        side_effect=mock_complete,
    ):
        scene = await run_task(
            task="Print a greeting message",
            max_iterations=5,
        )

    print(f"Final state  : {scene.current_state}")
    print(f"Iterations   : {scene.iteration}")
    print(f"Budget spent : ${scene.budget_spent_usd:.4f}")
    if scene.outputs:
        print("Outputs:")
        for key, value in scene.outputs.items():
            print(f"  {key}: {value}")

    if scene.current_state == PerformerState.COMPLETE:
        print("\nTask completed successfully.")
    else:
        print(
            f"\nTask ended with state: {scene.current_state}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
