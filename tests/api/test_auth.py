import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.user import User

client = TestClient(app)

def test_register_success() -> None:
    """Verify that a new user is successfully registered, password is hashed, and response is clean."""
    mock_db = AsyncMock()
    
    # Mock get_by_email query returning None (email not taken)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    
    # Mock refresh to populate generated id and timestamp
    created_uuid = uuid.uuid4()
    async def mock_refresh(user):
        user.id = created_uuid
        user.created_at = "2026-08-19T18:00:00Z"
    mock_db.refresh = mock_refresh

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "StrongPassword123!"}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["id"] == str(created_uuid)
        assert "created_at" in data
        
        # Verify sensitive credentials do not leak in the response body
        assert "hashed_password" not in data
        assert "password" not in data
        
        # Verify repository add was called and password was hashed
        assert mock_db.add.called
        added_user = mock_db.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.email == "newuser@example.com"
        assert added_user.hashed_password != "StrongPassword123!"
        assert len(added_user.hashed_password) > 0
    finally:
        app.dependency_overrides.clear()

def test_register_duplicate_email() -> None:
    """Verify registration fails with 400 Bad Request when email is already registered."""
    mock_db = AsyncMock()
    
    # Mock get_by_email query returning an existing User
    mock_execute_result = MagicMock()
    existing_user = User(email="existing@example.com", hashed_password="somehash")
    mock_execute_result.scalars().first.return_value = existing_user
    mock_db.execute.return_value = mock_execute_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "StrongPassword123!"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"
        assert "request_id" in data["error"]
        assert "hashed_password" not in response.text
    finally:
        app.dependency_overrides.clear()

def test_register_invalid_inputs() -> None:
    """Verify validation triggers 422 status code on malformed emails or invalid password lengths."""
    # Invalid email syntax
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid_email_syntax", "password": "StrongPassword123!"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Password too short (< 8 chars)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Password too long (> 64 chars)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "a" * 65}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
