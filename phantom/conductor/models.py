"""Pydantic request/response models for the Conductor API."""

from pydantic import BaseModel, Field

from phantom.signal.report.control import PerformerState

__all__ = [
    "CreateSessionRequest",
    "HealthResponse",
    "MessageRequest",
    "SessionResponse",
    "SignalResponse",
]


class CreateSessionRequest(BaseModel):
    """Request body for creating a new execution session.

    Attributes:
        task: Natural-language description of the task to perform.
        performer_name: Name of the registered performer to use.
        voice_name: Optional override for the LLM voice provider.
        workspace_dir: Optional workspace directory on the stage.
        max_iterations: Hard cap on performer decision steps.
        max_budget_usd: Optional USD spending cap; None = unlimited.
    """

    task: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Task description for the performer.",
    )
    performer_name: str = Field(
        default="default",
        description="Registered performer identifier.",
    )
    voice_name: str | None = Field(
        default=None,
        description="Optional LLM voice override.",
    )
    workspace_dir: str | None = Field(
        default=None,
        description="Optional workspace directory on the stage.",
    )
    max_iterations: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum performer decision steps.",
    )
    max_budget_usd: float | None = Field(
        default=None,
        ge=0,
        description="Optional USD spending cap.",
    )


class SessionResponse(BaseModel):
    """Response body describing the current state of a session.

    Attributes:
        session_id: Unique identifier for the session.
        state: Current lifecycle state of the performer.
        iterations: Number of completed decision steps.
        budget_spent_usd: Accumulated LLM cost in USD.
        outputs: Named string outputs from the performer.
        message: Optional human-readable status message.
    """

    session_id: str
    state: PerformerState
    iterations: int
    budget_spent_usd: float
    outputs: dict[str, str]
    message: str | None = None


class MessageRequest(BaseModel):
    """Request body for sending a message to a running session.

    Attributes:
        content: Text content of the user message.
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="User message content.",
    )


class SignalResponse(BaseModel):
    """Response body representing a single signal from the channel.

    Attributes:
        signal_id: Monotonic signal identifier.
        signal_type: Discriminator string (directive/report type).
        content: Human-readable signal content.
        source: Originating source (performer/user/environment).
        timestamp: ISO-8601 UTC timestamp.
    """

    signal_id: int
    signal_type: str
    content: str
    source: str
    timestamp: str


class HealthResponse(BaseModel):
    """Response body for the health check endpoint.

    Attributes:
        status: ``"ok"`` when the service is healthy.
        version: Application version string.
        uptime_seconds: Seconds since the process started.
    """

    status: str
    version: str
    uptime_seconds: float
