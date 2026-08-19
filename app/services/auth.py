from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.exceptions import EmailAlreadyExistsException

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
