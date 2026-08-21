import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.profile import Profile

client = TestClient(app)

@pytest.fixture
def mock_user() -> User:
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        hashed_password="hashed_password_123"
    )
    return user

@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()

def test_get_profile_existing(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify GET /profile returns an existing profile successfully."""
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        user_id=mock_user.id,
        bio="Test Bio",
        avatar_url="https://example.com/avatar.jpg",
        github_username="github_test",
        leetcode_username="leetcode_test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Mock DB select to return mock_profile
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_profile
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/profile/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(profile_id)
        assert data["user_id"] == str(mock_user.id)
        assert data["bio"] == "Test Bio"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"
        assert data["github_username"] == "github_test"
        assert data["leetcode_username"] == "leetcode_test"
    finally:
        app.dependency_overrides.clear()

def test_get_profile_lazy_creation(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify GET /profile lazily provisions an empty profile if none exists."""
    # First select returns None (no profile exists)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result

    # Mock DB methods for creation
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    
    profile_id = uuid.uuid4()
    async def mock_refresh(profile):
        profile.id = profile_id
        profile.created_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
    mock_db.refresh = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/profile/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(profile_id)
        assert data["user_id"] == str(mock_user.id)
        assert data["bio"] is None
        assert data["avatar_url"] is None
        assert mock_db.add.called
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()

def test_get_profile_unauthenticated() -> None:
    """Verify GET /profile is rejected with HTTP 401 when unauthenticated."""
    # Do not override get_current_user to simulate real authentication check failing
    response = client.get("/api/v1/profile/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

def test_put_profile_success(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify PUT /profile partially updates allowed fields and returns updated profile."""
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        user_id=mock_user.id,
        bio="Old Bio",
        avatar_url="https://example.com/old.jpg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_profile
    mock_db.execute.return_value = mock_execute_result
    mock_db.commit = AsyncMock()
    
    async def mock_refresh(profile):
        profile.updated_at = datetime.now(timezone.utc)
    mock_db.refresh = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        # 1. Update bio and avatar_url
        response = client.put(
            "/api/v1/profile/",
            json={"bio": "New Bio", "avatar_url": "https://example.com/new.jpg"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == "New Bio"
        assert data["avatar_url"] == "https://example.com/new.jpg"
        assert mock_profile.bio == "New Bio"
        assert mock_profile.avatar_url == "https://example.com/new.jpg"

        # 2. Update bio only (avatar_url omitted, must remain unchanged)
        response = client.put(
            "/api/v1/profile/",
            json={"bio": "Even Newer Bio"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == "Even Newer Bio"
        assert data["avatar_url"] == "https://example.com/new.jpg"
        assert mock_profile.bio == "Even Newer Bio"
        assert mock_profile.avatar_url == "https://example.com/new.jpg"
    finally:
        app.dependency_overrides.clear()

def test_put_profile_lazy_creation(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify PUT /profile lazily provisions an empty profile and applies updates."""
    # First select returns None
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    
    profile_id = uuid.uuid4()
    async def mock_refresh(profile):
        profile.id = profile_id
        profile.created_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
    mock_db.refresh = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.put(
            "/api/v1/profile/",
            json={"bio": "Lazily Created Bio"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == "Lazily Created Bio"
        assert data["user_id"] == str(mock_user.id)
    finally:
        app.dependency_overrides.clear()

def test_put_profile_invalid_avatar(mock_user: User) -> None:
    """Verify PUT /profile rejects invalid avatar URL protocols with HTTP 422."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.put(
            "/api/v1/profile/",
            json={"avatar_url": "ftp://example.com/avatar.jpg"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    finally:
        app.dependency_overrides.clear()

def test_put_profile_forbidden_fields(mock_user: User) -> None:
    """Verify PUT /profile rejects forbidden parameters (extra="forbid") with HTTP 422."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        # Attempting to modify github_username
        response = client.put(
            "/api/v1/profile/",
            json={"github_username": "hacker"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Attempting to modify user_id
        response = client.put(
            "/api/v1/profile/",
            json={"user_id": str(uuid.uuid4())}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    finally:
        app.dependency_overrides.clear()

def test_put_profile_unauthenticated() -> None:
    """Verify PUT /profile is rejected with HTTP 401 when unauthenticated."""
    response = client.put(
        "/api/v1/profile/",
        json={"bio": "Unauth update"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_connect_platforms_github_only(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify successfully connecting only GitHub username."""
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        user_id=mock_user.id,
        github_username=None,
        leetcode_username="old_lc",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_profile
    mock_db.execute.return_value = mock_execute_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "valid-username-123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["github_username"] == "valid-username-123"
        assert data["leetcode_username"] == "old_lc"
        assert mock_profile.github_username == "valid-username-123"
        assert mock_profile.leetcode_username == "old_lc"
    finally:
        app.dependency_overrides.clear()

def test_connect_platforms_leetcode_only(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify successfully connecting only LeetCode username."""
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        user_id=mock_user.id,
        github_username="old_git",
        leetcode_username=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_profile
    mock_db.execute.return_value = mock_execute_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.put(
            "/api/v1/profile/connect",
            json={"leetcode_username": "valid_lc-name"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["github_username"] == "old_git"
        assert data["leetcode_username"] == "valid_lc-name"
    finally:
        app.dependency_overrides.clear()

def test_connect_platforms_both(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify successfully connecting both usernames."""
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        user_id=mock_user.id,
        github_username=None,
        leetcode_username=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_profile
    mock_db.execute.return_value = mock_execute_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "valid-git", "leetcode_username": "valid-lc"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["github_username"] == "valid-git"
        assert data["leetcode_username"] == "valid-lc"
    finally:
        app.dependency_overrides.clear()

def test_connect_platforms_lazy_creation(mock_user: User, mock_db: AsyncMock) -> None:
    """Verify lazy profile creation works when connecting platforms for a user without a profile."""
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    
    profile_id = uuid.uuid4()
    async def mock_refresh(profile):
        profile.id = profile_id
        profile.created_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
    mock_db.refresh = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "valid-git"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["github_username"] == "valid-git"
        assert data["user_id"] == str(mock_user.id)
    finally:
        app.dependency_overrides.clear()

def test_connect_platforms_validation_failures(mock_user: User) -> None:
    """Verify validation constraints reject invalid payloads with HTTP 422."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        # 1. Both fields omitted
        response = client.put("/api/v1/profile/connect", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 2. Both fields null
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": None, "leetcode_username": None}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 3. Empty string
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": ""}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 4. Whitespace-containing
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "git name"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 5. Invalid GitHub username (starts with hyphen)
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "-invalid"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 6. Invalid GitHub username (ends with hyphen)
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "invalid-"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 7. Invalid GitHub username (consecutive hyphens)
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "inv--alid"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 8. Invalid GitHub username (too long)
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "a" * 40}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 9. Invalid LeetCode username (contains special character)
        response = client.put(
            "/api/v1/profile/connect",
            json={"leetcode_username": "lc@name"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 10. Forbidden extra fields
        response = client.put(
            "/api/v1/profile/connect",
            json={"github_username": "valid-git", "bio": "forbidden bio update"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    finally:
        app.dependency_overrides.clear()

def test_connect_platforms_unauthenticated() -> None:
    """Verify PUT /profile/connect is rejected with HTTP 401 when unauthenticated."""
    response = client.put(
        "/api/v1/profile/connect",
        json={"github_username": "valid-git"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

