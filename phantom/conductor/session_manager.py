"""Manages active performer sessions for the Conductor."""

import asyncio
import time
from collections.abc import Callable

import structlog

from phantom.performer.base import Performer
from phantom.performer.director import Director
from phantom.performer.scene import Scene
from phantom.score.orchestra_config import OrchestraConfig
from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.signal.base import SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.depot import SignalDepot
from phantom.signal.directive.base import Directive
from phantom.signal.report.control import PerformerState
from phantom.stage.base import Stage
from phantom.stage.factory import create_stage
from phantom.vault.factory import create_repository
from phantom.voice.registry import VoiceRegistry

__all__ = ["ActiveSession", "SessionManager"]

logger = structlog.get_logger(__name__)


class ActiveSession:
    """Container for all runtime objects belonging to one session.

    Attributes:
        session_id: Unique session identifier.
        director: Director driving the performer loop.
        channel: SignalChannel for bidirectional signal flow.
        stage: Execution stage for running directives.
        created_at: Unix timestamp when the session was created.
    """

    def __init__(
        self,
        session_id: str,
        director: Director,
        channel: SignalChannel,
        stage: Stage,
    ) -> None:
        self.session_id = session_id
        self.director = director
        self.channel = channel
        self.stage = stage
        self.created_at = time.time()


class SessionManager:
    """Creates, tracks, and tears down performer sessions.

    Args:
        config: Master orchestration configuration used to
            construct voices, performers, stages, and repositories.
    """

    def __init__(self, config: OrchestraConfig) -> None:
        self._config = config
        self._sessions: dict[str, ActiveSession] = {}
        self._voice_registry = VoiceRegistry.from_orchestra_config(config)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------

    async def create_session(
        self,
        task: str,
        session_id: str,
        performer_name: str = "default",
        voice_name: str | None = None,
        workspace_dir: str | None = None,
        max_iterations: int = 100,
        max_budget_usd: float | None = None,
        on_state_change: Callable[[PerformerState], None] | None = (None),
    ) -> Scene:
        """Create a new session and begin task execution.

        Wires together a repository, depot, channel, performer,
        scene, and stage; subscribes the stage as a directive
        executor on the channel; starts the director in a
        background asyncio task.

        Args:
            task: Natural-language task description.
            session_id: Unique identifier for this session.
            performer_name: Registered performer to instantiate.
            voice_name: Optional LLM voice override.
            workspace_dir: Optional stage workspace path.
            max_iterations: Hard cap on decision steps.
            max_budget_usd: Optional USD spending cap.
            on_state_change: Callback invoked on state transitions.

        Returns:
            The initial Scene (execution continues asynchronously).

        Raises:
            ValueError: When a session with the same ID already
                exists.
        """
        async with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session already exists: {session_id}")

        # Storage layer
        repository = create_repository(
            self._config.file_store_type,
            self._config.file_store_path,
        )
        depot = SignalDepot(session_id, repository)
        channel = SignalChannel(session_id, depot)

        # Optionally override the voice
        perf_config: PerformerConfig = self._config.primary_performer
        if voice_name:
            perf_config = PerformerConfig(
                **{
                    **perf_config.model_dump(),
                    "voice_config_name": voice_name,
                }
            )

        # Performer
        performer = Performer.create(
            performer_name,
            perf_config,
            self._voice_registry,
        )

        # Scene (mutable session state)
        scene = Scene(
            session_id=session_id,
            max_iterations=max_iterations,
            max_budget_usd=max_budget_usd,
        )

        # Stage — optionally override workspace
        stage_config: StageConfig = self._config.stage
        if workspace_dir:
            stage_config = StageConfig(
                **{
                    **stage_config.model_dump(),
                    "workspace_dir": workspace_dir,
                }
            )
        stage = create_stage(stage_config)
        await stage.initialize()

        # Wire stage: execute runnable directives broadcasted on
        # the channel and broadcast the resulting report back.
        def on_directive(signal: object) -> None:
            if isinstance(signal, Directive) and signal.runnable:
                asyncio.create_task(  # noqa: RUF006
                    self._execute_and_broadcast(stage, channel, signal)
                )

        channel.subscribe(
            ChannelSubscriber.STAGE,
            on_directive,  # type: ignore[arg-type]
            "stage_executor",
        )

        # Director
        director = Director(
            session_id=session_id,
            performer=performer,
            channel=channel,
            scene=scene,
            on_state_change=on_state_change,
        )

        # Register session before starting to avoid a race window
        session = ActiveSession(
            session_id=session_id,
            director=director,
            channel=channel,
            stage=stage,
        )
        async with self._lock:
            self._sessions[session_id] = session

        # Launch execution in the background
        asyncio.create_task(director.start(task))  # noqa: RUF006

        logger.info(
            "session_created",
            session_id=session_id,
            performer=performer_name,
            task_preview=task[:100],
        )

        return scene

    # ------------------------------------------------------------------
    # Directive execution helper
    # ------------------------------------------------------------------

    async def _execute_and_broadcast(
        self,
        stage: Stage,
        channel: SignalChannel,
        directive: Directive,
    ) -> None:
        """Execute a directive on the stage and broadcast result.

        Args:
            stage: Execution stage to dispatch the directive to.
            channel: Channel on which to broadcast the report.
            directive: Runnable directive to execute.
        """
        report = await stage.dispatch(directive)
        channel.broadcast(report, SignalSource.ENVIRONMENT)

    # ------------------------------------------------------------------
    # Session access
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> ActiveSession | None:
        """Retrieve an active session by ID.

        Args:
            session_id: Session to look up.

        Returns:
            The ActiveSession or None if not found.
        """
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def send_message(
        self,
        session_id: str,
        content: str,
    ) -> Scene:
        """Send a user message to a running session.

        Args:
            session_id: Target session.
            content: User message text.

        Returns:
            The updated Scene after resuming.

        Raises:
            KeyError: When the session does not exist.
        """
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        return await session.director.resume(content)

    # ------------------------------------------------------------------
    # Session teardown
    # ------------------------------------------------------------------

    async def stop_session(self, session_id: str) -> None:
        """Stop a running session and release its resources.

        Args:
            session_id: Session to stop.
        """
        session = self.get_session(session_id)
        if session is None:
            return

        session.director.stop()
        await session.stage.teardown()
        session.channel.close()

        async with self._lock:
            self._sessions.pop(session_id, None)

        logger.info("session_stopped", session_id=session_id)

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_sessions(self) -> list[dict]:
        """Return summary dicts for all active sessions.

        Returns:
            List of dicts with session_id, state, iteration count,
            and creation timestamp.
        """
        return [
            {
                "session_id": sid,
                "state": (s.director.scene.current_state),
                "iterations": s.director.scene.iteration,
                "created_at": s.created_at,
            }
            for sid, s in self._sessions.items()
        ]
