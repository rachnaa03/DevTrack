import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job import SyncJob
from app.repositories.sync_job import SyncJobRepository


@pytest.mark.asyncio
async def test_create_sync_job_success() -> None:
    """Verify create_sync_job adds, commits, and returns a new running SyncJob."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()

    repo = SyncJobRepository(mock_db)
    now = datetime.now(timezone.utc)
    job = await repo.create_sync_job(started_at=now)

    assert job.status == "running"
    assert job.started_at == now
    assert job.total_users == 0
    assert job.successful_users == 0
    assert job.failed_users == 0
    assert job.skipped_users == 0

    mock_db.add.assert_called_once_with(job)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(job)
    mock_db.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_sync_job_rollback_on_error() -> None:
    """Verify create_sync_job rolls back when a database error occurs."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.commit = AsyncMock(side_effect=Exception("DB write error"))
    mock_db.rollback = AsyncMock()

    repo = SyncJobRepository(mock_db)
    with pytest.raises(Exception, match="DB write error"):
        await repo.create_sync_job()

    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_sync_job_completion_success() -> None:
    """Verify update_sync_job_completion updates fields and commits."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()

    job_id = uuid.uuid4()
    existing_job = SyncJob(
        id=job_id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_job
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    completed_at = datetime.now(timezone.utc)

    updated = await repo.update_sync_job_completion(
        sync_job_id=job_id,
        status="success",
        completed_at=completed_at,
        total_users=5,
        successful_users=5,
        failed_users=0,
        skipped_users=0,
        error_summary=None,
    )

    assert updated is not None
    assert updated.status == "success"
    assert updated.completed_at == completed_at
    assert updated.total_users == 5
    assert updated.successful_users == 5
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_sync_job_completion_not_found() -> None:
    """Verify update_sync_job_completion returns None when job doesn't exist."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    result = await repo.update_sync_job_completion(
        sync_job_id=uuid.uuid4(),
        status="failed",
        completed_at=datetime.now(timezone.utc),
        total_users=0,
        successful_users=0,
        failed_users=0,
        skipped_users=0,
        error_summary="Not found",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_latest_sync_job() -> None:
    """Verify get_latest_sync_job executes query and returns first scalar."""
    mock_db = MagicMock(spec=AsyncSession)
    job = SyncJob(id=uuid.uuid4(), started_at=datetime.now(timezone.utc), status="success")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = job
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    result = await repo.get_latest_sync_job()
    assert result == job


@pytest.mark.asyncio
async def test_get_running_sync_job() -> None:
    """Verify get_running_sync_job queries for running status."""
    mock_db = MagicMock(spec=AsyncSession)
    job = SyncJob(id=uuid.uuid4(), started_at=datetime.now(timezone.utc), status="running")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = job
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    result = await repo.get_running_sync_job()
    assert result == job


@pytest.mark.asyncio
async def test_get_by_id() -> None:
    """Verify get_by_id returns specific job."""
    mock_db = MagicMock(spec=AsyncSession)
    job_id = uuid.uuid4()
    job = SyncJob(id=job_id, started_at=datetime.now(timezone.utc), status="success")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = job
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    result = await repo.get_by_id(job_id)
    assert result == job


@pytest.mark.asyncio
async def test_list_sync_jobs() -> None:
    """Verify list_sync_jobs returns list bounded by safe limits."""
    mock_db = MagicMock(spec=AsyncSession)
    jobs = [
        SyncJob(id=uuid.uuid4(), started_at=datetime.now(timezone.utc), status="success"),
        SyncJob(id=uuid.uuid4(), started_at=datetime.now(timezone.utc), status="failed"),
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = jobs
    mock_db.execute = AsyncMock(return_value=mock_result)

    repo = SyncJobRepository(mock_db)
    result = await repo.list_sync_jobs(limit=5)
    assert result == jobs
