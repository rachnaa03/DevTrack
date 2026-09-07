import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.sync.routes import get_sync_status_service
from app.main import app
from app.models.sync_job import SyncJob
from app.models.user import User
from app.repositories.sync_job import SyncJobRepository
from app.services.scheduler.status_service import SyncStatusService

client = TestClient(app)


@pytest.fixture
def mock_authenticated_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="developer@example.com",
        hashed_password="hashed_password",
    )


def test_get_sync_status_unauthenticated_returns_401() -> None:
    """Verify GET /api/v1/sync/status requires JWT authentication."""
    response = client.get("/api/v1/sync/status")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_sync_status_authenticated_success(mock_authenticated_user: User) -> None:
    """Verify GET /api/v1/sync/status returns 200 OK and SyncStatusResponse schema."""
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    mock_job = SyncJob(
        id=job_id,
        started_at=now,
        completed_at=now,
        status="success",
        total_users=2,
        successful_users=2,
        failed_users=0,
        skipped_users=0,
        error_summary=None,
    )

    mock_repo = MagicMock(spec=SyncJobRepository)
    mock_repo.get_running_sync_job = AsyncMock(return_value=None)
    mock_repo.get_latest_sync_job = AsyncMock(return_value=mock_job)

    mock_service = SyncStatusService(mock_repo)

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_sync_status_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/sync/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_running"]
        assert "scheduler_running" in data
        assert data["latest_job"] is not None
        assert data["latest_job"]["id"] == str(job_id)
        assert data["latest_job"]["status"] == "success"
        assert data["latest_job"]["total_users"] == 2
        assert data["latest_job"]["successful_users"] == 2
    finally:
        app.dependency_overrides.clear()


def test_get_sync_health_public_success() -> None:
    """Verify GET /api/v1/sync/health is public and returns 200 OK with SyncHealthResponse."""
    mock_repo = MagicMock(spec=SyncJobRepository)
    mock_repo.get_latest_sync_job = AsyncMock(return_value=None)

    mock_service = SyncStatusService(mock_repo)
    app.dependency_overrides[get_sync_status_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/sync/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert data["scheduler_status"] in ["running", "stopped"]
        assert data["last_sync_status"] in ["success", "partial_failure", "failed", "running", "never_run"]
        # Ensure sensitive internal diagnostic / error summary fields are never exposed in health
        assert "error_summary" not in data
        assert "password" not in response.text
        assert "token" not in response.text
    finally:
        app.dependency_overrides.clear()
