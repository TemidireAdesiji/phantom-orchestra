"""Filesystem directives for PhantomOrchestra."""

from dataclasses import dataclass, field
from typing import ClassVar

from phantom.signal.directive.base import Directive, DirectiveType

__all__ = [
    "EditFileDirective",
    "ReadFileDirective",
    "WriteFileDirective",
]


@dataclass
class ReadFileDirective(Directive):
    """Directive to read file contents from the stage filesystem.

    Attributes:
        path: Absolute or stage-relative path to the target file.
        start_line: First line to return (0-indexed, inclusive).
        end_line: Last line to return (0-indexed, exclusive);
            ``-1`` means read to end of file.
        directive_type: Fixed discriminator string.
    """

    path: str = ""
    start_line: int = 0
    end_line: int = -1
    directive_type: str = field(default=DirectiveType.READ_FILE, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a short summary of the read operation."""
        return f"Read file: {self.path}"


@dataclass
class WriteFileDirective(Directive):
    """Directive to write (create or overwrite) a file.

    Attributes:
        path: Absolute or stage-relative path for the target file.
        content: Full text content to write.
        directive_type: Fixed discriminator string.
    """

    path: str = ""
    content: str = ""
    directive_type: str = field(default=DirectiveType.WRITE_FILE, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a short summary of the write operation."""
        return f"Write file: {self.path} ({len(self.content)} chars)"


@dataclass
class EditFileDirective(Directive):
    """Directive to perform a structured edit on an existing file.

    Supports the str_replace_editor command set:
    ``view``, ``create``, ``str_replace``, ``insert``.

    Attributes:
        path: Absolute or stage-relative path to the target file.
        command: Edit sub-command (``view`` / ``create`` /
            ``str_replace`` / ``insert``).
        file_text: Full file content for ``create`` commands.
        old_str: Text to locate for ``str_replace`` commands.
        new_str: Replacement text for ``str_replace`` commands.
        insert_line: Line number after which to insert for
            ``insert`` commands.
        directive_type: Fixed discriminator string.
    """

    path: str = ""
    command: str = ""
    file_text: str | None = None
    old_str: str | None = None
    new_str: str | None = None
    insert_line: int | None = None
    directive_type: str = field(default=DirectiveType.EDIT_FILE, init=True)
    runnable: ClassVar[bool] = True

    @property
    def message(self) -> str:
        """Return a short summary of the edit operation."""
        return f"Edit file: {self.path} (command={self.command!r})"
