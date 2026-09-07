"""
Unit and integration tests for APScheduler Lifecycle Manager (Task 13.1).

Verifies:
- SchedulerManager initialization with MemoryJobStore and SQLAlchemyJobStore.
- Idempotent start and graceful shutdown.
- State transitions (is_running property).
- Sync database URL resolution.
- FastAPI lifespan integration (startup and shutdown lifecycle).
"""

from unittest.mock import patch

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.testclient import TestClient

from app.main import app
from app.services.scheduler.manager import (
    SchedulerManager,
    _get_sync_database_url,
    scheduler_manager,
)


def test_sync_database_url_converter() -> None:
    """Verify async database driver schemes are converted to synchronous equivalents."""
    async_pg = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert _get_sync_database_url(async_pg) == "postgresql+psycopg2://user:pass@localhost:5432/db"

    async_sqlite = "sqlite+aiosqlite:///test.db"
    assert _get_sync_database_url(async_sqlite) == "sqlite:///test.db"

    other_url = "postgresql://user:pass@localhost:5432/db"
    assert _get_sync_database_url(other_url) == other_url


def test_scheduler_manager_init_memory_jobstore() -> None:
    """Verify SchedulerManager configures MemoryJobStore when requested."""
    manager = SchedulerManager(use_memory_jobstore=True)
    scheduler = manager.get_scheduler()

    assert isinstance(scheduler, AsyncIOScheduler)
    assert "default" in scheduler._jobstores
    assert isinstance(scheduler._jobstores["default"], MemoryJobStore)
    assert not manager.is_running


def test_scheduler_manager_init_sqlalchemy_jobstore() -> None:
    """Verify SchedulerManager configures SQLAlchemyJobStore with apscheduler_jobs tablename."""
    manager = SchedulerManager(use_memory_jobstore=False)
    scheduler = manager.get_scheduler()

    assert isinstance(scheduler, AsyncIOScheduler)
    assert "default" in scheduler._jobstores
    assert isinstance(scheduler._jobstores["default"], SQLAlchemyJobStore)
    assert scheduler._jobstores["default"].jobs_t.name == "apscheduler_jobs"
    assert not manager.is_running


@pytest.mark.asyncio
async def test_scheduler_manager_start_and_shutdown() -> None:
    """Verify start() and shutdown() lifecycle transitions."""
    manager = SchedulerManager(use_memory_jobstore=True)
    assert not manager.is_running

    manager.start()
    assert manager.is_running

    manager.shutdown(wait=False)
    assert not manager.is_running


@pytest.mark.asyncio
async def test_scheduler_manager_idempotent_start() -> None:
    """Verify calling start() multiple times is safe and does not raise errors."""
    manager = SchedulerManager(use_memory_jobstore=True)
    manager.start()
    assert manager.is_running

    # Second start call should be a no-op
    manager.start()
    assert manager.is_running

    manager.shutdown(wait=False)
    assert not manager.is_running


def test_scheduler_manager_idempotent_shutdown() -> None:
    """Verify calling shutdown() on stopped scheduler is safe and does not raise errors."""
    manager = SchedulerManager(use_memory_jobstore=True)
    assert not manager.is_running

    # Shutdown when not running should be safe
    manager.shutdown(wait=False)
    assert not manager.is_running


def test_scheduler_manager_get_scheduler() -> None:
    """Verify get_scheduler returns the configured AsyncIOScheduler instance."""
    manager = SchedulerManager(use_memory_jobstore=True)
    scheduler = manager.get_scheduler()
    assert isinstance(scheduler, AsyncIOScheduler)


def test_fastapi_lifespan_starts_and_stops_scheduler() -> None:
    """Verify FastAPI application lifespan starts and stops the scheduler manager."""
    with patch.object(scheduler_manager, "start") as mock_start, \
         patch.object(scheduler_manager, "shutdown") as mock_shutdown:
        with TestClient(app) as client:
            mock_start.assert_called_once()
            response = client.get("/")
            assert response.status_code == 200

        mock_shutdown.assert_called_once_with(wait=False)
