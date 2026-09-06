"""
Integration tests for the Dashboard Summary API endpoint (Task 12.1).

Tests:
- GET /api/v1/dashboard/summary (200 OK — full data)
- GET /api/v1/dashboard/summary (200 OK — partial data / null platform stats)
- GET /api/v1/dashboard/summary (404 Not Found — no DeveloperScore)
- GET /api/v1/dashboard/summary (401 Unauthorized — missing/invalid token)
- User ownership: verifies data returned corresponds strictly to the authenticated user
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dashboard.routes import get_dashboard_summary_service
from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import User
from app.schemas.dashboard import (
    DashboardGitHubStatsSchema,
    DashboardLeetCodeStatsSchema,
    DashboardScoreSchema,
    DashboardStatsSchema,
    DashboardSummaryResponse,
)
from app.services.dashboard.summary import DashboardSummaryService

client = TestClient(app)


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="dev@example.com",
        hashed_password="hashed_password_123",
    )


@pytest.fixture
def sample_summary_response() -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        developer_score=DashboardScoreSchema(
            overall=720,
            consistency=180,
            depth=270,
            impact=270,
            computed_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        stats=DashboardStatsSchema(
            github=DashboardGitHubStatsSchema(
                total_commits=350,
                total_repositories=12,
                stars_earned=45,
                current_streak=5,
                longest_streak=14,
                contribution_consistency=0.85,
                primary_languages=["Python", "TypeScript"],
                data_as_of=date(2026, 9, 1),
            ),
            leetcode=DashboardLeetCodeStatsSchema(
                total_solved=150,
                easy_solved=50,
                medium_solved=80,
                hard_solved=20,
                active_streak=7,
                longest_streak=21,
                contribution_consistency=0.75,
                data_as_of=date(2026, 9, 1),
            ),
        ),
    )


def test_get_dashboard_summary_success(
    mock_user: User, sample_summary_response: DashboardSummaryResponse
) -> None:
    """Verify GET /api/v1/dashboard/summary returns 200 OK with full summary data."""
    mock_service = MagicMock(spec=DashboardSummaryService)
    mock_service.get_summary = AsyncMock(return_value=sample_summary_response)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_dashboard_summary_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "developer_score" in data
        assert data["developer_score"]["overall"] == 720
        assert data["developer_score"]["consistency"] == 180
        assert data["developer_score"]["depth"] == 270
        assert data["developer_score"]["impact"] == 270

        assert "stats" in data
        assert data["stats"]["github"]["total_commits"] == 350
        assert data["stats"]["github"]["primary_languages"] == ["Python", "TypeScript"]
        assert data["stats"]["leetcode"]["total_solved"] == 150
        assert data["stats"]["leetcode"]["active_streak"] == 7

        mock_service.get_summary.assert_awaited_once_with(mock_user.id)
    finally:
        app.dependency_overrides.clear()


def test_get_dashboard_summary_partial_data(mock_user: User) -> None:
    """Verify GET /api/v1/dashboard/summary preserves nulls when platform stats are missing."""
    partial_response = DashboardSummaryResponse(
        developer_score=DashboardScoreSchema(
            overall=500,
            consistency=125,
            depth=180,
            impact=195,
            computed_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        stats=DashboardStatsSchema(
            github=DashboardGitHubStatsSchema(
                total_commits=None,
                total_repositories=None,
                stars_earned=None,
                current_streak=None,
                longest_streak=None,
                contribution_consistency=None,
                primary_languages=None,
                data_as_of=None,
            ),
            leetcode=DashboardLeetCodeStatsSchema(
                total_solved=None,
                easy_solved=None,
                medium_solved=None,
                hard_solved=None,
                active_streak=None,
                longest_streak=None,
                contribution_consistency=None,
                data_as_of=None,
            ),
        ),
    )

    mock_service = MagicMock(spec=DashboardSummaryService)
    mock_service.get_summary = AsyncMock(return_value=partial_response)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_dashboard_summary_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["developer_score"]["overall"] == 500
        assert data["stats"]["github"]["total_commits"] is None
        assert data["stats"]["github"]["primary_languages"] is None
        assert data["stats"]["leetcode"]["total_solved"] is None
    finally:
        app.dependency_overrides.clear()


def test_get_dashboard_summary_not_found(mock_user: User) -> None:
    """Verify GET /api/v1/dashboard/summary returns 404 when no score is computed yet."""
    mock_service = MagicMock(spec=DashboardSummaryService)
    mock_service.get_summary = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_dashboard_summary_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No Developer Score found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_dashboard_summary_unauthorized() -> None:
    """Verify GET /api/v1/dashboard/summary returns 401 when no auth header is provided."""
    # Ensure no dependency override for get_current_user
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
