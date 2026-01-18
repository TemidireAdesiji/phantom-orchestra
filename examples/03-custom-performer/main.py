"""Example 03: Custom Performer.

Shows how to subclass Performer and register it so it can be
selected by name. The DiagnosticsPerformer runs a fixed sequence
of informational commands then completes.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phantom.main import run_task  # noqa: E402
from phantom.performer.base import Performer  # noqa: E402
from phantom.performer.scene import Scene  # noqa: E402
from phantom.score.performer_config import PerformerConfig  # noqa: E402
from phantom.signal.directive.base import Directive  # noqa: E402
from phantom.signal.directive.control import CompleteDirective  # noqa: E402
from phantom.signal.directive.terminal import (  # noqa: E402
    RunCommandDirective,
)
from phantom.voice.registry import VoiceRegistry  # noqa: E402


class DiagnosticsPerformer(Performer):
    """Runs a fixed sequence of diagnostic commands, then completes.

    This performer does not use an LLM at all — it follows a
    deterministic script. Useful as a template for rule-based agents.
    """

    STEPS: list[str] = [
        "python3 --version",
        "pwd",
        "echo 'Diagnostics complete'",
    ]

    def decide(self, scene: Scene) -> Directive:
        step_index = scene.iteration - 1

        if step_index < len(self.STEPS):
            cmd = self.STEPS[step_index]
            return RunCommandDirective(
                command=cmd,
                thought=f"Step {scene.iteration}: {cmd}",
            )

        return CompleteDirective(
            outputs={
                "steps_run": str(len(self.STEPS)),
                "status": "all diagnostics passed",
            }
        )

    def get_available_tools(self) -> list[dict]:
        return []

    def build_system_prompt(self) -> str:
        return "Diagnostics performer — no LLM required."


# Register so it can be referenced by name
Performer.register("Diagnostics", DiagnosticsPerformer)


async def main() -> None:
    # No LLM mock needed — DiagnosticsPerformer never calls complete()
    scene = await run_task(
        task="Run diagnostics",
        performer_name="Diagnostics",
        max_iterations=10,
    )

    print(f"Final state : {scene.current_state}")
    print(f"Iterations  : {scene.iteration}")
    print("Outputs:")
    for key, value in scene.outputs.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
