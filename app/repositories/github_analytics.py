from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.github_analytics import GitHubAnalytics
from app.schemas.github_analysis import GitHubAnalysisResultSchema

class GitHubAnalyticsRepository:
    """Repository class encapsulating database operations for the GitHubAnalytics model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        user_id: UUID,
        analysis_date: date,
        result: GitHubAnalysisResultSchema
    ) -> GitHubAnalytics:
        """
        Idempotently create or update a GitHubAnalytics record for a user and date.
        Uses PostgreSQL native ON CONFLICT DO UPDATE.
        """
        # Map subschemas to database JSONB formats
        languages = result.language_distribution
        most_starred = [r.model_dump(mode="json") for r in result.most_starred_repos]
        recently_updated = [r.model_dump(mode="json") for r in result.recently_updated_repositories]

        stmt = insert(GitHubAnalytics).values(
            user_id=user_id,
            date=analysis_date,
            total_repositories=result.repo_stats.total_repositories,
            total_stars=result.repo_stats.total_stars,
            total_forks=result.repo_stats.total_forks,
            total_size=result.repo_stats.total_size,
            total_open_issues=result.repo_stats.total_open_issues,
            repository_growth=result.repository_growth,
            star_growth=result.star_growth,
            fork_growth=result.fork_growth,
            total_commits=result.total_commits,
            commit_frequency_per_day=result.commit_frequency_per_day,
            active_days_count=result.active_days_count,
            contribution_consistency=result.contribution_consistency,
            current_streak=result.current_streak,
            longest_streak=result.longest_streak,
            languages=languages,
            most_starred_repos=most_starred,
            recently_updated_repos=recently_updated
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "date"],
            set_={
                "total_repositories": stmt.excluded.total_repositories,
                "total_stars": stmt.excluded.total_stars,
                "total_forks": stmt.excluded.total_forks,
                "total_size": stmt.excluded.total_size,
                "total_open_issues": stmt.excluded.total_open_issues,
                "repository_growth": stmt.excluded.repository_growth,
                "star_growth": stmt.excluded.star_growth,
                "fork_growth": stmt.excluded.fork_growth,
                "total_commits": stmt.excluded.total_commits,
                "commit_frequency_per_day": stmt.excluded.commit_frequency_per_day,
                "active_days_count": stmt.excluded.active_days_count,
                "contribution_consistency": stmt.excluded.contribution_consistency,
                "current_streak": stmt.excluded.current_streak,
                "longest_streak": stmt.excluded.longest_streak,
                "languages": stmt.excluded.languages,
                "most_starred_repos": stmt.excluded.most_starred_repos,
                "recently_updated_repos": stmt.excluded.recently_updated_repos,
                "updated_at": func.now()  # Refresh updated_at on collision
            }
        ).returning(GitHubAnalytics)

        try:
            db_result = await self.db.execute(stmt)
            record = db_result.scalars().one()
            await self.db.commit()
            return record
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_user_id_and_date(self, user_id: UUID, date_val: date) -> GitHubAnalytics | None:
        """Retrieve a specific GitHubAnalytics record by user and date."""
        query = select(GitHubAnalytics).filter(
            GitHubAnalytics.user_id == user_id,
            GitHubAnalytics.date == date_val
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_latest_by_user_id(self, user_id: UUID) -> GitHubAnalytics | None:
        """Retrieve the user's latest GitHubAnalytics record sorted by date DESC."""
        query = (
            select(GitHubAnalytics)
            .filter(GitHubAnalytics.user_id == user_id)
            .order_by(GitHubAnalytics.date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[GitHubAnalytics]:
        """
        Retrieve chronological history for a user, optionally filtered by a date range.
        Returns results sorted by date in ascending order.
        """
        query = select(GitHubAnalytics).filter(GitHubAnalytics.user_id == user_id)
        if start_date is not None:
            query = query.filter(GitHubAnalytics.date >= start_date)
        if end_date is not None:
            query = query.filter(GitHubAnalytics.date <= end_date)
        query = query.order_by(GitHubAnalytics.date.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
