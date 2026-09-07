"""
Sync Retry & Backoff Controller — Task 13.3

Executes asynchronous synchronization operations with configurable exponential backoff
and structured diagnostic logging for transient failure recovery and permanent error isolation.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

import httpx

from app.core.config import settings
from app.utils.exceptions import (
    PlatformAuthException,
    PlatformClientException,
    PlatformNotConnectedException,
    PlatformRateLimitException,
    PlatformTransientException,
    PlatformUserNotFoundException,
    PlatformValidationException,
)

logger = logging.getLogger("devtrack.scheduler.retry")

T = TypeVar("T")

# Non-retryable platform exceptions that must immediately fail without retry
NON_RETRYABLE_EXCEPTIONS = (
    PlatformUserNotFoundException,
    PlatformValidationException,
    PlatformAuthException,
    PlatformNotConnectedException,
)

# Retryable exceptions representing transient conditions
RETRYABLE_EXCEPTIONS = (
    PlatformTransientException,
    PlatformRateLimitException,
    PlatformClientException,
    httpx.TransportError,
    httpx.TimeoutException,
    httpx.NetworkError,
    ConnectionError,
    TimeoutError,
)


def is_retryable_exception(exc: Exception) -> bool:
    """
    Determine whether an exception represents a transient failure eligible for retry.

    Returns False for non-retryable domain exceptions, deterministic validation errors,
    and standard Python programming/runtime errors.
    """
    if isinstance(exc, NON_RETRYABLE_EXCEPTIONS):
        return False
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True
    if isinstance(exc, (ValueError, TypeError, KeyError, AttributeError, NotImplementedError)):
        return False
    return False


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    platform: str,
    user_id: UUID,
    max_retries: int | None = None,
    base_delay: float | None = None,
    backoff_factor: float | None = None,
) -> T:
    """
    Execute an asynchronous synchronization callable with exponential backoff retries.

    Retry semantics:
        max_retries is the number of retry attempts AFTER the initial attempt.
        - max_retries=3: 1 initial attempt + 3 retries (4 total attempts)
        - delay sequence: base_delay * (backoff_factor ^ retry_number)

    :param operation: Zero-argument async callable executing the sync operation.
    :param platform: Name of platform ('GitHub', 'LeetCode') for structured logging.
    :param user_id: User identifier for structured context.
    :param max_retries: Number of retries after initial failure (default: settings.SYNC_MAX_RETRIES).
    :param base_delay: Initial delay in seconds before first retry (default: settings.SYNC_RETRY_BASE_DELAY_SECONDS).
    :param backoff_factor: Multiplier for exponential backoff (default: settings.SYNC_RETRY_BACKOFF_FACTOR).
    :return: The result of the successful operation.
    :raises: The final exception if all retries are exhausted or non-retryable error occurs.
    """
    retries = max_retries if max_retries is not None else settings.SYNC_MAX_RETRIES
    delay = base_delay if base_delay is not None else settings.SYNC_RETRY_BASE_DELAY_SECONDS
    factor = backoff_factor if backoff_factor is not None else settings.SYNC_RETRY_BACKOFF_FACTOR

    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as exc:
            retryable = is_retryable_exception(exc)

            if not retryable or attempt >= retries:
                # Structured error logging for permanent / exhausted failure
                logger.error(
                    "Sync operation '%s' failed permanently for user_id=%s (attempt %d/%d): %s",
                    platform,
                    user_id,
                    attempt + 1,
                    retries + 1,
                    exc,
                    extra={
                        "extra_data": {
                            "event": "sync_failure_permanent",
                            "user_id": str(user_id),
                            "platform": platform,
                            "attempt": attempt + 1,
                            "max_retries": retries,
                            "error": str(exc),
                            "error_type": exc.__class__.__name__,
                            "retryable": retryable,
                        }
                    },
                )
                raise exc

            # Calculate exponential backoff delay: base_delay * (factor ^ attempt)
            current_delay = delay * (factor ** attempt)
            logger.warning(
                "Transient error syncing %s for user_id=%s: %s. Retrying in %.2fs (retry %d/%d)...",
                platform,
                user_id,
                exc,
                current_delay,
                attempt + 1,
                retries,
                extra={
                    "extra_data": {
                        "event": "sync_retry",
                        "user_id": str(user_id),
                        "platform": platform,
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "delay_seconds": current_delay,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
                },
            )

            await asyncio.sleep(current_delay)
            attempt += 1
