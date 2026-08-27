from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.leetcode_analytics import LeetCodeAnalytics
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema

class LeetCodeAnalyticsRepository:
    """Repository class encapsulating database operations for the LeetCodeAnalytics model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        user_id: UUID,
        analysis_date: date,
        result: LeetCodeAnalysisResultSchema
    ) -> LeetCodeAnalytics:
        """
        Idempotently create or update a LeetCodeAnalytics record for a user and date.
        Uses PostgreSQL native ON CONFLICT DO UPDATE.
        """
        # Map subschemas to database JSONB formats
        most_practiced = [t.model_dump(mode="json") for t in result.most_practiced_topics]

        stmt = insert(LeetCodeAnalytics).values(
            user_id=user_id,
            date=analysis_date,
            easy_solved=result.problem_stats.easy_solved,
            medium_solved=result.problem_stats.medium_solved,
            hard_solved=result.problem_stats.hard_solved,
            total_solved=result.problem_stats.total_solved,
            easy_submissions=result.problem_stats.easy_submissions,
            medium_submissions=result.problem_stats.medium_submissions,
            hard_submissions=result.problem_stats.hard_submissions,
            total_submissions=result.problem_stats.total_submissions,
            problems_solved_growth=result.problems_solved_growth,
            easy_solved_growth=result.easy_solved_growth,
            medium_solved_growth=result.medium_solved_growth,
            hard_solved_growth=result.hard_solved_growth,
            submissions_growth=result.submissions_growth,
            problems_solved_frequency_per_day=result.problems_solved_frequency_per_day,
            active_days_count=result.active_days_count,
            contribution_consistency=result.contribution_consistency,
            current_streak=result.current_streak,
            longest_streak=result.longest_streak,
            most_practiced_topics=most_practiced
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "date"],
            set_={
                "easy_solved": stmt.excluded.easy_solved,
                "medium_solved": stmt.excluded.medium_solved,
                "hard_solved": stmt.excluded.hard_solved,
                "total_solved": stmt.excluded.total_solved,
                "easy_submissions": stmt.excluded.easy_submissions,
                "medium_submissions": stmt.excluded.medium_submissions,
                "hard_submissions": stmt.excluded.hard_submissions,
                "total_submissions": stmt.excluded.total_submissions,
                "problems_solved_growth": stmt.excluded.problems_solved_growth,
                "easy_solved_growth": stmt.excluded.easy_solved_growth,
                "medium_solved_growth": stmt.excluded.medium_solved_growth,
                "hard_solved_growth": stmt.excluded.hard_solved_growth,
                "submissions_growth": stmt.excluded.submissions_growth,
                "problems_solved_frequency_per_day": stmt.excluded.problems_solved_frequency_per_day,
                "active_days_count": stmt.excluded.active_days_count,
                "contribution_consistency": stmt.excluded.contribution_consistency,
                "current_streak": stmt.excluded.current_streak,
                "longest_streak": stmt.excluded.longest_streak,
                "most_practiced_topics": stmt.excluded.most_practiced_topics,
                "updated_at": func.now()  # Refresh updated_at on collision
            }
        ).returning(LeetCodeAnalytics)

        try:
            db_result = await self.db.execute(stmt)
            record = db_result.scalars().one()
            await self.db.commit()
            return record
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_user_id_and_date(self, user_id: UUID, date_val: date) -> LeetCodeAnalytics | None:
        """Retrieve a specific LeetCodeAnalytics record by user and date."""
        query = select(LeetCodeAnalytics).filter(
            LeetCodeAnalytics.user_id == user_id,
            LeetCodeAnalytics.date == date_val
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_latest_by_user_id(self, user_id: UUID) -> LeetCodeAnalytics | None:
        """Retrieve the user's latest LeetCodeAnalytics record sorted by date DESC."""
        query = (
            select(LeetCodeAnalytics)
            .filter(LeetCodeAnalytics.user_id == user_id)
            .order_by(LeetCodeAnalytics.date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[LeetCodeAnalytics]:
        """
        Retrieve chronological history for a user, optionally filtered by a date range.
        Returns results sorted by date in ascending order.
        """
        query = select(LeetCodeAnalytics).filter(LeetCodeAnalytics.user_id == user_id)
        if start_date is not None:
            query = query.filter(LeetCodeAnalytics.date >= start_date)
        if end_date is not None:
            query = query.filter(LeetCodeAnalytics.date <= end_date)
        query = query.order_by(LeetCodeAnalytics.date.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
