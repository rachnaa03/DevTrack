"""
RecommendationRepository — Task 11.3

Encapsulates all database operations for the Recommendation model.

Design notes
------------
- Follows the same constructor-injection pattern as InsightRepository:
  __init__(self, db: AsyncSession).
- Every write commits and refreshes the record before returning it.
  On failure it rolls back and re-raises, following InsightRepository convention.
- The deduplication key is (user_id, rule_id, rule_version) — enforced by
  the DB UNIQUE constraint and also queried here before any INSERT attempt.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation


class RecommendationRepository:
    """Repository class encapsulating database operations for the Recommendation model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, record: Recommendation) -> Recommendation:
        """
        Persist a new Recommendation record and commit the transaction.

        Rolls back on any error.
        """
        self.db.add(record)
        try:
            await self.db.commit()
            await self.db.refresh(record)
            return record
        except Exception:
            await self.db.rollback()
            raise

    async def update_status(self, record: Recommendation, new_status: str) -> Recommendation:
        """
        Update the status of an existing Recommendation in place.

        new_status must be one of: 'active', 'dismissed', 'completed'.
        Commits and refreshes before returning.
        Rolls back on any error.
        """
        record.status = new_status
        self.db.add(record)
        try:
            await self.db.commit()
            await self.db.refresh(record)
            return record
        except Exception:
            await self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_rule_key(
        self,
        user_id: UUID,
        rule_id: str,
        rule_version: str,
    ) -> Recommendation | None:
        """
        Look up an existing recommendation by the deduplication key.

        Returns None if no matching record exists.
        This is the primary method used by the orchestrator to decide whether
        to insert a new record or skip/update an existing one.
        """
        query = select(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.rule_id == rule_id,
            Recommendation.rule_version == rule_version,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_active_by_user(
        self,
        user_id: UUID,
    ) -> list[Recommendation]:
        """
        Return all active recommendations for a user, ordered newest-first.

        Used by the orchestrator to discover stale active recommendations
        that should be resolved when their rule no longer fires.
        """
        query = (
            select(Recommendation)
            .filter(
                Recommendation.user_id == user_id,
                Recommendation.status == "active",
            )
            .order_by(Recommendation.generated_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[Recommendation]:
        """
        Return all recommendations for a user (any status), newest-first.

        Useful for history/audit queries from API routes (Task 12.x).
        """
        if limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        query = (
            select(Recommendation)
            .filter(Recommendation.user_id == user_id)
            .order_by(Recommendation.generated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
