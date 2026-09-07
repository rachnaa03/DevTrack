"""
APScheduler Lifecycle Manager — Task 13.1

Manages the in-process AsyncIOScheduler instance lifecycle for DevTrack
(ADR 008, TECH_STACK.md Section 8, IMPLEMENTATION_ROADMAP.md Task 13.1).

Responsibilities:
1. Initialize AsyncIOScheduler with appropriate job store:
   - Development / Production: SQLAlchemyJobStore backed by PostgreSQL ('apscheduler_jobs' table).
   - Testing: MemoryJobStore for fast, isolated tests.
2. Provide idempotent startup and graceful shutdown hooks for FastAPI lifespan.
3. Expose scheduler access for future job registration (Task 13.2).
"""

import logging
from typing import Any

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger("devtrack.scheduler")


def _get_sync_database_url(async_url: str) -> str:
    """
    Derive a synchronous database URL for APScheduler's SQLAlchemyJobStore.

    APScheduler 3.x SQLAlchemyJobStore requires a synchronous DB-API connection
    (e.g., psycopg2). The primary application engine remains asynchronous (asyncpg).
    """
    if async_url.startswith("postgresql+asyncpg://"):
        return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if async_url.startswith("sqlite+aiosqlite://"):
        return async_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return async_url


class SchedulerManager:
    """
    Encapsulates APScheduler instance creation, configuration, and lifecycle management.
    """

    def __init__(self, use_memory_jobstore: bool | None = None) -> None:
        """
        Initialize the scheduler manager.

        :param use_memory_jobstore: Explicitly force MemoryJobStore. If None, uses
                                    MemoryJobStore when ENVIRONMENT == 'testing',
                                    otherwise uses SQLAlchemyJobStore.
        """
        self._use_memory_jobstore = (
            use_memory_jobstore
            if use_memory_jobstore is not None
            else (settings.ENVIRONMENT == "testing")
        )
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running: bool = False
        self._init_scheduler()

    def _init_scheduler(self) -> None:
        """Configure the AsyncIOScheduler with appropriate job stores and executors."""
        jobstores: dict[str, Any] = {}

        if self._use_memory_jobstore:
            jobstores["default"] = MemoryJobStore()
            store_type = "memory"
        else:
            sync_url = _get_sync_database_url(settings.DATABASE_URL)
            jobstores["default"] = SQLAlchemyJobStore(
                url=sync_url,
                tablename="apscheduler_jobs",
            )
            store_type = "sqlalchemy_postgresql"

        executors = {
            "default": AsyncIOExecutor(),
        }

        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        logger.info(
            "APScheduler initialized",
            extra={
                "extra_data": {
                    "job_store_type": store_type,
                    "environment": settings.ENVIRONMENT,
                    "timezone": "UTC",
                }
            },
        )

    @property
    def is_running(self) -> bool:
        """Return True if the scheduler is currently active and running."""
        return bool(self._is_running and self._scheduler and self._scheduler.running)

    def get_scheduler(self) -> AsyncIOScheduler:
        """
        Access the underlying AsyncIOScheduler instance for job registration.

        :raises RuntimeError: If the scheduler has not been initialized.
        """
        if self._scheduler is None:
            raise RuntimeError("Scheduler has not been initialized.")
        return self._scheduler

    def start(self) -> None:
        """
        Start the APScheduler instance.

        Safe and idempotent: if the scheduler is already running, no action is taken.
        """
        if self.is_running:
            logger.info("APScheduler start requested but it is already running.")
            return

        try:
            self.get_scheduler().start()
            self._is_running = True
            logger.info(
                "APScheduler started successfully",
                extra={
                    "extra_data": {
                        "environment": settings.ENVIRONMENT,
                        "sync_interval_hours": settings.SYNC_INTERVAL_HOURS,
                    }
                },
            )
        except Exception as exc:
            self._is_running = False
            logger.exception("Failed to start APScheduler")
            raise exc

    def shutdown(self, wait: bool = False) -> None:
        """
        Gracefully stop the APScheduler instance and release resources.

        Safe and idempotent: if the scheduler is not running, no action is taken.

        :param wait: If True, wait for currently executing jobs to finish.
        """
        if not self.is_running:
            logger.debug("APScheduler shutdown requested but it is not running.")
            return

        try:
            self.get_scheduler().shutdown(wait=wait)
            self._is_running = False
            logger.info(
                "APScheduler shut down successfully",
                extra={"extra_data": {"wait": wait}},
            )
        except Exception as exc:
            logger.exception("Error during APScheduler shutdown")
            raise exc

    def register_sync_job(self, job_func: Any = None) -> Any:
        """
        Register the recurring developer data synchronization job in APScheduler.

        :param job_func: Async callable to execute. If None, lazily imports
                         `run_scheduled_sync` from `app.services.scheduler.orchestrator`.
        """
        if job_func is None:
            from app.services.scheduler.orchestrator import run_scheduled_sync

            job_func = run_scheduled_sync

        return self.get_scheduler().add_job(
            func=job_func,
            trigger="interval",
            hours=settings.SYNC_INTERVAL_HOURS,
            id="periodic_developer_sync",
            name="Periodic Developer Data Synchronization",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )


# Singleton instance for application lifecycle integration
scheduler_manager = SchedulerManager()

