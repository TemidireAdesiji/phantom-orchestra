"""Abstract runtime stage for executing performer directives."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

import structlog

from phantom.score.stage_config import StageConfig
from phantom.signal.directive.base import Directive
from phantom.signal.directive.filesystem import (
    EditFileDirective,
    ReadFileDirective,
    WriteFileDirective,
)
from phantom.signal.directive.terminal import (
    RunCommandDirective,
    RunNotebookDirective,
)
from phantom.signal.report.base import Report
from phantom.signal.report.fault import FaultReport
from phantom.signal.report.filesystem import (
    FileEditReport,
    FileReadReport,
    FileWriteReport,
)
from phantom.signal.report.terminal import (
    CommandOutputReport,
)

logger = structlog.get_logger(__name__)


class StageStatus(StrEnum):
    """Lifecycle status of an execution stage."""

    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    FAILED = "failed"
    CLOSED = "closed"


class Stage(ABC):
    """Abstract execution environment for directives.

    Subclasses implement the concrete execution layer — local
    filesystem, Docker container, or remote sandbox — while this
    base class provides the dispatch logic and context-manager
    protocol.

    Args:
        config: Stage configuration controlling isolation,
            resources, and workspace layout.
    """

    def __init__(self, config: StageConfig) -> None:
        self._config = config
        self._status = StageStatus.INITIALIZING
        self._working_dir: str = config.workspace_dir or "/workspace"

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare the execution environment."""

    @abstractmethod
    async def teardown(self) -> None:
        """Release all resources."""

    @abstractmethod
    async def execute_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> CommandOutputReport:
        """Run a shell command and return its output.

        Args:
            command: Shell command string to execute.
            cwd: Optional working directory override.
            timeout_seconds: Maximum execution time before
                the command is aborted.

        Returns:
            A CommandOutputReport with stdout/stderr and exit code.
        """

    @abstractmethod
    async def read_file(self, path: str) -> FileReadReport:
        """Read file contents from the stage filesystem.

        Args:
            path: Path of the file to read.

        Returns:
            A FileReadReport containing the file text.
        """

    @abstractmethod
    async def write_file(
        self,
        path: str,
        content: str,
    ) -> FileWriteReport:
        """Write content to a file (create or overwrite).

        Args:
            path: Destination path for the file.
            content: Full text content to write.

        Returns:
            A FileWriteReport confirming the write.
        """

    # ------------------------------------------------------------------
    # Directive dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, directive: Directive) -> Report:
        """Dispatch a directive to the appropriate executor.

        Routes the directive to ``execute_command``,
        ``read_file``, ``write_file``, or ``_apply_file_edit``
        based on the directive type.  Returns a FaultReport for
        unrecognised directive types.

        Args:
            directive: The directive to execute.

        Returns:
            A Report subclass with the execution result.
        """
        if isinstance(directive, RunCommandDirective):
            return await self.execute_command(
                command=directive.command,
                cwd=directive.cwd,
            )
        if isinstance(directive, ReadFileDirective):
            return await self.read_file(directive.path)
        if isinstance(directive, WriteFileDirective):
            return await self.write_file(directive.path, directive.content)
        if isinstance(directive, EditFileDirective):
            return await self._apply_file_edit(directive)
        if isinstance(directive, RunNotebookDirective):
            return await self.execute_command(
                command=f"python3 -c {directive.code!r}",
            )
        return FaultReport(
            content=(
                f"Unsupported directive type: {type(directive).__name__}"
            ),
            fault_id="unsupported_directive",
        )

    async def _apply_file_edit(
        self,
        directive: EditFileDirective,
    ) -> FileEditReport:
        """Apply a structured edit directive to a file.

        Handles the ``create`` and ``str_replace`` sub-commands.
        Unknown commands produce a no-error report with a
        descriptive message.

        Args:
            directive: The EditFileDirective to apply.

        Returns:
            A FileEditReport describing the outcome.
        """
        if directive.command == "create" and directive.file_text:
            await self.write_file(directive.path, directive.file_text)
            return FileEditReport(
                content=f"Created {directive.path}",
                path=directive.path,
            )

        if directive.command == "str_replace":
            read_result = await self.read_file(directive.path)
            old = directive.old_str or ""
            if old not in read_result.content:
                return FileEditReport(
                    content=(f"String not found in {directive.path}"),
                    path=directive.path,
                )
            new_content = read_result.content.replace(
                old,
                directive.new_str or "",
                1,
            )
            await self.write_file(directive.path, new_content)
            return FileEditReport(
                content=f"Edited {directive.path}",
                path=directive.path,
            )

        return FileEditReport(
            content=(f"Unknown edit command: {directive.command}"),
            path=directive.path,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def status(self) -> StageStatus:
        """Current lifecycle status of this stage."""
        return self._status

    @property
    def working_dir(self) -> str:
        """Absolute path of the active working directory."""
        return self._working_dir

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "Stage":
        """Initialize the stage and return self."""
        await self.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Tear down the stage on context exit."""
        await self.teardown()
