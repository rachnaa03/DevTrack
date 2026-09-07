from datetime import datetime
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

    async def get_scores_by_date_range(
        self,
        user_id: UUID,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> list[DeveloperScore]:
        """
        Retrieve chronological score history for a user, optionally filtered by datetime range.
        Returns results sorted by computed_at in ascending order.
        """
        query = select(DeveloperScore).filter(DeveloperScore.user_id == user_id)
        if start_datetime is not None:
            query = query.filter(DeveloperScore.computed_at >= start_datetime)
        if end_datetime is not None:
            query = query.filter(DeveloperScore.computed_at <= end_datetime)
        query = query.order_by(DeveloperScore.computed_at.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_before(
        self,
        user_id: UUID,
        before_datetime: datetime,
    ) -> DeveloperScore | None:
        """
        Retrieve the latest score calculated before or at the specified datetime.
        """
        query = (
            select(DeveloperScore)
            .filter(
                DeveloperScore.user_id == user_id,
                DeveloperScore.computed_at <= before_datetime,
            )
            .order_by(DeveloperScore.computed_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
