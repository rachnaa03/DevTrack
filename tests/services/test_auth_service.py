import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.utils.exceptions import EmailAlreadyExistsException

@pytest.mark.asyncio
async def test_service_register_success() -> None:
    """Verify that AuthService registers a user, hashes the password, and returns the User object."""
    mock_repo = MagicMock(spec=UserRepository)
    mock_repo.get_by_email = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(side_effect=lambda user: user)

    service = AuthService(mock_repo)
    user = await service.register_user(email="test@example.com", password="SecurePassword123!")

    assert isinstance(user, User)
    assert user.email == "test@example.com"
    # Password must be hashed (not plain)
    assert user.hashed_password != "SecurePassword123!"
    assert len(user.hashed_password) > 0
    mock_repo.get_by_email.assert_called_once_with("test@example.com")
    mock_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_service_register_duplicate_email() -> None:
    """Verify that AuthService raises EmailAlreadyExistsException when checking duplicate email."""
    mock_repo = MagicMock(spec=UserRepository)
    existing_user = User(email="test@example.com", hashed_password="somehash")
    mock_repo.get_by_email = AsyncMock(return_value=existing_user)

    service = AuthService(mock_repo)
    with pytest.raises(EmailAlreadyExistsException):
        await service.register_user(email="test@example.com", password="SecurePassword123!")

    mock_repo.get_by_email.assert_called_once_with("test@example.com")
    mock_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_service_register_database_integrity_race() -> None:
    """Verify that AuthService handles database IntegrityError race conditions gracefully."""
    mock_repo = MagicMock(spec=UserRepository)
    mock_repo.get_by_email = AsyncMock(return_value=None)
    # Simulate DB integrity error (unique constraint violation on insert)
    mock_repo.create = AsyncMock(side_effect=IntegrityError(None, None, Exception()))

    service = AuthService(mock_repo)
    with pytest.raises(EmailAlreadyExistsException):
        await service.register_user(email="race@example.com", password="SecurePassword123!")

    mock_repo.get_by_email.assert_called_once_with("race@example.com")
    mock_repo.create.assert_called_once()

from app.core.security import hash_password
from app.utils.exceptions import InvalidCredentialsException
import uuid

@pytest.mark.asyncio
async def test_service_authenticate_success() -> None:
    """Verify that AuthService authenticates a user successfully and returns tokens."""
    mock_repo = MagicMock(spec=UserRepository)
    
    plain_password = "SecurePassword123!"
    hashed_pw = hash_password(plain_password)
    user_id = uuid.uuid4()
    
    existing_user = User(
        id=user_id,
        email="auth@example.com",
        hashed_password=hashed_pw
    )
    mock_repo.get_by_email = AsyncMock(return_value=existing_user)

    service = AuthService(mock_repo)
    result = await service.authenticate_user(email="auth@example.com", password=plain_password)

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"
    assert result["expires_in"] > 0
    mock_repo.get_by_email.assert_called_once_with("auth@example.com")

@pytest.mark.asyncio
async def test_service_authenticate_incorrect_password() -> None:
    """Verify that AuthService raises InvalidCredentialsException on bad password."""
    mock_repo = MagicMock(spec=UserRepository)
    
    plain_password = "SecurePassword123!"
    hashed_pw = hash_password(plain_password)
    
    existing_user = User(
        id=uuid.uuid4(),
        email="auth@example.com",
        hashed_password=hashed_pw
    )
    mock_repo.get_by_email = AsyncMock(return_value=existing_user)

    service = AuthService(mock_repo)
    with pytest.raises(InvalidCredentialsException):
        await service.authenticate_user(email="auth@example.com", password="WrongPassword123!")

    mock_repo.get_by_email.assert_called_once_with("auth@example.com")

@pytest.mark.asyncio
async def test_service_authenticate_nonexistent_user() -> None:
    """Verify that AuthService raises InvalidCredentialsException on nonexistent email."""
    mock_repo = MagicMock(spec=UserRepository)
    mock_repo.get_by_email = AsyncMock(return_value=None)

    service = AuthService(mock_repo)
    with pytest.raises(InvalidCredentialsException):
        await service.authenticate_user(email="notfound@example.com", password="AnyPassword123!")

    mock_repo.get_by_email.assert_called_once_with("notfound@example.com")

