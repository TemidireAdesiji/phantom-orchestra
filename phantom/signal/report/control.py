"""Control-flow and state reports for PhantomOrchestra."""

from dataclasses import dataclass, field
from enum import StrEnum

from phantom.signal.report.base import Report

__all__ = [
    "PerformerState",
    "RecallReport",
    "StateTransitionReport",
]


class PerformerState(StrEnum):
    """Lifecycle states of a performer session."""

    LOADING = "loading"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_INPUT = "awaiting_input"
    COMPLETE = "complete"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class StateTransitionReport(Report):
    """Report emitted whenever a performer changes lifecycle state.

    Attributes:
        previous_state: The state the performer transitioned *from*;
            ``None`` for the initial state assignment.
        current_state: The state the performer transitioned *to*.
        report_type: Fixed discriminator string.
    """

    previous_state: PerformerState | None = None
    current_state: PerformerState = PerformerState.LOADING
    report_type: str = field(default="state_transition", init=True)

    @property
    def message(self) -> str:
        """Return a human-readable state transition summary."""
        prev = (
            self.previous_state.value
            if self.previous_state is not None
            else "none"
        )
        return f"State: {prev} -> {self.current_state.value}"


@dataclass
class RecallReport(Report):
    """Report returning results of a memory recall query.

    Attributes:
        context_entries: List of retrieved memory entries as strings.
        report_type: Fixed discriminator string.
    """

    context_entries: list[str] = field(default_factory=list)
    report_type: str = field(default="recall", init=True)

    @property
    def message(self) -> str:
        """Return a summary of recall results."""
        n = len(self.context_entries)
        return f"Recalled {n} context entries."
