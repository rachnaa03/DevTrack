"""
Unit tests for Sync Retry Controller and Exponential Backoff (Task 13.3).

Verifies:
- First-attempt success without retries or sleep.
- Recovery from transient failures (HTTP 503, HTTP 429, timeouts, network errors) via exponential backoff.
- Retry exhaustion after exactly SYNC_MAX_RETRIES attempts and re-raising the original exception.
- Immediate non-retry of permanent domain errors (404, schema invalid, auth failed, not connected).
- Non-retry of standard Python programming/runtime errors.
- Correct exponential backoff formula calculation.
- Structured logging context for `sync_retry` and `sync_failure_permanent` events.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.services.scheduler.retry import (
    NON_RETRYABLE_EXCEPTIONS,
    RETRYABLE_EXCEPTIONS,
    execute_with_retry,
    is_retryable_exception,
)
from app.utils.exceptions import (
    PlatformAuthException,
    PlatformClientException,
    PlatformNotConnectedException,
    PlatformRateLimitException,
    PlatformTransientException,
    PlatformUserNotFoundException,
    PlatformValidationException,
)


def test_is_retryable_exception_classification() -> None:
    """Verify correct classification of transient vs permanent exceptions."""
    # Retryable exceptions
    assert is_retryable_exception(PlatformTransientException(platform="GitHub", message="503"))
    assert is_retryable_exception(PlatformRateLimitException(platform="GitHub"))
    assert is_retryable_exception(PlatformClientException(platform="GitHub", message="network drop"))
    assert is_retryable_exception(httpx.ConnectError("Connection refused"))
    assert is_retryable_exception(httpx.ReadTimeout("Timeout reading response"))
    assert is_retryable_exception(httpx.NetworkError("Network down"))
    assert is_retryable_exception(ConnectionError("Socket closed"))
    assert is_retryable_exception(TimeoutError("Operation timed out"))

    # Non-retryable exceptions
    assert not is_retryable_exception(PlatformUserNotFoundException(platform="GitHub", username="ghost"))
    assert not is_retryable_exception(PlatformValidationException(platform="GitHub", details="bad schema"))
    assert not is_retryable_exception(PlatformAuthException(platform="GitHub"))
    assert not is_retryable_exception(PlatformNotConnectedException(platform="GitHub"))
    assert not is_retryable_exception(ValueError("Invalid argument"))
    assert not is_retryable_exception(TypeError("Bad type"))
    assert not is_retryable_exception(KeyError("missing_key"))
    assert not is_retryable_exception(AttributeError("no attribute"))


@pytest.mark.asyncio
async def test_execute_with_retry_first_attempt_success() -> None:
    """Verify successful operation executes once with zero retries and zero sleep."""
    user_id = uuid4()
    mock_op = AsyncMock(return_value={"status": "ok"})

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await execute_with_retry(
            operation=mock_op,
            platform="GitHub",
            user_id=user_id,
        )

        assert result == {"status": "ok"}
        mock_op.assert_called_once()
        mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_execute_with_retry_transient_failure_then_success() -> None:
    """Verify transient error triggers exponential backoff and succeeds on retry 1."""
    user_id = uuid4()
    mock_op = AsyncMock(
        side_effect=[
            PlatformTransientException(platform="GitHub", message="503 Service Unavailable"),
            {"status": "recovered"},
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("app.services.scheduler.retry.logger") as mock_logger:

        result = await execute_with_retry(
            operation=mock_op,
            platform="GitHub",
            user_id=user_id,
            max_retries=3,
            base_delay=1.0,
            backoff_factor=2.0,
        )

        assert result == {"status": "recovered"}
        assert mock_op.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

        # Verify structured retry log
        mock_logger.warning.assert_called_once()
        warning_args = mock_logger.warning.call_args
        assert "Transient error syncing" in warning_args[0][0]
        extra_data = warning_args[1]["extra"]["extra_data"]
        assert extra_data["event"] == "sync_retry"
        assert extra_data["platform"] == "GitHub"
        assert extra_data["retry_attempt"] == 1
        assert extra_data["delay_seconds"] == 1.0



@pytest.mark.asyncio
async def test_execute_with_retry_multiple_transient_failures_then_success() -> None:
    """Verify multiple transient failures sleep with exponential delays (1.0s, 2.0s)."""
    user_id = uuid4()
    mock_op = AsyncMock(
        side_effect=[
            httpx.ConnectError("Connection refused"),
            PlatformRateLimitException(platform="LeetCode"),
            {"status": "ok_on_attempt_3"},
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await execute_with_retry(
            operation=mock_op,
            platform="LeetCode",
            user_id=user_id,
            max_retries=3,
            base_delay=1.0,
            backoff_factor=2.0,
        )

        assert result == {"status": "ok_on_attempt_3"}
        assert mock_op.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)


@pytest.mark.asyncio
async def test_execute_with_retry_exhaustion() -> None:
    """Verify retry exhaustion raises the original exception after max_retries attempts."""
    user_id = uuid4()
    transient_err = PlatformTransientException(platform="GitHub", message="Down")
    mock_op = AsyncMock(side_effect=transient_err)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("app.services.scheduler.retry.logger") as mock_logger:

        with pytest.raises(PlatformTransientException) as exc_info:
            await execute_with_retry(
                operation=mock_op,
                platform="GitHub",
                user_id=user_id,
                max_retries=3,
                base_delay=1.0,
                backoff_factor=2.0,
            )

        assert exc_info.value is transient_err
        # 1 initial attempt + 3 retries = 4 total calls
        assert mock_op.call_count == 4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

        # Verify structured permanent failure log
        mock_logger.error.assert_called_once()
        error_args = mock_logger.error.call_args
        assert "failed permanently" in error_args[0][0]
        extra_data = error_args[1]["extra"]["extra_data"]
        assert extra_data["event"] == "sync_failure_permanent"
        assert extra_data["platform"] == "GitHub"
        assert extra_data["attempt"] == 4
        assert extra_data["max_retries"] == 3
        assert extra_data["retryable"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "non_retryable_exc",
    [
        PlatformUserNotFoundException(platform="GitHub", username="ghost"),
        PlatformValidationException(platform="GitHub", details="Missing keys"),
        PlatformAuthException(platform="GitHub"),
        PlatformNotConnectedException(platform="GitHub"),
        ValueError("Deterministic input error"),
        TypeError("Invalid type"),
    ],
)
async def test_execute_with_retry_non_retryable_fails_immediately(
    non_retryable_exc: Exception,
) -> None:
    """Verify non-retryable exceptions immediately fail on first attempt with 0 retries."""
    user_id = uuid4()
    mock_op = AsyncMock(side_effect=non_retryable_exc)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("app.services.scheduler.retry.logger") as mock_logger:

        with pytest.raises(type(non_retryable_exc)):
            await execute_with_retry(
                operation=mock_op,
                platform="GitHub",
                user_id=user_id,
                max_retries=3,
            )

        mock_op.assert_called_once()
        mock_sleep.assert_not_called()

        mock_logger.error.assert_called_once()
        extra_data = mock_logger.error.call_args[1]["extra"]["extra_data"]
        assert extra_data["event"] == "sync_failure_permanent"
        assert extra_data["retryable"] is False
        assert extra_data["attempt"] == 1


@pytest.mark.asyncio
async def test_execute_with_retry_custom_backoff_parameters() -> None:
    """Verify custom backoff parameters (base_delay=0.5, factor=3.0, max_retries=2)."""
    user_id = uuid4()
    mock_op = AsyncMock(
        side_effect=[
            PlatformTransientException(platform="GitHub", message="Fail 1"),
            PlatformTransientException(platform="GitHub", message="Fail 2"),
            {"status": "ok"},
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await execute_with_retry(
            operation=mock_op,
            platform="GitHub",
            user_id=user_id,
            max_retries=2,
            base_delay=0.5,
            backoff_factor=3.0,
        )

        assert result == {"status": "ok"}
        assert mock_op.call_count == 3
        assert mock_sleep.call_count == 2
        # attempt 0 retry: 0.5 * (3.0^0) = 0.5s
        # attempt 1 retry: 0.5 * (3.0^1) = 1.5s
        mock_sleep.assert_any_call(0.5)
        mock_sleep.assert_any_call(1.5)
