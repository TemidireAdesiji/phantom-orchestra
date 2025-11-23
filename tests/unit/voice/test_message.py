"""Tests for Message and UsageMetrics."""

import json

import pytest

from phantom.voice.message import (
    Message,
    MessageRole,
    ToolCall,
    UsageMetrics,
)


class TestMessageFactoryMethods:
    def test_system_creates_system_role_message(self):
        msg = Message.system("You are a helpful assistant.")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are a helpful assistant."

    def test_user_creates_user_role_message(self):
        msg = Message.user("What is 2+2?")
        assert msg.role == MessageRole.USER
        assert msg.content == "What is 2+2?"

    def test_assistant_creates_assistant_role_message(self):
        msg = Message.assistant(content="4")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "4"

    def test_assistant_can_be_created_with_no_content(self):
        msg = Message.assistant()
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content is None

    def test_assistant_can_carry_tool_calls(self):
        tc = ToolCall(id="call-1", name="run_cmd", arguments={})
        msg = Message.assistant(tool_calls=[tc])
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "run_cmd"


class TestMessageToLitellmDict:
    def test_basic_text_message_serialises_role_and_content(self):
        msg = Message.user("hello")
        d = msg.to_litellm_dict()
        assert d["role"] == "user"
        assert d["content"] == "hello"

    def test_system_message_serialises_correctly(self):
        msg = Message.system("be helpful")
        d = msg.to_litellm_dict()
        assert d["role"] == "system"
        assert d["content"] == "be helpful"

    def test_content_key_absent_when_content_is_none(self):
        msg = Message.assistant()
        d = msg.to_litellm_dict()
        assert "content" not in d

    def test_tool_calls_serialised_with_function_type(self):
        tc = ToolCall(
            id="call-abc",
            name="execute",
            arguments={"cmd": "ls"},
        )
        msg = Message.assistant(tool_calls=[tc])
        d = msg.to_litellm_dict()
        assert "tool_calls" in d
        assert d["tool_calls"][0]["type"] == "function"
        assert d["tool_calls"][0]["id"] == "call-abc"
        fn = d["tool_calls"][0]["function"]
        assert fn["name"] == "execute"
        args = json.loads(fn["arguments"])
        assert args["cmd"] == "ls"

    def test_tool_call_id_included_when_set(self):
        msg = Message(
            role=MessageRole.TOOL,
            content="result",
            tool_call_id="call-xyz",
        )
        d = msg.to_litellm_dict()
        assert d["tool_call_id"] == "call-xyz"

    def test_name_field_included_when_set(self):
        msg = Message(
            role=MessageRole.TOOL,
            content="output",
            name="my_tool",
        )
        d = msg.to_litellm_dict()
        assert d["name"] == "my_tool"

    def test_name_field_absent_when_none(self):
        msg = Message.user("no name")
        d = msg.to_litellm_dict()
        assert "name" not in d


class TestUsageMetrics:
    def test_usage_metrics_defaults_to_zero(self):
        m = UsageMetrics()
        assert m.prompt_tokens == 0
        assert m.completion_tokens == 0
        assert m.total_tokens == 0
        assert m.cost_usd == 0.0

    def test_usage_metrics_accepts_values(self):
        m = UsageMetrics(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.002,
        )
        assert m.total_tokens == 150
        assert m.cost_usd == pytest.approx(0.002)
