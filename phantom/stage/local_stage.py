"""Local execution stage (runs in host process)."""

import asyncio
import os
import tempfile
from pathlib import Path

import structlog

from phantom.score.stage_config import StageConfig
from phantom.signal.report.filesystem import (
    FileReadReport,
    FileWriteReport,
)
from phantom.signal.report.terminal import (
    CommandOutputMetadata,
    CommandOutputReport,
)
from phantom.stage.base import Stage, StageStatus

logger = structlog.get_logger(__name__)


class LocalStage(Stage):
    """Executes directives on the local host filesystem.

    When ``config.workspace_dir`` is set the stage uses that
    directory; otherwise a fresh temporary directory is created
    and cleaned up in :meth:`teardown`.

    Args:
        config: Stage configuration.
    """

    def __init__(self, config: StageConfig) -> None:
        super().__init__(config)
        self._tmp_dir: tempfile.TemporaryDirectory | None = None
        if config.workspace_dir:
            self._workspace = Path(config.workspace_dir)
        else:
            self._tmp_dir = tempfile.TemporaryDirectory()
            self._workspace = Path(self._tmp_dir.name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create workspace directory and mark stage ready."""
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._working_dir = str(self._workspace)
        self._status = StageStatus.READY
        logger.info(
            "local_stage_ready",
            workspace=str(self._workspace),
        )

    async def teardown(self) -> None:
        """Mark stage closed and remove temporary workspace."""
        self._status = StageStatus.CLOSED
        if self._tmp_dir is not None:
            self._tmp_dir.cleanup()
        logger.info("local_stage_closed")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> CommandOutputReport:
        """Run a shell command via asyncio subprocess.

        Args:
            command: Shell command string to execute.
            cwd: Optional working directory; defaults to workspace.
            timeout_seconds: Abort after this many seconds.

        Returns:
            CommandOutputReport with combined stdout/stderr.
        """
        working_dir = cwd or str(self._workspace)

        logger.debug(
            "executing_command",
            command=command[:80],
            cwd=working_dir,
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=working_dir,
                env={**os.environ, **self._config.env_vars},
            )

            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            logger.debug(
                "command_complete",
                exit_code=exit_code,
                output_len=len(stdout),
            )

            return CommandOutputReport(
                content=stdout,
                command=command,
                metadata=CommandOutputMetadata(
                    exit_code=exit_code,
                    pid=proc.pid or -1,
                    working_dir=working_dir,
                ),
            )

        except TimeoutError:
            return CommandOutputReport(
                content=(f"Command timed out after {timeout_seconds:.0f}s"),
                command=command,
                metadata=CommandOutputMetadata(
                    exit_code=-1,
                    working_dir=working_dir,
                ),
            )
        except Exception as exc:
            logger.exception(
                "command_execution_error",
                command=command[:80],
                error=str(exc),
            )
            return CommandOutputReport(
                content=f"Execution error: {exc}",
                command=command,
                metadata=CommandOutputMetadata(exit_code=-1),
            )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    async def read_file(self, path: str) -> FileReadReport:
        """Read text content from the given path.

        Args:
            path: Absolute or workspace-relative file path.

        Returns:
            FileReadReport with file content or error message.
        """
        try:
            resolved = self._resolve_path(path)
        except ValueError as exc:
            return FileReadReport(
                content=str(exc),
                path=path,
            )
        try:
            content = Path(resolved).read_text(encoding="utf-8")
            return FileReadReport(content=content, path=path)
        except FileNotFoundError:
            return FileReadReport(
                content=f"File not found: {path}",
                path=path,
            )
        except Exception as exc:
            return FileReadReport(
                content=f"Error reading {path}: {exc}",
                path=path,
            )

    async def write_file(
        self,
        path: str,
        content: str,
    ) -> FileWriteReport:
        """Write text content to the given path.

        Parent directories are created automatically.

        Args:
            path: Absolute or workspace-relative destination.
            content: Text to write.

        Returns:
            FileWriteReport with byte count or error message.
        """
        try:
            resolved = self._resolve_path(path)
        except ValueError as exc:
            return FileWriteReport(
                content=str(exc),
                path=path,
            )
        try:
            target = Path(resolved)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            byte_count = len(content)
            return FileWriteReport(
                content=(f"Written {byte_count} bytes to {path}"),
                path=path,
            )
        except Exception as exc:
            return FileWriteReport(
                content=f"Error writing {path}: {exc}",
                path=path,
            )

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, path: str) -> str:
        """Resolve path inside the workspace, block traversal.

        Args:
            path: Raw path from a directive.

        Returns:
            Absolute real path guaranteed to be under workspace.

        Raises:
            ValueError: When the resolved path escapes the workspace.
        """
        if os.path.isabs(path):
            resolved = os.path.realpath(path)
        else:
            resolved = os.path.realpath(
                os.path.join(str(self._workspace), path)
            )

        workspace_real = os.path.realpath(str(self._workspace))
        if not resolved.startswith(workspace_real):
            raise ValueError(f"Path traversal detected: {path!r}")
        return resolved
