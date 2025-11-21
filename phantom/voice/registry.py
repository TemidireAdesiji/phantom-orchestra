"""LLM provider registry for PhantomOrchestra voice module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from phantom.score.voice_config import VoiceConfig
from phantom.voice.provider import VoiceProvider

if TYPE_CHECKING:
    from phantom.score.orchestra_config import OrchestraConfig

__all__ = ["VoiceRegistry"]


class VoiceRegistry:
    """Manages a collection of named :class:`VoiceProvider` instances.

    Providers are created lazily on first access to avoid making
    network connections or loading credentials until they are needed.

    Args:
        configs: Mapping of logical name to :class:`VoiceConfig`.
        default_name: The name returned when :meth:`get` is called
            without an argument.
    """

    def __init__(
        self,
        configs: dict[str, VoiceConfig],
        default_name: str = "default",
    ) -> None:
        self._configs: dict[str, VoiceConfig] = dict(configs)
        self._default_name = default_name
        self._providers: dict[str, VoiceProvider] = {}

    # ------------------------------------------------------------------
    # Provider access
    # ------------------------------------------------------------------

    def get(self, name: str | None = None) -> VoiceProvider:
        """Get a VoiceProvider by name, creating it lazily if needed.

        Args:
            name: Logical provider name.  ``None`` uses the default.

        Returns:
            The requested VoiceProvider instance.

        Raises:
            KeyError: If the requested name is not registered and no
                default is available.
        """
        resolved = name if name is not None else self._default_name

        if resolved not in self._providers:
            if resolved not in self._configs:
                if self._configs:
                    # Fall back to default
                    if self._default_name in self._configs:
                        resolved = self._default_name
                    else:
                        resolved = next(iter(self._configs))
                else:
                    # No configs at all: create a bare default
                    self._configs[resolved] = VoiceConfig()

            self._providers[resolved] = VoiceProvider(
                config=self._configs[resolved],
                provider_id=resolved,
            )

        return self._providers[resolved]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, config: VoiceConfig) -> None:
        """Register a new voice configuration.

        If a provider was already created for this name it is evicted
        so the new config takes effect on the next call to :meth:`get`.

        Args:
            name: Logical name to associate with the config.
            config: VoiceConfig describing the LLM endpoint.
        """
        self._configs[name] = config
        # Evict cached provider so it is rebuilt with the new config
        self._providers.pop(name, None)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_providers(self) -> list[str]:
        """Return a sorted list of all registered provider names.

        Returns:
            List of registered logical names.
        """
        return sorted(self._configs.keys())

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_orchestra_config(cls, config: OrchestraConfig) -> VoiceRegistry:
        """Build a VoiceRegistry from an OrchestraConfig.

        Uses ``config.voices`` as the registry's config map and
        ``config.default_voice`` as the default provider name.  When
        no voices are configured, a single default VoiceConfig is
        synthesised from the primary voice property.

        Args:
            config: Master orchestration configuration.

        Returns:
            A populated VoiceRegistry instance.
        """
        configs: dict[str, VoiceConfig] = dict(config.voices)

        if not configs:
            configs[config.default_voice] = config.primary_voice

        return cls(
            configs=configs,
            default_name=config.default_voice,
        )
