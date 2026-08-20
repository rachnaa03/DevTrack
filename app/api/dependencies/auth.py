from uuid import UUID
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.exceptions import AuthenticationException

# Define OAuth2 scheme with the tokenUrl configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract JWT token, decode/validate it, and return the currently authenticated User.
    
    Args:
        token: The extracted Bearer token from the request (if present).
        db: Database session.
        
    Returns:
        The authenticated User model instance.
        
    Raises:
        AuthenticationException: For any validation, signature, expiration, claim,
                                 or user retrieval failure.
    """
    if token is None:
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
