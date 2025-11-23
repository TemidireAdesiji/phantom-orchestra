"""Model capability registry for PhantomOrchestra voice module."""

from dataclasses import dataclass

__all__ = [
    "KNOWN_MODEL_CAPABILITIES",
    "ModelCapabilities",
    "get_model_capabilities",
]


@dataclass
class ModelCapabilities:
    """Describes what a given LLM model supports.

    Attributes:
        supports_vision: Can the model process image inputs.
        supports_function_calling: Supports structured tool calls.
        supports_streaming: Can stream tokens incrementally.
        max_context_tokens: Maximum combined input token window.
        max_output_tokens: Maximum tokens the model can generate.
        supports_prompt_caching: Supports Anthropic-style caching.
        supports_reasoning: Has extended chain-of-thought reasoning.
    """

    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_streaming: bool = True
    max_context_tokens: int = 128_000
    max_output_tokens: int = 4096
    supports_prompt_caching: bool = False
    supports_reasoning: bool = False


# ---------------------------------------------------------------------------
# Model capabilities registry
# ---------------------------------------------------------------------------

KNOWN_MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    "claude-sonnet-4-6": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=200_000,
        max_output_tokens=64_000,
        supports_prompt_caching=True,
        supports_reasoning=False,
    ),
    "claude-opus-4-6": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=200_000,
        max_output_tokens=32_000,
        supports_prompt_caching=True,
        supports_reasoning=False,
    ),
    "claude-haiku-4-5-20251001": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=200_000,
        max_output_tokens=8096,
        supports_prompt_caching=True,
        supports_reasoning=False,
    ),
    "claude-3-5-sonnet-20241022": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=200_000,
        max_output_tokens=8096,
        supports_prompt_caching=True,
        supports_reasoning=False,
    ),
    "gpt-4o": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        supports_prompt_caching=False,
        supports_reasoning=False,
    ),
    "gpt-4o-mini": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        supports_prompt_caching=False,
        supports_reasoning=False,
    ),
    "o1": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=False,
        max_context_tokens=200_000,
        max_output_tokens=100_000,
        supports_prompt_caching=False,
        supports_reasoning=True,
    ),
    "gemini/gemini-2.0-flash": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=1_048_576,
        max_output_tokens=8192,
        supports_prompt_caching=False,
        supports_reasoning=False,
    ),
    "gemini/gemini-1.5-pro": ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=2_097_152,
        max_output_tokens=8192,
        supports_prompt_caching=False,
        supports_reasoning=False,
    ),
    "deepseek/deepseek-chat": ModelCapabilities(
        supports_vision=False,
        supports_function_calling=True,
        supports_streaming=True,
        max_context_tokens=64_000,
        max_output_tokens=8192,
        supports_prompt_caching=False,
        supports_reasoning=False,
    ),
}

# Default capabilities for unknown models
_DEFAULT_CAPABILITIES = ModelCapabilities()


def get_model_capabilities(model: str) -> ModelCapabilities:
    """Get capabilities for a model, falling back to defaults.

    Looks up the model by exact name first, then tries stripping
    provider prefixes (e.g. ``bedrock/``, ``azure/``).

    Args:
        model: Model identifier string.

    Returns:
        ModelCapabilities for the model, or default capabilities
        if the model is not in the registry.
    """
    if model in KNOWN_MODEL_CAPABILITIES:
        return KNOWN_MODEL_CAPABILITIES[model]

    # Try stripping a provider prefix (e.g. "bedrock/claude-...")
    if "/" in model:
        base = model.split("/", 1)[1]
        if base in KNOWN_MODEL_CAPABILITIES:
            return KNOWN_MODEL_CAPABILITIES[base]

    # Fuzzy match: find a registry key that appears in the model name
    model_lower = model.lower()
    for key, caps in KNOWN_MODEL_CAPABILITIES.items():
        key_base = key.split("/")[-1].lower()
        if key_base in model_lower or model_lower in key_base:
            return caps

    return _DEFAULT_CAPABILITIES
