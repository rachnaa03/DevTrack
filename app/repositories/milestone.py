from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.milestone import Milestone


class MilestoneRepository:
    """Repository class encapsulating database operations for the Milestone model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_milestone(
        self,
        user_id: UUID,
        name: str,
        description: str | None,
        badge_url: str | None,
        achieved_at: datetime | None = None,
    ) -> Milestone:
        """
        Create and persist a new milestone badge for a user.
        """
        if achieved_at is None:
            achieved_at = datetime.now(timezone.utc)

        milestone = Milestone(
            user_id=user_id,
            name=name,
            description=description,
            badge_url=badge_url,
            achieved_at=achieved_at,
        )
        self.db.add(milestone)
        try:
            await self.db.commit()
            await self.db.refresh(milestone)
            return milestone
        except Exception:
            await self.db.rollback()
            raise

    async def get_milestones_by_user_id(
        self,
        user_id: UUID,
    ) -> list[Milestone]:
        """
        Retrieve all milestones earned by a user, sorted by achieved_at descending.
        """
        query = (
            select(Milestone)
            .filter(Milestone.user_id == user_id)
            .order_by(Milestone.achieved_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_milestone_names_by_user_id(
        self,
        user_id: UUID,
    ) -> set[str]:
        """
        Retrieve the set of milestone names already earned by the user.
        """
        query = (
            select(Milestone.name)
            .filter(Milestone.user_id == user_id)
        )
        result = await self.db.execute(query)
        return set(result.scalars().all())
