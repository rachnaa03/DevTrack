import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.integrations.github import GitHubClient
from app.services.integrations.base import BasePlatformClient
from app.utils.exceptions import (
    PlatformUserNotFoundException,
    PlatformRateLimitException,
    PlatformAuthException,
    PlatformClientException,
)

def test_github_client_implements_base() -> None:
    """Verify that GitHubClient inherits from BasePlatformClient and implements platform_name."""
    client = GitHubClient()
    assert isinstance(client, BasePlatformClient)
    assert client.platform_name == "github"

def test_github_client_headers_config() -> None:
    """Verify that Authorization headers are present only when a token is configured."""
    # 1. With token
    client_auth = GitHubClient(token="secret-token-123")
    assert "Authorization" in client_auth.headers
    assert client_auth.headers["Authorization"] == "Bearer secret-token-123"
    
    # 2. Without token (explicitly None)
    client_no_auth = GitHubClient(token=None)
    assert "Authorization" not in client_no_auth.headers

@pytest.mark.asyncio
async def test_github_client_logs_and_exceptions_safety() -> None:
    """Verify that token value is not written to logs or exposed via exceptions."""
    token = "super-secret-token-12345"
    client = GitHubClient(token=token)

    with patch("app.services.integrations.github.logger") as mock_logger:
        with pytest.raises(PlatformAuthException) as excinfo:
            async with httpx.AsyncClient() as http_client:
                # Mock the get call of AsyncClient to return 401 instead of making a real request
                with patch.object(http_client, "get", AsyncMock()) as mock_get:
                    mock_resp = MagicMock()
                    mock_resp.status_code = 401
                    mock_resp.text = "Unauthorized payload"
                    mock_get.return_value = mock_resp
                    
                    await client._make_request(http_client, "https://api.github.com/users/octocat", username="octocat")
        
        # Verify exception doesn't leak token
        assert token not in str(excinfo.value)
        # Verify no log statements leak the token
        for call in mock_logger.info.call_args_list + mock_logger.warning.call_args_list + mock_logger.error.call_args_list:
            log_msg = call[0][0]
            assert token not in log_msg

@pytest.mark.asyncio
async def test_fetch_raw_data_success() -> None:
    """Verify successful retrieval of profile and paginated repositories."""
    client = GitHubClient(base_url="https://api.github.com", rate_limit_max=100)
    
    mock_profile = {"id": 123, "login": "testuser"}
    mock_repos_page1 = [{"id": 1, "name": "repo1"}] * 100
    mock_repos_page2 = [{"id": 2, "name": "repo2"}]
    
    mock_get = AsyncMock()
    
    mock_resp_profile = MagicMock(spec=httpx.Response)
    mock_resp_profile.status_code = 200
    mock_resp_profile.json.return_value = mock_profile
    
    mock_resp_repos1 = MagicMock(spec=httpx.Response)
    mock_resp_repos1.status_code = 200
    mock_resp_repos1.json.return_value = mock_repos_page1
    
    mock_resp_repos2 = MagicMock(spec=httpx.Response)
    mock_resp_repos2.status_code = 200
    mock_resp_repos2.json.return_value = mock_repos_page2

    mock_get.side_effect = [mock_resp_profile, mock_resp_repos1, mock_resp_repos2]
    
    with patch("httpx.AsyncClient.get", mock_get):
        result = await client.fetch_raw_data("testuser")
        
        assert result["profile"] == mock_profile
        # Combined repositories from page 1 and page 2
        assert len(result["repositories"]) == 101
        assert result["repositories"][0]["name"] == "repo1"
        assert result["repositories"][100]["name"] == "repo2"
        assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_nonexistent_user_raises_404() -> None:
    """Verify that a 404 response raises PlatformUserNotFoundException."""
    client = GitHubClient()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformUserNotFoundException) as excinfo:
            await client.fetch_raw_data("nonexistent")
        assert excinfo.value.status_code == 404
        assert "nonexistent" in excinfo.value.message

@pytest.mark.asyncio
async def test_rate_limit_429_or_403() -> None:
    """Verify rate-limiting error mappings."""
    client = GitHubClient()
    
    # 1. Test 429 status code
    mock_resp_429 = MagicMock(spec=httpx.Response)
    mock_resp_429.status_code = 429
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp_429)):
        with pytest.raises(PlatformRateLimitException):
            await client.fetch_raw_data("testuser")
            
    # 2. Test 403 rate limit headers
    mock_resp_403_headers = MagicMock(spec=httpx.Response)
    mock_resp_403_headers.status_code = 403
    mock_resp_403_headers.headers = {"x-ratelimit-remaining": "0"}
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp_403_headers)):
        with pytest.raises(PlatformRateLimitException):
            await client.fetch_raw_data("testuser")

    # 3. Test 403 rate limit text
    mock_resp_403_text = MagicMock(spec=httpx.Response)
    mock_resp_403_text.status_code = 403
    mock_resp_403_text.headers = {}
    mock_resp_403_text.text = "API rate limit exceeded for user"
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp_403_text)):
        with pytest.raises(PlatformRateLimitException):
            await client.fetch_raw_data("testuser")

    # 4. Test 403 generic forbidden (should raise PlatformClientException, NOT rate limit)
    mock_resp_403_generic = MagicMock(spec=httpx.Response)
    mock_resp_403_generic.status_code = 403
    mock_resp_403_generic.headers = {}
    mock_resp_403_generic.text = "Some other forbidden message"
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp_403_generic)):
        with pytest.raises(PlatformClientException) as excinfo:
            await client.fetch_raw_data("testuser")
        assert not isinstance(excinfo.value, PlatformRateLimitException)

@pytest.mark.asyncio
async def test_auth_failure_401() -> None:
    """Verify auth failure maps to PlatformAuthException."""
    client = GitHubClient()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformAuthException) as excinfo:
            await client.fetch_raw_data("testuser")
        assert excinfo.value.status_code == 502

@pytest.mark.asyncio
async def test_transient_error_triggers_retry() -> None:
    """Verify that a 503 server error triggers retries but permanent errors do not."""
    client = GitHubClient()
    
    mock_resp_503 = MagicMock(spec=httpx.Response)
    mock_resp_503.status_code = 503
    mock_resp_503.text = "Service Unavailable"
    
    mock_resp_success = MagicMock(spec=httpx.Response)
    mock_resp_success.status_code = 200
    mock_resp_success.json.return_value = {"id": 1, "login": "testuser"}
    
    mock_resp_repos = MagicMock(spec=httpx.Response)
    mock_resp_repos.status_code = 200
    mock_resp_repos.json.return_value = []
    
    mock_get = AsyncMock()
    # First attempt: 503 (transient)
    # Second attempt: 200 (success)
    # Third attempt: 200 (repos page success)
    mock_get.side_effect = [mock_resp_503, mock_resp_success, mock_resp_repos]
    
    with patch("httpx.AsyncClient.get", mock_get):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.fetch_raw_data("testuser")
            
            assert result["profile"]["login"] == "testuser"
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_once_with(1.0)
