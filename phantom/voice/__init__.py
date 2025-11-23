"""Voice (LLM) module for PhantomOrchestra.

Provides the abstraction layer between performers and language model
APIs via the litellm library.  Import the main classes from here
rather than from internal submodules.

Exported names:
    VoiceProvider  -- wraps litellm.completion with retries and metrics.
    VoiceRegistry  -- manages a collection of named VoiceProvider
                      instances, created lazily.
    Message        -- a single conversation turn (system / user /
                      assistant / tool).
    MessageRole    -- enum of valid message roles.
    ModelCapabilities -- dataclass describing what a model supports.
"""

from phantom.voice.capabilities import ModelCapabilities
from phantom.voice.message import Message, MessageRole
from phantom.voice.provider import VoiceProvider
from phantom.voice.registry import VoiceRegistry

__all__ = [
    "Message",
    "MessageRole",
    "ModelCapabilities",
    "VoiceProvider",
    "VoiceRegistry",
]
