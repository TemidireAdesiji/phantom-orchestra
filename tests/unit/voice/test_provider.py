"""Tests for VoiceProvider (LLM abstraction)."""

from unittest.mock import MagicMock, patch

import pytest

from phantom.score.voice_config import VoiceConfig
from phantom.voice.message import Message, MessageRole
from phantom.voice.provider import VoiceProvider


@pytest.fixture
def voice_config():
    return VoiceConfig(model="claude-sonnet-4-6", temperature=0.0)


@pytest.fixture
def provider(voice_config):
    return VoiceProvider(config=voice_config, provider_id="test")


def _mock_litellm_response(content="Hello!", tool_calls=None):
    """Build a minimal object that looks like a LiteLLM ModelResponse."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response._hidden_params = {}
    return response


class TestVoiceProviderProperties:
    def test_model_returns_config_model(self, provider, voice_config):
        assert provider.model == voice_config.model

    def test_provider_id_stored(self, voice_config):
        p = VoiceProvider(config=voice_config, provider_id="my-id")
        assert p._provider_id == "my-id"

    def test_cumulative_metrics_start_at_zero(self, provider):
        m = provider.cumulative_metrics
        assert m.prompt_tokens == 0
        assert m.completion_tokens == 0
        assert m.cost_usd == 0.0


class TestVoiceProviderComplete:
    def test_complete_returns_assistant_message(self, provider):
        mock_resp = _mock_litellm_response("World!")
        with patch("litellm.completion", return_value=mock_resp):
            result = provider.complete(
                messages=[Message.user("Hello")],
            )
        assert result.role == MessageRole.ASSISTANT
        assert result.content == "World!"

    def test_complete_updates_metrics(self, provider):
        mock_resp = _mock_litellm_response("ok")
        with patch("litellm.completion", return_value=mock_resp):
            provider.complete(messages=[Message.user("hi")])
        assert provider.cumulative_metrics.prompt_tokens == 10
        assert provider.cumulative_metrics.completion_tokens == 5

    def test_complete_with_tools_passes_tools_to_litellm(self, provider):
        mock_resp = _mock_litellm_response("done")
        tools = [{"type": "function", "function": {"name": "run_bash"}}]
        with patch("litellm.completion", return_value=mock_resp) as mock_call:
            provider.complete(
                messages=[Message.user("do it")],
                tools=tools,
            )
        call_kwargs = mock_call.call_args[1]
        assert "tools" in call_kwargs

    def test_complete_with_tool_call_response(self, provider):
        tc = MagicMock()
        tc.id = "call-1"
        tc.function.name = "run_bash"
        tc.function.arguments = '{"command": "ls"}'
        mock_resp = _mock_litellm_response(content=None, tool_calls=[tc])
        with patch("litellm.completion", return_value=mock_resp):
            result = provider.complete(messages=[Message.user("list")])
        assert result.tool_calls is not None
        assert result.tool_calls[0].name == "run_bash"
        assert result.tool_calls[0].arguments["command"] == "ls"

    def test_retry_on_rate_limit(self, provider):
        from litellm.exceptions import RateLimitError

        mock_resp = _mock_litellm_response("ok after retry")
        with patch(
            "litellm.completion",
            side_effect=[
                RateLimitError(
                    "rate limit",
                    llm_provider="anthropic",
                    model="claude",
                ),
                mock_resp,
            ],
        ):
            # Override retry wait to 0 for test speed
            provider._config.retry_min_wait = 0
            provider._config.retry_max_wait = 0
            result = provider.complete(messages=[Message.user("hi")])
        assert result.content == "ok after retry"


class TestVoiceRegistry:
    def test_registry_creates_provider_on_demand(self):
        from phantom.voice.registry import VoiceRegistry

        cfg = VoiceConfig(model="gpt-4o")
        registry = VoiceRegistry(
            configs={"default": cfg},
            default_name="default",
        )
        p = registry.get("default")
        assert isinstance(p, VoiceProvider)
        assert p.model == "gpt-4o"

    def test_registry_reuses_provider_instance(self):
        from phantom.voice.registry import VoiceRegistry

        cfg = VoiceConfig()
        registry = VoiceRegistry(configs={"default": cfg})
        p1 = registry.get("default")
        p2 = registry.get("default")
        assert p1 is p2

    def test_registry_falls_back_to_default(self):
        from phantom.voice.registry import VoiceRegistry

        cfg = VoiceConfig()
        registry = VoiceRegistry(configs={"default": cfg})
        p = registry.get("nonexistent")
        assert isinstance(p, VoiceProvider)

    def test_registry_list_providers(self):
        from phantom.voice.registry import VoiceRegistry

        registry = VoiceRegistry(
            configs={"a": VoiceConfig(), "b": VoiceConfig()}
        )
        assert set(registry.list_providers()) == {"a", "b"}

    def test_registry_register_adds_config(self):
        from phantom.voice.registry import VoiceRegistry

        registry = VoiceRegistry(configs={})
        registry.register("new", VoiceConfig(model="gpt-4o-mini"))
        p = registry.get("new")
        assert p.model == "gpt-4o-mini"
