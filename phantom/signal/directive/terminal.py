"""Terminal / notebook execution directives for PhantomOrchestra."""

from dataclasses import dataclass, field
from typing import ClassVar

from phantom.signal.directive.base import Directive, DirectiveType

__all__ = ["RunCommandDirective", "RunNotebookDirective"]


@dataclass
class RunCommandDirective(Directive):
    """Directive to execute a shell command in the stage terminal.

    Attributes:
        command: The shell command string to run.
        is_input: When ``True``, the command is treated as stdin input
            to a running interactive process rather than a new command.
        blocking: When ``True``, wait for the command to complete
            before proceeding.
        cwd: Optional working directory override for the command.
        hidden: When ``True``, suppress this directive from UI display.
        directive_type: Fixed discriminator string.
    """

    command: str = ""
    is_input: bool = False
    blocking: bool = False
    cwd: str | None = None
    hidden: bool = False
    directive_type: str = field(default=DirectiveType.RUN_COMMAND, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a short summary of the command."""
        return f"Run command: {self.command[:50]}"


@dataclass
class RunNotebookDirective(Directive):
    """Directive to execute code in a Jupyter notebook kernel.

    Attributes:
        code: Source code to execute in the kernel.
        include_context: Whether to inject prior cell outputs as
            context before executing ``code``.
        directive_type: Fixed discriminator string.
    """

    code: str = ""
    include_context: bool = True
    directive_type: str = field(default=DirectiveType.RUN_NOTEBOOK, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a short summary of the notebook cell."""
        return f"Run notebook cell: {self.code[:50]}"
