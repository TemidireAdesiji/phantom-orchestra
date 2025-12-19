"""Abstract base Performer class for PhantomOrchestra."""

from abc import ABC, abstractmethod
from typing import ClassVar

from phantom.performer.scene import Scene
from phantom.score.performer_config import PerformerConfig
from phantom.signal.directive.base import Directive
from phantom.voice.registry import VoiceRegistry

__all__ = ["Performer"]


class Performer(ABC):
    """Abstract base for all autonomous performers (agents).

    Subclasses implement :meth:`decide` to translate the current
    :class:`Scene` into the next :class:`Directive`.  The class-level
    registry maps logical names to concrete subclasses so that the
    Director can instantiate performers by name at runtime.

    Attributes:
        _registry: Class-level map of ``{name: Performer subclass}``.
    """

    _registry: ClassVar[dict[str, type["Performer"]]] = {}

    def __init__(
        self,
        config: PerformerConfig,
        voice_registry: VoiceRegistry,
    ) -> None:
        self._config = config
        self._voice_registry = voice_registry
        self._complete = False

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def decide(self, scene: Scene) -> Directive:
        """Analyse the current scene and return the next directive.

        Implementations should:
        1. Read ``scene.history`` to understand prior context.
        2. Call the LLM via ``self._voice_registry``.
        3. Parse the LLM response into a concrete Directive subclass.

        Args:
            scene: Current session state including conversation history.

        Returns:
            The next Directive to be executed by the Stage.
        """

    # ------------------------------------------------------------------
    # Optional overrides
    # ------------------------------------------------------------------

    def get_available_tools(self) -> list[dict]:
        """Return tool definitions based on config capability flags.

        Base implementation returns an empty list.  Subclasses
        override this to expose their specific tool set.

        Returns:
            List of OpenAI-format tool definition dicts.
        """
        return []

    def build_system_prompt(self) -> str:
        """Build the system prompt for this performer.

        Base implementation returns an empty string.  Subclasses
        override to provide task-specific instructions.

        Returns:
            System prompt text to prepend to conversation history.
        """
        return ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def complete(self) -> bool:
        """True when this performer has finished its session."""
        return self._complete

    @complete.setter
    def complete(self, value: bool) -> None:
        self._complete = value

    @property
    def name(self) -> str:
        """Class name of this performer, used for logging."""
        return self.__class__.__name__

    # ------------------------------------------------------------------
    # Class-level registry
    # ------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        name: str,
        performer_cls: type["Performer"],
    ) -> None:
        """Register a Performer subclass under a logical name.

        Args:
            name: The registration key (e.g. ``"CodeActPerformer"``).
            performer_cls: The concrete Performer class to register.
        """
        cls._registry[name] = performer_cls

    @classmethod
    def get_class(cls, name: str) -> type["Performer"]:
        """Look up a registered Performer class by name.

        Args:
            name: The registration key.

        Returns:
            The registered Performer subclass.

        Raises:
            ValueError: If ``name`` is not in the registry.
        """
        if name not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown performer: {name!r}. Available: {available}"
            )
        return cls._registry[name]

    @classmethod
    def create(
        cls,
        name: str,
        config: PerformerConfig,
        voice_registry: VoiceRegistry,
    ) -> "Performer":
        """Instantiate a registered Performer by name.

        Args:
            name: Registration key for the desired performer type.
            config: PerformerConfig passed to the constructor.
            voice_registry: VoiceRegistry passed to the constructor.

        Returns:
            A new Performer instance of the requested type.

        Raises:
            ValueError: If ``name`` is not in the registry.
        """
        performer_cls = cls.get_class(name)
        return performer_cls(
            config=config,
            voice_registry=voice_registry,
        )
