"""
Dashboard API Router — Tasks 12.1, 12.2 & 12.3

Implements:
- GET /api/v1/dashboard/summary (Task 12.1)
- GET /api/v1/dashboard/charts (Task 12.2)
- GET /api/v1/dashboard/timeline (Task 12.3)
- GET /api/v1/dashboard/milestones (Task 12.3)

Follows the same router pattern as app/api/profile/routes.py:
  - APIRouter with tag
  - Local dependency factory functions for services
  - Route handlers delegate entirely to the service layer
  - get_current_user enforces JWT authentication and user ownership

HTTP behavior:
  200 OK          — data assembled successfully
  401 Unauthorized — missing or invalid JWT (handled by get_current_user)
  404 Not Found   — user has no computed Developer Score yet (for /summary)
  422 Unprocessable Content — query validation failure (e.g. invalid parameter ranges)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.repositories.milestone import MilestoneRepository
from app.repositories.profile import ProfileRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.dashboard import (
    DashboardChartsResponse,
    DashboardSummaryResponse,
    MilestonesResponse,
    TimelineEventsResponse,
)
from app.services.dashboard.charts import DashboardChartService
from app.services.dashboard.milestones import MilestoneService
from app.services.dashboard.summary import DashboardSummaryService
from app.services.dashboard.timeline import TimelineService

router = APIRouter(tags=["Dashboard"])


async def get_dashboard_summary_service(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryService:
    """Construct and return a DashboardSummaryService with injected repositories."""
    return DashboardSummaryService(
        score_repo=DeveloperScoreRepository(db),
        github_repo=GitHubAnalyticsRepository(db),
        leetcode_repo=LeetCodeAnalyticsRepository(db),
    )


async def get_dashboard_chart_service(
    db: AsyncSession = Depends(get_db),
) -> DashboardChartService:
    """Construct and return a DashboardChartService with injected history repositories."""
    return DashboardChartService(
        github_history_repo=GitHubHistoryRepository(db),
        leetcode_history_repo=LeetCodeHistoryRepository(db),
    )


async def get_milestone_service(
    db: AsyncSession = Depends(get_db),
) -> MilestoneService:
    """Construct and return a MilestoneService with injected repositories."""
    return MilestoneService(
        milestone_repo=MilestoneRepository(db),
        timeline_repo=TimelineRepository(db),
        github_repo=GitHubAnalyticsRepository(db),
        leetcode_repo=LeetCodeAnalyticsRepository(db),
        score_repo=DeveloperScoreRepository(db),
    )


async def get_timeline_service(
    db: AsyncSession = Depends(get_db),
) -> TimelineService:
    """Construct and return a TimelineService with injected repositories and milestone service."""
    milestone_service = MilestoneService(
        milestone_repo=MilestoneRepository(db),
        timeline_repo=TimelineRepository(db),
        github_repo=GitHubAnalyticsRepository(db),
        leetcode_repo=LeetCodeAnalyticsRepository(db),
        score_repo=DeveloperScoreRepository(db),
    )
    return TimelineService(
        timeline_repo=TimelineRepository(db),
        profile_repo=ProfileRepository(db),
        milestone_service=milestone_service,
    )


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Fetch Dashboard Summary Metrics",
    description=(
        "Returns the current Developer Score, sub-scores, and key GitHub/LeetCode "
        "statistics for the authenticated user. "
        "Returns HTTP 404 if data ingestion has not yet completed for this user."
    ),
    responses={
        200: {"description": "Dashboard summary data successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
        404: {"description": "No Developer Score found — ingestion not yet complete."},
    },
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    service: DashboardSummaryService = Depends(get_dashboard_summary_service),
) -> DashboardSummaryResponse:
    """
    Retrieve the dashboard summary for the currently authenticated user.

    Returns the latest Developer Score alongside GitHub and LeetCode statistics.
    Platform stats fields may be null when analytics data is not yet available
    for that platform — null is never substituted with zero.
    """
    summary = await service.get_summary(current_user.id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Developer Score found for this user. Data ingestion has not completed yet.",
        )
    return summary


@router.get(
    "/charts",
    response_model=DashboardChartsResponse,
    summary="Fetch Historical Chart Range Data",
    description=(
        "Returns daily chronological history counts for commits and problems solved "
        "for the authenticated user across the specified calendar day interval."
    ),
    responses={
        200: {"description": "Historical chart data successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
        422: {"description": "Invalid query parameter values."},
    },
)
async def get_dashboard_charts(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Calendar interval filter in days (1-365).",
    ),
    current_user: User = Depends(get_current_user),
    service: DashboardChartService = Depends(get_dashboard_chart_service),
) -> DashboardChartsResponse:
    """
    Retrieve historical chart time-series data for the authenticated user.
    """
    return await service.get_historical_charts(user_id=current_user.id, days=days)


@router.get(
    "/timeline",
    response_model=TimelineEventsResponse,
    summary="Fetch Timeline Events",
    description=(
        "Returns chronologically sorted progression events (account linking, "
        "milestones earned) for the authenticated developer."
    ),
    responses={
        200: {"description": "Timeline events successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
        422: {"description": "Invalid limit parameter."},
    },
)
async def get_dashboard_timeline(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum count of timeline events (1-100).",
    ),
    current_user: User = Depends(get_current_user),
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineEventsResponse:
    """
    Retrieve timeline progression events for the authenticated user.
    """
    return await service.get_timeline(user_id=current_user.id, limit=limit)


@router.get(
    "/milestones",
    response_model=MilestonesResponse,
    summary="Fetch Earned Milestones",
    description=(
        "Returns all achievement milestone badges earned by the authenticated developer."
    ),
    responses={
        200: {"description": "Earned milestones successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
    },
)
async def get_dashboard_milestones(
    current_user: User = Depends(get_current_user),
    service: MilestoneService = Depends(get_milestone_service),
) -> MilestonesResponse:
    """
    Retrieve earned milestone badges for the authenticated user.
    """
    return await service.get_milestones(user_id=current_user.id)


