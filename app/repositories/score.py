from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.score import DeveloperScore

class DeveloperScoreRepository:
    """Repository class encapsulating database operations for the DeveloperScore model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, score_record: DeveloperScore) -> DeveloperScore:
        """Persist a DeveloperScore record and commit the transaction."""
        self.db.add(score_record)
        try:
            await self.db.commit()
            await self.db.refresh(score_record)
            return score_record
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_id(self, score_id: UUID) -> DeveloperScore | None:
        """Retrieve a DeveloperScore by id."""
        result = await self.db.execute(select(DeveloperScore).filter(DeveloperScore.id == score_id))
        return result.scalars().first()

    async def get_latest_by_user_id(self, user_id: UUID) -> DeveloperScore | None:
        """Retrieve the user's most recent score record based on computed_at DESC."""
        query = (
            select(DeveloperScore)
            .filter(DeveloperScore.user_id == user_id)
            .order_by(DeveloperScore.computed_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_history(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> list[DeveloperScore]:
        """Retrieve the user's score history sorted by computed_at descending."""
        if limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        query = (
            select(DeveloperScore)
            .filter(DeveloperScore.user_id == user_id)
            .order_by(DeveloperScore.computed_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
