import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.core.security import hash_password

client = TestClient(app)

def test_login_success() -> None:
    """Verify successful login with valid credentials returns access/refresh tokens and correct claims."""
    mock_db = AsyncMock()
    
    plain_password = "StrongPassword123!"
    hashed_pw = hash_password(plain_password)
    user_id = uuid.uuid4()
    
    existing_user = User(
        id=user_id,
        email="testlogin@example.com",
        hashed_password=hashed_pw
    )
    
    # Mock repository lookup
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = existing_user
    mock_db.execute.return_value = mock_execute_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "testlogin@example.com", "password": plain_password}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        # Verify access token signature and claims
        decoded_access = jwt.decode(
            data["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        assert decoded_access["sub"] == str(user_id)
        assert decoded_access["type"] == "access"
        assert "exp" in decoded_access
        
        # Verify refresh token signature and claims
        decoded_refresh = jwt.decode(
            data["refresh_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        assert decoded_refresh["sub"] == str(user_id)
        assert decoded_refresh["type"] == "refresh"
        assert "exp" in decoded_refresh
    finally:
        app.dependency_overrides.clear()

def test_login_incorrect_password() -> None:
    """Verify login fails with HTTP 401 and generic message when password is wrong."""
    mock_db = AsyncMock()
    
    plain_password = "StrongPassword123!"
    hashed_pw = hash_password(plain_password)
    
    existing_user = User(
        id=uuid.uuid4(),
        email="testlogin@example.com",
        hashed_password=hashed_pw
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = existing_user
    mock_db.execute.return_value = mock_execute_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "testlogin@example.com", "password": "WrongPassword123!"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"
        assert data["error"]["message"] == "Invalid email or password."
        assert "request_id" in data["error"]
        assert "hashed_password" not in response.text
    finally:
        app.dependency_overrides.clear()

def test_login_nonexistent_email() -> None:
    """Verify login fails with HTTP 401 and identical generic message when email does not exist."""
    mock_db = AsyncMock()
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "notfound@example.com", "password": "StrongPassword123!"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"
        assert data["error"]["message"] == "Invalid email or password."
        assert "request_id" in data["error"]
    finally:
        app.dependency_overrides.clear()
