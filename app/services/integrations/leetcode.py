import logging
from typing import Any
import httpx

from app.core.config import settings
from app.services.integrations.base import BasePlatformClient
from app.services.integrations.helpers import AsyncRateLimiter, async_retry
from app.utils.exceptions import (
    PlatformClientException,
    PlatformRateLimitException,
    PlatformTransientException,
    PlatformUserNotFoundException,
)

logger = logging.getLogger(__name__)

class LeetCodeClient(BasePlatformClient):
    """
    Concrete implementation of BasePlatformClient for communicating with the LeetCode GraphQL API.
    """
    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_max: int | None = None,
        rate_limit_period: float | None = None,
    ) -> None:
        self.base_url = base_url or settings.LEETCODE_API_URL
        
        # Determine rate limit configuration explicitly
        if rate_limit_max is not None:
            max_reqs = rate_limit_max
        elif settings.LEETCODE_RATE_LIMIT_OVERRIDE is not None:
            max_reqs = settings.LEETCODE_RATE_LIMIT_OVERRIDE
        else:
            max_reqs = settings.LEETCODE_RATE_LIMIT_MAX
            
        period = rate_limit_period or settings.LEETCODE_RATE_LIMIT_PERIOD
        self.limiter = AsyncRateLimiter(max_requests=max_reqs, period_seconds=period)
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        logger.info(f"Initialized LeetCodeClient with base URL: {self.base_url}")

    @property
    def platform_name(self) -> str:
        return "leetcode"

    @async_retry(
        max_retries=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions_to_catch=(httpx.TimeoutException, httpx.ConnectError, PlatformTransientException),
    )
    async def _make_request(
        self,
        client: httpx.AsyncClient,
        query: str,
        variables: dict[str, Any],
        username: str,
    ) -> httpx.Response:
        """
        Internal request helper wrapped with the async_retry decorator.
        Only retries transient network/server failures.
        """
        try:
            # Enforce client-side rate limiting before outbound request
            await self.limiter.acquire()
            response = await client.post(
                self.base_url,
                json={"query": query, "variables": variables}
            )
        except (httpx.TimeoutException, httpx.ConnectError):
            # Let network and timeout failures propagate to be caught by the decorator
            raise
        except httpx.RequestError as e:
            # Wrap general request/network failures in PlatformClientException (permanent, no retry)
            raise PlatformClientException(platform="LeetCode", message=str(e))

        status_code = response.status_code

        if 200 <= status_code < 300:
            return response

        if status_code == 429:
            raise PlatformRateLimitException(platform="LeetCode")

        if 500 <= status_code < 600:
            # Raise PlatformTransientException (transient, retryable)
            raise PlatformTransientException(platform="LeetCode", message=f"Server error ({status_code})")

        raise PlatformClientException(platform="LeetCode", message=f"Unexpected status code {status_code}")

    async def fetch_raw_data(self, username: str) -> dict[str, Any]:
        """
        Asynchronously fetches the complete profile, submission stats, and topic tags solved
        for a given LeetCode username using the GraphQL endpoint.
        """
        query = """
        query getLeetCodeUserData($username: String!) {
          matchedUser(username: $username) {
            username
            profile {
              realName
              aboutMe
              userAvatar
            }
            submitStats {
              acSubmissionNum {
                difficulty
                count
                submissions
              }
            }
            tagProblemsSolved {
              fundamental {
                tagName
                tagSlug
                solvedCount
              }
              intermediate {
                tagName
                tagSlug
                solvedCount
              }
              advanced {
                tagName
                tagSlug
                solvedCount
              }
            }
          }
        }
        """
        variables = {"username": username}

        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            response = await self._make_request(client, query, variables, username)
            data = response.json()

            # 1. Handle GraphQL level errors
            if "errors" in data and data["errors"]:
                err_msg = data["errors"][0].get("message", "")
                if "rate limit" in err_msg.lower() or "too many requests" in err_msg.lower():
                    raise PlatformRateLimitException(platform="LeetCode")
                raise PlatformClientException(platform="LeetCode", message=f"GraphQL error: {err_msg}")

            # 2. Handle nonexistent user (GraphQL returns matchedUser: null)
            if not data.get("data") or data["data"].get("matchedUser") is None:
                raise PlatformUserNotFoundException(platform="LeetCode", username=username)

            return data
