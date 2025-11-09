"""Signal module: event system for PhantomOrchestra.

Directives (actions) flow from performers to the stage.
Reports (observations) flow from the stage back to performers.
"""

from phantom.signal.base import Signal, SignalSource, SignalType
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.codec import decode_signal, encode_signal
from phantom.signal.depot import SignalDepot
from phantom.signal.directive import (
    CompleteDirective,
    DelegateDirective,
    Directive,
    DirectiveType,
    EditFileDirective,
    MessageDirective,
    NoOpDirective,
    ReadFileDirective,
    RecallDirective,
    RunCommandDirective,
    RunNotebookDirective,
    SystemBootDirective,
    WriteFileDirective,
)
from phantom.signal.report import (
    CommandOutputMetadata,
    CommandOutputReport,
    FaultReport,
    FileEditReport,
    FileReadReport,
    FileWriteReport,
    NoOpReport,
    NotebookOutputReport,
    PerformerState,
    RecallReport,
    Report,
    StateTransitionReport,
)

__all__ = [
    "ChannelSubscriber",
    "CommandOutputMetadata",
    "CommandOutputReport",
    "CompleteDirective",
    "DelegateDirective",
    "Directive",
    "DirectiveType",
    "EditFileDirective",
    "FaultReport",
    "FileEditReport",
    "FileReadReport",
    "FileWriteReport",
    "MessageDirective",
    "NoOpDirective",
    "NoOpReport",
    "NotebookOutputReport",
    "PerformerState",
    "ReadFileDirective",
    "RecallDirective",
    "RecallReport",
    "Report",
    "RunCommandDirective",
    "RunNotebookDirective",
    "Signal",
    "SignalChannel",
    "SignalDepot",
    "SignalSource",
    "SignalType",
    "StateTransitionReport",
    "SystemBootDirective",
    "WriteFileDirective",
    "decode_signal",
    "encode_signal",
]
