"""LLM (voice) configuration model for PhantomOrchestra."""

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr, model_validator

__all__ = ["VoiceConfig"]


class VoiceConfig(BaseModel):
    """Configuration for a language model (voice) endpoint.

    Supports OpenAI-compatible APIs, Azure OpenAI, and AWS Bedrock.
    Secrets are stored as Pydantic SecretStr and never logged.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )

    model: str = "claude-sonnet-4-6"
    api_key: SecretStr | None = None
    base_url: str | None = None
    api_version: str | None = None

    # AWS Bedrock credentials
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_region_name: str | None = None

    # Retry behaviour
    num_retries: int = 5
    retry_multiplier: float = 8.0
    retry_min_wait: int = 8
    retry_max_wait: int = 64

    # Token / content limits
    max_message_chars: int = 30_000
    timeout: int | None = None

    # Sampling parameters
    temperature: float = 0.0
    top_p: float = 1.0
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None

    # Feature flags
    use_prompt_caching: bool = True
    native_tool_calling: bool | None = None
    reasoning_effort: str | None = None
    disable_vision: bool = False

    # Completion logging
    log_completions: bool = False
    log_completions_folder: str = "completions"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _propagate_credentials_to_env(self) -> "VoiceConfig":
        """Push Azure / AWS credentials into environment variables.

        Libraries such as litellm read credentials from the environment,
        so we mirror configured secrets there at validation time.
        """
        if self.api_key is not None:
            os.environ.setdefault(
                "OPENAI_API_KEY",
                self.api_key.get_secret_value(),
            )

        if self.api_version is not None:
            os.environ.setdefault("AZURE_API_VERSION", self.api_version)

        if self.base_url is not None and "azure" in self.base_url.lower():
            os.environ.setdefault("AZURE_API_BASE", self.base_url)
            if self.api_key is not None:
                os.environ.setdefault(
                    "AZURE_API_KEY",
                    self.api_key.get_secret_value(),
                )

        if self.aws_access_key_id is not None:
            os.environ.setdefault(
                "AWS_ACCESS_KEY_ID",
                self.aws_access_key_id.get_secret_value(),
            )

        if self.aws_secret_access_key is not None:
            os.environ.setdefault(
                "AWS_SECRET_ACCESS_KEY",
                self.aws_secret_access_key.get_secret_value(),
            )

        if self.aws_region_name is not None:
            os.environ.setdefault("AWS_DEFAULT_REGION", self.aws_region_name)

        return self

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceConfig":
        """Construct a VoiceConfig from a plain dictionary.

        Args:
            data: Mapping of field names to raw values.  SecretStr
                fields may be supplied as plain strings.

        Returns:
            A validated VoiceConfig instance.
        """
        return cls.model_validate(data)
