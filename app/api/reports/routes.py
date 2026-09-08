"""
Weekly Retrospective Reports API Router — Task 14.3

Implements:
- GET /api/v1/reports/weekly (API_SPECIFICATION.md Section 7.1)
- GET /api/v1/reports/weekly/{id} (API_SPECIFICATION.md Section 7.2)

Follows the DevTrack layered architecture:
  - APIRouter tagged 'Reports'
  - Local dependency factory get_weekly_report_service
  - Route handlers delegate to WeeklyReportService
  - get_current_user enforces JWT authentication and user ownership
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.weekly_report import WeeklyReportRepository
from app.schemas.reports import (
    WeeklyReportListItemSchema,
    WeeklyReportResponseSchema,
    WeeklyReportsIndexResponse,
)
from app.services.reports.summary import WeeklyReportService

router = APIRouter(tags=["Reports"])


async def get_weekly_report_service(
    db: AsyncSession = Depends(get_db),
) -> WeeklyReportService:
    """Construct and return a WeeklyReportService with injected repositories."""
    return WeeklyReportService(
        weekly_report_repo=WeeklyReportRepository(db),
        github_history_repo=GitHubHistoryRepository(db),
        leetcode_history_repo=LeetCodeHistoryRepository(db),
        score_repo=DeveloperScoreRepository(db),
    )


@router.get(
    "/weekly",
    response_model=WeeklyReportsIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Weekly Reports Index",
    description="Get chronological listing of generated weekly retrospective reports for the authenticated developer.",
    responses={
        200: {"description": "Weekly reports index successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
        422: {"description": "Validation error on limit query parameter."},
    },
)
async def get_weekly_reports_index(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of reports to return (1-100).",
    ),
    current_user: User = Depends(get_current_user),
    service: WeeklyReportService = Depends(get_weekly_report_service),
) -> WeeklyReportsIndexResponse:
    """
    Retrieve chronological listing of generated weekly retrospective reports.
    """
    reports = await service.get_user_reports_index(user_id=current_user.id, limit=limit)
    return WeeklyReportsIndexResponse(
        reports=[WeeklyReportListItemSchema.model_validate(r) for r in reports]
    )


@router.get(
    "/weekly/{id}",
    response_model=WeeklyReportResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Fetch Weekly Report Details",
    description="Fetch the complete aggregated retrospective values of a specific weekly report.",
    responses={
        200: {"description": "Weekly report details successfully retrieved."},
        401: {"description": "Missing or invalid authentication token."},
        404: {"description": "Report not found or does not belong to authenticated user."},
        422: {"description": "Invalid UUID format."},
    },
)
async def get_weekly_report_detail(
    id: UUID = Path(description="UUID of the weekly report to retrieve."),
    current_user: User = Depends(get_current_user),
    service: WeeklyReportService = Depends(get_weekly_report_service),
) -> WeeklyReportResponseSchema:
    """
    Retrieve complete retrospective values of a specific weekly report.
    Returns 404 if the report does not exist or belongs to another user.
    """
    report = await service.get_user_report_by_id(user_id=current_user.id, report_id=id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly report not found.",
        )
    return WeeklyReportResponseSchema.model_validate(report)
