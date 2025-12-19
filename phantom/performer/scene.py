"""Scene: agent state container for a PhantomOrchestra session."""

from dataclasses import dataclass, field
from typing import Any

from phantom.signal.directive.base import Directive
from phantom.signal.report.base import Report
from phantom.signal.report.control import PerformerState
from phantom.voice.message import Message, UsageMetrics

__all__ = ["Scene"]


@dataclass
class Scene:
    """Captures all mutable state for an active performer session.

    A Scene travels through the Director loop: directives and reports
    are appended as the session progresses, the history list grows
    with each LLM turn, and iteration/budget counters are incremented.

    Attributes:
        session_id: Unique identifier for this session.
        history: Ordered conversation messages for LLM context.
        directives: All directives emitted during this session.
        reports: All reports received during this session.
        iteration: Number of completed performer decision steps.
        max_iterations: Hard stop on iteration count.
        current_state: Current lifecycle state of the performer.
        budget_spent_usd: Accumulated LLM cost for the session.
        max_budget_usd: Optional spending cap in US dollars.
        outputs: Named string outputs produced by the performer.
    """

    session_id: str

    # Conversation history for LLM context
    history: list[Message] = field(default_factory=list)

    # All signals emitted this session
    directives: list[Directive] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)

    # Execution tracking
    iteration: int = 0
    max_iterations: int = 100
    current_state: PerformerState = PerformerState.LOADING

    # Budget tracking
    budget_spent_usd: float = 0.0
    max_budget_usd: float | None = None

    # Result outputs
    outputs: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Computed stop conditions
    # ------------------------------------------------------------------

    @property
    def budget_exceeded(self) -> bool:
        """True when spending cap has been reached or exceeded."""
        if self.max_budget_usd is None:
            return False
        return self.budget_spent_usd >= self.max_budget_usd

    @property
    def iterations_exceeded(self) -> bool:
        """True when the iteration limit has been reached."""
        return self.iteration >= self.max_iterations

    @property
    def should_stop(self) -> bool:
        """True when the session should terminate on its next check.

        Combines all stopping conditions: budget, iteration cap, and
        terminal lifecycle states.
        """
        return (
            self.iterations_exceeded
            or self.budget_exceeded
            or self.current_state
            in (
                PerformerState.COMPLETE,
                PerformerState.FAILED,
                PerformerState.STOPPED,
            )
        )

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_user_message(self, content: str) -> None:
        """Append a user message to the conversation history.

        Args:
            content: Text of the user message.
        """
        self.history.append(Message.user(content))

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant message to the conversation history.

        Args:
            content: Text of the assistant message.
        """
        self.history.append(Message.assistant(content=content))

    def update_metrics(self, metrics: UsageMetrics) -> None:
        """Incorporate LLM usage from one completion into totals.

        The accumulated cost is added to ``budget_spent_usd`` so that
        the budget guard can fire on the next ``should_stop`` check.

        Args:
            metrics: UsageMetrics snapshot from VoiceProvider.
        """
        self.budget_spent_usd += metrics.cost_usd

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_summary(self) -> dict[str, Any]:
        """Return a JSON-serialisable state summary.

        Returns:
            Dict with scalar fields; lists are represented by counts
            rather than full contents to keep the summary compact.
        """
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "history_length": len(self.history),
            "directive_count": len(self.directives),
            "report_count": len(self.reports),
            "budget_spent_usd": round(self.budget_spent_usd, 6),
            "max_budget_usd": self.max_budget_usd,
            "budget_exceeded": self.budget_exceeded,
            "iterations_exceeded": self.iterations_exceeded,
            "should_stop": self.should_stop,
            "output_keys": list(self.outputs.keys()),
        }
