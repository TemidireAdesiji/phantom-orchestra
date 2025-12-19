"""Director: orchestrates a Performer through its execution loop."""

import asyncio
from collections.abc import Callable

import structlog

from phantom.performer.base import Performer
from phantom.performer.scene import Scene
from phantom.signal.base import Signal, SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.directive.base import Directive
from phantom.signal.directive.control import CompleteDirective
from phantom.signal.directive.message import MessageDirective
from phantom.signal.report.base import Report
from phantom.signal.report.control import (
    PerformerState,
    StateTransitionReport,
)
from phantom.signal.report.fault import FaultReport
from phantom.voice.message import Message

__all__ = ["Director"]

logger = structlog.get_logger(__name__)


class Director:
    """Controls a Performer through the task execution lifecycle.

    The Director subscribes to the SignalChannel to receive incoming
    Reports (observations from the Stage), feeds them back into the
    Scene, calls the Performer for the next Directive, and manages
    all state transitions and stopping conditions.

    The Director uses an asyncio.Lock internally; it must be used
    from within an asyncio event loop.  Signal callbacks arriving on
    the channel's thread pool are routed to async tasks.

    Args:
        session_id: Unique identifier for this session (used in logs).
        performer: The Performer instance to drive.
        channel: SignalChannel for bidirectional signal flow.
        scene: Mutable session state container.
        on_state_change: Optional callback invoked synchronously after
            each lifecycle state transition.
    """

    def __init__(
        self,
        session_id: str,
        performer: Performer,
        channel: SignalChannel,
        scene: Scene,
        on_state_change: (Callable[[PerformerState], None] | None) = None,
    ) -> None:
        self._session_id = session_id
        self._performer = performer
        self._channel = channel
        self._scene = scene
        self._on_state_change = on_state_change
        self._lock: asyncio.Lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

        channel.subscribe(
            ChannelSubscriber.DIRECTOR,
            self._handle_signal,
            "director_main",
        )

        logger.info(
            "director_initialized",
            session_id=session_id,
            performer=performer.name,
        )

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _handle_signal(self, signal: Signal) -> None:
        """Synchronous channel callback: schedule async processing.

        This method is called from the channel's thread pool so we
        schedule processing on the event loop thread rather than
        blocking.

        Args:
            signal: Incoming Signal from the channel.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._process_signal(signal), loop)

    async def _process_signal(self, signal: Signal) -> None:
        """Route an incoming signal to the appropriate handler.

        Args:
            signal: Signal to process.
        """
        async with self._lock:
            if isinstance(signal, Report):
                await self._handle_report(signal)
            elif isinstance(signal, Directive):
                await self._handle_directive(signal)

    async def _handle_report(self, report: Report) -> None:
        """Process an observation: update scene, then step performer.

        Appends the report content as a user message to the
        conversation history and triggers the next decision step if
        the performer is still running.

        Args:
            report: Incoming Report signal.
        """
        if report.content:
            self._scene.history.append(
                Message.user(f"[Observation]\n{report.content}")
            )

        self._scene.reports.append(report)

        if self._scene.current_state == PerformerState.RUNNING:
            await self._step()

    async def _handle_directive(self, directive: Directive) -> None:
        """Process an incoming directive (from performer or user).

        MessageDirectives that wait for a response trigger a state
        transition to AWAITING_INPUT.

        Args:
            directive: Incoming Directive signal.
        """
        self._scene.directives.append(directive)

        if (
            isinstance(directive, MessageDirective)
            and directive.wait_for_response
        ):
            await self._transition_to(PerformerState.AWAITING_INPUT)

    # ------------------------------------------------------------------
    # Execution step
    # ------------------------------------------------------------------

    async def _step(self) -> None:
        """Execute one performer decision step.

        Increments the iteration counter, calls the Performer, emits
        the resulting Directive onto the channel, and handles terminal
        conditions.
        """
        if self._scene.should_stop:
            await self._finalize()
            return

        self._scene.iteration += 1

        logger.info(
            "performer_step",
            session_id=self._session_id,
            iteration=self._scene.iteration,
            state=self._scene.current_state.value,
        )

        try:
            directive = self._performer.decide(self._scene)
        except Exception as exc:
            logger.exception(
                "performer_decide_error",
                session_id=self._session_id,
                error=str(exc),
            )
            fault = FaultReport(
                content=f"Performer error: {exc}",
                fault_id="performer_decide_error",
            )
            self._channel.broadcast(fault, SignalSource.ENVIRONMENT)
            await self._transition_to(PerformerState.FAILED)
            return

        if isinstance(directive, CompleteDirective):
            self._scene.outputs = directive.outputs
            await self._finalize()
            return

        self._channel.broadcast(directive, SignalSource.PERFORMER)

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    async def _finalize(self) -> None:
        """Mark the session complete and clean up.

        Chooses between COMPLETE and FAILED based on scene state,
        transitions to that terminal state, and marks the performer
        as complete.
        """
        if self._scene.current_state == PerformerState.FAILED:
            final_state = PerformerState.FAILED
        else:
            final_state = PerformerState.COMPLETE

        await self._transition_to(final_state)
        self._performer.complete = True

        logger.info(
            "session_complete",
            session_id=self._session_id,
            final_state=final_state.value,
            iterations=self._scene.iteration,
            output_keys=list(self._scene.outputs.keys()),
            budget_spent_usd=round(self._scene.budget_spent_usd, 6),
        )

    async def _transition_to(self, state: PerformerState) -> None:
        """Emit a StateTransitionReport and notify the callback.

        Args:
            state: Target lifecycle state.
        """
        previous = self._scene.current_state
        self._scene.current_state = state

        report = StateTransitionReport(
            content=(f"State changed: {previous.value} -> {state.value}"),
            previous_state=previous,
            current_state=state,
        )
        self._channel.broadcast(report, SignalSource.ENVIRONMENT)

        if self._on_state_change is not None:
            self._on_state_change(state)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def start(self, initial_task: str) -> Scene:
        """Begin execution with an initial task description.

        Captures the running event loop, transitions to RUNNING,
        appends the task as the first user message, then triggers the
        first decision step.

        Args:
            initial_task: Natural-language description of the task.

        Returns:
            The session Scene (updated in place throughout execution).
        """
        self._loop = asyncio.get_running_loop()
        await self._transition_to(PerformerState.RUNNING)
        self._scene.history.append(Message.user(initial_task))
        await self._step()
        return self._scene

    async def resume(self, user_message: str) -> Scene:
        """Resume a paused session with new user input.

        Appends the user message to history, transitions back to
        RUNNING, and triggers the next step.

        Args:
            user_message: The user's reply or follow-up instruction.

        Returns:
            The updated session Scene.
        """
        self._loop = asyncio.get_running_loop()
        self._scene.history.append(Message.user(user_message))
        await self._transition_to(PerformerState.RUNNING)
        await self._step()
        return self._scene

    def stop(self) -> None:
        """Immediately halt execution by scheduling a STOPPED state.

        Safe to call from synchronous contexts.  Marks the performer
        complete to prevent further steps.
        """
        loop = self._loop
        if loop is not None and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._transition_to(PerformerState.STOPPED),
                loop,
            )
        self._performer.complete = True

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def scene(self) -> Scene:
        """The current session Scene."""
        return self._scene

    @property
    def is_complete(self) -> bool:
        """True when the performer has finished."""
        return self._performer.complete
