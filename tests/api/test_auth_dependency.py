import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.core.security import create_access_token

client = TestClient(app)

def test_get_me_success() -> None:
    """Verify that a valid access token successfully authenticates a user and returns safe details."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    
    existing_user = User(
        id=user_id,
        email="me@example.com",
        created_at=datetime.now(timezone.utc)
    )
    
    # Mock Repository get_by_id lookup
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = existing_user
    mock_db.execute.return_value = mock_execute_result
    
    # Generate valid access token
    access_token = create_access_token({"sub": str(user_id)})
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["id"] == str(user_id)
        assert "created_at" in data
        assert "hashed_password" not in data
        assert "password" not in data
    finally:
        app.dependency_overrides.clear()

def test_get_me_missing_auth_header() -> None:
    """Verify that missing Authorization header returns HTTP 401 generic error."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert data["error"]["message"] == "Could not validate credentials."

def test_get_me_invalid_signature() -> None:
    """Verify that a token with an invalid signature returns HTTP 401 generic error."""
    user_id = uuid.uuid4()
    payload = {"sub": str(user_id), "type": "access"}
    bad_token = jwt.encode(payload, "invalid_secret_key_12345", algorithm=settings.JWT_ALGORITHM)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert data["error"]["message"] == "Could not validate credentials."

def test_get_me_expired_token() -> None:
    """Verify that an expired token returns HTTP 401 generic error."""
    user_id = uuid.uuid4()
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": past_time
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert data["error"]["message"] == "Could not validate credentials."

def test_get_me_refresh_token_fails() -> None:
    """Verify that using a refresh token as an access token fails with HTTP 401."""
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }
    refresh_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

def test_get_me_invalid_uuid() -> None:
    """Verify that a token with an invalid UUID string in sub fails with HTTP 401."""
    payload = {
        "sub": "not-a-valid-uuid-string",
        "type": "access"
    }
    bad_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

def test_get_me_nonexistent_user() -> None:
    """Verify that a valid token referencing a non-existent user returns HTTP 401."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    
    # Mock Repository returning None (user not found in DB)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    access_token = create_access_token({"sub": str(user_id)})
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    finally:
        app.dependency_overrides.clear()

def test_get_me_unsupported_scheme() -> None:
    """Verify that an unsupported authentication scheme (like Basic or generic token) is rejected with HTTP 401."""
    user_id = uuid.uuid4()
    access_token = create_access_token({"sub": str(user_id)})
    
    # Try with Basic auth
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Basic {access_token}"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert data["error"]["message"] == "Could not validate credentials."

    # Try with raw token (no scheme prefix)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": access_token}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

