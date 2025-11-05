"""Serialisation and deserialisation codec for Signal objects.

Every concrete Signal subclass must register its discriminator
key(s) with this module so that ``decode_signal`` can reconstruct
the correct type from a plain dictionary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from phantom.signal.base import Signal
from phantom.signal.directive.base import DirectiveType
from phantom.signal.directive.control import (
    CompleteDirective,
    DelegateDirective,
    NoOpDirective,
    RecallDirective,
)
from phantom.signal.directive.filesystem import (
    EditFileDirective,
    ReadFileDirective,
    WriteFileDirective,
)
from phantom.signal.directive.message import (
    MessageDirective,
    SystemBootDirective,
)
from phantom.signal.directive.terminal import (
    RunCommandDirective,
    RunNotebookDirective,
)
from phantom.signal.report.control import (
    RecallReport,
    StateTransitionReport,
)
from phantom.signal.report.fault import FaultReport, NoOpReport
from phantom.signal.report.filesystem import (
    FileEditReport,
    FileReadReport,
    FileWriteReport,
)
from phantom.signal.report.terminal import (
    CommandOutputReport,
    NotebookOutputReport,
)

if TYPE_CHECKING:
    pass

__all__ = ["decode_signal", "encode_signal"]

# ------------------------------------------------------------------
# Dispatch registry
# ------------------------------------------------------------------

# Directives keyed by their directive_type value
_DIRECTIVE_REGISTRY: dict[str, type[Signal]] = {
    DirectiveType.RUN_COMMAND: RunCommandDirective,
    DirectiveType.RUN_NOTEBOOK: RunNotebookDirective,
    DirectiveType.READ_FILE: ReadFileDirective,
    DirectiveType.WRITE_FILE: WriteFileDirective,
    DirectiveType.EDIT_FILE: EditFileDirective,
    DirectiveType.SEND_MESSAGE: MessageDirective,
    DirectiveType.COMPLETE: CompleteDirective,
    DirectiveType.DELEGATE: DelegateDirective,
    DirectiveType.NO_OP: NoOpDirective,
    DirectiveType.RECALL: RecallDirective,
    "system_boot": SystemBootDirective,
}

# Reports keyed by their report_type value
_REPORT_REGISTRY: dict[str, type[Signal]] = {
    "command_output": CommandOutputReport,
    "notebook_output": NotebookOutputReport,
    "file_read": FileReadReport,
    "file_write": FileWriteReport,
    "file_edit": FileEditReport,
    "fault": FaultReport,
    "no_op": NoOpReport,
    "state_transition": StateTransitionReport,
    "recall": RecallReport,
}


def encode_signal(signal: Signal) -> dict[str, Any]:
    """Convert a Signal instance to a JSON-serialisable dictionary.

    The dictionary includes all dataclass fields along with private
    metadata fields (``_id``, ``_timestamp``, ``_source``, ``_cause``)
    and a ``_signal_class`` key for debugging.

    Args:
        signal: Any concrete Signal subclass instance.

    Returns:
        A flat dictionary suitable for ``json.dumps``.
    """
    return signal.to_dict()


def decode_signal(data: dict[str, Any]) -> Signal:
    """Reconstruct a Signal from a serialised dictionary.

    Dispatch is performed in the following order:

    1. Look up ``directive_type`` in the directive registry.
    2. Look up ``report_type`` in the report registry.
    3. Fall back to a bare :class:`~phantom.signal.base.Signal`.

    Args:
        data: Dictionary previously produced by ``encode_signal``.

    Returns:
        A fully reconstructed Signal subclass instance.

    Raises:
        ValueError: When the discriminator is present but unknown.
    """
    # Directive dispatch
    directive_type = data.get("directive_type")
    if directive_type is not None:
        cls = _DIRECTIVE_REGISTRY.get(directive_type)
        if cls is None:
            raise ValueError(f"Unknown directive_type: {directive_type!r}")
        return cls.from_dict(data)

    # Report dispatch
    report_type = data.get("report_type")
    if report_type is not None:
        cls = _REPORT_REGISTRY.get(report_type)
        if cls is None:
            raise ValueError(f"Unknown report_type: {report_type!r}")
        return cls.from_dict(data)

    # Fallback: plain Signal (metadata only)
    return Signal.from_dict(data)
