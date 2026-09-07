import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.sync_job import SyncJobRepository
from app.schemas.sync_status import (
    SyncHealthResponse,
    SyncStatusResponse,
)
from app.services.scheduler.status_service import SyncStatusService

logger = logging.getLogger("devtrack.api.sync")

router = APIRouter(tags=["Sync"])


def get_sync_status_service(db: AsyncSession = Depends(get_db)) -> SyncStatusService:
    """Dependency provider for SyncStatusService."""
    repo = SyncJobRepository(db)
    return SyncStatusService(repo)


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background synchronization status",
    description="Retrieve detailed status, metrics, and error summaries for background synchronization jobs. Requires JWT authentication.",
)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    service: SyncStatusService = Depends(get_sync_status_service),
) -> SyncStatusResponse:
    """Return execution metrics and scheduler status for authenticated users."""
    return await service.get_sync_status()


@router.get(
    "/health",
    response_model=SyncHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get synchronization health status",
    description="Public lightweight health check endpoint returning high-level scheduler and sync status without exposing sensitive diagnostic data.",
)
async def get_sync_health(
    service: SyncStatusService = Depends(get_sync_status_service),
) -> SyncHealthResponse:
    """Return sanitized, high-level sync health status."""
    return await service.get_sync_health()
