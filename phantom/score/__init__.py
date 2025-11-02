"""Score module: configuration system for PhantomOrchestra."""

from phantom.score.loader import load_config
from phantom.score.orchestra_config import OrchestraConfig
from phantom.score.performer_config import PerformerConfig
from phantom.score.stage_config import StageConfig
from phantom.score.voice_config import VoiceConfig

__all__ = [
    "OrchestraConfig",
    "PerformerConfig",
    "StageConfig",
    "VoiceConfig",
    "load_config",
]
