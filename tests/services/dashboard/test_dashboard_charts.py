"""
Unit tests for DashboardChartService (Task 12.2).

Verifies:
- Normal historical series combining GitHub and LeetCode data.
- Handling distinct non-overlapping dates.
- Nullability preservation when one platform has no record on a given date.
- Empty history returns an empty list without errors.
- Chronological sorting (ascending order).
- Date calculation and repository argument forwarding for custom lookback days.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.schemas.dashboard import DashboardChartsResponse
from app.services.dashboard.charts import DashboardChartService

USER_ID = uuid.uuid4()


def _make_github_record(record_date: date, commits: int = 5) -> MagicMock:
    gh = MagicMock(spec=GitHubHistory)
    gh.id = uuid.uuid4()
    gh.user_id = USER_ID
    gh.date = record_date
    gh.commits = commits
    gh.stars = 10
    gh.forks = 2
    gh.repositories = 8
    gh.parsed_metrics = {}
    return gh


def _make_leetcode_record(record_date: date, problems_solved: int = 3) -> MagicMock:
    lc = MagicMock(spec=LeetCodeHistory)
    lc.id = uuid.uuid4()
    lc.user_id = USER_ID
    lc.date = record_date
    lc.problems_solved = problems_solved
    lc.easy_solved = 1
    lc.medium_solved = 2
    lc.hard_solved = 0
    lc.submissions = 5
    lc.parsed_metrics = {}
    return lc


def _make_service(
    gh_records: list | None = None,
    lc_records: list | None = None,
) -> tuple[DashboardChartService, MagicMock, MagicMock]:
    gh_repo = MagicMock(spec=GitHubHistoryRepository)
    gh_repo.get_history = AsyncMock(return_value=gh_records or [])

    lc_repo = MagicMock(spec=LeetCodeHistoryRepository)
    lc_repo.get_history = AsyncMock(return_value=lc_records or [])

    service = DashboardChartService(
        github_history_repo=gh_repo,
        leetcode_history_repo=lc_repo,
    )
    return service, gh_repo, lc_repo


@pytest.mark.asyncio
async def test_get_charts_combined_dates() -> None:
    """Verify points with both GitHub and LeetCode records are merged into single daily entries."""
    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 2)

    gh_list = [_make_github_record(d1, commits=10), _make_github_record(d2, commits=5)]
    lc_list = [_make_leetcode_record(d1, problems_solved=2), _make_leetcode_record(d2, problems_solved=4)]

    service, _, _ = _make_service(gh_records=gh_list, lc_records=lc_list)
    result = await service.get_historical_charts(user_id=USER_ID, days=30)

    assert isinstance(result, DashboardChartsResponse)
    assert result.interval_days == 30
    assert len(result.history) == 2

    assert result.history[0].date == d1
    assert result.history[0].commits == 10
    assert result.history[0].problems_solved == 2

    assert result.history[1].date == d2
    assert result.history[1].commits == 5
    assert result.history[1].problems_solved == 4


@pytest.mark.asyncio
async def test_get_charts_disjoint_dates() -> None:
    """Verify days with activity on only one platform correctly preserve null on the other."""
    d1 = date(2026, 8, 1)  # GitHub only
    d2 = date(2026, 8, 2)  # LeetCode only

    gh_list = [_make_github_record(d1, commits=7)]
    lc_list = [_make_leetcode_record(d2, problems_solved=3)]

    service, _, _ = _make_service(gh_records=gh_list, lc_records=lc_list)
    result = await service.get_historical_charts(user_id=USER_ID, days=30)

    assert len(result.history) == 2
    assert result.history[0].date == d1
    assert result.history[0].commits == 7
    assert result.history[0].problems_solved is None

    assert result.history[1].date == d2
    assert result.history[1].commits is None
    assert result.history[1].problems_solved == 3


@pytest.mark.asyncio
async def test_get_charts_chronological_sorting() -> None:
    """Verify output history points are sorted chronologically ascending regardless of input order."""
    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 5)
    d3 = date(2026, 8, 10)

    # Supply in scrambled order
    gh_list = [_make_github_record(d3, commits=3), _make_github_record(d1, commits=1)]
    lc_list = [_make_leetcode_record(d2, problems_solved=4)]

    service, _, _ = _make_service(gh_records=gh_list, lc_records=lc_list)
    result = await service.get_historical_charts(user_id=USER_ID, days=15)

    assert len(result.history) == 3
    assert [p.date for p in result.history] == [d1, d2, d3]


@pytest.mark.asyncio
async def test_get_charts_empty_dataset() -> None:
    """Verify empty history results in empty list with appropriate interval_days."""
    service, _, _ = _make_service(gh_records=[], lc_records=[])
    result = await service.get_historical_charts(user_id=USER_ID, days=60)

    assert result.interval_days == 60
    assert result.history == []


@pytest.mark.asyncio
async def test_get_charts_repository_call_arguments() -> None:
    """Verify date ranges and user_id are passed to underlying repositories."""
    service, gh_repo, lc_repo = _make_service()
    days = 14
    await service.get_historical_charts(user_id=USER_ID, days=days)

    expected_end = datetime.now(timezone.utc).date()
    expected_start = expected_end - timedelta(days=days)

    gh_repo.get_history.assert_awaited_once_with(
        user_id=USER_ID,
        start_date=expected_start,
        end_date=expected_end,
    )
    lc_repo.get_history.assert_awaited_once_with(
        user_id=USER_ID,
        start_date=expected_start,
        end_date=expected_end,
    )
