from datetime import date
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.github_history import GitHubHistory

class GitHubHistoryRepository:
    """Repository class encapsulating database operations for the GitHubHistory model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        user_id: UUID,
        history_date: date,
        commits: int,
        stars: int,
        forks: int,
        repositories: int,
        parsed_metrics: dict[str, Any]
    ) -> GitHubHistory:
        """
        Idempotently create or update a GitHubHistory record for a user and date.
        Uses PostgreSQL native ON CONFLICT DO UPDATE.
        """
        stmt = insert(GitHubHistory).values(
            user_id=user_id,
            date=history_date,
            commits=commits,
            stars=stars,
            forks=forks,
            repositories=repositories,
            parsed_metrics=parsed_metrics
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "date"],
            set_={
                "commits": stmt.excluded.commits,
                "stars": stmt.excluded.stars,
                "forks": stmt.excluded.forks,
                "repositories": stmt.excluded.repositories,
                "parsed_metrics": stmt.excluded.parsed_metrics
            }
        ).returning(GitHubHistory)

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
    ) -> list[GitHubHistory]:
        """
        Retrieve chronological history for a user, optionally filtered by a date range.
        Returns results sorted by date in ascending order.
        """
        query = select(GitHubHistory).filter(GitHubHistory.user_id == user_id)
        if start_date is not None:
            query = query.filter(GitHubHistory.date >= start_date)
        if end_date is not None:
            query = query.filter(GitHubHistory.date <= end_date)
        query = query.order_by(GitHubHistory.date.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_user_id(self, user_id: UUID) -> GitHubHistory | None:
        """
        Retrieve the user's most recent history record based on date DESC.
        """
        query = (
            select(GitHubHistory)
            .filter(GitHubHistory.user_id == user_id)
            .order_by(GitHubHistory.date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_recent_by_user_id(
        self,
        user_id: UUID,
        limit: int = 2
    ) -> list[GitHubHistory]:
        """
        Retrieve the user's most recent history records sorted by date descending.
        """
        if limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        query = (
            select(GitHubHistory)
            .filter(GitHubHistory.user_id == user_id)
            .order_by(GitHubHistory.date.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
