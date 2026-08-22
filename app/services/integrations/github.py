import logging
from typing import Any
import httpx

from app.core.config import settings
from app.services.integrations.base import BasePlatformClient
from app.services.integrations.helpers import AsyncRateLimiter, async_retry
from app.utils.exceptions import (
    PlatformAuthException,
    PlatformClientException,
    PlatformRateLimitException,
    PlatformTransientException,
    PlatformUserNotFoundException,
)

logger = logging.getLogger(__name__)

_SENTINEL = object()

class GitHubClient(BasePlatformClient):
    """
    Concrete implementation of BasePlatformClient for communicating with the GitHub REST API.
    """
    def __init__(
        self,
        base_url: str | None = None,
        token: Any = _SENTINEL,
        rate_limit_max: int | None = None,
        rate_limit_period: float | None = None,
    ) -> None:
        self.base_url = base_url or settings.GITHUB_API_URL
        self.token = settings.GITHUB_API_TOKEN if token is _SENTINEL else token
        
        # 1. Determine rate limit configuration explicitly
        if rate_limit_max is not None:
            max_reqs = rate_limit_max
        elif settings.GITHUB_RATE_LIMIT_OVERRIDE is not None:
            max_reqs = settings.GITHUB_RATE_LIMIT_OVERRIDE
        elif self.token:
            max_reqs = settings.GITHUB_RATE_LIMIT_AUTH
        else:
            max_reqs = settings.GITHUB_RATE_LIMIT_UNAUTH
            
        period = rate_limit_period or settings.GITHUB_RATE_LIMIT_PERIOD
        self.limiter = AsyncRateLimiter(max_requests=max_reqs, period_seconds=period)
        
        # 2. Configure HTTP headers (do not log/expose token value)
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
            
        logger.info(f"Initialized GitHubClient with base URL: {self.base_url}")

    @property
    def platform_name(self) -> str:
        return "github"

    @async_retry(
        max_retries=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions_to_catch=(httpx.TimeoutException, httpx.ConnectError, PlatformTransientException),
    )
    async def _make_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        username: str,
        params: dict | None = None
    ) -> httpx.Response:
        """
        Internal request helper wrapped with the async_retry decorator.
        Only retries transient network/server failures.
        """
        try:
            # Enforce client-side rate limiting before outbound request
            await self.limiter.acquire()
            response = await client.get(url, params=params)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Let network and timeout failures be caught by the decorator to trigger retry
            raise
        except httpx.RequestError as e:
            # Wrap general request/network failures in PlatformClientException (permanent, no retry)
            raise PlatformClientException(platform="GitHub", message=str(e))

        status_code = response.status_code

        if 200 <= status_code < 300:
            return response

        if status_code == 401:
            raise PlatformAuthException(platform="GitHub")

        if status_code == 403:
            # Check headers and body for rate-limit exhaustion evidence
            is_rate_limit = (
                response.headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in response.text.lower()
            )
            if is_rate_limit:
                raise PlatformRateLimitException(platform="GitHub")
            else:
                raise PlatformClientException(platform="GitHub", message=f"Access forbidden (403)")

        if status_code == 404:
            raise PlatformUserNotFoundException(platform="GitHub", username=username)

        if status_code == 429:
            raise PlatformRateLimitException(platform="GitHub")

        if 500 <= status_code < 600:
            # Raise PlatformTransientException (transient, retryable)
            raise PlatformTransientException(platform="GitHub", message=f"Server error ({status_code})")

        raise PlatformClientException(platform="GitHub", message=f"Unexpected status code {status_code}")

    async def fetch_raw_data(self, username: str) -> dict[str, Any]:
        """
        Asynchronously fetches the complete profile and public repositories for a given GitHub username.
        Handles pagination of repositories to ensure data is not truncated.
        """
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            # 1. Fetch Profile
            profile_url = f"{self.base_url}/users/{username}"
            profile_response = await self._make_request(client, profile_url, username=username)
            profile_data = profile_response.json()

            # 2. Fetch Repositories with Pagination
            repos = []
            page = 1
            repos_url = f"{self.base_url}/users/{username}/repos"
            
            while True:
                params = {"per_page": 100, "page": page}
                repos_response = await self._make_request(client, repos_url, username=username, params=params)
                page_repos = repos_response.json()
                
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                
                if len(page_repos) < 100:
                    break
                    
                page += 1

            return {
                "profile": profile_data,
                "repositories": repos
            }
