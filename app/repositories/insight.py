from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight


class InsightRepository:
    """Repository class encapsulating database operations for the Insight model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, record: Insight) -> Insight:
        """Persist an Insight record and commit the transaction."""
        self.db.add(record)
        try:
            await self.db.commit()
            await self.db.refresh(record)
            return record
        except Exception:
            await self.db.rollback()
            raise

    async def get_existing(
        self,
        user_id: UUID,
        platform: str,
        metric_name: str,
        current_date: date,
        historical_date: date,
        rule_version: str,
    ) -> Insight | None:
        """
        Retrieve an existing insight record matching the deduplication key.

        The deduplication key is:
            (user_id, platform, metric_name, current_date, historical_date, rule_version)

        This prevents the same comparison cycle from persisting multiple identical
        insight records if the service is invoked more than once.
        """
        query = select(Insight).filter(
            Insight.user_id == user_id,
            Insight.platform == platform,
            Insight.metric_name == metric_name,
            Insight.current_date == current_date,
            Insight.historical_date == historical_date,
            Insight.rule_version == rule_version,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_latest_by_user_id(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[Insight]:
        """Retrieve the user's most recent insight records ordered by generated_at DESC."""
        if limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        query = (
            select(Insight)
            .filter(Insight.user_id == user_id)
            .order_by(Insight.generated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
