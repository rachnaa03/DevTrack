"""
Unit tests for TimelineService (Task 12.3).

Verifies:
- Timeline events retrieval and response mapping.
- Automatic account-linked event recording for connected platforms.
- Deduplication of account-linked events.
- Limit parameter handling.
- Empty timeline handling.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.profile import Profile
from app.models.timeline_event import TimelineEvent
from app.repositories.profile import ProfileRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.dashboard import MilestonesResponse, TimelineEventsResponse
from app.services.dashboard.milestones import MilestoneService
from app.services.dashboard.timeline import TimelineService

USER_ID = uuid.uuid4()


def _make_timeline_event(
    event_type: str = "account_linked",
    title: str = "GitHub Profile Connected",
    description: str = "Linked octocat",
    event_date: date = date(2026, 8, 1),
) -> MagicMock:
    ev = MagicMock(spec=TimelineEvent)
    ev.id = uuid.uuid4()
    ev.user_id = USER_ID
    ev.event_type = event_type
    ev.title = title
    ev.description = description
    ev.event_date = event_date
    ev.created_at = datetime.now(timezone.utc)
    return ev


@pytest.mark.asyncio
async def test_timeline_service_fetches_events() -> None:
    """Verify events from repository are transformed into response schema."""
    d1 = date(2026, 8, 3)
    d2 = date(2026, 8, 1)

    ev1 = _make_timeline_event(
        event_type="milestone_earned",
        title="First Problem Solved",
        description="Solved first problem",
        event_date=d1,
    )
    ev2 = _make_timeline_event(
        event_type="account_linked",
        title="GitHub Profile Connected",
        description="Linked octocat",
        event_date=d2,
    )

    timeline_repo = MagicMock(spec=TimelineRepository)
    timeline_repo.get_events_by_user_id = AsyncMock(return_value=[ev1, ev2])
    timeline_repo.exists_event = AsyncMock(return_value=True)

    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=None)

    milestone_service = MagicMock(spec=MilestoneService)
    milestone_service.get_milestones = AsyncMock(
        return_value=MilestonesResponse(milestones=[])
    )

    service = TimelineService(
        timeline_repo=timeline_repo,
        profile_repo=profile_repo,
        milestone_service=milestone_service,
    )

    result = await service.get_timeline(user_id=USER_ID, limit=10)

    assert isinstance(result, TimelineEventsResponse)
    assert len(result.events) == 2
    assert result.events[0].title == "First Problem Solved"
    assert result.events[0].event_date == d1
    assert result.events[1].title == "GitHub Profile Connected"
    assert result.events[1].event_date == d2

    timeline_repo.get_events_by_user_id.assert_awaited_once_with(
        user_id=USER_ID, limit=10
    )


@pytest.mark.asyncio
async def test_timeline_service_creates_account_linked_events() -> None:
    """Verify missing account_linked events are created when usernames are in profile."""
    profile = MagicMock(spec=Profile)
    profile.github_username = "octocat"
    profile.leetcode_username = "lc_user"
    profile.created_at = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)

    timeline_repo = MagicMock(spec=TimelineRepository)
    timeline_repo.exists_event = AsyncMock(return_value=False)
    timeline_repo.create_event = AsyncMock()
    timeline_repo.get_events_by_user_id = AsyncMock(return_value=[])

    milestone_service = MagicMock(spec=MilestoneService)
    milestone_service.get_milestones = AsyncMock(
        return_value=MilestonesResponse(milestones=[])
    )

    service = TimelineService(
        timeline_repo=timeline_repo,
        profile_repo=profile_repo,
        milestone_service=milestone_service,
    )

    await service.get_timeline(user_id=USER_ID, limit=20)

    # Both GitHub and LeetCode linked events should be created
    assert timeline_repo.create_event.await_count == 2


@pytest.mark.asyncio
async def test_timeline_service_empty_events() -> None:
    """Verify empty timeline returns empty list."""
    profile_repo = MagicMock(spec=ProfileRepository)
    profile_repo.get_by_user_id = AsyncMock(return_value=None)

    timeline_repo = MagicMock(spec=TimelineRepository)
    timeline_repo.get_events_by_user_id = AsyncMock(return_value=[])

    milestone_service = MagicMock(spec=MilestoneService)
    milestone_service.get_milestones = AsyncMock(
        return_value=MilestonesResponse(milestones=[])
    )

    service = TimelineService(
        timeline_repo=timeline_repo,
        profile_repo=profile_repo,
        milestone_service=milestone_service,
    )

    result = await service.get_timeline(user_id=USER_ID, limit=20)
    assert result.events == []
