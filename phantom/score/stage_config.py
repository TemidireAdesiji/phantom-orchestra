"""Stage (runtime environment) configuration for PhantomOrchestra."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["StageConfig"]


class StageConfig(BaseModel):
    """Configuration for the execution stage (sandbox environment).

    Governs how performer tasks are isolated and executed, including
    Docker container settings, resource limits, and workspace layout.
    """

    model_config = ConfigDict(populate_by_name=True)

    stage_type: Literal["docker", "local"] = "docker"
    container_image: str = "ghcr.io/phantom-orchestra/runtime:latest"
    sandbox_timeout: int = 120

    # Workspace; resolved to a temp dir when None
    workspace_dir: str | None = None

    use_host_network: bool = False
    max_memory_mb: int = 4096

    # Extra environment variables injected into the stage
    env_vars: dict[str, str] = Field(default_factory=dict)

    # Volume mount specs in Docker "src:dst" notation
    mount_volumes: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageConfig":
        """Construct a StageConfig from a plain dictionary.

        Args:
            data: Mapping of field names to raw values.

        Returns:
            A validated StageConfig instance.
        """
        return cls.model_validate(data)
