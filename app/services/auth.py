from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.exceptions import EmailAlreadyExistsException, InvalidCredentialsException

class AuthService:
    """Service class executing authentication-related business logic."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user account.
        
        Args:
            email: Plaintext email address to register.
            password: Plaintext password to hash.
            
        Returns:
            The created User database model instance.
            
        Raises:
            EmailAlreadyExistsException: If email exists or unique constraint is violated.
        """
        # Standardize email representation
        normalized_email = email.strip().lower()
        
        # Check service-level registration constraint
        existing = await self.user_repo.get_by_email(normalized_email)
        if existing is not None:
            raise EmailAlreadyExistsException()
            
        # Compute secure bcrypt password hash
        hashed_pw = hash_password(password)
        
        # Build user model instance
        new_user = User(
            email=normalized_email,
            hashed_password=hashed_pw
        )
        
        try:
            return await self.user_repo.create(new_user)
        except IntegrityError:
            # Catch database unique constraint race conditions
            raise EmailAlreadyExistsException()

    async def authenticate_user(self, email: str, password: str) -> dict:
        """
        Authenticate a user by email and password, and return JWT tokens.
        
        Args:
            email: User's login email address.
            password: User's login password.
            
        Returns:
            A dictionary containing access_token, refresh_token, token_type, and expires_in.
            
        Raises:
            InvalidCredentialsException: If email/password are incorrect.
        """
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_email(normalized_email)
        
        # Timing attack mitigation: always execute verify_password
        if user is None:
            # Dummy hash matching standard bcrypt shape
            verify_password(password, "$2b$12$12345678901234567890123456789012345678901234567890123")
            raise InvalidCredentialsException()
            
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()
            
        # Generate token payload
        payload = {"sub": str(user.id)}
        
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
