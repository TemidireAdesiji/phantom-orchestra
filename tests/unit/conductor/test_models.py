"""Tests for Conductor Pydantic models."""

import pytest
from pydantic import ValidationError

from phantom.conductor.models import (
    CreateSessionRequest,
    HealthResponse,
    MessageRequest,
    SessionResponse,
)
from phantom.signal.report.control import PerformerState


class TestCreateSessionRequest:
    def test_valid_task_field(self):
        req = CreateSessionRequest(task="Do something useful.")
        assert req.task == "Do something useful."

    def test_default_performer_name(self):
        req = CreateSessionRequest(task="task")
        assert req.performer_name == "default"

    def test_default_max_iterations(self):
        req = CreateSessionRequest(task="task")
        assert req.max_iterations == 100

    def test_default_max_budget_is_none(self):
        req = CreateSessionRequest(task="task")
        assert req.max_budget_usd is None

    def test_empty_task_raises_validation_error(self):
        with pytest.raises(ValidationError):
            CreateSessionRequest(task="")

    def test_task_exceeding_max_length_raises_error(self):
        with pytest.raises(ValidationError):
            CreateSessionRequest(task="x" * 10_001)

    def test_max_iterations_below_one_raises_error(self):
        with pytest.raises(ValidationError):
            CreateSessionRequest(task="t", max_iterations=0)

    def test_max_iterations_above_500_raises_error(self):
        with pytest.raises(ValidationError):
            CreateSessionRequest(task="t", max_iterations=501)

    def test_custom_voice_name(self):
        req = CreateSessionRequest(task="t", voice_name="gpt-4o-provider")
        assert req.voice_name == "gpt-4o-provider"

    def test_custom_workspace_dir(self):
        req = CreateSessionRequest(
            task="t",
            workspace_dir="/tmp/ws",  # noqa: S108
        )
        assert req.workspace_dir == "/tmp/ws"  # noqa: S108


class TestSessionResponse:
    def _make(self, **kwargs):
        defaults = {
            "session_id": "sess-1",
            "state": PerformerState.RUNNING,
            "iterations": 3,
            "budget_spent_usd": 0.05,
            "outputs": {},
        }
        defaults.update(kwargs)
        return SessionResponse(**defaults)

    def test_session_response_serialises_correctly(self):
        resp = self._make()
        d = resp.model_dump()
        assert d["session_id"] == "sess-1"
        assert d["iterations"] == 3
        assert d["budget_spent_usd"] == pytest.approx(0.05)

    def test_session_response_state_is_performer_state(self):
        resp = self._make(state=PerformerState.COMPLETE)
        assert resp.state == PerformerState.COMPLETE

    def test_session_response_optional_message_default_none(self):
        resp = self._make()
        assert resp.message is None

    def test_session_response_accepts_message(self):
        resp = self._make(message="done!")
        assert resp.message == "done!"

    def test_session_response_outputs_dict(self):
        resp = self._make(outputs={"result": "42"})
        assert resp.outputs["result"] == "42"


class TestMessageRequest:
    def test_valid_content(self):
        req = MessageRequest(content="Hello agent!")
        assert req.content == "Hello agent!"

    def test_empty_content_raises_validation_error(self):
        with pytest.raises(ValidationError):
            MessageRequest(content="")

    def test_content_exceeding_max_length_raises_error(self):
        with pytest.raises(ValidationError):
            MessageRequest(content="x" * 10_001)


class TestHealthResponse:
    def test_health_response_fields(self):
        h = HealthResponse(
            status="ok",
            version="0.1.0",
            uptime_seconds=42.5,
        )
        assert h.status == "ok"
        assert h.version == "0.1.0"
        assert h.uptime_seconds == pytest.approx(42.5)
