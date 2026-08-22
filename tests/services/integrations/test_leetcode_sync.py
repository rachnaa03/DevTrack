import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.profile import Profile
from app.models.leetcode_snapshot import LeetCodeSnapshot
from app.repositories.profile import ProfileRepository
from app.repositories.leetcode_snapshot import LeetCodeSnapshotRepository
from app.services.integrations.leetcode import LeetCodeClient
from app.services.integrations.leetcode_parser import LeetCodeDataParser
from app.services.integrations.leetcode_sync import LeetCodeSyncService
from app.schemas.sync import LeetCodeSyncResult
from app.utils.exceptions import (
    PlatformNotConnectedException,
    PlatformValidationException,
    PlatformClientException,
)

# --- Pytest Fixtures ---

@pytest.fixture
def mock_snapshot_repo() -> MagicMock:
    """Fixture returning a mocked LeetCodeSnapshotRepository."""
    repo = MagicMock(spec=LeetCodeSnapshotRepository)
    repo.create = AsyncMock(side_effect=lambda x: x)
    return repo

# --- LeetCodeDataParser Tests ---

def test_parser_success() -> None:
    """Verify successful parsing of a complete, valid LeetCode payload."""
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "leetcode_user",
                "profile": {
                    "realName": "LeetCode Coder",
                    "aboutMe": "Software Engineer & Competitor",
                    "userAvatar": "https://assets.leetcode.com/avatar.jpg"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 100, "submissions": 200},
                        {"difficulty": "Easy", "count": 50, "submissions": 90},
                        {"difficulty": "Medium", "count": 30, "submissions": 70},
                        {"difficulty": "Hard", "count": 20, "submissions": 40}
                    ]
                },
                "tagProblemsSolved": {
                    "fundamental": [
                        {"tagName": "Array", "tagSlug": "array", "solvedCount": 15}
                    ],
                    "intermediate": [
                        {"tagName": "Stack", "tagSlug": "stack", "solvedCount": 5}
                    ],
                    "advanced": [
                        {"tagName": "Segment Tree", "tagSlug": "segment-tree", "solvedCount": 2}
                    ]
                }
            }
        }
    }
    
    parsed = LeetCodeDataParser.parse(raw_payload)
    
    # Assert profile
    assert parsed.username == "leetcode_user"
    assert parsed.real_name == "LeetCode Coder"
    assert parsed.about_me == "Software Engineer & Competitor"
    assert parsed.user_avatar == "https://assets.leetcode.com/avatar.jpg"
    
    # Assert problem counts
    assert parsed.problems.easy_solved == 50
    assert parsed.problems.easy_submissions == 90
    assert parsed.problems.medium_solved == 30
    assert parsed.problems.medium_submissions == 70
    assert parsed.problems.hard_solved == 20
    assert parsed.problems.hard_submissions == 40
    assert parsed.problems.total_solved == 100
    assert parsed.problems.total_submissions == 200

    # Assert tags
    assert len(parsed.tags.fundamental) == 1
    assert parsed.tags.fundamental[0].tag_name == "Array"
    assert parsed.tags.fundamental[0].tag_slug == "array"
    assert parsed.tags.fundamental[0].solved_count == 15
    
    assert len(parsed.tags.intermediate) == 1
    assert parsed.tags.intermediate[0].tag_name == "Stack"
    assert parsed.tags.intermediate[0].solved_count == 5
    
    assert len(parsed.tags.advanced) == 1
    assert parsed.tags.advanced[0].tag_name == "Segment Tree"
    assert parsed.tags.advanced[0].solved_count == 2

def test_parser_shuffled_difficulty_order() -> None:
    """Verify that difficulty counts are mapped by name rather than list position."""
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "shuffled_user",
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "Hard", "count": 10, "submissions": 20},
                        {"difficulty": "Easy", "count": 40, "submissions": 80},
                        {"difficulty": "All", "count": 70, "submissions": 140},
                        {"difficulty": "Medium", "count": 20, "submissions": 40}
                    ]
                }
            }
        }
    }
    parsed = LeetCodeDataParser.parse(raw_payload)
    assert parsed.problems.easy_solved == 40
    assert parsed.problems.medium_solved == 20
    assert parsed.problems.hard_solved == 10
    assert parsed.problems.total_solved == 70

def test_parser_fallback_all_missing() -> None:
    """Verify that total solved and submissions counts are derived if 'All' difficulty is missing."""
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "fallback_user",
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "Easy", "count": 10, "submissions": 20},
                        {"difficulty": "Medium", "count": 20, "submissions": 30},
                        {"difficulty": "Hard", "count": 5, "submissions": 10}
                    ]
                }
            }
        }
    }
    parsed = LeetCodeDataParser.parse(raw_payload)
    assert parsed.problems.easy_solved == 10
    assert parsed.problems.medium_solved == 20
    assert parsed.problems.hard_solved == 5
    # Total derived: 10 + 20 + 5 = 35
    assert parsed.problems.total_solved == 35
    # Submissions derived: 20 + 30 + 10 = 60
    assert parsed.problems.total_submissions == 60

def test_parser_missing_optional_values() -> None:
    """Verify that missing optional tag groups and profile values default gracefully."""
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "bare_user",
                "profile": {},
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 0, "submissions": 0}
                    ]
                }
            }
        }
    }
    parsed = LeetCodeDataParser.parse(raw_payload)
    assert parsed.real_name is None
    assert parsed.about_me is None
    assert parsed.user_avatar is None
    assert parsed.tags.fundamental == []
    assert parsed.tags.intermediate == []
    assert parsed.tags.advanced == []

def test_parser_malformed_payload_raises_validation() -> None:
    """Verify malformed payloads raise PlatformValidationException."""
    # 1. Missing username
    raw_payload = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": []
                }
            }
        }
    }
    with pytest.raises(PlatformValidationException):
        LeetCodeDataParser.parse(raw_payload)

# --- LeetCodeSyncService Tests ---

@pytest.mark.asyncio
async def test_sync_missing_profile_raises_not_connected(mock_snapshot_repo: MagicMock) -> None:
    """Verify that user without profile raises PlatformNotConnectedException."""
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=None)
    leetcode_client = MagicMock(spec=LeetCodeClient)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    with pytest.raises(PlatformNotConnectedException):
        await service.sync_leetcode_data(uuid.uuid4())

@pytest.mark.asyncio
async def test_sync_missing_leetcode_username_raises_not_connected(mock_snapshot_repo: MagicMock) -> None:
    """Verify that profile without connected leetcode_username raises PlatformNotConnectedException."""
    profile = Profile(user_id=uuid.uuid4(), leetcode_username=None)
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    leetcode_client = MagicMock(spec=LeetCodeClient)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    with pytest.raises(PlatformNotConnectedException):
        await service.sync_leetcode_data(profile.user_id)

@pytest.mark.asyncio
async def test_sync_success_profile_updated(mock_snapshot_repo: MagicMock) -> None:
    """Verify that new non-null LeetCode bio/avatar values update the database Profile and create snapshot."""
    profile = Profile(
        user_id=uuid.uuid4(),
        leetcode_username="leetcode_test",
        bio="Old Bio",
        avatar_url="https://old.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(return_value=profile)
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "leetcode_test",
                "profile": {
                    "realName": "LeetCode Pro",
                    "aboutMe": "New Bio from LeetCode",
                    "userAvatar": "https://new.com/avatar.png"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 12, "submissions": 30}
                    ]
                }
            }
        }
    }
    leetcode_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    result = await service.sync_leetcode_data(profile.user_id)
    
    assert result.success is True
    assert result.profile_updated is True
    assert result.leetcode_username == "leetcode_test"
    assert result.problems_solved == 12
    assert profile.bio == "New Bio from LeetCode"
    assert profile.avatar_url == "https://new.com/avatar.png"
    profile_repo.update.assert_called_once_with(profile)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_partial_update_only_bio_changes(mock_snapshot_repo: MagicMock) -> None:
    """Verify update is triggered when only the bio field changes."""
    profile = Profile(
        user_id=uuid.uuid4(),
        leetcode_username="leetcode_test",
        bio="Old Bio",
        avatar_url="https://same.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock(return_value=profile)
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "leetcode_test",
                "profile": {
                    "realName": "LeetCode Pro",
                    "aboutMe": "New Bio Only",
                    "userAvatar": "https://same.com/avatar.png"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 12, "submissions": 30}
                    ]
                }
            }
        }
    }
    leetcode_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    result = await service.sync_leetcode_data(profile.user_id)
    
    assert result.profile_updated is True
    assert profile.bio == "New Bio Only"
    profile_repo.update.assert_called_once_with(profile)
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_null_values_preserved(mock_snapshot_repo: MagicMock) -> None:
    """Verify that incoming null values from LeetCode do not erase existing local profile values."""
    profile = Profile(
        user_id=uuid.uuid4(),
        leetcode_username="leetcode_test",
        bio="Valuable Bio",
        avatar_url="https://valuable.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "leetcode_test",
                "profile": {
                    "realName": None,
                    "aboutMe": None,
                    "userAvatar": None
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 12, "submissions": 30}
                    ]
                }
            }
        }
    }
    leetcode_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    result = await service.sync_leetcode_data(profile.user_id)
    
    assert result.profile_updated is False
    assert profile.bio == "Valuable Bio"
    assert profile.avatar_url == "https://valuable.com/avatar.png"
    profile_repo.update.assert_not_called()
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_idempotent_no_writes(mock_snapshot_repo: MagicMock) -> None:
    """Verify that identical data triggers no database updates."""
    profile = Profile(
        user_id=uuid.uuid4(),
        leetcode_username="leetcode_test",
        bio="Same Bio",
        avatar_url="https://same.com/avatar.png"
    )
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    raw_payload = {
        "data": {
            "matchedUser": {
                "username": "leetcode_test",
                "profile": {
                    "realName": "Same Name",
                    "aboutMe": "Same Bio",
                    "userAvatar": "https://same.com/avatar.png"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 12, "submissions": 30}
                    ]
                }
            }
        }
    }
    leetcode_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    result = await service.sync_leetcode_data(profile.user_id)
    
    assert result.profile_updated is False
    profile_repo.update.assert_not_called()
    mock_snapshot_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_sync_client_exceptions_propagate(mock_snapshot_repo: MagicMock) -> None:
    """Verify that client exceptions propagate without being swallowed and do not write snapshots."""
    profile = Profile(user_id=uuid.uuid4(), leetcode_username="leetcode_test")
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    leetcode_client.fetch_raw_data = AsyncMock(side_effect=PlatformClientException(platform="LeetCode", message="Service Down"))
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    with pytest.raises(PlatformClientException):
        await service.sync_leetcode_data(profile.user_id)
    mock_snapshot_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_sync_parser_exceptions_propagate_but_preserve_snapshot(mock_snapshot_repo: MagicMock) -> None:
    """Verify that parser validation exceptions propagate but snapshot is still committed (Option A)."""
    profile = Profile(user_id=uuid.uuid4(), leetcode_username="leetcode_test")
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)
    profile_repo.update = AsyncMock()
    
    leetcode_client = MagicMock(spec=LeetCodeClient)
    raw_payload = {"malformed": "structure"}
    leetcode_client.fetch_raw_data = AsyncMock(return_value=raw_payload)
    
    service = LeetCodeSyncService(profile_repo, leetcode_client, mock_snapshot_repo)
    with pytest.raises(PlatformValidationException):
        await service.sync_leetcode_data(profile.user_id)
        
    profile_repo.update.assert_not_called()
    # In separate transaction stages (Option A), snapshot is still committed
    mock_snapshot_repo.create.assert_called_once()
