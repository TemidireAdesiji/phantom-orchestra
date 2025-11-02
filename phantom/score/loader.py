"""Configuration loader for PhantomOrchestra.

Supports TOML files and environment variable overrides.
Search order for config file:
  1. Explicit ``path`` argument
  2. ``$PHANTOM_CONFIG_PATH`` environment variable
  3. ``~/.phantom/config.toml``
  4. ``./config.toml``
  5. Built-in defaults
"""

import logging
import os
from pathlib import Path
from typing import Any

from phantom.score.orchestra_config import OrchestraConfig
from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.score.voice_config import VoiceConfig

__all__ = ["load_config"]

logger = logging.getLogger(__name__)

# Mapping of env-var suffix -> OrchestraConfig field
_ORCHESTRA_ENV: dict[str, str] = {
    "MAX_ITERATIONS": "max_iterations",
    "FILE_STORE_TYPE": "file_store_type",
    "FILE_STORE_PATH": "file_store_path",
    "WORKSPACE_PATH": "workspace_path",
    "DEFAULT_VOICE": "default_voice",
    "DEFAULT_PERFORMER": "default_performer",
}

# Env vars that map into the default VoiceConfig
_VOICE_ENV: dict[str, str] = {
    "MODEL": "model",
    "API_KEY": "api_key",
    "BASE_URL": "base_url",
    "API_VERSION": "api_version",
    "AWS_ACCESS_KEY_ID": "aws_access_key_id",
    "AWS_SECRET_ACCESS_KEY": "aws_secret_access_key",
    "AWS_REGION_NAME": "aws_region_name",
    "TEMPERATURE": "temperature",
    "MAX_OUTPUT_TOKENS": "max_output_tokens",
    "MAX_INPUT_TOKENS": "max_input_tokens",
    "TIMEOUT": "timeout",
    "NUM_RETRIES": "num_retries",
    "REASONING_EFFORT": "reasoning_effort",
}

_ENV_PREFIX = "PHANTOM"


def _candidate_paths(path: str | None) -> list[Path]:
    """Return ordered list of candidate config file paths."""
    candidates: list[Path] = []

    if path is not None:
        candidates.append(Path(path))

    env_path = os.environ.get(f"{_ENV_PREFIX}_CONFIG_PATH")
    if env_path:
        candidates.append(Path(env_path))

    candidates.append(Path.home() / ".phantom" / "config.toml")
    candidates.append(Path("config.toml"))
    return candidates


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning an empty dict on parse failure."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            logger.warning(
                "No TOML library available; install tomli for Python < 3.11"
            )
            return {}

    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Failed to parse config file %s: %s", path, exc)
        return {}


def _apply_env_overrides(
    voice_data: dict[str, Any],
    orchestra_data: dict[str, Any],
) -> None:
    """Read PHANTOM_* env vars and populate data dicts in-place."""
    for suffix, field in _VOICE_ENV.items():
        val = os.environ.get(f"{_ENV_PREFIX}_{suffix}")
        if val is not None:
            voice_data[field] = val

    for suffix, field in _ORCHESTRA_ENV.items():
        val = os.environ.get(f"{_ENV_PREFIX}_{suffix}")
        if val is not None:
            orchestra_data[field] = val


def _build_voices(
    raw: dict[str, Any],
    default_voice_data: dict[str, Any],
) -> dict[str, VoiceConfig]:
    """Construct named VoiceConfig instances from TOML ``[voice]`` data.

    The top-level ``[voice]`` table becomes the ``"default"`` voice.
    Nested tables ``[voice.custom_name]`` become additional named voices.

    Args:
        raw: The full parsed TOML mapping.
        default_voice_data: Accumulated default-voice overrides.

    Returns:
        Mapping of voice name to VoiceConfig.
    """
    voices: dict[str, VoiceConfig] = {}
    voice_section: dict[str, Any] = dict(raw.get("voice", {}))

    # Scalar keys at [voice] level go into "default"
    default_from_toml: dict[str, Any] = {}
    named_voices: dict[str, dict[str, Any]] = {}

    for key, val in voice_section.items():
        if isinstance(val, dict):
            named_voices[key] = val
        else:
            default_from_toml[key] = val

    merged_default = {**default_from_toml, **default_voice_data}
    if merged_default:
        voices["default"] = VoiceConfig.from_dict(merged_default)
    else:
        voices["default"] = VoiceConfig()

    for name, data in named_voices.items():
        voices[name] = VoiceConfig.from_dict(data)

    return voices


def _build_performers(
    raw: dict[str, Any],
) -> dict[str, PerformerConfig]:
    """Construct named PerformerConfig instances from TOML data.

    The top-level ``[performer]`` table becomes ``"default"``.
    Nested tables become additional named performers.

    Args:
        raw: The full parsed TOML mapping.

    Returns:
        Mapping of performer name to PerformerConfig.
    """
    performers: dict[str, PerformerConfig] = {}
    perf_section: dict[str, Any] = dict(raw.get("performer", {}))

    default_from_toml: dict[str, Any] = {}
    named_performers: dict[str, dict[str, Any]] = {}

    for key, val in perf_section.items():
        if isinstance(val, dict):
            named_performers[key] = val
        else:
            default_from_toml[key] = val

    if default_from_toml:
        performers["default"] = PerformerConfig.from_dict(default_from_toml)
    else:
        performers["default"] = PerformerConfig()

    for name, data in named_performers.items():
        performers[name] = PerformerConfig.from_dict(data)

    return performers


def load_config(path: str | None = None) -> OrchestraConfig:
    """Load OrchestraConfig from a TOML file or environment variables.

    Config file search order:
      1. ``path`` argument (if provided)
      2. ``$PHANTOM_CONFIG_PATH`` environment variable
      3. ``~/.phantom/config.toml``
      4. ``./config.toml``
      5. Pure defaults if no file is found

    Environment variables (prefixed ``PHANTOM_``) always take
    precedence over file-based values for the default voice.

    Args:
        path: Optional explicit path to a TOML configuration file.

    Returns:
        A fully validated OrchestraConfig instance.
    """
    raw: dict[str, Any] = {}

    for candidate in _candidate_paths(path):
        if candidate.exists():
            logger.debug("Loading config from %s", candidate)
            raw = _load_toml(candidate)
            break
    else:
        logger.debug("No config file found; using defaults + env vars")

    # Collect env-var overrides for the default voice
    voice_env_data: dict[str, Any] = {}
    orchestra_env_data: dict[str, Any] = {}
    _apply_env_overrides(voice_env_data, orchestra_env_data)

    voices = _build_voices(raw, voice_env_data)
    performers = _build_performers(raw)

    stage_data: dict[str, Any] = dict(raw.get("stage", {}))
    stage = StageConfig.from_dict(stage_data) if stage_data else StageConfig()

    # Top-level orchestra-level keys from TOML
    orchestra_toml: dict[str, Any] = {
        k: v
        for k, v in raw.items()
        if k not in ("voice", "performer", "stage") and not isinstance(v, dict)
    }

    orchestra_data: dict[str, Any] = {
        **orchestra_toml,
        **orchestra_env_data,
        "voices": voices,
        "performers": performers,
        "stage": stage,
    }

    return OrchestraConfig.model_validate(orchestra_data)
