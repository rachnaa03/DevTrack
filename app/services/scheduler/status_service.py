import logging
from app.repositories.sync_job import SyncJobRepository
from app.schemas.sync_status import (
    SyncHealthResponse,
    SyncJobSchema,
    SyncStatusResponse,
)
from app.services.scheduler.manager import scheduler_manager

logger = logging.getLogger("devtrack.sync_status")


class SyncStatusService:
    """
    Coordinates and computes synchronization status and health metrics.
    """

    def __init__(self, sync_job_repo: SyncJobRepository) -> None:
        self.sync_job_repo = sync_job_repo

    async def get_sync_status(self) -> SyncStatusResponse:
        """
        Assemble detailed synchronization status and execution metrics for authenticated consumers.
        """
        scheduler_running = scheduler_manager.is_running
        running_job = await self.sync_job_repo.get_running_sync_job()
        is_running = running_job is not None

        latest_job = await self.sync_job_repo.get_latest_sync_job()
        latest_job_schema: SyncJobSchema | None = None

        if latest_job is not None:
            duration_seconds: float | None = None
            if latest_job.completed_at is not None:
                duration_seconds = round(
                    (latest_job.completed_at - latest_job.started_at).total_seconds(), 2
                )

            latest_job_schema = SyncJobSchema(
                id=latest_job.id,
                started_at=latest_job.started_at,
                completed_at=latest_job.completed_at,
                status=latest_job.status,  # type: ignore[arg-type]
                total_users=latest_job.total_users if latest_job.total_users is not None else 0,
                successful_users=latest_job.successful_users if latest_job.successful_users is not None else 0,
                failed_users=latest_job.failed_users if latest_job.failed_users is not None else 0,
                skipped_users=latest_job.skipped_users if latest_job.skipped_users is not None else 0,
                error_summary=latest_job.error_summary,
                duration_seconds=duration_seconds,
            )


        return SyncStatusResponse(
            is_running=is_running,
            scheduler_running=scheduler_running,
            latest_job=latest_job_schema,
        )

    async def get_sync_health(self) -> SyncHealthResponse:
        """
        Evaluate and return high-level synchronization and scheduler health.
        Safe for public health checks without exposing sensitive error traces.
        """
        scheduler_running = scheduler_manager.is_running
        scheduler_status = "running" if scheduler_running else "stopped"

        latest_job = await self.sync_job_repo.get_latest_sync_job()

        if not scheduler_running:
            # Scheduler is stopped -> System is unhealthy
            last_sync_status = (
                latest_job.status
                if latest_job is not None
                else "never_run"
            )
            last_sync_timestamp = latest_job.started_at if latest_job is not None else None
            return SyncHealthResponse(
                status="unhealthy",
                scheduler_status="stopped",
                last_sync_status=last_sync_status,  # type: ignore[arg-type]
                last_sync_timestamp=last_sync_timestamp,
            )

        if latest_job is None:
            # Scheduler active, no sync has executed yet -> System is healthy
            return SyncHealthResponse(
                status="healthy",
                scheduler_status="running",
                last_sync_status="never_run",
                last_sync_timestamp=None,
            )

        last_sync_timestamp = latest_job.started_at
        job_status = latest_job.status

        if job_status == "running":
            health_status = "healthy"
            last_sync_status = "running"
        elif job_status == "success":
            health_status = "healthy"
            last_sync_status = "success"
        elif job_status == "partial_failure":
            health_status = "degraded"
            last_sync_status = "partial_failure"
        elif job_status == "failed":
            health_status = "unhealthy"
            last_sync_status = "failed"
        else:
            health_status = "healthy"
            last_sync_status = "success"

        return SyncHealthResponse(
            status=health_status,
            scheduler_status="running",
            last_sync_status=last_sync_status,  # type: ignore[arg-type]
            last_sync_timestamp=last_sync_timestamp,
        )
