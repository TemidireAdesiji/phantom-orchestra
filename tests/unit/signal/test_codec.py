"""Tests for encode_signal / decode_signal codec."""

import pytest

from phantom.signal.base import SignalSource
from phantom.signal.codec import decode_signal, encode_signal
from phantom.signal.directive.control import (
    CompleteDirective,
    NoOpDirective,
)
from phantom.signal.directive.message import MessageDirective
from phantom.signal.directive.terminal import RunCommandDirective
from phantom.signal.report.fault import FaultReport
from phantom.signal.report.terminal import CommandOutputReport


def _stamp(sig, sid: int = 0, source=SignalSource.PERFORMER):
    """Attach minimal metadata so round-trip is meaningful."""
    sig.id = sid
    sig.source = source
    sig.timestamp = "2026-04-04T00:00:00+00:00"
    return sig


class TestEncodeDecodeRoundTrip:
    def test_run_command_directive_round_trip(self):
        orig = _stamp(RunCommandDirective(command="echo hello", blocking=True))
        data = encode_signal(orig)
        restored = decode_signal(data)

        assert isinstance(restored, RunCommandDirective)
        assert restored.command == "echo hello"
        assert restored.blocking is True
        assert restored.id == 0

    def test_command_output_report_round_trip(self):
        orig = _stamp(
            CommandOutputReport(content="stdout text", command="echo hi"),
            sid=1,
        )
        data = encode_signal(orig)
        restored = decode_signal(data)

        assert isinstance(restored, CommandOutputReport)
        assert restored.content == "stdout text"
        assert restored.command == "echo hi"

    def test_message_directive_round_trip(self):
        orig = _stamp(
            MessageDirective(
                content="Hello user",
                wait_for_response=True,
            ),
            sid=2,
        )
        data = encode_signal(orig)
        restored = decode_signal(data)

        assert isinstance(restored, MessageDirective)
        assert restored.content == "Hello user"
        assert restored.wait_for_response is True

    def test_complete_directive_round_trip(self):
        orig = _stamp(
            CompleteDirective(outputs={"result": "done"}),
            sid=3,
        )
        data = encode_signal(orig)
        restored = decode_signal(data)

        assert isinstance(restored, CompleteDirective)
        assert restored.outputs == {"result": "done"}

    def test_fault_report_round_trip(self):
        orig = _stamp(
            FaultReport(
                fault_id="EXEC_TIMEOUT",
                content="command timed out",
            ),
            sid=4,
        )
        data = encode_signal(orig)
        restored = decode_signal(data)

        assert isinstance(restored, FaultReport)
        assert restored.fault_id == "EXEC_TIMEOUT"
        assert restored.content == "command timed out"

    def test_no_op_directive_round_trip(self):
        orig = _stamp(NoOpDirective(), sid=5)
        data = encode_signal(orig)
        restored = decode_signal(data)
        assert isinstance(restored, NoOpDirective)


class TestDecodeSignalErrors:
    def test_decode_raises_value_error_for_unknown_directive_type(
        self,
    ):
        data = {
            "directive_type": "completely_unknown_action",
            "_id": 0,
            "_timestamp": "",
            "_source": None,
            "_cause": None,
        }
        with pytest.raises(ValueError, match="Unknown directive_type"):
            decode_signal(data)

    def test_decode_raises_value_error_for_unknown_report_type(
        self,
    ):
        data = {
            "report_type": "phantom_mystery_report",
            "_id": 0,
            "_timestamp": "",
            "_source": None,
            "_cause": None,
            "content": "",
        }
        with pytest.raises(ValueError, match="Unknown report_type"):
            decode_signal(data)

    def test_decode_falls_back_to_plain_signal_when_no_discriminator(
        self,
    ):
        from phantom.signal.base import Signal

        data = {
            "_id": 99,
            "_timestamp": "ts",
            "_source": None,
            "_cause": None,
        }
        result = decode_signal(data)
        assert isinstance(result, Signal)
        assert result.id == 99
