from datetime import date
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.timeline_event import TimelineEvent


class TimelineRepository:
    """Repository class encapsulating database operations for the TimelineEvent model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_event(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
        description: str | None,
        event_date: date,
    ) -> TimelineEvent:
        """
        Create and persist a new timeline event.
        """
        event = TimelineEvent(
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            event_date=event_date,
        )
        self.db.add(event)
        try:
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except Exception:
            await self.db.rollback()
            raise

    async def get_events_by_user_id(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[TimelineEvent]:
        """
        Retrieve chronological timeline events for a user, sorted by date descending.
        """
        query = (
            select(TimelineEvent)
            .filter(TimelineEvent.user_id == user_id)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def exists_event(
        self,
        user_id: UUID,
        event_type: str,
        title: str,
    ) -> bool:
        """
        Check if an event of a specific type and title already exists for the user.
        """
        query = (
            select(TimelineEvent.id)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == event_type,
                TimelineEvent.title == title,
            )
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar() is not None
