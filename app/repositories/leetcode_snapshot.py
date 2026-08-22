from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.leetcode_snapshot import LeetCodeSnapshot

class LeetCodeSnapshotRepository:
    """Repository class encapsulating database operations for the LeetCodeSnapshot model."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, snapshot: LeetCodeSnapshot) -> LeetCodeSnapshot:
        """Persist a LeetCodeSnapshot instance and commit the transaction."""
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_by_user_id(self, user_id: UUID) -> LeetCodeSnapshot | None:
        """Retrieve the user's latest LeetCode snapshot sorted by fetched_at DESC."""
        result = await self.db.execute(
            select(LeetCodeSnapshot)
            .filter(LeetCodeSnapshot.user_id == user_id)
            .order_by(LeetCodeSnapshot.fetched_at.desc())
            .limit(1)
        )
        return result.scalars().first()
