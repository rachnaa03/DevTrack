import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.models.sync_job import SyncJob
from app.repositories.sync_job import SyncJobRepository
from app.services.scheduler.manager import SchedulerManager
from app.services.scheduler.status_service import SyncStatusService


@pytest.mark.asyncio
async def test_get_sync_status_never_run() -> None:
    """Verify get_sync_status returns empty latest_job when no sync has ever executed."""
    mock_repo = MagicMock(spec=SyncJobRepository)
    mock_repo.get_running_sync_job = AsyncMock(return_value=None)
    mock_repo.get_latest_sync_job = AsyncMock(return_value=None)

    service = SyncStatusService(mock_repo)

    with patch.object(SchedulerManager, "is_running", new_callable=PropertyMock, return_value=True):
        status = await service.get_sync_status()

        assert not status.is_running
        assert status.scheduler_running
        assert status.latest_job is None


@pytest.mark.asyncio
async def test_get_sync_status_currently_running() -> None:
    """Verify get_sync_status returns is_running=True when a job is in progress."""
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    running_job = SyncJob(
        id=job_id,
        started_at=now,
        completed_at=None,
        status="running",
        total_users=0,
        successful_users=0,
        failed_users=0,
        skipped_users=0,
    )


    mock_repo = MagicMock(spec=SyncJobRepository)
    mock_repo.get_running_sync_job = AsyncMock(return_value=running_job)
    mock_repo.get_latest_sync_job = AsyncMock(return_value=running_job)

    service = SyncStatusService(mock_repo)

    with patch.object(SchedulerManager, "is_running", new_callable=PropertyMock, return_value=True):
        status = await service.get_sync_status()

        assert status.is_running
        assert status.scheduler_running
        assert status.latest_job is not None
        assert status.latest_job.id == job_id
        assert status.latest_job.status == "running"
        assert status.latest_job.duration_seconds is None


@pytest.mark.asyncio
async def test_get_sync_status_completed_with_duration() -> None:
    """Verify get_sync_status calculates duration_seconds for completed job."""
    job_id = uuid.uuid4()
    start = datetime.now(timezone.utc) - timedelta(seconds=12.5)
    end = datetime.now(timezone.utc)
    completed_job = SyncJob(
        id=job_id,
        started_at=start,
        completed_at=end,
        status="success",
        total_users=10,
        successful_users=10,
        failed_users=0,
        skipped_users=0,
        error_summary=None,
    )

    mock_repo = MagicMock(spec=SyncJobRepository)
    mock_repo.get_running_sync_job = AsyncMock(return_value=None)
    mock_repo.get_latest_sync_job = AsyncMock(return_value=completed_job)

    service = SyncStatusService(mock_repo)

    with patch.object(SchedulerManager, "is_running", new_callable=PropertyMock, return_value=True):
        status = await service.get_sync_status()

        assert not status.is_running
        assert status.scheduler_running
        assert status.latest_job is not None
        assert status.latest_job.status == "success"
        assert status.latest_job.total_users == 10
        assert status.latest_job.duration_seconds == pytest.approx(12.5, 0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scheduler_active", "job_status", "expected_health", "expected_last_sync"),
    [
        (False, "success", "unhealthy", "success"),
        (False, None, "unhealthy", "never_run"),
        (True, None, "healthy", "never_run"),
        (True, "running", "healthy", "running"),
        (True, "success", "healthy", "success"),
        (True, "partial_failure", "degraded", "partial_failure"),
        (True, "failed", "unhealthy", "failed"),
    ],
)
async def test_get_sync_health_matrix(
    scheduler_active: bool,
    job_status: str | None,
    expected_health: str,
    expected_last_sync: str,
) -> None:
    """Verify the deterministic health evaluation matrix across scheduler and sync states."""
    mock_repo = MagicMock(spec=SyncJobRepository)
    job: SyncJob | None = None

    if job_status is not None:
        job = SyncJob(
            id=uuid.uuid4(),
            started_at=datetime.now(timezone.utc),
            status=job_status,
        )

    mock_repo.get_latest_sync_job = AsyncMock(return_value=job)
    service = SyncStatusService(mock_repo)

    with patch.object(
        SchedulerManager,
        "is_running",
        new_callable=PropertyMock,
        return_value=scheduler_active,
    ):
        health = await service.get_sync_health()

        assert health.status == expected_health
        assert health.scheduler_status == ("running" if scheduler_active else "stopped")
        assert health.last_sync_status == expected_last_sync
        if job is not None:
            assert health.last_sync_timestamp == job.started_at
        else:
            assert health.last_sync_timestamp is None
