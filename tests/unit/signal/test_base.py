"""Tests for the Signal base class."""

from dataclasses import dataclass

from phantom.signal.base import Signal, SignalSource


# Minimal concrete subclass for testing the abstract base
@dataclass
class _ConcreteSignal(Signal):
    """Concrete Signal used only in tests."""

    label: str = ""


class TestSignalDefaults:
    def test_signal_starts_with_invalid_id(self):
        sig = _ConcreteSignal()
        assert sig.id == Signal.INVALID_ID
        assert sig.id == -1

    def test_signal_id_is_set_via_setter(self):
        sig = _ConcreteSignal()
        sig.id = 42
        assert sig.id == 42

    def test_signal_timestamp_is_empty_by_default(self):
        sig = _ConcreteSignal()
        assert sig.timestamp == ""

    def test_timestamp_setter_stores_iso_string(self):
        sig = _ConcreteSignal()
        iso = Signal._now_utc()
        sig.timestamp = iso
        assert sig.timestamp == iso
        # Basic ISO-8601 check: contains "T" and "+"
        assert "T" in iso

    def test_source_is_none_by_default(self):
        sig = _ConcreteSignal()
        assert sig.source is None

    def test_source_setter_and_getter(self):
        sig = _ConcreteSignal()
        sig.source = SignalSource.PERFORMER
        assert sig.source == SignalSource.PERFORMER

    def test_cause_is_none_by_default(self):
        sig = _ConcreteSignal()
        assert sig.cause is None

    def test_cause_setter_and_getter(self):
        sig = _ConcreteSignal()
        sig.cause = 7
        assert sig.cause == 7


class TestSignalToDict:
    def test_to_dict_returns_dict(self):
        sig = _ConcreteSignal(label="hello")
        result = sig.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_metadata_keys(self):
        sig = _ConcreteSignal(label="x")
        sig.id = 3
        sig.source = SignalSource.USER
        result = sig.to_dict()
        assert "_id" in result
        assert "_timestamp" in result
        assert "_source" in result
        assert "_cause" in result
        assert "_signal_class" in result

    def test_to_dict_metadata_values(self):
        sig = _ConcreteSignal(label="y")
        sig.id = 5
        sig.source = SignalSource.ENVIRONMENT
        sig.cause = 2
        result = sig.to_dict()
        assert result["_id"] == 5
        assert result["_source"] == "environment"
        assert result["_cause"] == 2

    def test_to_dict_includes_public_fields(self):
        sig = _ConcreteSignal(label="test-label")
        result = sig.to_dict()
        assert result["label"] == "test-label"

    def test_to_dict_signal_class_name(self):
        sig = _ConcreteSignal()
        result = sig.to_dict()
        assert result["_signal_class"] == "_ConcreteSignal"


class TestSignalFromDict:
    def test_from_dict_reconstructs_label(self):
        sig = _ConcreteSignal(label="round-trip")
        sig.id = 10
        sig.source = SignalSource.PERFORMER
        sig.cause = 3
        data = sig.to_dict()

        restored = _ConcreteSignal.from_dict(data)
        assert restored.label == "round-trip"

    def test_from_dict_restores_metadata(self):
        sig = _ConcreteSignal(label="meta")
        sig.id = 99
        sig.source = SignalSource.USER
        sig.cause = 5
        data = sig.to_dict()

        restored = _ConcreteSignal.from_dict(data)
        assert restored.id == 99
        assert restored.source == SignalSource.USER
        assert restored.cause == 5

    def test_from_dict_handles_missing_source(self):
        data = {
            "_id": 1,
            "_timestamp": "",
            "_source": None,
            "_cause": None,
            "label": "no-source",
        }
        restored = _ConcreteSignal.from_dict(data)
        assert restored.source is None

    def test_from_dict_defaults_id_when_absent(self):
        data = {"label": "bare"}
        restored = _ConcreteSignal.from_dict(data)
        assert restored.id == Signal.INVALID_ID


class TestSignalMessage:
    def test_message_includes_class_name_and_id(self):
        sig = _ConcreteSignal()
        sig.id = 7
        assert "_ConcreteSignal" in sig.message
        assert "7" in sig.message
