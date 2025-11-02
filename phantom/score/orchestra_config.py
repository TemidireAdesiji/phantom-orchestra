"""Master orchestration configuration for PhantomOrchestra."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.score.voice_config import VoiceConfig

__all__ = ["OrchestraConfig"]


class OrchestraConfig(BaseModel):
    """Top-level configuration for a PhantomOrchestra deployment.

    Aggregates all sub-configurations and provides convenience
    properties for accessing the primary voice and performer.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Named LLM configurations keyed by logical name
    voices: dict[str, VoiceConfig] = Field(default_factory=dict)

    # Named performer (agent) configurations
    performers: dict[str, PerformerConfig] = Field(default_factory=dict)

    # Execution stage configuration
    stage: StageConfig = Field(default_factory=StageConfig)

    # Default named references
    default_voice: str = "default"
    default_performer: str = "default"

    # Task budget controls
    max_iterations: int = 100
    max_budget_per_task: float | None = None

    # Persistence
    file_store_type: Literal["local", "memory"] = "local"
    file_store_path: str = "/tmp/phantom/store"  # noqa: S108

    # Global feature flags
    enable_browser: bool = True
    workspace_path: str | None = None

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def primary_voice(self) -> VoiceConfig:
        """Return the primary VoiceConfig.

        Returns the voice registered under ``default_voice``; if that
        key is absent, falls back to the first registered voice.  If no
        voices are configured, returns a default VoiceConfig.

        Returns:
            The primary VoiceConfig instance.
        """
        if self.default_voice in self.voices:
            return self.voices[self.default_voice]
        if self.voices:
            return next(iter(self.voices.values()))
        return VoiceConfig()

    @property
    def primary_performer(self) -> PerformerConfig:
        """Return the primary PerformerConfig.

        Returns the performer registered under ``default_performer``; if
        that key is absent, falls back to the first registered performer.
        If none are configured, returns a default PerformerConfig.

        Returns:
            The primary PerformerConfig instance.
        """
        if self.default_performer in self.performers:
            return self.performers[self.default_performer]
        if self.performers:
            return next(iter(self.performers.values()))
        return PerformerConfig()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrchestraConfig":
        """Construct an OrchestraConfig from a plain dictionary.

        Args:
            data: Mapping of field names to raw values.

        Returns:
            A validated OrchestraConfig instance.
        """
        return cls.model_validate(data)
