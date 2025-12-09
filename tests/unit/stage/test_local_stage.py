"""Tests for LocalStage (async)."""

import pytest

from phantom.score.stage_config import StageConfig
from phantom.signal.report.filesystem import (
    FileReadReport,
    FileWriteReport,
)
from phantom.signal.report.terminal import CommandOutputReport
from phantom.stage.base import StageStatus
from phantom.stage.local_stage import LocalStage

pytestmark = pytest.mark.asyncio


@pytest.fixture
def stage_config(tmp_path):
    """Return a StageConfig pointing to a temp workspace."""
    return StageConfig(
        stage_type="local",
        workspace_dir=str(tmp_path / "workspace"),
    )


@pytest.fixture
def stage(stage_config):
    """Return an uninitialised LocalStage."""
    return LocalStage(stage_config)


class TestLocalStageLifecycle:
    async def test_initialize_creates_workspace_directory(
        self, stage, tmp_path
    ):
        await stage.initialize()
        assert stage._workspace.exists()
        assert stage._workspace.is_dir()
        await stage.teardown()

    async def test_initialize_sets_status_to_ready(self, stage):
        await stage.initialize()
        assert stage.status == StageStatus.READY
        await stage.teardown()

    async def test_teardown_sets_status_to_closed(self, stage):
        await stage.initialize()
        await stage.teardown()
        assert stage.status == StageStatus.CLOSED

    async def test_context_manager_initializes_and_tears_down(
        self, stage_config
    ):
        stage = LocalStage(stage_config)
        async with stage as s:
            assert s.status == StageStatus.READY
        assert stage.status == StageStatus.CLOSED


class TestLocalStageExecuteCommand:
    async def test_execute_command_returns_command_output_report(self, stage):
        await stage.initialize()
        report = await stage.execute_command("echo hi")
        await stage.teardown()
        assert isinstance(report, CommandOutputReport)

    async def test_execute_command_captures_stdout(self, stage):
        await stage.initialize()
        report = await stage.execute_command("echo phantom")
        await stage.teardown()
        assert "phantom" in report.content

    async def test_execute_command_returns_zero_exit_code(self, stage):
        await stage.initialize()
        report = await stage.execute_command("true")
        await stage.teardown()
        assert report.metadata.exit_code == 0

    async def test_execute_command_returns_nonzero_exit_code(self, stage):
        await stage.initialize()
        report = await stage.execute_command("false")
        await stage.teardown()
        assert report.metadata.exit_code != 0

    async def test_execute_command_stores_command_string(self, stage):
        await stage.initialize()
        report = await stage.execute_command("echo stored")
        await stage.teardown()
        assert report.command == "echo stored"

    async def test_execute_command_timeout_returns_error_report(self, stage):
        await stage.initialize()
        report = await stage.execute_command("sleep 10", timeout_seconds=0.1)
        await stage.teardown()
        assert report.metadata.exit_code == -1
        assert "timed out" in report.content.lower()


class TestLocalStageFileIO:
    async def test_write_file_creates_file(self, stage):
        await stage.initialize()
        report = await stage.write_file("out.txt", "hello")
        await stage.teardown()
        assert isinstance(report, FileWriteReport)

    async def test_read_file_returns_written_content(self, stage):
        await stage.initialize()
        await stage.write_file("data.txt", "test content")
        report = await stage.read_file("data.txt")
        await stage.teardown()
        assert isinstance(report, FileReadReport)
        assert report.content == "test content"

    async def test_read_file_returns_error_message_for_missing(self, stage):
        await stage.initialize()
        report = await stage.read_file("does_not_exist.txt")
        await stage.teardown()
        assert isinstance(report, FileReadReport)
        assert (
            "not found" in report.content.lower()
            or "error" in report.content.lower()
        )

    async def test_write_file_creates_nested_directories(self, stage):
        await stage.initialize()
        await stage.write_file("a/b/c/nested.txt", "deep")
        report = await stage.read_file("a/b/c/nested.txt")
        await stage.teardown()
        assert report.content == "deep"
