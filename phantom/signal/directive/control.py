"""Control-flow directives for PhantomOrchestra."""

from dataclasses import dataclass, field
from typing import ClassVar

from phantom.signal.directive.base import Directive, DirectiveType

__all__ = [
    "CompleteDirective",
    "DelegateDirective",
    "NoOpDirective",
    "RecallDirective",
]


@dataclass
class CompleteDirective(Directive):
    """Directive signalling that the performer has finished its task.

    Attributes:
        outputs: Key-value map of named output artefacts produced by
            the performer (e.g. ``{"result": "...", "summary": "..."}``.
        directive_type: Fixed discriminator string.
    """

    outputs: dict[str, str] = field(default_factory=dict)
    directive_type: str = field(default=DirectiveType.COMPLETE, init=True)
    runnable: ClassVar[bool] = False

    @property
    def message(self) -> str:
        """Return a summary of task completion."""
        keys = ", ".join(self.outputs.keys())
        return f"Task complete. Outputs: [{keys}]"


@dataclass
class DelegateDirective(Directive):
    """Directive to hand off a sub-task to another performer.

    Attributes:
        performer_name: Logical name of the target performer.
        task: Natural-language description of the work to delegate.
        directive_type: Fixed discriminator string.
    """

    performer_name: str = ""
    task: str = ""
    directive_type: str = field(default=DirectiveType.DELEGATE, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a summary of the delegation directive."""
        return f"Delegate to {self.performer_name!r}: {self.task[:60]}"


@dataclass
class NoOpDirective(Directive):
    """Directive that intentionally performs no operation.

    Used when the performer needs to yield a turn without acting.

    Attributes:
        directive_type: Fixed discriminator string.
    """

    directive_type: str = field(default=DirectiveType.NO_OP, init=True)
    runnable: ClassVar[bool] = False

    @property
    def message(self) -> str:
        """Return a description of the no-op."""
        return "No operation."


@dataclass
class RecallDirective(Directive):
    """Directive to query the performer's long-term memory.

    Attributes:
        query: Natural-language query string.
        directive_type: Fixed discriminator string.
    """

    query: str = ""
    directive_type: str = field(default=DirectiveType.RECALL, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a summary of the recall directive."""
        return f"Recall: {self.query[:80]}"
