"""LLM provider abstraction using litellm for PhantomOrchestra."""

import json
import time
from collections.abc import Iterator
from typing import Any

import litellm
import structlog
from litellm import ModelResponse
from litellm.exceptions import (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from phantom.score.voice_config import VoiceConfig
from phantom.voice.capabilities import (
    ModelCapabilities,
    get_model_capabilities,
)
from phantom.voice.message import Message, MessageRole, ToolCall, UsageMetrics

__all__ = ["VoiceProvider", "VoiceProviderError"]

logger = structlog.get_logger(__name__)

# Exceptions that trigger retry
_RETRYABLE = (
    RateLimitError,
    APIConnectionError,
    ServiceUnavailableError,
    Timeout,
)


class VoiceProviderError(Exception):
    """Raised when the LLM provider encounters an unrecoverable error."""


class VoiceProvider:
    """Wraps litellm to provide a typed LLM completion interface.

    Handles retries with exponential backoff, usage metric tracking,
    and conversion between :class:`Message` objects and the dicts
    expected by litellm.

    Args:
        config: VoiceConfig holding model name, credentials, and
            sampling parameters.
        provider_id: Logical name for this provider instance; used
            in log records for disambiguation.
    """

    def __init__(
        self,
        config: VoiceConfig,
        provider_id: str = "default",
    ) -> None:
        self._config = config
        self._provider_id = provider_id
        self._capabilities = get_model_capabilities(config.model)
        self._metrics = UsageMetrics()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model(self) -> str:
        """The LLM model identifier string."""
        return self._config.model

    @property
    def capabilities(self) -> ModelCapabilities:
        """Capabilities of the configured model."""
        return self._capabilities

    @property
    def cumulative_metrics(self) -> UsageMetrics:
        """Accumulated token and cost metrics since instantiation."""
        return self._metrics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Message:
        """Send messages to the LLM and return a response Message.

        Args:
            messages: Conversation history including the latest turn.
            tools: Optional OpenAI-format tool definitions.
            max_tokens: Override max output tokens for this call.
            temperature: Override sampling temperature for this call.

        Returns:
            Assistant Message parsed from the LLM response.

        Raises:
            VoiceProviderError: If all retries are exhausted or an
                unrecoverable error is encountered.
        """
        kwargs = self._build_litellm_kwargs(
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        logger.debug(
            "voice_complete",
            provider_id=self._provider_id,
            model=self.model,
            num_messages=len(messages),
            has_tools=tools is not None,
        )

        response = self._execute_with_retries(litellm.completion, kwargs)
        self._update_metrics(response)

        return self._extract_message(response)

    def complete_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        """Stream LLM response tokens.

        Args:
            messages: Conversation history.
            tools: Optional tool definitions.

        Yields:
            Individual string token chunks as they arrive.

        Raises:
            VoiceProviderError: If streaming fails entirely.
        """
        kwargs = self._build_litellm_kwargs(
            messages=messages,
            tools=tools,
        )
        kwargs["stream"] = True

        logger.debug(
            "voice_complete_stream",
            provider_id=self._provider_id,
            model=self.model,
        )

        try:
            stream = self._execute_with_retries(litellm.completion, kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                token = getattr(delta, "content", None)
                if token:
                    yield token
        except VoiceProviderError:
            raise
        except Exception as exc:
            raise VoiceProviderError(f"Streaming failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_litellm_kwargs(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Build the kwargs dict for a litellm.completion() call.

        Args:
            messages: Conversation messages to include.
            tools: Optional tool definitions.
            max_tokens: Optional token override.
            temperature: Optional temperature override.

        Returns:
            Dict suitable for passing to litellm.completion(**kwargs).
        """
        cfg = self._config
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "messages": [m.to_litellm_dict() for m in messages],
            "temperature": (
                temperature if temperature is not None else cfg.temperature
            ),
        }

        # Max tokens
        resolved_max_tokens = max_tokens or cfg.max_output_tokens
        if resolved_max_tokens is not None:
            kwargs["max_tokens"] = resolved_max_tokens

        # top_p
        if cfg.top_p != 1.0:
            kwargs["top_p"] = cfg.top_p

        # Credentials
        if cfg.api_key is not None:
            kwargs["api_key"] = cfg.api_key.get_secret_value()

        if cfg.base_url is not None:
            kwargs["base_url"] = cfg.base_url

        if cfg.api_version is not None:
            kwargs["api_version"] = cfg.api_version

        # AWS Bedrock
        if cfg.aws_access_key_id is not None:
            kwargs["aws_access_key_id"] = (
                cfg.aws_access_key_id.get_secret_value()
            )
        if cfg.aws_secret_access_key is not None:
            kwargs["aws_secret_access_key"] = (
                cfg.aws_secret_access_key.get_secret_value()
            )
        if cfg.aws_region_name is not None:
            kwargs["aws_region_name"] = cfg.aws_region_name

        # Timeout
        if cfg.timeout is not None:
            kwargs["timeout"] = cfg.timeout

        # Tools
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Prompt caching (Anthropic)
        if (
            cfg.use_prompt_caching
            and self._capabilities.supports_prompt_caching
        ):
            kwargs["cache"] = {"type": "ephemeral"}

        # Reasoning
        if cfg.reasoning_effort is not None:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 8000,
            }

        return kwargs

    def _extract_message(self, response: ModelResponse) -> Message:
        """Extract a typed Message from a LiteLLM ModelResponse.

        Args:
            response: Raw LiteLLM ModelResponse object.

        Returns:
            Parsed assistant Message.

        Raises:
            VoiceProviderError: If the response has no choices.
        """
        if not response.choices:
            raise VoiceProviderError("LLM response contained no choices.")

        choice = response.choices[0]
        msg = choice.message  # type: ignore[union-attr]
        content: str | None = getattr(msg, "content", None)
        raw_tool_calls = getattr(msg, "tool_calls", None)

        tool_calls: list[ToolCall] | None = None
        if raw_tool_calls:
            parsed: list[ToolCall] = []
            for tc in raw_tool_calls:
                fn = tc.function
                raw_args = fn.arguments or "{}"
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {"_raw": raw_args}
                else:
                    args = raw_args
                parsed.append(
                    ToolCall(
                        id=tc.id,
                        name=fn.name,
                        arguments=args,
                    )
                )
            tool_calls = parsed

        return Message(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )

    def _update_metrics(self, response: ModelResponse) -> None:
        """Update cumulative usage metrics from a response.

        Args:
            response: LiteLLM ModelResponse containing usage data.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        self._metrics.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self._metrics.completion_tokens += (
            getattr(usage, "completion_tokens", 0) or 0
        )
        self._metrics.total_tokens += getattr(usage, "total_tokens", 0) or 0

        # litellm exposes cost via response._hidden_params
        hidden = getattr(response, "_hidden_params", {}) or {}
        cost = hidden.get("response_cost") or 0.0
        self._metrics.cost_usd += float(cost)

    def _execute_with_retries(
        self,
        fn: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        """Execute a litellm call with exponential backoff retries.

        Retries on :data:`_RETRYABLE` exceptions using a delay
        starting at ``config.retry_min_wait`` and doubling each
        attempt up to ``config.retry_max_wait``, multiplied by
        ``config.retry_multiplier``.

        Args:
            fn: Callable to invoke (e.g. litellm.completion).
            kwargs: Keyword arguments to pass to the callable.

        Returns:
            Return value of the callable on success.

        Raises:
            VoiceProviderError: After all retries are exhausted, or
                immediately for non-retryable exceptions.
        """
        cfg = self._config
        max_attempts = max(1, cfg.num_retries + 1)
        delay = float(cfg.retry_min_wait)

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return fn(**kwargs)
            except _RETRYABLE as exc:
                last_exc = exc
                if attempt >= max_attempts:
                    break

                wait = min(
                    delay * cfg.retry_multiplier,
                    float(cfg.retry_max_wait),
                )
                logger.warning(
                    "llm_retry",
                    provider_id=self._provider_id,
                    model=self.model,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    wait_seconds=round(wait, 2),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                time.sleep(wait)
                delay = min(delay * 2, float(cfg.retry_max_wait))
            except Exception as exc:
                raise VoiceProviderError(
                    f"LLM call failed (non-retryable): {exc}"
                ) from exc

        raise VoiceProviderError(
            f"LLM call failed after {max_attempts} attempts: {last_exc}"
        ) from last_exc
