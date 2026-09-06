"""
Unit tests for DashboardSummaryService (Task 12.1).

All tests are pure — no database, no HTTP, no FastAPI.

Strategy
--------
- All three repositories (DeveloperScoreRepository, GitHubAnalyticsRepository,
  LeetCodeAnalyticsRepository) are fully mocked.
- ORM objects are MagicMock instances with the correct attributes set.
- Tests verify: score required for 200, platform data optional, None never
  converted to 0, language extraction, data_as_of propagation.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.score import DeveloperScoreRepository
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard.summary import DashboardSummaryService

USER_ID = uuid.uuid4()


def _make_service(
    score_return=None,
    gh_return=None,
    lc_return=None,
) -> DashboardSummaryService:
    score_repo = MagicMock(spec=DeveloperScoreRepository)
    score_repo.get_latest_by_user_id = AsyncMock(return_value=score_return)
    gh_repo = MagicMock(spec=GitHubAnalyticsRepository)
    gh_repo.get_latest_by_user_id = AsyncMock(return_value=gh_return)
    lc_repo = MagicMock(spec=LeetCodeAnalyticsRepository)
    lc_repo.get_latest_by_user_id = AsyncMock(return_value=lc_return)
    return DashboardSummaryService(score_repo, gh_repo, lc_repo)


def _make_score(
    overall: int = 700,
    consistency: int = 175,
    problem_solving: int = 260,
    open_source: int = 265,
) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.overall_score = overall
    s.consistency_score = consistency
    s.problem_solving_score = problem_solving
    s.open_source_score = open_source
    s.computed_at = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    return s


def _make_github(
    total_commits: int | None = 150,
    total_repositories: int | None = 12,
    total_stars: int | None = 45,
    current_streak: int | None = 5,
    longest_streak: int | None = 14,
    contribution_consistency: float | None = 0.72,
    languages: dict | None = None,
    analytics_date: date | None = None,
) -> MagicMock:
    g = MagicMock()
    g.id = uuid.uuid4()
    g.total_commits = total_commits
    g.total_repositories = total_repositories
    g.total_stars = total_stars
    g.current_streak = current_streak
    g.longest_streak = longest_streak
    g.contribution_consistency = contribution_consistency
    g.languages = languages if languages is not None else {"Python": 72.5, "TypeScript": 20.0, "Shell": 7.5}
    g.date = analytics_date or date(2026, 9, 1)
    return g


def _make_leetcode(
    total_solved: int | None = 150,
    easy_solved: int | None = 50,
    medium_solved: int | None = 80,
    hard_solved: int | None = 20,
    current_streak: int | None = 7,
    longest_streak: int | None = 21,
    contribution_consistency: float | None = 0.68,
    analytics_date: date | None = None,
) -> MagicMock:
    lc = MagicMock()
    lc.id = uuid.uuid4()
    lc.total_solved = total_solved
    lc.easy_solved = easy_solved
    lc.medium_solved = medium_solved
    lc.hard_solved = hard_solved
    lc.current_streak = current_streak
    lc.longest_streak = longest_streak
    lc.contribution_consistency = contribution_consistency
    lc.date = analytics_date or date(2026, 9, 1)
    return lc


# ---------------------------------------------------------------------------
# Test: No score — returns None (→ 404)
# ---------------------------------------------------------------------------

class TestNoScore:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_score(self) -> None:
        service = _make_service(score_return=None)
        result = await service.get_summary(USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_github_lc_repos_not_queried_when_no_score(self) -> None:
        """When no score exists, we short-circuit and avoid unnecessary DB reads."""
        gh_repo = MagicMock(spec=GitHubAnalyticsRepository)
        gh_repo.get_latest_by_user_id = AsyncMock()
        lc_repo = MagicMock(spec=LeetCodeAnalyticsRepository)
        lc_repo.get_latest_by_user_id = AsyncMock()
        score_repo = MagicMock(spec=DeveloperScoreRepository)
        score_repo.get_latest_by_user_id = AsyncMock(return_value=None)

        service = DashboardSummaryService(score_repo, gh_repo, lc_repo)
        await service.get_summary(USER_ID)

        # Both repos should NOT be called because we returned early after score=None
        gh_repo.get_latest_by_user_id.assert_not_called()
        lc_repo.get_latest_by_user_id.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Full data — all three repos return data
# ---------------------------------------------------------------------------

class TestFullData:
    @pytest.mark.asyncio
    async def test_returns_dashboard_summary_response(self) -> None:
        service = _make_service(
            score_return=_make_score(),
            gh_return=_make_github(),
            lc_return=_make_leetcode(),
        )
        result = await service.get_summary(USER_ID)
        assert isinstance(result, DashboardSummaryResponse)

    @pytest.mark.asyncio
    async def test_score_fields_mapped_correctly(self) -> None:
        score = _make_score(overall=720, consistency=180, problem_solving=270, open_source=270)
        service = _make_service(score_return=score, gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)

        assert result.developer_score.overall == 720
        assert result.developer_score.consistency == 180
        assert result.developer_score.depth == 270       # problem_solving → depth
        assert result.developer_score.impact == 270      # open_source → impact

    @pytest.mark.asyncio
    async def test_computed_at_preserved(self) -> None:
        score = _make_score()
        service = _make_service(score_return=score, gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.developer_score.computed_at == score.computed_at

    @pytest.mark.asyncio
    async def test_github_stats_mapped_correctly(self) -> None:
        gh = _make_github(
            total_commits=200,
            total_repositories=15,
            total_stars=50,
            current_streak=7,
            longest_streak=20,
            contribution_consistency=0.80,
        )
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        gh_stats = result.stats.github

        assert gh_stats.total_commits == 200
        assert gh_stats.total_repositories == 15
        assert gh_stats.stars_earned == 50
        assert gh_stats.current_streak == 7
        assert gh_stats.longest_streak == 20
        assert gh_stats.contribution_consistency == 0.80

    @pytest.mark.asyncio
    async def test_leetcode_stats_mapped_correctly(self) -> None:
        lc = _make_leetcode(
            total_solved=200,
            easy_solved=80,
            medium_solved=100,
            hard_solved=20,
            current_streak=10,
            longest_streak=30,
        )
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=lc)
        result = await service.get_summary(USER_ID)
        lc_stats = result.stats.leetcode

        assert lc_stats.total_solved == 200
        assert lc_stats.easy_solved == 80
        assert lc_stats.medium_solved == 100
        assert lc_stats.hard_solved == 20
        assert lc_stats.active_streak == 10   # current_streak → active_streak
        assert lc_stats.longest_streak == 30

    @pytest.mark.asyncio
    async def test_data_as_of_propagated_from_analytics_date(self) -> None:
        gh_date = date(2026, 8, 28)
        lc_date = date(2026, 8, 27)
        service = _make_service(
            score_return=_make_score(),
            gh_return=_make_github(analytics_date=gh_date),
            lc_return=_make_leetcode(analytics_date=lc_date),
        )
        result = await service.get_summary(USER_ID)
        assert result.stats.github.data_as_of == gh_date
        assert result.stats.leetcode.data_as_of == lc_date


# ---------------------------------------------------------------------------
# Test: Missing GitHub data
# ---------------------------------------------------------------------------

class TestMissingGitHub:
    @pytest.mark.asyncio
    async def test_github_fields_are_none_when_no_gh_record(self) -> None:
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)
        gh = result.stats.github

        assert gh.total_commits is None
        assert gh.total_repositories is None
        assert gh.stars_earned is None
        assert gh.current_streak is None
        assert gh.longest_streak is None
        assert gh.contribution_consistency is None
        assert gh.primary_languages is None
        assert gh.data_as_of is None

    @pytest.mark.asyncio
    async def test_github_null_never_converted_to_zero(self) -> None:
        """Crucial: None fields stay None, never become 0."""
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.stats.github.total_commits != 0
        assert result.stats.github.total_commits is None


# ---------------------------------------------------------------------------
# Test: Missing LeetCode data
# ---------------------------------------------------------------------------

class TestMissingLeetCode:
    @pytest.mark.asyncio
    async def test_leetcode_fields_are_none_when_no_lc_record(self) -> None:
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)
        lc = result.stats.leetcode

        assert lc.total_solved is None
        assert lc.easy_solved is None
        assert lc.medium_solved is None
        assert lc.hard_solved is None
        assert lc.active_streak is None
        assert lc.longest_streak is None
        assert lc.contribution_consistency is None
        assert lc.data_as_of is None

    @pytest.mark.asyncio
    async def test_leetcode_null_never_converted_to_zero(self) -> None:
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.stats.leetcode.total_solved is None


# ---------------------------------------------------------------------------
# Test: Language extraction
# ---------------------------------------------------------------------------

class TestLanguageExtraction:
    @pytest.mark.asyncio
    async def test_languages_sorted_by_usage_descending(self) -> None:
        gh = _make_github(languages={"Go": 5.0, "Python": 70.0, "TypeScript": 25.0})
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.stats.github.primary_languages == ["Python", "TypeScript", "Go"]

    @pytest.mark.asyncio
    async def test_top_5_languages_only(self) -> None:
        gh = _make_github(languages={
            "Python": 50.0, "TypeScript": 20.0, "Go": 10.0,
            "Rust": 8.0, "Java": 7.0, "C++": 5.0,
        })
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert len(result.stats.github.primary_languages) == 5
        assert result.stats.github.primary_languages[0] == "Python"

    @pytest.mark.asyncio
    async def test_null_languages_stays_none(self) -> None:
        gh = _make_github(languages=None)
        gh.languages = None
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.stats.github.primary_languages is None

    @pytest.mark.asyncio
    async def test_empty_languages_dict_returns_empty_list(self) -> None:
        gh = _make_github(languages={})
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        # Empty dict → sorted result is empty → primary_languages is []
        assert result.stats.github.primary_languages == []


# ---------------------------------------------------------------------------
# Test: Partial analytics data (fields within record are None)
# ---------------------------------------------------------------------------

class TestPartialAnalyticsFields:
    @pytest.mark.asyncio
    async def test_github_record_with_null_commits_passes_null_through(self) -> None:
        """Nullable analytics fields in existing records must not be coerced."""
        gh = _make_github(total_commits=None)
        service = _make_service(score_return=_make_score(), gh_return=gh, lc_return=None)
        result = await service.get_summary(USER_ID)
        assert result.stats.github.total_commits is None

    @pytest.mark.asyncio
    async def test_lc_record_with_null_streak_passes_null_through(self) -> None:
        lc = _make_leetcode(current_streak=None)
        service = _make_service(score_return=_make_score(), gh_return=None, lc_return=lc)
        result = await service.get_summary(USER_ID)
        assert result.stats.leetcode.active_streak is None
