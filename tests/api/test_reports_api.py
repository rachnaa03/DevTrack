"""
Weekly Reports API Integration Tests — Task 14.3

Tests for:
- GET /api/v1/reports/weekly (Index endpoint)
- GET /api/v1/reports/weekly/{id} (Detail endpoint)
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.reports.routes import get_weekly_report_service
from app.main import app
from app.models.user import User
from app.models.weekly_report import WeeklyReport
from app.services.reports.summary import WeeklyReportService

client = TestClient(app)


@pytest.fixture
def mock_authenticated_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="developer@example.com",
        hashed_password="hashed_password",
    )


def test_get_weekly_reports_unauthenticated_returns_401() -> None:
    """Verify GET /api/v1/reports/weekly requires authentication."""
    response = client.get("/api/v1/reports/weekly")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_weekly_reports_authenticated_success_default_limit(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly returns 200 OK and default 20 limit."""
    report_id = uuid.uuid4()
    mock_report = WeeklyReport(
        id=report_id,
        user_id=mock_authenticated_user.id,
        week_start=date(2026, 8, 17),
        week_end=date(2026, 8, 23),
        report_data={},
        created_at=datetime(2026, 8, 24, 0, 1, tzinfo=timezone.utc),
    )

    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_reports_index = AsyncMock(return_value=[mock_report])

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/reports/weekly")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reports" in data
        assert len(data["reports"]) == 1
        item = data["reports"][0]
        assert item["id"] == str(report_id)
        assert item["week_start"] == "2026-08-17"
        assert item["week_end"] == "2026-08-23"
        assert "created_at" in item
        mock_service.get_user_reports_index.assert_called_once_with(
            user_id=mock_authenticated_user.id,
            limit=20,
        )
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_reports_authenticated_custom_limit(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly passes custom limit to service."""
    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_reports_index = AsyncMock(return_value=[])

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/reports/weekly?limit=50")
        assert response.status_code == status.HTTP_200_OK
        mock_service.get_user_reports_index.assert_called_once_with(
            user_id=mock_authenticated_user.id,
            limit=50,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, 101, 500, "abc", ""],
)
def test_get_weekly_reports_invalid_limits_returns_422(
    mock_authenticated_user: User,
    invalid_limit: object,
) -> None:
    """Verify GET /api/v1/reports/weekly rejects invalid limits with 422."""
    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user

    try:
        response = client.get(f"/api/v1/reports/weekly?limit={invalid_limit}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_reports_empty_returns_200(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly returns empty reports list when no reports exist."""
    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_reports_index = AsyncMock(return_value=[])

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/reports/weekly")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"reports": []}
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_report_detail_unauthenticated_returns_401() -> None:
    """Verify GET /api/v1/reports/weekly/{id} requires authentication."""
    report_id = uuid.uuid4()
    response = client.get(f"/api/v1/reports/weekly/{report_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_weekly_report_detail_authenticated_success(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly/{id} returns complete detailed report matching spec."""
    report_id = uuid.uuid4()
    created_dt = datetime(2026, 8, 24, 0, 1, tzinfo=timezone.utc)
    mock_report = WeeklyReport(
        id=report_id,
        user_id=mock_authenticated_user.id,
        week_start=date(2026, 8, 17),
        week_end=date(2026, 8, 23),
        report_data={
            "commits_count": 25,
            "problems_solved": 8,
            "score_delta": 15,
            "summary": "Consistent performance this week. You excelled in Array algorithms and maintained a daily commit streak.",
            "weekly_subscores": {
                "consistency": 185,
                "depth": 275,
                "impact": 275,
            },
            "weak_topics": ["Dynamic Programming"],
        },
        created_at=created_dt,
    )

    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_report_by_id = AsyncMock(return_value=mock_report)

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get(f"/api/v1/reports/weekly/{report_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(report_id)
        assert data["week_start"] == "2026-08-17"
        assert data["week_end"] == "2026-08-23"
        assert data["report_data"]["commits_count"] == 25
        assert data["report_data"]["problems_solved"] == 8
        assert data["report_data"]["score_delta"] == 15
        assert "Consistent performance" in data["report_data"]["summary"]
        assert data["report_data"]["weekly_subscores"] == {
            "consistency": 185,
            "depth": 275,
            "impact": 275,
        }
        assert data["report_data"]["weak_topics"] == ["Dynamic Programming"]
        assert "created_at" in data
        mock_service.get_user_report_by_id.assert_called_once_with(
            user_id=mock_authenticated_user.id,
            report_id=report_id,
        )
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_report_detail_not_found_returns_404(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly/{id} returns 404 when report does not exist."""
    report_id = uuid.uuid4()
    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_report_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get(f"/api/v1/reports/weekly/{report_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Weekly report not found" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_report_detail_wrong_user_returns_404(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly/{id} returns 404 when report belongs to another user."""
    report_id = uuid.uuid4()
    # When report belongs to another user, service returns None, resulting in 404
    mock_service = MagicMock(spec=WeeklyReportService)
    mock_service.get_user_report_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user
    app.dependency_overrides[get_weekly_report_service] = lambda: mock_service

    try:
        response = client.get(f"/api/v1/reports/weekly/{report_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Weekly report not found" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_weekly_report_detail_invalid_uuid_returns_422(
    mock_authenticated_user: User,
) -> None:
    """Verify GET /api/v1/reports/weekly/{id} returns 422 for malformed UUID."""
    app.dependency_overrides[get_current_user] = lambda: mock_authenticated_user

    try:
        response = client.get("/api/v1/reports/weekly/not-a-valid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    finally:
        app.dependency_overrides.clear()
