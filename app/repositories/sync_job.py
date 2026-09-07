from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job import SyncJob


class SyncJobRepository:
    """Repository encapsulating database operations for the SyncJob model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_sync_job(
        self,
        started_at: datetime | None = None,
    ) -> SyncJob:
        """
        Create and persist a new SyncJob with status 'running'.
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)

        job = SyncJob(
            started_at=started_at,
            status="running",
            total_users=0,
            successful_users=0,
            failed_users=0,
            skipped_users=0,
        )
        self.db.add(job)
        try:
            await self.db.commit()
            await self.db.refresh(job)
            return job
        except Exception:
            await self.db.rollback()
            raise

    async def update_sync_job_completion(
        self,
        sync_job_id: UUID,
        status: str,
        completed_at: datetime,
        total_users: int,
        successful_users: int,
        failed_users: int,
        skipped_users: int,
        error_summary: str | None,
    ) -> SyncJob | None:
        """
        Update a SyncJob upon execution completion and commit changes.
        """
        job = await self.get_by_id(sync_job_id)
        if not job:
            return None

        job.status = status
        job.completed_at = completed_at
        job.total_users = total_users
        job.successful_users = successful_users
        job.failed_users = failed_users
        job.skipped_users = skipped_users
        job.error_summary = error_summary

        try:
            await self.db.commit()
            await self.db.refresh(job)
            return job
        except Exception:
            await self.db.rollback()
            raise

    async def get_latest_sync_job(self) -> SyncJob | None:
        """
        Retrieve the most recently started SyncJob.
        """
        query = select(SyncJob).order_by(SyncJob.started_at.desc()).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_running_sync_job(self) -> SyncJob | None:
        """
        Retrieve the currently running SyncJob, if any.
        """
        query = (
            select(SyncJob)
            .filter(SyncJob.status == "running")
            .order_by(SyncJob.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_id(self, sync_job_id: UUID) -> SyncJob | None:
        """
        Retrieve a SyncJob by its unique UUID.
        """
        query = select(SyncJob).filter(SyncJob.id == sync_job_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_sync_jobs(self, limit: int = 10) -> list[SyncJob]:
        """
        Retrieve a list of recent SyncJobs sorted by started_at descending.
        """
        safe_limit = max(1, min(limit, 100))
        query = select(SyncJob).order_by(SyncJob.started_at.desc()).limit(safe_limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
