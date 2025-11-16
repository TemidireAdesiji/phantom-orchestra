"""Messaging and boot directives for PhantomOrchestra."""

from dataclasses import dataclass, field
from typing import ClassVar

from phantom.signal.directive.base import Directive, DirectiveType

__all__ = ["MessageDirective", "SystemBootDirective"]


@dataclass
class MessageDirective(Directive):
    """Directive to send a message to the user or another performer.

    Attributes:
        content: Text body of the message.
        image_urls: Optional list of image URLs to attach.
        wait_for_response: When ``True``, execution pauses until the
            recipient replies.
        directive_type: Fixed discriminator string.
    """

    content: str = ""
    image_urls: list[str] = field(default_factory=list)
    wait_for_response: bool = False
    directive_type: str = field(default=DirectiveType.SEND_MESSAGE, init=True)
    runnable: ClassVar[bool] = False

    @property
    def message(self) -> str:
        """Return the first 100 characters of the message content."""
        return self.content[:100]


@dataclass
class SystemBootDirective(Directive):
    """Synthetic directive injected at performer initialisation.

    Carries system-level metadata (tool list, performer class, platform
    version) needed to prime the performer's context window.

    Attributes:
        content: System prompt content.
        tools: List of tool-definition dicts available to the performer.
        performer_class: Fully-qualified name of the performer class.
        platform_version: PhantomOrchestra version string.
        directive_type: Fixed discriminator string.
    """

    content: str = ""
    tools: list[dict] | None = None  # type: ignore[type-arg]
    performer_class: str | None = None
    platform_version: str | None = None
    directive_type: str = field(default="system_boot", init=True)
    runnable: ClassVar[bool] = False

    @property
    def message(self) -> str:
        """Return a brief description of the boot directive."""
        return (
            f"SystemBoot(performer={self.performer_class!r}, "
            f"version={self.platform_version!r})"
        )
