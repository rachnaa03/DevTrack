import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_report import WeeklyReport
from app.repositories.weekly_report import WeeklyReportRepository


@pytest.mark.asyncio
async def test_weekly_report_create_or_update_success() -> None:
    """Verify create_or_update executes upsert statement, commits, and returns WeeklyReport."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)
    report_data = {
        "commits_count": 15,
        "problems_solved": 5,
        "score_delta": 10,
        "summary": "Solid progress.",
        "weekly_subscores": {"consistency": 150, "depth": 200, "impact": 180},
        "weak_topics": [],
    }

    mock_report = WeeklyReport(
        id=uuid.uuid4(),
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        report_data=report_data,
        created_at=datetime.now(timezone.utc),
    )

    mock_exec_result = MagicMock()
    mock_exec_result.scalars().one.return_value = mock_report
    mock_db.execute.return_value = mock_exec_result

    repo = WeeklyReportRepository(mock_db)
    result = await repo.create_or_update(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        report_data=report_data,
    )

    assert result == mock_report
    assert result.week_start == week_start
    assert result.week_end == week_end
    assert result.report_data["commits_count"] == 15
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_weekly_report_create_or_update_failure_rolls_back() -> None:
    """Verify create_or_update rolls back and re-raises exception on database error."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(side_effect=Exception("DB write error"))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    user_id = uuid.uuid4()
    repo = WeeklyReportRepository(mock_db)

    with pytest.raises(Exception, match="DB write error"):
        await repo.create_or_update(
            user_id=user_id,
            week_start=date(2026, 8, 17),
            week_end=date(2026, 8, 23),
            report_data={},
        )

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_report_get_by_id_found() -> None:
    """Verify get_by_id returns report when found."""
    mock_db = MagicMock(spec=AsyncSession)
    report_id = uuid.uuid4()
    mock_report = WeeklyReport(
        id=report_id,
        user_id=uuid.uuid4(),
        week_start=date(2026, 8, 17),
        week_end=date(2026, 8, 23),
        report_data={},
    )

    mock_exec_result = MagicMock()
    mock_exec_result.scalars().first.return_value = mock_report
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    repo = WeeklyReportRepository(mock_db)
    result = await repo.get_by_id(report_id)

    assert result == mock_report
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_report_get_by_id_none() -> None:
    """Verify get_by_id returns None when not found."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_exec_result = MagicMock()
    mock_exec_result.scalars().first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    repo = WeeklyReportRepository(mock_db)
    result = await repo.get_by_id(uuid.uuid4())

    assert result is None
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_report_get_by_user_and_week_found() -> None:
    """Verify get_by_user_and_week returns specific report."""
    mock_db = MagicMock(spec=AsyncSession)
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    mock_report = WeeklyReport(
        id=uuid.uuid4(),
        user_id=user_id,
        week_start=week_start,
        week_end=date(2026, 8, 23),
        report_data={},
    )

    mock_exec_result = MagicMock()
    mock_exec_result.scalars().first.return_value = mock_report
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    repo = WeeklyReportRepository(mock_db)
    result = await repo.get_by_user_and_week(user_id=user_id, week_start=week_start)

    assert result == mock_report
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_report_get_by_user_and_week_none() -> None:
    """Verify get_by_user_and_week returns None when record does not exist."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_exec_result = MagicMock()
    mock_exec_result.scalars().first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    repo = WeeklyReportRepository(mock_db)
    result = await repo.get_by_user_and_week(user_id=uuid.uuid4(), week_start=date(2026, 8, 17))

    assert result is None
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_report_get_reports_by_user() -> None:
    """Verify get_reports_by_user returns chronological list."""
    mock_db = MagicMock(spec=AsyncSession)
    user_id = uuid.uuid4()
    reports = [
        WeeklyReport(id=uuid.uuid4(), user_id=user_id, week_start=date(2026, 8, 17), week_end=date(2026, 8, 23), report_data={}),
        WeeklyReport(id=uuid.uuid4(), user_id=user_id, week_start=date(2026, 8, 10), week_end=date(2026, 8, 16), report_data={}),
    ]

    mock_exec_result = MagicMock()
    mock_exec_result.scalars().all.return_value = reports
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    repo = WeeklyReportRepository(mock_db)
    result = await repo.get_reports_by_user(user_id=user_id, limit=10)

    assert len(result) == 2
    assert result == reports
    mock_db.execute.assert_called_once()
