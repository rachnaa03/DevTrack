import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch
from app.services.integrations.helpers import AsyncRateLimiter, async_retry

# --- AsyncRateLimiter Tests ---

def test_rate_limiter_invalid_config() -> None:
    """Verify that invalid configurations raise ValueError."""
    with pytest.raises(ValueError, match="max_requests must be greater than 0"):
        AsyncRateLimiter(max_requests=0, period_seconds=1.0)
        
    with pytest.raises(ValueError, match="max_requests must be greater than 0"):
        AsyncRateLimiter(max_requests=-5, period_seconds=1.0)

    with pytest.raises(ValueError, match="period_seconds must be greater than 0"):
        AsyncRateLimiter(max_requests=5, period_seconds=0)

    with pytest.raises(ValueError, match="period_seconds must be greater than 0"):
        AsyncRateLimiter(max_requests=5, period_seconds=-1.5)

@pytest.mark.asyncio
async def test_rate_limiter_under_limit() -> None:
    """Verify that requests under the limit pass immediately without sleeping."""
    limiter = AsyncRateLimiter(max_requests=3, period_seconds=10.0)
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_rate_limiter_exceeds_limit_triggers_sleep() -> None:
    """Verify that exceeding the limit triggers asyncio.sleep with correct duration."""
    limiter = AsyncRateLimiter(max_requests=2, period_seconds=5.0)
    
    # Pre-populate timestamps to simulate previous requests
    now = time.monotonic()
    limiter.requests.append(now - 4.0) # oldest request, expires in 1.0s
    limiter.requests.append(now - 2.0) # newest request, expires in 3.0s
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # First call inside acquire will see queue is full, will calculate sleep_time = oldest + 5.0 - now
        # oldest + 5.0 - now = now - 4.0 + 5.0 - now = 1.0s
        # To prevent infinite loop in test, we make the second check succeed by clearing requests
        async def side_effect(*args, **kwargs):
            limiter.requests.clear()
        mock_sleep.side_effect = side_effect
        
        await limiter.acquire()
        
        mock_sleep.assert_called_once()
        # The sleep time should be approximately 1.0s (allow minor float margin)
        sleep_arg = mock_sleep.call_args[0][0]
        assert pytest.approx(sleep_arg, abs=0.1) == 1.0

@pytest.mark.asyncio
async def test_rate_limiter_concurrency() -> None:
    """Verify that concurrent acquisitions do not violate the rate limit."""
    # Limit: 2 requests per 10 seconds
    limiter = AsyncRateLimiter(max_requests=2, period_seconds=10.0)
    
    # We run 3 concurrent acquires
    # The first 2 should succeed immediately. The 3rd should be forced to sleep.
    sleep_calls = []
    
    original_sleep = asyncio.sleep
    async def mock_sleep(delay):
        sleep_calls.append(delay)
        # Clear the queue to let the loop exit during test
        limiter.requests.clear()
        await original_sleep(0.001)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        await asyncio.gather(
            limiter.acquire(),
            limiter.acquire(),
            limiter.acquire()
        )
        
    # We should have triggered exactly 1 sleep call for the 3rd request
    assert len(sleep_calls) == 1
    assert sleep_calls[0] > 0


# --- async_retry Tests ---

def test_retry_invalid_config() -> None:
    """Verify that invalid decorator configurations raise ValueError."""
    with pytest.raises(ValueError, match="max_retries must be greater than or equal to 0"):
        async_retry(max_retries=-1)
        
    with pytest.raises(ValueError, match="initial_delay must be greater than or equal to 0"):
        async_retry(initial_delay=-0.5)

    with pytest.raises(ValueError, match="backoff_factor must be greater than 0"):
        async_retry(backoff_factor=0)

    with pytest.raises(ValueError, match="backoff_factor must be greater than 0"):
        async_retry(backoff_factor=-2.0)

@pytest.mark.asyncio
async def test_retry_success_first_attempt() -> None:
    """Verify successful execution on first attempt does not retry or sleep."""
    call_count = 0
    
    @async_retry(max_retries=3, initial_delay=1.0)
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        return "success"

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await dummy_func()
        assert result == "success"
        assert call_count == 1
        mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_retry_exhausted_raises_original_exception() -> None:
    """Verify that after exhausting max_retries, the original exception is raised."""
    call_count = 0
    
    @async_retry(max_retries=2, initial_delay=1.0, exceptions_to_catch=(ValueError,))
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("transient failure")

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(ValueError, match="transient failure") as excinfo:
            await dummy_func()
        
        # Max retries = 2 -> 3 total attempts
        assert call_count == 3
        # Should have slept twice before failure
        assert mock_sleep.call_count == 2
        # Check sleep delay sequence: 1.0, 2.0 (factor = 2.0 by default)
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0]

@pytest.mark.asyncio
async def test_retry_untracked_exception_propagates_immediately() -> None:
    """Verify that exceptions not in exceptions_to_catch are raised immediately without retry."""
    call_count = 0
    
    @async_retry(max_retries=5, initial_delay=1.0, exceptions_to_catch=(KeyError,))
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("untracked failure")

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(ValueError, match="untracked failure"):
            await dummy_func()
        
        assert call_count == 1
        mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_retry_zero_performs_only_one_attempt() -> None:
    """Verify that max_retries=0 performs exactly one attempt and raises exception on failure."""
    call_count = 0
    
    @async_retry(max_retries=0, initial_delay=1.0, exceptions_to_catch=(Exception,))
    async def dummy_func():
        nonlocal call_count
        call_count += 1
        raise KeyError("fail")

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(KeyError, match="fail"):
            await dummy_func()
        
        assert call_count == 1
        mock_sleep.assert_not_called()
