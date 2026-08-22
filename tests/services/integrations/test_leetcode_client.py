import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.integrations.leetcode import LeetCodeClient
from app.services.integrations.base import BasePlatformClient
from app.utils.exceptions import (
    PlatformUserNotFoundException,
    PlatformRateLimitException,
    PlatformClientException,
    PlatformTransientException,
)

def test_leetcode_client_implements_base() -> None:
    """Verify that LeetCodeClient inherits from BasePlatformClient and implements platform_name."""
    client = LeetCodeClient()
    assert isinstance(client, BasePlatformClient)
    assert client.platform_name == "leetcode"

def test_leetcode_client_headers_config() -> None:
    """Verify that Content-Type and Accept headers are set correctly."""
    client = LeetCodeClient()
    assert client.headers["Content-Type"] == "application/json"
    assert client.headers["Accept"] == "application/json"

@pytest.mark.asyncio
async def test_fetch_raw_data_success() -> None:
    """Verify successful retrieval of LeetCode profile, submissions, and tag solved stats."""
    client = LeetCodeClient(base_url="https://leetcode.com/graphql", rate_limit_max=100)
    
    mock_payload = {
        "data": {
            "matchedUser": {
                "username": "testuser",
                "profile": {
                    "realName": "Test User",
                    "aboutMe": "Developer Bio",
                    "userAvatar": "https://example.com/avatar.jpg"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 50, "submissions": 100}
                    ]
                },
                "tagProblemsSolved": {
                    "fundamental": [],
                    "intermediate": [],
                    "advanced": []
                }
            }
        }
    }
    
    mock_post = AsyncMock()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_post.return_value = mock_resp
    
    with patch("httpx.AsyncClient.post", mock_post):
        result = await client.fetch_raw_data("testuser")
        
        # Verify result structure matches the full returned payload
        assert result == mock_payload
        assert mock_post.call_count == 1
        call_args, call_kwargs = mock_post.call_args
        assert call_kwargs["json"]["variables"]["username"] == "testuser"

@pytest.mark.asyncio
async def test_nonexistent_user_raises_user_not_found() -> None:
    """Verify that matchedUser: null in GraphQL payload raises PlatformUserNotFoundException."""
    client = LeetCodeClient()
    mock_payload = {"data": {"matchedUser": None}}
    
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformUserNotFoundException) as excinfo:
            await client.fetch_raw_data("nonexistent")
        assert excinfo.value.status_code == 404
        assert "nonexistent" in excinfo.value.message

@pytest.mark.asyncio
async def test_graphql_errors_list_raises_client_exception() -> None:
    """Verify that other GraphQL query errors raise PlatformClientException."""
    client = LeetCodeClient()
    mock_payload = {
        "errors": [{"message": "Syntax Error in Query"}]
    }
    
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformClientException) as excinfo:
            await client.fetch_raw_data("testuser")
        assert "Syntax Error in Query" in excinfo.value.message

@pytest.mark.asyncio
async def test_graphql_rate_limit_error_raises_rate_limit_exception() -> None:
    """Verify that GraphQL rate limiting warning messages raise PlatformRateLimitException."""
    client = LeetCodeClient()
    mock_payload = {
        "errors": [{"message": "API rate limit exceeded for IP"}]
    }
    
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformRateLimitException):
            await client.fetch_raw_data("testuser")

@pytest.mark.asyncio
async def test_rate_limit_429() -> None:
    """Verify HTTP status 429 raises PlatformRateLimitException."""
    client = LeetCodeClient()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformRateLimitException):
            await client.fetch_raw_data("testuser")

@pytest.mark.asyncio
async def test_endpoint_error_404_raises_client_exception() -> None:
    """Verify HTTP status 404 from endpoint raises PlatformClientException (not user not found)."""
    client = LeetCodeClient()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformClientException) as excinfo:
            await client.fetch_raw_data("testuser")
        assert "404" in excinfo.value.message
        assert not isinstance(excinfo.value, PlatformUserNotFoundException)

@pytest.mark.asyncio
async def test_transient_error_503_triggers_retry() -> None:
    """Verify HTTP status 503 triggers retries, resolving on success on a later attempt."""
    client = LeetCodeClient()
    
    mock_resp_503 = MagicMock(spec=httpx.Response)
    mock_resp_503.status_code = 503
    mock_resp_503.text = "Service Unavailable"
    
    mock_resp_success = MagicMock(spec=httpx.Response)
    mock_resp_success.status_code = 200
    mock_resp_success.json.return_value = {"data": {"matchedUser": {"username": "testuser"}}}
    
    mock_post = AsyncMock()
    mock_post.side_effect = [mock_resp_503, mock_resp_success]
    
    with patch("httpx.AsyncClient.post", mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.fetch_raw_data("testuser")
            
            assert result["data"]["matchedUser"]["username"] == "testuser"
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_once_with(1.0)

@pytest.mark.asyncio
async def test_timeout_triggers_retry() -> None:
    """Verify httpx.TimeoutException triggers retries."""
    client = LeetCodeClient()
    
    mock_resp_success = MagicMock(spec=httpx.Response)
    mock_resp_success.status_code = 200
    mock_resp_success.json.return_value = {"data": {"matchedUser": {"username": "testuser"}}}
    
    mock_post = AsyncMock()
    mock_post.side_effect = [httpx.TimeoutException("Connection Timeout"), mock_resp_success]
    
    with patch("httpx.AsyncClient.post", mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.fetch_raw_data("testuser")
            
            assert result["data"]["matchedUser"]["username"] == "testuser"
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_once_with(1.0)

@pytest.mark.asyncio
async def test_malformed_json_raises_client_exception() -> None:
    """Verify malformed JSON responses raise PlatformClientException."""
    client = LeetCodeClient()
    
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    # Simulate malformed payload (missing expected data keys completely)
    mock_resp.json.return_value = {"random": "payload"}
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(PlatformUserNotFoundException): # because matchedUser is not in the data dict
            await client.fetch_raw_data("testuser")
