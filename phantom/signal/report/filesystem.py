"""Filesystem operation reports for PhantomOrchestra."""

from dataclasses import dataclass, field

from phantom.signal.report.base import Report

__all__ = ["FileEditReport", "FileReadReport", "FileWriteReport"]


@dataclass
class FileReadReport(Report):
    """Report returned after a file read operation.

    Attributes:
        path: Path of the file that was read.
        report_type: Fixed discriminator string.
    """

    path: str = ""
    report_type: str = field(default="file_read", init=True)

    @property
    def message(self) -> str:
        """Return a summary of the file read."""
        return f"Read file: {self.path} ({len(self.content)} chars)"


@dataclass
class FileWriteReport(Report):
    """Report returned after a file write operation.

    Attributes:
        path: Path of the file that was written.
        report_type: Fixed discriminator string.
    """

    path: str = ""
    report_type: str = field(default="file_write", init=True)

    @property
    def message(self) -> str:
        """Return a summary of the file write."""
        return f"Wrote file: {self.path} ({len(self.content)} chars)"


@dataclass
class FileEditReport(Report):
    """Report returned after a structured file edit operation.

    Attributes:
        path: Path of the file that was edited.
        report_type: Fixed discriminator string.
    """

    path: str = ""
    report_type: str = field(default="file_edit", init=True)

    @property
    def message(self) -> str:
        """Return a summary of the file edit."""
        return f"Edited file: {self.path}"
