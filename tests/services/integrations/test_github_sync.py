import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.profile import Profile
from app.models.github_snapshot import GitHubSnapshot
from app.repositories.profile import ProfileRepository
from app.repositories.github_snapshot import GitHubSnapshotRepository
from app.services.integrations.github import GitHubClient
from app.services.integrations.github_parser import GitHubDataParser
from app.services.integrations.github_sync import GitHubSyncService
from app.schemas.sync import GitHubSyncResult
from app.utils.exceptions import (
    PlatformNotConnectedException,
    PlatformValidationException,
    PlatformRateLimitException,
)

# --- Pytest Fixtures ---

@pytest.fixture
def mock_snapshot_repo() -> MagicMock:
    """Fixture returning a mocked GitHubSnapshotRepository."""
    repo = MagicMock(spec=GitHubSnapshotRepository)
    repo.create = AsyncMock(side_effect=lambda x: x)
    return repo

# --- GitHubDataParser Tests ---

def test_parser_success() -> None:
    """Verify successful parsing of a complete, valid GitHub API payload."""
    raw_payload = {
        "profile": {
            "id": 12345,
            "login": "testuser",
            "avatar_url": "https://avatars.github.com/u/testuser",
            "bio": "Software Engineer"
        },
        "repositories": [
            {
                "id": 9991,
                "name": "repo1",
                "full_name": "testuser/repo1",
                "description": "Awesome repo 1",
                "html_url": "https://github.com/testuser/repo1",
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 2,
                "open_issues_count": 1,
                "size": 500,
                "created_at": "2020-01-01T12:00:00Z",
                "updated_at": "2020-02-01T12:00:00Z",
                "pushed_at": "2020-02-15T12:00:00Z",
                "fork": False,
                "private": False,
                "archived": False
            },
            {
                "id": 9992,
                "name": "repo2",
                "full_name": "testuser/repo2",
                "description": None,
                "html_url": "https://github.com/testuser/repo2",
                "language": "TypeScript",
                "stargazers_count": 5,
                "forks_count": 0,
                "open_issues_count": 0,
                "size": 250,
                "created_at": "2021-06-01T12:00:00Z",
                "updated_at": "2021-07-01T12:00:00Z",
                "pushed_at": None,
                "fork": True,
                "private": True,
                "archived": True
            }
        ]
    }
    
    parsed = GitHubDataParser.parse(raw_payload)
    
    assert parsed.login == "testuser"
    assert parsed.bio == "Software Engineer"
    assert parsed.avatar_url == "https://avatars.github.com/u/testuser"
    assert parsed.repositories_count == 2
    
    # Aggregated stats assertions
    assert parsed.total_stars == 15
    assert parsed.total_forks == 2
    assert parsed.total_size == 750
    assert parsed.total_open_issues == 1
    assert parsed.languages == {"Python": 1, "TypeScript": 1}
    
    # Repository details assertions
    repo1 = parsed.repositories[0]
    assert repo1.github_id == 9991
    assert repo1.name == "repo1"
    assert repo1.language == "Python"
    assert repo1.is_fork is False
    assert repo1.is_private is False
    assert repo1.is_archived is False
    assert repo1.created_at.year == 2020
    
    repo2 = parsed.repositories[1]
    assert repo2.github_id == 9992
    assert repo2.name == "repo2"
    assert repo2.language == "TypeScript"
    assert repo2.is_fork is True
    assert repo2.is_private is True
    assert repo2.is_archived is True

def test_parser_missing_optional_fields() -> None:
    """Verify that omitting optional fields results in clean None parsing."""
    raw_payload = {
        "profile": {
            "id": 12345,
            "login": "testuser",
        },
        "repositories": [
            {
                "id": 9991,
                "name": "repo1",
                "full_name": "testuser/repo1",
                "html_url": "https://github.com/testuser/repo1",
                "stargazers_count": 0,
                "forks_count": 0,
                "open_issues_count": 0,
                "size": 10,
                "created_at": "2020-01-01T12:00:00Z",
                "updated_at": "2020-01-01T12:00:00Z",
                "fork": False,
                "private": False,
                "archived": False
            }
        ]
    }
    
    parsed = GitHubDataParser.parse(raw_payload)
    assert parsed.bio is None
    assert parsed.avatar_url is None
    assert parsed.repositories[0].description is None
    assert parsed.repositories[0].language is None

def test_parser_empty_repository_list() -> None:
    """Verify parser handles profiles with zero repositories."""
    raw_payload = {
        "profile": {
            "id": 12345,
            "login": "testuser"
        },
        "repositories": []
    }
    
    parsed = GitHubDataParser.parse(raw_payload)
    assert parsed.repositories_count == 0
    assert parsed.total_stars == 0
    assert parsed.languages == {}

def test_parser_malformed_type_raises_exception() -> None:
    """Verify that invalid field types raise PlatformValidationException."""
    raw_payload = {
        "profile": {
            "id": 12345,
            "login": "testuser"
        },
        "repositories": [
            {
                "id": "not-an-int-id", # StrictInt constraint violation
                "name": "repo1",
                "full_name": "testuser/repo1",
                "html_url": "https://github.com/testuser/repo1",
                "stargazers_count": 0,
                "forks_count": 0,
                "open_issues_count": 0,
                "size": 10,
                "created_at": "2020-01-01T12:00:00Z",
                "updated_at": "2020-01-01T12:00:00Z",
                "fork": False,
                "private": False,
                "archived": False
            }
        ]
    }
    
    with pytest.raises(PlatformValidationException):
        GitHubDataParser.parse(raw_payload)

# --- GitHubSyncService Tests ---

@pytest.mark.asyncio
async def test_sync_missing_profile_raises_not_connected(mock_snapshot_repo: MagicMock) -> None:
    """Verify that a user without a profile raises PlatformNotConnectedException."""
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=None)
    github_client = MagicMock(spec=GitHubClient)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    
    with pytest.raises(PlatformNotConnectedException):
        await service.sync_github_data(uuid.uuid4())

@pytest.mark.asyncio
async def test_sync_missing_github_username_raises_not_connected(mock_snapshot_repo: MagicMock) -> None:
    """Verify that a profile without a connected github_username raises PlatformNotConnectedException."""
    profile = Profile(user_id=uuid.uuid4(), github_username=None)
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    github_client = MagicMock(spec=GitHubClient)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    
    with pytest.raises(PlatformNotConnectedException):
        await service.sync_github_data(profile.user_id)

@pytest.mark.asyncio
async def test_sync_success_profile_updated(mock_snapshot_repo: MagicMock) -> None:
    """Verify that new non-null GitHub bio/avatar values update the database Profile."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Old Bio",
        avatar_url="https://old.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(return_value=profile)
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 12345,
            "login": "testuser",
            "bio": "New Bio from GitHub",
            "avatar_url": "https://new.com/avatar.png"
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    result = await service.sync_github_data(profile.user_id)
    
    assert result.success is True
    assert result.profile_updated is True
    assert result.github_username == "testuser"
    assert profile.bio == "New Bio from GitHub"
    assert profile.avatar_url == "https://new.com/avatar.png"
    profile_repo.update.assert_called_once_with(profile)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_only_bio_changes(mock_snapshot_repo: MagicMock) -> None:
    """Verify update is triggered when only the bio field changes."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Old Bio",
        avatar_url="https://same.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(return_value=profile)
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 123,
            "login": "testuser",
            "bio": "New Bio",
            "avatar_url": "https://same.com/avatar.png"
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    result = await service.sync_github_data(profile.user_id)
    
    assert result.profile_updated is True
    assert profile.bio == "New Bio"
    profile_repo.update.assert_called_once_with(profile)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_only_avatar_changes(mock_snapshot_repo: MagicMock) -> None:
    """Verify update is triggered when only the avatar field changes."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Same Bio",
        avatar_url="https://old.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(return_value=profile)
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 123,
            "login": "testuser",
            "bio": "Same Bio",
            "avatar_url": "https://new.com/avatar.png"
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    result = await service.sync_github_data(profile.user_id)
    
    assert result.profile_updated is True
    assert profile.avatar_url == "https://new.com/avatar.png"
    profile_repo.update.assert_called_once_with(profile)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_idempotency_fields_unchanged(mock_snapshot_repo: MagicMock) -> None:
    """Verify that identical data triggers no database write."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Same Bio",
        avatar_url="https://same.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 123,
            "login": "testuser",
            "bio": "Same Bio",
            "avatar_url": "https://same.com/avatar.png"
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    result = await service.sync_github_data(profile.user_id)
    
    assert result.profile_updated is False
    profile_repo.update.assert_not_called()
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_null_value_preserves_local_data(mock_snapshot_repo: MagicMock) -> None:
    """Verify that incoming null values from GitHub do not erase existing local profile values."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Valuable Bio",
        avatar_url="https://valuable.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 123,
            "login": "testuser",
            "bio": None,
            "avatar_url": None
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    result = await service.sync_github_data(profile.user_id)
    
    assert result.profile_updated is False
    assert profile.bio == "Valuable Bio"
    assert profile.avatar_url == "https://valuable.com/avatar.png"
    profile_repo.update.assert_not_called()
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_client_failures_propagate_without_db_updates(mock_snapshot_repo: MagicMock) -> None:
    """Verify that downstream client errors propagate directly and do not run database updates."""
    profile = Profile(user_id=uuid.uuid4(), github_username="testuser")
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    github_client = MagicMock(spec=GitHubClient)
    github_client.fetch_raw_data = AsyncMock(side_effect=PlatformRateLimitException(platform="GitHub"))
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    
    with pytest.raises(PlatformRateLimitException):
        await service.sync_github_data(profile.user_id)
        
    profile_repo.update.assert_not_called()
    mock_snapshot_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_sync_parser_failures_result_in_no_db_updates(mock_snapshot_repo: MagicMock) -> None:
    """Verify that payload parsing validation failures result in no database updates."""
    profile = Profile(user_id=uuid.uuid4(), github_username="testuser")
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {"profile": {}, "repositories": "invalid-repos-format"}
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    
    with pytest.raises(PlatformValidationException):
        await service.sync_github_data(profile.user_id)
        
    profile_repo.update.assert_not_called()
    # Snapshot must still be committed under separate stage transaction flow (Option A)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_persistence_failure_propagates(mock_snapshot_repo: MagicMock) -> None:
    """Verify that database transaction/commit failure propagates directly to the caller."""
    profile = Profile(
        user_id=uuid.uuid4(),
        github_username="testuser",
        bio="Old Bio",
        avatar_url="https://old.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(side_effect=RuntimeError("Database Connection Lost"))
    
    github_client = MagicMock(spec=GitHubClient)
    raw_payload = {
        "profile": {
            "id": 123,
            "login": "testuser",
            "bio": "New Bio",
            "avatar_url": "https://old.com/avatar.png"
        },
        "repositories": []
    }
    github_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = GitHubSyncService(profile_repo, github_client, mock_snapshot_repo)
    
    with pytest.raises(RuntimeError, match="Database Connection Lost"):
        await service.sync_github_data(profile.user_id)
