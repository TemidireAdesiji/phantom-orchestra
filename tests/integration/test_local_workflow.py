"""Integration test: full local task execution workflow.

Tests that a task flows through the pipeline:
    Director → Performer → Stage → Report

The VoiceProvider is mocked so no real LLM calls are made.
"""

import asyncio

import pytest

from phantom.performer.base import Performer
from phantom.performer.director import Director
from phantom.performer.scene import Scene
from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.score.voice_config import VoiceConfig
from phantom.signal.base import SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.depot import SignalDepot
from phantom.signal.directive.base import Directive
from phantom.signal.directive.control import CompleteDirective
from phantom.signal.directive.terminal import RunCommandDirective
from phantom.signal.report.control import PerformerState
from phantom.stage.local_stage import LocalStage
from phantom.vault.memory_vault import MemoryRepository
from phantom.voice.registry import VoiceRegistry

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_channel(session_id: str = "integ-test") -> SignalChannel:
    """Build a SignalChannel backed by an in-memory depot."""
    repo = MemoryRepository()
    depot = SignalDepot(session_id=session_id, repository=repo)
    return SignalChannel(session_id=session_id, depot=depot)


# ---------------------------------------------------------------------------
# Minimal Performer that emits one command then completes
# ---------------------------------------------------------------------------


class _SingleCommandPerformer(Performer):
    """Performer that runs one shell command, then completes.

    On the first call to ``decide`` it emits a ``RunCommandDirective``
    (which the stage will execute and return as a Report).  On the
    second call it emits a ``CompleteDirective`` so the Director
    finalises the session.
    """

    def __init__(self, config, voice_registry, command: str):
        super().__init__(config, voice_registry)
        self._command = command
        self._call_count = 0

    def decide(self, scene: Scene) -> Directive:
        self._call_count += 1
        if self._call_count == 1:
            return RunCommandDirective(command=self._command)
        return CompleteDirective(
            outputs={"status": "done"},
            thought="Task finished",
        )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestLocalWorkflowIntegration:
    """Full pipeline: Director → Performer → Stage → Report → Complete."""

    async def test_task_runs_and_reaches_complete_state(self, tmp_path):
        """A task that runs one shell command completes successfully."""
        session_id = "wf-complete"
        channel = _build_channel(session_id)

        config = PerformerConfig()
        registry = VoiceRegistry(
            configs={"default": VoiceConfig()},
            default_name="default",
        )
        stage_cfg = StageConfig(
            stage_type="local",
            workspace_dir=str(tmp_path / "ws"),
        )

        performer = _SingleCommandPerformer(
            config=config,
            voice_registry=registry,
            command="echo integration-test",
        )

        scene = Scene(
            session_id=session_id,
            max_iterations=50,
        )

        states_seen: list[PerformerState] = []
        director = Director(
            session_id=session_id,
            performer=performer,
            channel=channel,
            scene=scene,
            on_state_change=lambda s: states_seen.append(s),
        )

        # Wire stage: dispatch RunCommandDirective and broadcast result
        async with LocalStage(stage_cfg) as stage:
            # Hook stage to channel: when a RunCommandDirective arrives,
            # execute it and broadcast the report back.
            completion_event = asyncio.Event()

            def _on_signal(sig):
                if isinstance(sig, RunCommandDirective):

                    async def _run():
                        report = await stage.execute_command(sig.command)
                        report.cause = sig.id
                        channel.broadcast(report, SignalSource.ENVIRONMENT)

                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(_run(), loop)
                elif isinstance(sig, CompleteDirective):
                    completion_event.set()

            channel.subscribe(
                ChannelSubscriber.STAGE,
                _on_signal,
                "stage-hook",
            )

            await director.start("Run echo and complete.")

            # Wait for completion (with timeout to prevent hangs)
            try:
                await asyncio.wait_for(completion_event.wait(), timeout=5.0)
            except TimeoutError:
                pass  # Check state below

        channel.close()

        # The scene should have reached COMPLETE
        assert scene.current_state == PerformerState.COMPLETE
        assert director.is_complete is True

    async def test_complete_directive_stores_outputs_in_scene(self, tmp_path):
        """Outputs from CompleteDirective end up in scene.outputs."""
        session_id = "wf-outputs"
        channel = _build_channel(session_id)

        config = PerformerConfig()
        registry = VoiceRegistry(
            configs={"default": VoiceConfig()},
            default_name="default",
        )

        class _ImmediateCompleter(Performer):
            def decide(self, scene: Scene) -> Directive:
                return CompleteDirective(
                    outputs={"answer": "42", "note": "done"},
                )

        performer = _ImmediateCompleter(config=config, voice_registry=registry)
        scene = Scene(session_id=session_id)
        director = Director(
            session_id=session_id,
            performer=performer,
            channel=channel,
            scene=scene,
        )

        await director.start("Immediately complete.")
        channel.close()

        assert scene.outputs.get("answer") == "42"
        assert scene.outputs.get("note") == "done"
        assert scene.current_state == PerformerState.COMPLETE

    async def test_performer_error_transitions_to_failed_state(
        self,
    ):
        """When Performer.decide raises, Director transitions to FAILED."""
        session_id = "wf-fail"
        channel = _build_channel(session_id)

        config = PerformerConfig()
        registry = VoiceRegistry(
            configs={"default": VoiceConfig()},
            default_name="default",
        )

        class _BrokenPerformer(Performer):
            def decide(self, scene: Scene) -> Directive:
                raise RuntimeError("internal performer error")

        performer = _BrokenPerformer(config=config, voice_registry=registry)
        scene = Scene(session_id=session_id)
        director = Director(
            session_id=session_id,
            performer=performer,
            channel=channel,
            scene=scene,
        )

        await director.start("This will fail.")
        channel.close()

        assert scene.current_state == PerformerState.FAILED

    async def test_signals_are_persisted_to_depot(self, tmp_path):
        """All broadcast signals are readable from the depot."""
        session_id = "wf-depot"
        repo = MemoryRepository()
        depot = SignalDepot(session_id=session_id, repository=repo)
        channel = SignalChannel(session_id=session_id, depot=depot)

        config = PerformerConfig()
        registry = VoiceRegistry(
            configs={"default": VoiceConfig()},
            default_name="default",
        )

        class _QuickComplete(Performer):
            def decide(self, scene: Scene) -> Directive:
                return CompleteDirective(outputs={})

        performer = _QuickComplete(config=config, voice_registry=registry)
        scene = Scene(session_id=session_id)
        director = Director(
            session_id=session_id,
            performer=performer,
            channel=channel,
            scene=scene,
        )

        await director.start("Persist me.")
        channel.close()

        # Depot should have at least the StateTransition reports
        signals = depot.fetch_signals(start_id=0)
        assert len(signals) > 0
