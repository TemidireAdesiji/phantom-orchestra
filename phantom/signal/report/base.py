"""Base report (observation) class for PhantomOrchestra."""

import dataclasses
from dataclasses import dataclass

from phantom.signal.base import Signal

__all__ = ["Report"]


@dataclass
class Report(Signal):
    """Base class for all reports (observations) flowing to performers.

    A report carries a ``content`` string that represents the textual
    result of an action.  Long content is typically truncated before
    being forwarded to the language model to avoid exceeding context
    limits.

    Attributes:
        content: Primary text payload of the observation.
    """

    content: str = ""

    @property
    def message(self) -> str:
        """Return first 100 characters of content as a summary."""
        return self.content[:100]

    def truncate(self, max_chars: int) -> "Report":
        """Return a shallow copy of this report with truncated content.

        When ``content`` exceeds ``max_chars``, the middle portion is
        replaced with a truncation notice indicating the number of
        omitted characters.

        Args:
            max_chars: Maximum number of characters to retain.

        Returns:
            A new Report instance with the same fields but potentially
            shorter ``content``.
        """
        if len(self.content) <= max_chars:
            return dataclasses.replace(self)

        half = max_chars // 2
        omitted = len(self.content) - max_chars
        notice = f"\n[... {omitted} chars truncated ...]\n"
        truncated = self.content[:half] + notice + self.content[-half:]
        copy = dataclasses.replace(self, content=truncated)
        # Preserve metadata
        copy._id = self._id
        copy._timestamp = self._timestamp
        copy._source = self._source
        copy._cause = self._cause
        return copy
