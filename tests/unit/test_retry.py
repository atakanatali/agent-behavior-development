"""Unit tests for orchestify.utils.retry module."""
import asyncio
import pytest
from unittest.mock import MagicMock

from orchestify.utils.retry import (
    RateLimitError,
    TimeoutError,
    ConnectionError,
    with_retries,
)


# ─── Custom Exception Tests ───


class TestCustomExceptions:
    def test_rate_limit_error(self):
        err = RateLimitError("Rate limited")
        assert str(err) == "Rate limited"

    def test_timeout_error(self):
        err = TimeoutError("Timed out")
        assert str(err) == "Timed out"

    def test_connection_error(self):
        err = ConnectionError("Connection failed")
        assert str(err) == "Connection failed"


# ─── with_retries Tests ───


class TestWithRetries:
    def test_sync_success_first_try(self):
        call_count = 0

        @with_retries(max_retries=3, backoff=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_sync_retry_then_success(self):
        call_count = 0

        @with_retries(max_retries=3, backoff=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Fail")
            return "ok"

        result = fail_then_succeed()
        assert result == "ok"
        assert call_count == 3

    def test_sync_all_retries_fail(self):
        @with_retries(max_retries=2, backoff=0.01)
        def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fail()

    def test_sync_on_retry_callback(self):
        retries = []

        def on_retry_cb(attempt, exc):
            retries.append((attempt, str(exc)))

        call_count = 0

        @with_retries(max_retries=3, backoff=0.01, on_retry=on_retry_cb)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Fail #{call_count}")
            return "ok"

        result = fail_twice()
        assert result == "ok"
        assert len(retries) == 2

    @pytest.mark.asyncio
    async def test_async_success(self):
        @with_retries(max_retries=3, backoff=0.01)
        async def async_succeed():
            return "async ok"

        result = await async_succeed()
        assert result == "async ok"

    @pytest.mark.asyncio
    async def test_async_retry_then_success(self):
        call_count = 0

        @with_retries(max_retries=3, backoff=0.01)
        async def async_fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Async fail")
            return "async ok"

        result = await async_fail_then_succeed()
        assert result == "async ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_all_retries_fail(self):
        @with_retries(max_retries=2, backoff=0.01)
        async def always_fail():
            raise RuntimeError("Async always fails")

        with pytest.raises(RuntimeError, match="Async always fails"):
            await always_fail()

    def test_decorator_without_parentheses(self):
        """with_retries can be used without parentheses."""
        call_count = 0

        @with_retries
        def simple_func():
            nonlocal call_count
            call_count += 1
            return "simple"

        result = simple_func()
        assert result == "simple"
        assert call_count == 1
