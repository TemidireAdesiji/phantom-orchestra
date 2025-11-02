"""Performer (agent) configuration model for PhantomOrchestra."""

from typing import Any

from pydantic import BaseModel, ConfigDict

__all__ = ["PerformerConfig"]


class PerformerConfig(BaseModel):
    """Configuration for an autonomous performer (agent).

    Controls which capabilities are available to the performer at
    runtime, as well as prompt and LLM overrides.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Capability toggles
    enable_browsing: bool = True
    enable_file_editor: bool = True
    enable_terminal: bool = True
    enable_jupyter: bool = False
    enable_finish_signal: bool = True
    enable_stuck_detection: bool = True

    # Observation handling
    max_chars_per_observation: int = 30_000

    # Prompt customisation
    system_prompt_template: str = "default"

    # Optional named LLM config reference (key in OrchestraConfig.voices)
    voice_config_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformerConfig":
        """Construct a PerformerConfig from a plain dictionary.

        Args:
            data: Mapping of field names to raw values.

        Returns:
            A validated PerformerConfig instance.
        """
        return cls.model_validate(data)
