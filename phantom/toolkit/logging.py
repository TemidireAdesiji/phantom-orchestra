"""Structured logging configuration for PhantomOrchestra.

Uses ``structlog`` for consistent, machine-parseable log output.
JSON format is recommended for production deployments; the coloured
console renderer is used when ``format="console"``.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

__all__ = ["configure_logging", "get_logger"]

_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    format: str = "json",  # noqa: A002
    include_timestamps: bool = True,
) -> None:
    """Configure structlog for structured application logging.

    Should be called once at application startup before any loggers
    are created.  Subsequent calls are no-ops.

    Args:
        level: Standard logging level name (e.g. ``"DEBUG"``,
            ``"INFO"``, ``"WARNING"``).
        format: Output format; ``"json"`` for production JSON lines,
            ``"console"`` for human-friendly coloured output.
        include_timestamps: When ``True``, add an ISO-8601 UTC
            ``timestamp`` key to every log entry.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors applied before rendering
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
    ]

    if include_timestamps:
        shared_processors.insert(
            0,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
        )

    shared_processors.append(structlog.stdlib.PositionalArgumentsFormatter())
    shared_processors.append(structlog.processors.StackInfoRenderer())

    if format.lower() == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    _CONFIGURED = True


def get_logger(name: str) -> Any:
    """Return a named structured logger bound to the given name.

    The returned logger supports the standard ``debug``, ``info``,
    ``warning``, ``error``, and ``critical`` methods, plus structlog's
    key-value binding via ``bind()``.

    Args:
        name: Logical name for the logger (typically ``__name__``).

    Returns:
        A structlog :class:`~structlog.stdlib.BoundLogger` instance.
    """
    return structlog.get_logger(name)
