from datetime import date
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_report import WeeklyReport


class WeeklyReportRepository:
    """Repository class encapsulating database operations for the WeeklyReport model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_or_update(
        self,
        user_id: UUID,
        week_start: date,
        week_end: date,
        report_data: dict[str, Any],
    ) -> WeeklyReport:
        """
        Idempotently create or update a WeeklyReport record for a user and week_start.
        Uses PostgreSQL native ON CONFLICT (user_id, week_start) DO UPDATE.
        """
        stmt = insert(WeeklyReport).values(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            report_data=report_data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "week_start"],
            set_={
                "week_end": stmt.excluded.week_end,
                "report_data": stmt.excluded.report_data,
            },
        ).returning(WeeklyReport)

        try:
            result = await self.db.execute(stmt)
            report_record = result.scalars().one()
            await self.db.commit()
            return report_record
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_id(self, report_id: UUID) -> WeeklyReport | None:
        """Retrieve a WeeklyReport by its primary key ID."""
        query = select(WeeklyReport).filter(WeeklyReport.id == report_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_user_and_week(
        self,
        user_id: UUID,
        week_start: date,
    ) -> WeeklyReport | None:
        """Retrieve a specific WeeklyReport for a user and week_start."""
        query = select(WeeklyReport).filter(
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start == week_start,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_reports_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[WeeklyReport]:
        """
        Retrieve chronological weekly reports for a user, sorted by week_start descending.
        """
        safe_limit = max(1, min(limit, 100))
        query = (
            select(WeeklyReport)
            .filter(WeeklyReport.user_id == user_id)
            .order_by(WeeklyReport.week_start.desc())
            .limit(safe_limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
