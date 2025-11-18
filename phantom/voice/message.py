"""LLM message types for PhantomOrchestra voice module."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    "UsageMetrics",
]


class MessageRole(StrEnum):
    """Role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents an LLM-requested tool invocation.

    Attributes:
        id: Unique identifier for this tool call (from LLM).
        name: Name of the tool to invoke.
        arguments: Parsed JSON arguments for the tool.
    """

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result returned from executing a tool call.

    Attributes:
        tool_call_id: ID matching the originating ToolCall.
        content: Text result from the tool execution.
        is_error: Whether this result represents an error.
    """

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """A single message in an LLM conversation.

    Attributes:
        role: Who sent this message.
        content: Text content, or list of content parts
            (for multimodal messages).
        tool_calls: Tool calls requested by an assistant message.
        tool_call_id: For role=tool messages, the originating
            tool call ID.
        name: Optional name for role=tool messages.
    """

    role: MessageRole
    content: str | list[dict[str, Any]] | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_litellm_dict(self) -> dict[str, Any]:
        """Convert to LiteLLM-compatible message dict.

        Returns:
            Dictionary ready for passing to litellm.completion().
        """
        d: dict[str, Any] = {"role": self.role.value}

        if self.content is not None:
            d["content"] = self.content

        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": (
                            tc.arguments
                            if isinstance(tc.arguments, str)
                            else __import__("json").dumps(tc.arguments)
                        ),
                    },
                }
                for tc in self.tool_calls
            ]

        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id

        if self.name is not None:
            d["name"] = self.name

        return d

    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message.

        Args:
            content: System prompt text.

        Returns:
            Message with role=SYSTEM.
        """
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message.

        Args:
            content: User message text.

        Returns:
            Message with role=USER.
        """
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(
        cls,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> "Message":
        """Create an assistant message.

        Args:
            content: Optional text response from assistant.
            tool_calls: Optional list of tool calls requested.

        Returns:
            Message with role=ASSISTANT.
        """
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )


@dataclass
class UsageMetrics:
    """Accumulated token and cost metrics from LLM calls.

    Attributes:
        prompt_tokens: Total input tokens consumed.
        completion_tokens: Total output tokens generated.
        total_tokens: Sum of prompt and completion tokens.
        cost_usd: Estimated cost in US dollars.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
