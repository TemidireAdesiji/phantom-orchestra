"""Tests for directive (action) signal types."""

from phantom.signal.directive.base import DirectiveType
from phantom.signal.directive.control import (
    CompleteDirective,
    DelegateDirective,
    NoOpDirective,
    RecallDirective,
)
from phantom.signal.directive.filesystem import (
    EditFileDirective,
    ReadFileDirective,
    WriteFileDirective,
)
from phantom.signal.directive.message import (
    MessageDirective,
    SystemBootDirective,
)
from phantom.signal.directive.terminal import (
    RunCommandDirective,
    RunNotebookDirective,
)


class TestRunCommandDirective:
    def test_defaults(self):
        d = RunCommandDirective(command="ls")
        assert d.command == "ls"
        assert d.is_input is False
        assert d.blocking is False
        assert d.cwd is None
        assert d.hidden is False
        assert d.directive_type == DirectiveType.RUN_COMMAND
        assert d.runnable is True

    def test_message_property(self):
        d = RunCommandDirective(command="echo hello")
        assert "echo hello" in d.message


class TestRunNotebookDirective:
    def test_defaults(self):
        d = RunNotebookDirective(code="print(1)")
        assert d.code == "print(1)"
        assert d.include_context is True
        assert d.directive_type == DirectiveType.RUN_NOTEBOOK
        assert d.runnable is True

    def test_message_property(self):
        d = RunNotebookDirective(code="x = 1")
        assert "x = 1" in d.message


class TestFileDirectives:
    def test_read_file_directive(self):
        d = ReadFileDirective(path="/a/b.py")
        assert d.path == "/a/b.py"
        assert d.start_line == 0
        assert d.end_line == -1
        assert d.directive_type == DirectiveType.READ_FILE
        assert d.runnable is True

    def test_write_file_directive(self):
        d = WriteFileDirective(path="/out.txt", content="hello")
        assert d.content == "hello"
        assert d.directive_type == DirectiveType.WRITE_FILE
        assert d.runnable is True

    def test_edit_file_directive_str_replace(self):
        d = EditFileDirective(
            path="/f.py",
            command="str_replace",
            old_str="foo",
            new_str="bar",
        )
        assert d.old_str == "foo"
        assert d.new_str == "bar"
        assert d.directive_type == DirectiveType.EDIT_FILE
        assert d.runnable is True


class TestMessageDirectives:
    def test_message_directive_defaults(self):
        d = MessageDirective(content="hi")
        assert d.content == "hi"
        assert d.wait_for_response is False
        assert d.directive_type == DirectiveType.SEND_MESSAGE

    def test_message_directive_message_property(self):
        d = MessageDirective(content="hello world")
        assert "hello world" in d.message

    def test_system_boot_directive(self):
        d = SystemBootDirective(content="system prompt text")
        assert d.content == "system prompt text"
        assert d.directive_type == "system_boot"


class TestControlDirectives:
    def test_complete_directive(self):
        d = CompleteDirective(outputs={"result": "done"})
        assert d.outputs["result"] == "done"
        assert d.directive_type == DirectiveType.COMPLETE

    def test_complete_directive_not_runnable(self):
        assert CompleteDirective.runnable is False

    def test_delegate_directive(self):
        d = DelegateDirective(performer_name="Audit", task="run checks")
        assert d.performer_name == "Audit"
        assert d.directive_type == DirectiveType.DELEGATE

    def test_no_op_directive(self):
        d = NoOpDirective()
        assert d.directive_type == DirectiveType.NO_OP

    def test_recall_directive(self):
        d = RecallDirective(query="previous errors")
        assert d.query == "previous errors"
        assert d.directive_type == DirectiveType.RECALL
        assert d.runnable is True
