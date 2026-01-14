"""Example 02: File Operations.

Shows the full read / write / edit signal flow using a scripted
performer so no LLM API key is required.
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phantom.main import run_task  # noqa: E402
from phantom.signal.report.control import PerformerState  # noqa: E402
from phantom.voice.message import Message  # noqa: E402


_SCRIPT = [
    # Turn 1: write a file
    Message.assistant(
        content=(
            "First I will write a Python file.\n\n"
            "```bash\n"
            "cat > /workspace/greet.py << 'PY'\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello, {name}!'\n"
            "PY\n"
            "```"
        )
    ),
    # Turn 2: verify by reading it back
    Message.assistant(
        content="Now I will verify the file was written.\n\n"
        "```bash\npython3 /workspace/greet.py || cat /workspace/greet.py\n```"
    ),
    # Turn 3: complete
    Message.assistant(
        content="File written and verified. Task complete."
    ),
]

_TURN = 0


def _mock_complete(messages, tools=None, **kwargs):
    global _TURN
    response = _SCRIPT[min(_TURN, len(_SCRIPT) - 1)]
    _TURN += 1
    return response


async def main() -> None:
    global _TURN
    _TURN = 0

    with tempfile.TemporaryDirectory() as workspace:
        with patch(
            "phantom.voice.provider.VoiceProvider.complete",
            side_effect=_mock_complete,
        ):
            scene = await run_task(
                task=(
                    "Create a greet.py file with a greet() function"
                ),
                max_iterations=6,
            )

        greet_path = Path(workspace) / "greet.py"
        if greet_path.exists():
            print("greet.py content:")
            print(greet_path.read_text())
        else:
            print("(file written to stage workspace)")

    print(f"Final state: {scene.current_state}")
    print(f"Iterations : {scene.iteration}")


if __name__ == "__main__":
    asyncio.run(main())
