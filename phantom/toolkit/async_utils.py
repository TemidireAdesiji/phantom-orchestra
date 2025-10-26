"""Async utility helpers for PhantomOrchestra."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

__all__ = [
    "gather_with_errors",
    "run_sync",
    "run_with_timeout",
]

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    error_message: str = "Operation timed out",
) -> T:
    """Run a coroutine with a wall-clock timeout.

    Args:
        coro: The coroutine to execute.
        timeout_seconds: Maximum number of seconds to wait.
        error_message: Message embedded in the raised
            :class:`TimeoutError` when the deadline is exceeded.

    Returns:
        The value returned by ``coro``.

    Raises:
        TimeoutError: When ``coro`` does not complete within
            ``timeout_seconds``.
    """
    try:
        return await asyncio.wait_for(
            asyncio.ensure_future(coro),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        raise TimeoutError(error_message) from None


def run_sync(coro: Awaitable[T]) -> T:
    """Execute an async coroutine from a synchronous context.

    Uses the running event loop when one exists (e.g. inside a
    Jupyter notebook); otherwise creates a new event loop via
    :func:`asyncio.run`.

    Args:
        coro: The coroutine to execute.

    Returns:
        The value returned by the coroutine.

    Raises:
        RuntimeError: When called from within a coroutine on the
            same thread (use ``await`` instead).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We are inside an async context — schedule and block via
        # a concurrent.futures.Future.
        import concurrent.futures

        future: concurrent.futures.Future[T] = concurrent.futures.Future()

        async def _runner() -> None:
            try:
                result = await coro  # type: ignore[misc]
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)

        loop.create_task(_runner())
        return future.result(timeout=None)

    return asyncio.run(coro)  # type: ignore[arg-type]


async def gather_with_errors(
    *coros: Awaitable,
    return_exceptions: bool = True,
) -> list:
    """Run coroutines concurrently, collecting results and exceptions.

    Unlike plain :func:`asyncio.gather`, this wrapper always collects
    *all* outcomes regardless of individual failures when
    ``return_exceptions=True`` (the default).

    Args:
        *coros: Coroutines to execute concurrently.
        return_exceptions: When ``True`` (default), exceptions are
            included in the result list rather than being re-raised.
            When ``False``, the first exception propagates immediately.

    Returns:
        A list of return values or :class:`Exception` instances,
        ordered to correspond with the ``coros`` arguments.
    """
    return await asyncio.gather(*coros, return_exceptions=return_exceptions)
