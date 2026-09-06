"""
Timeline Events Service — Task 12.3

Orchestrates chronological developer progression events
(API_SPECIFICATION.md Section 4.3, SRS Section 3.6).

Aggregates events such as:
- Account linking milestones (GitHub profile connected, LeetCode profile connected).
- Earned milestone badges.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.models.profile import Profile
from app.repositories.profile import ProfileRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.dashboard import TimelineEventSchema, TimelineEventsResponse
from app.services.dashboard.milestones import MilestoneService

logger = logging.getLogger(__name__)


class TimelineService:
    """
    Service layer responsible for assembling and returning chronological timeline events.
    """

    def __init__(
        self,
        timeline_repo: TimelineRepository,
        profile_repo: ProfileRepository,
        milestone_service: MilestoneService,
    ) -> None:
        self.timeline_repo = timeline_repo
        self.profile_repo = profile_repo
        self.milestone_service = milestone_service

    async def get_timeline(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> TimelineEventsResponse:
        """
        Retrieve chronologically sorted achievements and events for the authenticated user.

        :param user_id: Authenticated user UUID.
        :param limit: Maximum count of events (1-100).
        :return: TimelineEventsResponse with sorted events.
        """
        # 1. Sync milestone events
        await self.milestone_service.get_milestones(user_id)

        # 2. Check profile for account linking events
        profile: Profile | None = await self.profile_repo.get_by_user_id(user_id)
        if profile is not None:
            now_date = datetime.now(timezone.utc).date()
            profile_date = profile.created_at.date() if profile.created_at else now_date

            if profile.github_username:
                gh_exists = await self.timeline_repo.exists_event(
                    user_id=user_id,
                    event_type="account_linked",
                    title="GitHub Profile Connected",
                )
                if not gh_exists:
                    await self.timeline_repo.create_event(
                        user_id=user_id,
                        event_type="account_linked",
                        title="GitHub Profile Connected",
                        description=f"Linked handle '{profile.github_username}' to DevTrack profile.",
                        event_date=profile_date,
                    )

            if profile.leetcode_username:
                lc_exists = await self.timeline_repo.exists_event(
                    user_id=user_id,
                    event_type="account_linked",
                    title="LeetCode Profile Connected",
                )
                if not lc_exists:
                    await self.timeline_repo.create_event(
                        user_id=user_id,
                        event_type="account_linked",
                        title="LeetCode Profile Connected",
                        description=f"Linked handle '{profile.leetcode_username}' to DevTrack profile.",
                        event_date=profile_date,
                    )

        # 3. Retrieve events
        records = await self.timeline_repo.get_events_by_user_id(user_id=user_id, limit=limit)

        return TimelineEventsResponse(
            events=[
                TimelineEventSchema(
                    event_date=r.event_date,
                    event_type=r.event_type,
                    title=r.title,
                    description=r.description,
                )
                for r in records
            ]
        )
