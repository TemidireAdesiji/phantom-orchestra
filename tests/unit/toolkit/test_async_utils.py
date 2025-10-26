"""Tests for toolkit async utilities."""

import asyncio

import pytest

from phantom.toolkit.async_utils import (
    gather_with_errors,
    run_sync,
    run_with_timeout,
)


class TestRunWithTimeout:
    async def test_completes_within_timeout(self):
        async def fast():
            return 42

        result = await run_with_timeout(fast(), timeout_seconds=5.0)
        assert result == 42

    async def test_raises_timeout_error_when_slow(self):
        async def slow():
            await asyncio.sleep(10)
            return "too late"

        with pytest.raises(TimeoutError):
            await run_with_timeout(slow(), timeout_seconds=0.01)

    async def test_custom_error_message_in_exception(self):
        async def slow():
            await asyncio.sleep(10)

        with pytest.raises(TimeoutError, match="custom msg"):
            await run_with_timeout(
                slow(),
                timeout_seconds=0.01,
                error_message="custom msg",
            )


class TestRunSync:
    def test_runs_coroutine_synchronously(self):
        async def coro():
            return "sync result"

        result = run_sync(coro())
        assert result == "sync result"

    def test_propagates_exceptions(self):
        async def failing():
            raise ValueError("sync fail")

        with pytest.raises(ValueError, match="sync fail"):
            run_sync(failing())


class TestGatherWithErrors:
    async def test_all_succeed(self):
        async def ok(n):
            return n * 2

        results = await gather_with_errors(ok(1), ok(2), ok(3))
        assert results == [2, 4, 6]

    async def test_collects_exceptions_when_return_exceptions_true(self):
        async def fail():
            raise RuntimeError("oops")

        async def ok():
            return "fine"

        results = await gather_with_errors(ok(), fail(), ok())
        assert results[0] == "fine"
        assert isinstance(results[1], RuntimeError)
        assert results[2] == "fine"
