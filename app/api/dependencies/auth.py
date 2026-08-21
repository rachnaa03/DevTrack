from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.exceptions import AuthenticationException

# Define HTTPBearer scheme and disable automatic error raising
security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract JWT token from Bearer authorization, validate it, and return the currently authenticated User.
    
    Args:
        credentials: The parsed HTTP Authorization credentials.
        db: Database session.
        
    Returns:
        The authenticated User model instance.
        
    Raises:
        AuthenticationException: For any validation, signature, expiration, claim,
                                 unsupported scheme, or user retrieval failure.
    """
    if credentials is None:
        raise AuthenticationException()
        
    if credentials.scheme.lower() != "bearer":
        raise AuthenticationException()
        
    token = credentials.credentials
    if not token:
        raise AuthenticationException()
        
    try:
        # Decode the token and check signature/algorithm
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify it is an access token (not a refresh token)
        if payload.get("type") != "access":
            raise AuthenticationException()
            
        # Extract user ID claim
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise AuthenticationException()
            
        # Validate that the subject is a valid UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise AuthenticationException()
            
    except JWTError:
        raise AuthenticationException()

    # Look up the user in database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationException()
        
    return user
