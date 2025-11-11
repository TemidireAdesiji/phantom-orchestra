"""Base directive (action) types for PhantomOrchestra."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from phantom.signal.base import Signal

__all__ = ["Directive", "DirectiveType"]


class DirectiveType(StrEnum):
    """Enumeration of all recognised directive kinds."""

    RUN_COMMAND = "run_command"
    RUN_NOTEBOOK = "run_notebook"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    SEND_MESSAGE = "send_message"
    DELEGATE = "delegate"
    COMPLETE = "complete"
    RECALL = "recall"
    BROWSE = "browse"
    BROWSE_INTERACT = "browse_interact"
    NO_OP = "no_op"


@dataclass
class Directive(Signal):
    """Base class for all directives emitted by a performer.

    A directive represents an intent to perform an action.  Concrete
    subclasses set ``runnable = True`` when the stage is expected to
    execute them.

    Attributes:
        runnable: Class-level flag; ``True`` when the directive should
            be dispatched to a stage executor.
        thought: Optional chain-of-thought text from the performer.
    """

    runnable: ClassVar[bool] = False
    thought: str = ""

    @property
    def message(self) -> str:
        """Return a short summary of this directive."""
        return f"{self.__class__.__name__}(thought={self.thought[:40]!r})"
