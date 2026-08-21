import asyncio
import functools
import logging
import time
from collections import deque
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger(__name__)

class AsyncRateLimiter:
    """
    An in-memory, asyncio-compatible sliding window rate limiter.
    
    Limits operations to a maximum number of requests within a specified time window.
    """
    def __init__(self, max_requests: int, period_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")
        if period_seconds <= 0:
            raise ValueError("period_seconds must be greater than 0")
            
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.requests: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a slot. If the rate limit is exceeded, suspends the coroutine
        until a slot becomes available. Re-checks the window before reserving a slot.
        """
        while True:
            # We acquire the lock ONLY to inspect and modify the shared state (the timestamp queue).
            async with self.lock:
                now = time.monotonic()
                # 1. Clean up expired timestamps outside the configured period window
                while self.requests and self.requests[0] <= now - self.period_seconds:
                    self.requests.popleft()
                
                # 2. If below max_requests, record timestamp and return immediately
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return
                
                # 3. Calculate how long until the oldest request exits the active window
                sleep_time = self.requests[0] + self.period_seconds - now

            # We release the lock BEFORE sleeping. This allows other coroutines to execute
            # and enter the acquire loop (and possibly also compute their wait times and sleep concurrently).
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)


def async_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions_to_catch: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator that retries an asynchronous function using exponential backoff.

    Retry semantics:
        max_retries is the number of retries after the initial attempt.
        - max_retries=0: 1 total attempt (0 retries)
        - max_retries=N: N+1 total attempts (N retries)

    Delay sequence:
        attempt 1 retry delay: initial_delay
        attempt 2 retry delay: initial_delay * backoff_factor
        attempt 3 retry delay: initial_delay * backoff_factor^2
        ...
    """
    if max_retries < 0:
        raise ValueError("max_retries must be greater than or equal to 0")
    if initial_delay < 0:
        raise ValueError("initial_delay must be greater than or equal to 0")
    if backoff_factor <= 0:
        raise ValueError("backoff_factor must be greater than 0")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            # total attempts = max_retries + 1 (initial attempt + max_retries)
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions_to_catch as e:
                    # If this is the last attempt, re-raise the exception immediately
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries. "
                            f"Final error: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} raised {e.__class__.__name__}. "
                        f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})."
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            return None
        return wrapper
    return decorator
