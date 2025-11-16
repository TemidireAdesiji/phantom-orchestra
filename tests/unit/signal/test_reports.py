"""Tests for report (observation) signal types."""

from phantom.signal.report.base import Report
from phantom.signal.report.control import (
    PerformerState,
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
    CommandOutputMetadata,
    CommandOutputReport,
)


class TestReport:
    def test_truncate_inserts_notice_and_keeps_head_and_tail(self):
        # truncate() replaces the middle with a "[... N chars truncated ...]"
        # notice; the result is longer than max_chars but shorter than original
        r = Report(content="hello world")
        out = r.truncate(5)
        assert "truncated" in out.content
        assert out.content.startswith("he")
        assert out.content.endswith("ld")
        assert len(out.content) < len(r.content) + 60

    def test_truncate_no_op_when_within_limit(self):
        r = Report(content="hi")
        out = r.truncate(100)
        assert out.content == "hi"

    def test_truncate_preserves_type(self):
        r = FaultReport(content="x" * 200, fault_id="e1")
        out = r.truncate(50)
        assert isinstance(out, FaultReport)


class TestCommandOutputReport:
    def test_short_content_not_truncated(self):
        r = CommandOutputReport(content="ok", command="echo ok")
        assert r.content == "ok"

    def test_long_content_is_truncated(self):
        big = "A" * 40_000
        r = CommandOutputReport(content=big, command="cmd")
        assert len(r.content) < 40_000
        assert "truncated" in r.content

    def test_metadata_defaults(self):
        r = CommandOutputReport(content="", command="ls")
        assert r.metadata.exit_code == -1
        assert r.metadata.pid == -1

    def test_metadata_set(self):
        meta = CommandOutputMetadata(exit_code=0, pid=1234, working_dir="/tmp")  # noqa: S108
        r = CommandOutputReport(content="out", command="ls", metadata=meta)
        assert r.metadata.exit_code == 0
        assert r.metadata.pid == 1234

    def test_report_type_field(self):
        r = CommandOutputReport(content="", command="x")
        assert r.report_type == "command_output"

    def test_hidden_defaults_false(self):
        r = CommandOutputReport(content="", command="x")
        assert r.hidden is False


class TestFileReports:
    def test_file_read_report(self):
        r = FileReadReport(content="data", path="/a/b.txt")
        assert r.path == "/a/b.txt"
        assert r.report_type == "file_read"

    def test_file_write_report(self):
        r = FileWriteReport(content="written", path="/out.txt")
        assert r.report_type == "file_write"

    def test_file_edit_report(self):
        r = FileEditReport(content="edited", path="/f.py")
        assert r.report_type == "file_edit"


class TestFaultReport:
    def test_fault_id_stored(self):
        r = FaultReport(content="boom", fault_id="err-42")
        assert r.fault_id == "err-42"
        assert r.report_type == "fault"

    def test_no_op_report_type(self):
        r = NoOpReport(content="")
        assert r.report_type == "no_op"


class TestControlReports:
    def test_state_transition_report(self):
        r = StateTransitionReport(
            content="running→complete",
            previous_state=PerformerState.RUNNING,
            current_state=PerformerState.COMPLETE,
        )
        assert r.previous_state == PerformerState.RUNNING
        assert r.current_state == PerformerState.COMPLETE
        assert r.report_type == "state_transition"

    def test_recall_report_entries(self):
        r = RecallReport(
            content="ctx",
            context_entries=["entry1", "entry2"],
        )
        assert len(r.context_entries) == 2
        assert r.report_type == "recall"
