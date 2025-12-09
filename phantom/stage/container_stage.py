"""Docker container-based execution stage."""

import asyncio
import shlex
import uuid
from base64 import b64encode

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


class ContainerStage(Stage):
    """Executes directives inside a Docker container.

    Each session gets an isolated container.  Commands run via
    ``docker exec``, files are read/written via exec cat/tee.

    Args:
        config: Stage configuration controlling the image,
            resource limits, and network policy.
    """

    def __init__(self, config: StageConfig) -> None:
        super().__init__(config)
        self._container_id: str | None = None
        self._container_name = f"phantom-stage-{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Pull image and start container in detached mode."""
        image = self._config.container_image

        logger.info(
            "starting_container",
            image=image,
            name=self._container_name,
        )

        try:
            cmd = [
                "docker",
                "run",
                "--detach",
                "--name",
                self._container_name,
                "--memory",
                f"{self._config.max_memory_mb}m",
            ]

            if not self._config.use_host_network:
                cmd.extend(["--network", "none"])

            for env_key, env_val in self._config.env_vars.items():
                cmd.extend(["-e", f"{env_key}={env_val}"])

            for volume in self._config.mount_volumes:
                cmd.extend(["-v", volume])

            cmd.extend([image, "sleep", "infinity"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error = stderr.decode().strip()
                raise RuntimeError(f"Failed to start container: {error}")

            self._container_id = stdout.decode().strip()[:12]
            self._status = StageStatus.READY

            # Ensure workspace directory exists inside container
            await self.execute_command(
                f"mkdir -p {shlex.quote(self._working_dir)}"
            )

            logger.info(
                "container_ready",
                container_id=self._container_id,
                name=self._container_name,
            )

        except Exception as exc:
            self._status = StageStatus.FAILED
            logger.exception(
                "container_initialization_failed",
                error=str(exc),
            )
            raise

    async def teardown(self) -> None:
        """Stop and remove the container."""
        if not self._container_name:
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "rm",
                "-f",
                self._container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            logger.info(
                "container_removed",
                name=self._container_name,
            )
        except Exception as exc:
            logger.warning(
                "container_removal_failed",
                name=self._container_name,
                error=str(exc),
            )
        finally:
            self._status = StageStatus.CLOSED

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> CommandOutputReport:
        """Run a shell command inside the container via docker exec.

        Args:
            command: Shell command string to execute.
            cwd: Optional working directory; defaults to workspace.
            timeout_seconds: Abort after this many seconds.

        Returns:
            CommandOutputReport with combined stdout/stderr.
        """
        working_dir = cwd or self._working_dir

        exec_cmd = [
            "docker",
            "exec",
            "--workdir",
            working_dir,
            self._container_name,
            "bash",
            "-c",
            command,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")

            return CommandOutputReport(
                content=stdout,
                command=command,
                metadata=CommandOutputMetadata(
                    exit_code=proc.returncode or 0,
                    working_dir=working_dir,
                ),
            )

        except TimeoutError:
            return CommandOutputReport(
                content=(f"Command timed out after {timeout_seconds:.0f}s"),
                command=command,
                metadata=CommandOutputMetadata(exit_code=-1),
            )
        except Exception as exc:
            logger.exception(
                "container_command_error",
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
        """Read file content from inside the container.

        Args:
            path: Absolute path inside the container.

        Returns:
            FileReadReport with file content or error message.
        """
        result = await self.execute_command(f"cat {shlex.quote(path)}")
        return FileReadReport(
            content=result.content,
            path=path,
        )

    async def write_file(
        self,
        path: str,
        content: str,
    ) -> FileWriteReport:
        """Write text content to a file inside the container.

        Content is base64-encoded to safely handle special
        characters and newlines in the shell pipeline.

        Args:
            path: Absolute destination path inside the container.
            content: Text to write.

        Returns:
            FileWriteReport confirming the write.
        """
        encoded = b64encode(content.encode("utf-8")).decode("ascii")
        # Ensure parent directory exists, then decode and write
        parent = shlex.quote(str(__import__("pathlib").Path(path).parent))
        dest = shlex.quote(path)
        cmd = (
            f"mkdir -p {parent} && "
            f"echo {shlex.quote(encoded)} | base64 -d > {dest}"
        )
        await self.execute_command(cmd)
        return FileWriteReport(
            content=f"Written to {path}",
            path=path,
        )
