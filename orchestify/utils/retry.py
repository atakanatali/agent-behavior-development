"""
Retry utilities for LLM and API calls.

Provides decorators for robust retry handling with exponential backoff.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar

try:
    from tenacity import (
        AsyncRetrying,
        RetryError,
        Retrying,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception,
    )
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RateLimitError(Exception):
    """Rate limit error."""
    pass


class TimeoutError(Exception):
    """Timeout error."""
    pass


class ConnectionError(Exception):
    """Connection error."""
    pass


def retry_llm_call(
    max_retries: int = 3,
    initial_wait: int = 1,
    max_wait: int = 32,
) -> Callable[[F], F]:
    """
    Decorator for retrying LLM API calls.

    Retries on rate limits, timeouts, and connection errors with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        if not HAS_TENACITY:
            logger.warning("tenacity not installed, retry decorator disabled")
            return func

        is_async = asyncio.iscoroutinefunction(func)

        def should_retry_exception(exc: Exception) -> bool:
            """Determine if exception should trigger retry."""
            exc_str = str(exc).lower()
            return any(pattern in exc_str for pattern in [
                "rate limit",
                "429",
                "timeout",
                "connection",
                "connection reset",
                "broken pipe",
                "network",
            ])

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                retry_config = AsyncRetrying(
                    retry=retry_if_exception(should_retry_exception),
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(
                        multiplier=initial_wait,
                        min=initial_wait,
                        max=max_wait,
                    ),
                    reraise=True,
                )

                async for attempt in retry_config:
                    with attempt:
                        try:
                            return await func(*args, **kwargs)
                        except Exception as e:
                            if attempt.retry_state.attempt_number < max_retries:
                                logger.debug(
                                    f"Retry {attempt.retry_state.attempt_number}/"
                                    f"{max_retries} after error: {e}"
                                )
                            raise

            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                retry_config = Retrying(
                    retry=retry_if_exception(should_retry_exception),
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(
                        multiplier=initial_wait,
                        min=initial_wait,
                        max=max_wait,
                    ),
                    reraise=True,
                )

                for attempt in retry_config:
                    with attempt:
                        try:
                            return func(*args, **kwargs)
                        except Exception as e:
                            if attempt.retry_state.attempt_number < max_retries:
                                logger.debug(
                                    f"Retry {attempt.retry_state.attempt_number}/"
                                    f"{max_retries} after error: {e}"
                                )
                            raise

            return sync_wrapper  # type: ignore

    return decorator


def retry_github_call(
    max_retries: int = 3,
    initial_wait: int = 2,
    max_wait: int = 60,
) -> Callable[[F], F]:
    """
    Decorator for retrying GitHub API calls.

    Specifically handles GitHub rate limiting and API errors with longer backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        if not HAS_TENACITY:
            logger.warning("tenacity not installed, retry decorator disabled")
            return func

        is_async = asyncio.iscoroutinefunction(func)

        def should_retry_github_exception(exc: Exception) -> bool:
            """Determine if GitHub exception should trigger retry."""
            exc_str = str(exc).lower()
            # GitHub specific patterns
            return any(pattern in exc_str for pattern in [
                "api rate limit",
                "403",
                "x-ratelimit",
                "secondary rate limit",
                "abuse",
                "timeout",
                "connection",
            ])

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                retry_config = AsyncRetrying(
                    retry=retry_if_exception(should_retry_github_exception),
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(
                        multiplier=initial_wait,
                        min=initial_wait,
                        max=max_wait,
                    ),
                    reraise=True,
                )

                async for attempt in retry_config:
                    with attempt:
                        try:
                            return await func(*args, **kwargs)
                        except Exception as e:
                            if attempt.retry_state.attempt_number < max_retries:
                                logger.warning(
                                    f"GitHub API retry "
                                    f"{attempt.retry_state.attempt_number}/{max_retries}: "
                                    f"{e}"
                                )
                            raise

            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                retry_config = Retrying(
                    retry=retry_if_exception(should_retry_github_exception),
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(
                        multiplier=initial_wait,
                        min=initial_wait,
                        max=max_wait,
                    ),
                    reraise=True,
                )

                for attempt in retry_config:
                    with attempt:
                        try:
                            return func(*args, **kwargs)
                        except Exception as e:
                            if attempt.retry_state.attempt_number < max_retries:
                                logger.warning(
                                    f"GitHub API retry "
                                    f"{attempt.retry_state.attempt_number}/{max_retries}: "
                                    f"{e}"
                                )
                            raise

            return sync_wrapper  # type: ignore

    return decorator


def with_retries(
    func: Optional[Callable[..., Any]] = None,
    *,
    max_retries: int = 3,
    backoff: float = 1.5,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable:
    """
    Simple retry decorator without tenacity dependency.

    Useful for basic retry logic when tenacity is not available.

    Args:
        func: Function to decorate
        max_retries: Maximum retry attempts
        backoff: Backoff multiplier
        on_retry: Optional callback on retry

    Returns:
        Decorated function
    """
    def decorator(f: F) -> F:
        is_async = asyncio.iscoroutinefunction(f)

        if is_async:
            @functools.wraps(f)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                wait_time = 1.0
                last_error = None

                for attempt in range(max_retries):
                    try:
                        return await f(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            if on_retry:
                                on_retry(attempt + 1, e)
                            logger.debug(
                                f"Attempt {attempt + 1}/{max_retries} failed: {e}, "
                                f"retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            wait_time *= backoff

                raise last_error or Exception("All retries failed")

            return async_wrapper  # type: ignore
        else:
            @functools.wraps(f)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                wait_time = 1.0
                last_error = None

                for attempt in range(max_retries):
                    try:
                        return f(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            if on_retry:
                                on_retry(attempt + 1, e)
                            logger.debug(
                                f"Attempt {attempt + 1}/{max_retries} failed: {e}, "
                                f"retrying in {wait_time}s"
                            )
                            asyncio.run(asyncio.sleep(wait_time))
                            wait_time *= backoff

                raise last_error or Exception("All retries failed")

            return sync_wrapper  # type: ignore

    if func is None:
        return decorator
    else:
        return decorator(func)
