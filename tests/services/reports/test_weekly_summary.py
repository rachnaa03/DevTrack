import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory
from app.models.score import DeveloperScore
from app.models.weekly_report import WeeklyReport
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.weekly_report import WeeklyReportRepository
from app.services.reports.summary import WeeklyReportService


@pytest.fixture
def mock_weekly_report_repo() -> MagicMock:
    repo = MagicMock(spec=WeeklyReportRepository)
    repo.create_or_update = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_user_and_week = AsyncMock()
    repo.get_reports_by_user = AsyncMock()
    return repo


@pytest.fixture
def mock_github_history_repo() -> MagicMock:
    repo = MagicMock(spec=GitHubHistoryRepository)
    repo.get_history = AsyncMock()
    return repo


@pytest.fixture
def mock_leetcode_history_repo() -> MagicMock:
    repo = MagicMock(spec=LeetCodeHistoryRepository)
    repo.get_history = AsyncMock()
    return repo


@pytest.fixture
def mock_score_repo() -> MagicMock:
    repo = MagicMock(spec=DeveloperScoreRepository)
    repo.get_latest_before = AsyncMock()
    repo.get_scores_by_date_range = AsyncMock()
    return repo


@pytest.fixture
def weekly_service(
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> WeeklyReportService:
    return WeeklyReportService(
        weekly_report_repo=mock_weekly_report_repo,
        github_history_repo=mock_github_history_repo,
        leetcode_history_repo=mock_leetcode_history_repo,
        score_repo=mock_score_repo,
    )


def test_resolve_week_bounds_default(weekly_service: WeeklyReportService) -> None:
    """Verify default week resolution produces the previous completed Monday-Sunday."""
    today = datetime.now(timezone.utc).date()
    current_monday = today - timedelta(days=today.weekday())
    expected_start = current_monday - timedelta(days=7)
    expected_end = expected_start + timedelta(days=6)

    start, end = weekly_service.resolve_week_bounds()
    assert start == expected_start
    assert end == expected_end
    assert start.weekday() == 0  # Monday
    assert end.weekday() == 6    # Sunday


def test_resolve_week_bounds_custom_monday(weekly_service: WeeklyReportService) -> None:
    """Verify custom Monday resolves to that week's Monday-Sunday."""
    custom_monday = date(2026, 8, 17)
    start, end = weekly_service.resolve_week_bounds(custom_monday)
    assert start == date(2026, 8, 17)
    assert end == date(2026, 8, 23)


def test_resolve_week_bounds_custom_midweek(weekly_service: WeeklyReportService) -> None:
    """Verify custom midweek date (e.g. Wednesday) aligns to the enclosing Monday-Sunday."""
    custom_wednesday = date(2026, 8, 19)
    start, end = weekly_service.resolve_week_bounds(custom_wednesday)
    assert start == date(2026, 8, 17)
    assert end == date(2026, 8, 23)


@pytest.mark.asyncio
async def test_generate_weekly_report_full_data(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify full aggregation with GitHub, LeetCode, and Score data."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    # Mock GitHub daily records
    mock_github_history_repo.get_history.return_value = [
        GitHubHistory(user_id=user_id, date=date(2026, 8, 18), commits=5),
        GitHubHistory(user_id=user_id, date=date(2026, 8, 20), commits=7),
        GitHubHistory(user_id=user_id, date=date(2026, 8, 22), commits=3),
    ]

    # Mock LeetCode cumulative records (baseline on 2026-08-16 had 100 solved, end of week on 2026-08-23 has 108)
    mock_leetcode_history_repo.get_history.return_value = [
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 16), problems_solved=100),
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 20), problems_solved=105),
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 23), problems_solved=108),
    ]

    # Mock Developer Scores
    score_baseline = DeveloperScore(
        user_id=user_id,
        overall_score=700,
        consistency_score=200,
        problem_solving_score=250,
        open_source_score=250,
        computed_at=datetime(2026, 8, 16, 23, 0, tzinfo=timezone.utc),
    )
    score_end = DeveloperScore(
        user_id=user_id,
        overall_score=725,
        consistency_score=210,
        problem_solving_score=260,
        open_source_score=255,
        computed_at=datetime(2026, 8, 23, 22, 0, tzinfo=timezone.utc),
    )

    async def mock_get_latest_before(uid: uuid.UUID, dt: datetime) -> DeveloperScore | None:
        if dt.date() <= week_start:
            return score_baseline
        return score_end

    mock_score_repo.get_latest_before.side_effect = mock_get_latest_before

    expected_report = WeeklyReport(
        id=uuid.uuid4(),
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        report_data={},
        created_at=datetime.now(timezone.utc),
    )
    mock_weekly_report_repo.create_or_update.return_value = expected_report

    result = await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    assert result == expected_report
    mock_weekly_report_repo.create_or_update.assert_called_once()
    _, kwargs = mock_weekly_report_repo.create_or_update.call_args

    assert kwargs["user_id"] == user_id
    assert kwargs["week_start"] == week_start
    assert kwargs["week_end"] == week_end
    data = kwargs["report_data"]
    assert data["commits_count"] == 15  # 5 + 7 + 3
    assert data["problems_solved"] == 8  # 108 - 100
    assert data["score_delta"] == 25     # 725 - 700
    assert data["weekly_subscores"] == {
        "consistency": 210,
        "depth": 260,
        "impact": 255,
    }
    assert "15 commits pushed" in data["summary"]
    assert "8 problems solved" in data["summary"]
    assert "+25" in data["summary"]


@pytest.mark.asyncio
async def test_generate_weekly_report_empty_everything(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify empty user history yields 0 metrics and inactive summary."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    mock_github_history_repo.get_history.return_value = []
    mock_leetcode_history_repo.get_history.return_value = []
    mock_score_repo.get_latest_before.return_value = None
    mock_score_repo.get_scores_by_date_range.return_value = []

    expected_report = WeeklyReport(
        id=uuid.uuid4(),
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        report_data={},
    )
    mock_weekly_report_repo.create_or_update.return_value = expected_report

    result = await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    assert result == expected_report
    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["commits_count"] == 0
    assert data["problems_solved"] == 0
    assert data["score_delta"] == 0
    assert data["weekly_subscores"] == {"consistency": 0, "depth": 0, "impact": 0}
    assert data["summary"] == f"No platform activity was recorded for the week of {week_start} to {week_end}."


@pytest.mark.asyncio
async def test_generate_weekly_report_no_github_data(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify aggregation when GitHub has no activity but LeetCode and Score exist."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    mock_github_history_repo.get_history.return_value = []
    mock_leetcode_history_repo.get_history.return_value = [
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 15), problems_solved=50),
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 22), problems_solved=55),
    ]

    score = DeveloperScore(
        user_id=user_id,
        overall_score=500,
        consistency_score=150,
        problem_solving_score=200,
        open_source_score=150,
        computed_at=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
    )
    mock_score_repo.get_latest_before.return_value = score
    mock_score_repo.get_scores_by_date_range.return_value = [score]

    await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["commits_count"] == 0
    assert data["problems_solved"] == 5
    assert data["weekly_subscores"]["depth"] == 200


@pytest.mark.asyncio
async def test_generate_weekly_report_no_leetcode_data(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify aggregation when LeetCode has no activity but GitHub and Score exist."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    mock_github_history_repo.get_history.return_value = [
        GitHubHistory(user_id=user_id, date=date(2026, 8, 18), commits=12),
    ]
    mock_leetcode_history_repo.get_history.return_value = []

    score = DeveloperScore(
        user_id=user_id,
        overall_score=600,
        consistency_score=180,
        problem_solving_score=220,
        open_source_score=200,
        computed_at=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
    )
    mock_score_repo.get_latest_before.return_value = score
    mock_score_repo.get_scores_by_date_range.return_value = [score]

    await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["commits_count"] == 12
    assert data["problems_solved"] == 0
    assert data["weekly_subscores"]["impact"] == 200


@pytest.mark.asyncio
async def test_generate_weekly_report_leetcode_no_prior_baseline_multiple_in_week(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify LeetCode delta calculation when no baseline exists prior to the week."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    mock_github_history_repo.get_history.return_value = []
    # Two records in week, none before week_start
    mock_leetcode_history_repo.get_history.return_value = [
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 18), problems_solved=10),
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 22), problems_solved=14),
    ]
    mock_score_repo.get_latest_before.return_value = None
    mock_score_repo.get_scores_by_date_range.return_value = []

    await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["problems_solved"] == 4  # 14 - 10


@pytest.mark.asyncio
async def test_generate_weekly_report_leetcode_single_record_in_week_no_baseline(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify LeetCode delta is 0 when only 1 record exists and no prior baseline."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)

    mock_github_history_repo.get_history.return_value = []
    mock_leetcode_history_repo.get_history.return_value = [
        LeetCodeHistory(user_id=user_id, date=date(2026, 8, 20), problems_solved=15),
    ]
    mock_score_repo.get_latest_before.return_value = None
    mock_score_repo.get_scores_by_date_range.return_value = []

    await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["problems_solved"] == 0


@pytest.mark.asyncio
async def test_generate_weekly_report_score_intra_week_delta(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
    mock_github_history_repo: MagicMock,
    mock_leetcode_history_repo: MagicMock,
    mock_score_repo: MagicMock,
) -> None:
    """Verify score delta calculation when no baseline prior to week, but multiple scores within week."""
    user_id = uuid.uuid4()
    week_start = date(2026, 8, 17)
    week_end = date(2026, 8, 23)

    mock_github_history_repo.get_history.return_value = []
    mock_leetcode_history_repo.get_history.return_value = []

    score1 = DeveloperScore(
        user_id=user_id,
        overall_score=400,
        consistency_score=100,
        problem_solving_score=150,
        open_source_score=150,
        computed_at=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
    )
    score2 = DeveloperScore(
        user_id=user_id,
        overall_score=450,
        consistency_score=120,
        problem_solving_score=165,
        open_source_score=165,
        computed_at=datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc),
    )

    async def mock_get_latest_before(uid: uuid.UUID, dt: datetime) -> DeveloperScore | None:
        start_dt = datetime.combine(week_start, time.min, tzinfo=timezone.utc)
        if dt < start_dt:
            return None
        return score2

    mock_score_repo.get_latest_before.side_effect = mock_get_latest_before
    mock_score_repo.get_scores_by_date_range.return_value = [score1, score2]

    await weekly_service.generate_weekly_report(user_id=user_id, week_start=week_start)

    _, kwargs = mock_weekly_report_repo.create_or_update.call_args
    data = kwargs["report_data"]
    assert data["score_delta"] == 50  # 450 - 400
    assert data["weekly_subscores"]["consistency"] == 120
    assert data["weekly_subscores"]["depth"] == 165
    assert data["weekly_subscores"]["impact"] == 165


@pytest.mark.asyncio
async def test_get_user_reports_index(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
) -> None:
    """Verify get_user_reports_index delegates to repository with limit."""
    user_id = uuid.uuid4()
    mock_reports = [
        WeeklyReport(
            id=uuid.uuid4(),
            user_id=user_id,
            week_start=date(2026, 8, 17),
            week_end=date(2026, 8, 23),
            report_data={},
            created_at=datetime.now(timezone.utc),
        ),
        WeeklyReport(
            id=uuid.uuid4(),
            user_id=user_id,
            week_start=date(2026, 8, 10),
            week_end=date(2026, 8, 16),
            report_data={},
            created_at=datetime.now(timezone.utc),
        ),
    ]
    mock_weekly_report_repo.get_reports_by_user.return_value = mock_reports

    result = await weekly_service.get_user_reports_index(user_id=user_id, limit=10)

    assert result == mock_reports
    mock_weekly_report_repo.get_reports_by_user.assert_called_once_with(user_id=user_id, limit=10)


@pytest.mark.asyncio
async def test_get_user_report_by_id_success(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
) -> None:
    """Verify get_user_report_by_id returns report when it belongs to user."""
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    mock_report = WeeklyReport(
        id=report_id,
        user_id=user_id,
        week_start=date(2026, 8, 17),
        week_end=date(2026, 8, 23),
        report_data={"commits_count": 5},
        created_at=datetime.now(timezone.utc),
    )
    mock_weekly_report_repo.get_by_id.return_value = mock_report

    result = await weekly_service.get_user_report_by_id(user_id=user_id, report_id=report_id)

    assert result == mock_report
    mock_weekly_report_repo.get_by_id.assert_called_once_with(report_id=report_id)


@pytest.mark.asyncio
async def test_get_user_report_by_id_not_found(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
) -> None:
    """Verify get_user_report_by_id returns None when report does not exist."""
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    mock_weekly_report_repo.get_by_id.return_value = None

    result = await weekly_service.get_user_report_by_id(user_id=user_id, report_id=report_id)

    assert result is None
    mock_weekly_report_repo.get_by_id.assert_called_once_with(report_id=report_id)


@pytest.mark.asyncio
async def test_get_user_report_by_id_wrong_user_returns_none(
    weekly_service: WeeklyReportService,
    mock_weekly_report_repo: MagicMock,
) -> None:
    """Verify get_user_report_by_id returns None when report belongs to another user (isolation)."""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    mock_report = WeeklyReport(
        id=report_id,
        user_id=other_user_id,
        week_start=date(2026, 8, 17),
        week_end=date(2026, 8, 23),
        report_data={"commits_count": 5},
        created_at=datetime.now(timezone.utc),
    )
    mock_weekly_report_repo.get_by_id.return_value = mock_report

    result = await weekly_service.get_user_report_by_id(user_id=user_id, report_id=report_id)

    assert result is None
    mock_weekly_report_repo.get_by_id.assert_called_once_with(report_id=report_id)

