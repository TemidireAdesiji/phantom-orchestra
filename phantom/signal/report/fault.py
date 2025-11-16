"""Fault and no-op reports for PhantomOrchestra."""

from dataclasses import dataclass, field

from phantom.signal.report.base import Report

__all__ = ["FaultReport", "NoOpReport"]


@dataclass
class FaultReport(Report):
    """Report indicating that an error or fault occurred.

    Attributes:
        fault_id: A short machine-readable fault identifier
            (e.g. ``"EXEC_TIMEOUT"`` or ``"PERMISSION_DENIED"``).
        content: Human-readable description of the fault.
        report_type: Fixed discriminator string.
    """

    fault_id: str = ""
    report_type: str = field(default="fault", init=True)

    @property
    def message(self) -> str:
        """Return a summary of the fault."""
        return f"Fault [{self.fault_id}]: {self.content[:80]}"


@dataclass
class NoOpReport(Report):
    """Report returned for a no-op directive.

    Attributes:
        report_type: Fixed discriminator string.
    """

    report_type: str = field(default="no_op", init=True)

    @property
    def message(self) -> str:
        """Return a description of the no-op."""
        return "No operation performed."
