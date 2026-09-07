from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.profile import Profile

class ProfileRepository:
    """Repository class encapsulating database operations for the Profile model."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> Profile | None:
        """Retrieve a Profile by its associated User UUID."""
        result = await self.db.execute(select(Profile).filter(Profile.user_id == user_id))
        return result.scalars().first()

    async def create(self, profile: Profile) -> Profile:
        """Persist a Profile instance and commit the transaction."""
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: Profile) -> Profile:
        """Commit changes to the profile in the database transaction."""
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_connected_user_ids(self) -> list[UUID]:
        """Retrieve user UUIDs for all profiles that have at least one connected platform handle."""
        from sqlalchemy import and_, or_

        stmt = select(Profile.user_id).filter(
            or_(
                and_(Profile.github_username.isnot(None), Profile.github_username != ""),
                and_(Profile.leetcode_username.isnot(None), Profile.leetcode_username != ""),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

