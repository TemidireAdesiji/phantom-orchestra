"""Tests for score configuration models."""

from phantom.score.orchestra_config import OrchestraConfig
from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.score.voice_config import VoiceConfig


class TestVoiceConfig:
    def test_voice_config_default_model(self):
        cfg = VoiceConfig()
        assert cfg.model == "claude-sonnet-4-6"

    def test_voice_config_default_temperature(self):
        cfg = VoiceConfig()
        assert cfg.temperature == 0.0

    def test_voice_config_default_num_retries(self):
        cfg = VoiceConfig()
        assert cfg.num_retries == 5

    def test_voice_config_default_use_prompt_caching(self):
        cfg = VoiceConfig()
        assert cfg.use_prompt_caching is True

    def test_voice_config_api_key_stored_as_secret(self):
        cfg = VoiceConfig(api_key="sk-test")  # type: ignore
        assert cfg.api_key is not None
        assert cfg.api_key.get_secret_value() == "sk-test"

    def test_voice_config_from_dict_basic(self):
        data = {
            "model": "gpt-4o",
            "temperature": 0.5,
            "num_retries": 3,
        }
        cfg = VoiceConfig.from_dict(data)
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.5
        assert cfg.num_retries == 3

    def test_voice_config_from_dict_with_api_key(self):
        data = {"model": "gpt-4o", "api_key": "sk-abc"}
        cfg = VoiceConfig.from_dict(data)
        assert cfg.api_key.get_secret_value() == "sk-abc"


class TestPerformerConfig:
    def test_performer_config_default_enable_browsing(self):
        cfg = PerformerConfig()
        assert cfg.enable_browsing is True

    def test_performer_config_default_enable_terminal(self):
        cfg = PerformerConfig()
        assert cfg.enable_terminal is True

    def test_performer_config_default_enable_jupyter(self):
        cfg = PerformerConfig()
        assert cfg.enable_jupyter is False

    def test_performer_config_default_max_chars(self):
        cfg = PerformerConfig()
        assert cfg.max_chars_per_observation == 30_000

    def test_performer_config_from_dict(self):
        data = {
            "enable_browsing": False,
            "enable_terminal": False,
            "max_chars_per_observation": 5000,
        }
        cfg = PerformerConfig.from_dict(data)
        assert cfg.enable_browsing is False
        assert cfg.enable_terminal is False
        assert cfg.max_chars_per_observation == 5000


class TestStageConfig:
    def test_stage_config_default_stage_type(self):
        cfg = StageConfig()
        assert cfg.stage_type == "docker"

    def test_stage_config_default_sandbox_timeout(self):
        cfg = StageConfig()
        assert cfg.sandbox_timeout == 120

    def test_stage_config_default_max_memory_mb(self):
        cfg = StageConfig()
        assert cfg.max_memory_mb == 4096

    def test_stage_config_workspace_dir_is_none_by_default(self):
        cfg = StageConfig()
        assert cfg.workspace_dir is None

    def test_stage_config_env_vars_empty_by_default(self):
        cfg = StageConfig()
        assert cfg.env_vars == {}

    def test_stage_config_from_dict(self):
        data = {
            "stage_type": "local",
            "sandbox_timeout": 60,
            "env_vars": {"HOME": "/tmp"},  # noqa: S108
        }
        cfg = StageConfig.from_dict(data)
        assert cfg.stage_type == "local"
        assert cfg.sandbox_timeout == 60
        assert cfg.env_vars["HOME"] == "/tmp"  # noqa: S108


class TestOrchestraConfig:
    def test_orchestra_config_primary_voice_returns_default(self):
        voice = VoiceConfig(model="gpt-4o")
        cfg = OrchestraConfig(
            voices={"default": voice},
            default_voice="default",
        )
        assert cfg.primary_voice.model == "gpt-4o"

    def test_orchestra_config_primary_voice_falls_back_to_first(
        self,
    ):
        voice = VoiceConfig(model="gpt-3.5-turbo")
        cfg = OrchestraConfig(
            voices={"named": voice},
            default_voice="does-not-exist",
        )
        assert cfg.primary_voice.model == "gpt-3.5-turbo"

    def test_orchestra_config_primary_voice_default_when_empty(
        self,
    ):
        cfg = OrchestraConfig(voices={})
        # Should return a VoiceConfig instance (default)
        assert isinstance(cfg.primary_voice, VoiceConfig)

    def test_orchestra_config_primary_performer_returns_default(
        self,
    ):
        perf = PerformerConfig(enable_terminal=False)
        cfg = OrchestraConfig(
            performers={"default": perf},
            default_performer="default",
        )
        assert cfg.primary_performer.enable_terminal is False

    def test_orchestra_config_primary_performer_default_when_empty(
        self,
    ):
        cfg = OrchestraConfig(performers={})
        assert isinstance(cfg.primary_performer, PerformerConfig)

    def test_orchestra_config_default_max_iterations(self):
        cfg = OrchestraConfig()
        assert cfg.max_iterations == 100

    def test_orchestra_config_from_dict(self):
        data = {
            "max_iterations": 50,
            "file_store_type": "memory",
        }
        cfg = OrchestraConfig.from_dict(data)
        assert cfg.max_iterations == 50
        assert cfg.file_store_type == "memory"


class TestLoaderDefaults:
    """Test load_config fallback to defaults when no file is found."""

    def test_load_config_returns_orchestra_config_with_defaults(
        self, monkeypatch
    ):
        from phantom.score.loader import load_config
        from phantom.score.orchestra_config import OrchestraConfig

        monkeypatch.delenv("PHANTOM_CONFIG_PATH", raising=False)
        # Pass a nonexistent path so it falls back to defaults
        cfg = load_config(path="/nonexistent/path/config.toml")
        assert isinstance(cfg, OrchestraConfig)

    def test_load_config_applies_phantom_model_env_var(self, monkeypatch):
        from phantom.score.loader import load_config

        monkeypatch.setenv("PHANTOM_MODEL", "gpt-4o-mini")
        monkeypatch.delenv("PHANTOM_CONFIG_PATH", raising=False)
        cfg = load_config(path="/nonexistent/path/config.toml")
        assert cfg.primary_voice.model == "gpt-4o-mini"

    def test_load_config_applies_phantom_api_key_env_var(self, monkeypatch):
        from phantom.score.loader import load_config

        monkeypatch.setenv("PHANTOM_API_KEY", "test-key-xyz")
        monkeypatch.delenv("PHANTOM_CONFIG_PATH", raising=False)
        cfg = load_config(path="/nonexistent/path/config.toml")
        assert cfg.primary_voice.api_key.get_secret_value() == "test-key-xyz"
