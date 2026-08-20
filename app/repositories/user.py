from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User

class UserRepository:
    """Repository class encapsulating database operations for the User model."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a User by email address."""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a User by their UUID primary key."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def create(self, user: User) -> User:
        """Persist a User instance and commit the transaction."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
