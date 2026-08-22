from datetime import date
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.leetcode_history import LeetCodeHistory

class LeetCodeHistoryRepository:
    """Repository class encapsulating database operations for the LeetCodeHistory model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        user_id: UUID,
        history_date: date,
        problems_solved: int,
        easy_solved: int,
        medium_solved: int,
        hard_solved: int,
        submissions: int,
        parsed_metrics: dict[str, Any]
    ) -> LeetCodeHistory:
        """
        Idempotently create or update a LeetCodeHistory record for a user and date.
        Uses PostgreSQL native ON CONFLICT DO UPDATE.
        """
        stmt = insert(LeetCodeHistory).values(
            user_id=user_id,
            date=history_date,
            problems_solved=problems_solved,
            easy_solved=easy_solved,
            medium_solved=medium_solved,
            hard_solved=hard_solved,
            submissions=submissions,
            parsed_metrics=parsed_metrics
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "date"],
            set_={
                "problems_solved": stmt.excluded.problems_solved,
                "easy_solved": stmt.excluded.easy_solved,
                "medium_solved": stmt.excluded.medium_solved,
                "hard_solved": stmt.excluded.hard_solved,
                "submissions": stmt.excluded.submissions,
                "parsed_metrics": stmt.excluded.parsed_metrics
            }
        ).returning(LeetCodeHistory)

        try:
            result = await self.db.execute(stmt)
            history_record = result.scalars().one()
            await self.db.commit()
            return history_record
        except Exception:
            await self.db.rollback()
            raise

    async def get_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[LeetCodeHistory]:
        """
        Retrieve chronological history for a user, optionally filtered by a date range.
        Returns results sorted by date in ascending order.
        """
        query = select(LeetCodeHistory).filter(LeetCodeHistory.user_id == user_id)
        if start_date is not None:
            query = query.filter(LeetCodeHistory.date >= start_date)
        if end_date is not None:
            query = query.filter(LeetCodeHistory.date <= end_date)
        query = query.order_by(LeetCodeHistory.date.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_user_id(self, user_id: UUID) -> LeetCodeHistory | None:
        """
        Retrieve the user's most recent history record based on date DESC.
        """
        query = (
            select(LeetCodeHistory)
            .filter(LeetCodeHistory.user_id == user_id)
            .order_by(LeetCodeHistory.date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
