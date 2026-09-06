"""
Unit tests for InsightGenerationService and compose_message.

All repository and external dependencies are mocked.
No real database or HTTP calls are made.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.insight import Insight
from app.repositories.insight import InsightRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema
from app.schemas.score import DeveloperScoreResultSchema, ScoreSubcomponentSchema
from app.services.insights.service import (
    INSIGHT_RULE_VERSION,
    InsightGenerationService,
    compose_message,
)
from app.schemas.insights import InsightTriggerSchema

# ---------------------------------------------------------------------------
# Shared test dates
# ---------------------------------------------------------------------------
CURRENT_DATE = date(2024, 7, 1)
HISTORICAL_DATE = date(2024, 6, 1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_insight_repo() -> MagicMock:
    repo = MagicMock(spec=InsightRepository)
    # Default: no existing record (no duplicate)
    repo.get_existing = AsyncMock(return_value=None)
    # Default: create returns the passed record unchanged
    repo.create = AsyncMock(side_effect=lambda r: r)
    return repo


@pytest.fixture
def insight_service(mock_insight_repo: MagicMock) -> InsightGenerationService:
    return InsightGenerationService(mock_insight_repo)


@pytest.fixture
def sample_github_current() -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=uuid.uuid4(),
        login="devuser",
        repo_stats=RepositoryStatsSchema(
            total_repositories=10,
            total_stars=50,
            total_forks=5,
            total_size=2048,
            total_open_issues=3,
        ),
        language_distribution={"Python": 80, "Go": 20},
        most_starred_repos=[],
        recently_updated_repositories=[],
        repository_growth=2,
        star_growth=10,
        fork_growth=1,
        total_commits=200,
        commit_frequency_per_day=2.0,
        active_days_count=20,
        contribution_consistency=0.75,
        current_streak=10,
        longest_streak=15,
    )


@pytest.fixture
def sample_github_historical() -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=uuid.uuid4(),
        login="devuser",
        repo_stats=RepositoryStatsSchema(
            total_repositories=8,
            total_stars=30,
            total_forks=3,
            total_size=1800,
            total_open_issues=2,
        ),
        language_distribution={"Python": 100},
        most_starred_repos=[],
        recently_updated_repositories=[],
        repository_growth=0,
        star_growth=5,
        fork_growth=0,
        total_commits=100,            # +100 commits → should trigger increase
        commit_frequency_per_day=1.0,
        active_days_count=12,
        contribution_consistency=0.50, # +0.25 → should trigger increase
        current_streak=5,
        longest_streak=10,
    )


@pytest.fixture
def sample_leetcode_current() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid.uuid4(),
        username="devuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=30,
            medium_solved=20,
            hard_solved=5,
            total_solved=55,
            easy_submissions=60,
            medium_submissions=40,
            hard_submissions=10,
            total_submissions=110,
        ),
        most_practiced_topics=[],
        problems_solved_growth=10,
        easy_solved_growth=5,
        medium_solved_growth=4,
        hard_solved_growth=1,
        submissions_growth=20,
        problems_solved_frequency_per_day=1.0,
        active_days_count=15,
        contribution_consistency=0.70,
        current_streak=8,
        longest_streak=12,
    )


@pytest.fixture
def sample_leetcode_historical() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid.uuid4(),
        username="devuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=25,
            medium_solved=10,
            hard_solved=2,
            total_solved=37,              # +18 solved → should trigger increase
            easy_submissions=50,
            medium_submissions=20,
            hard_submissions=4,
            total_submissions=74,
        ),
        most_practiced_topics=[],
        problems_solved_growth=5,
        easy_solved_growth=3,
        medium_solved_growth=2,
        hard_solved_growth=0,
        submissions_growth=10,
        problems_solved_frequency_per_day=0.7,
        active_days_count=10,
        contribution_consistency=0.45,   # +0.25 → should trigger increase
        current_streak=3,
        longest_streak=8,
    )


@pytest.fixture
def sample_current_score() -> DeveloperScoreResultSchema:
    return DeveloperScoreResultSchema(
        overall_score=750,
        consistency_score=250,
        problem_solving_score=280,
        open_source_score=220,
        score_version="v1",
        subcomponents=ScoreSubcomponentSchema(),
    )


@pytest.fixture
def sample_historical_score() -> DeveloperScoreResultSchema:
    return DeveloperScoreResultSchema(
        overall_score=650,               # +100 → should trigger increase
        consistency_score=200,           # +50 → should trigger increase
        problem_solving_score=220,       # +60 → should trigger increase
        open_source_score=230,           # -10 → below threshold, should NOT trigger
        score_version="v1",
        subcomponents=ScoreSubcomponentSchema(),
    )


# ---------------------------------------------------------------------------
# Tests: compose_message
# ---------------------------------------------------------------------------

class TestComposeMessage:
    """Unit tests for the pure message composer function."""

    def test_github_commits_increase(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="github_commits",
            platform="github",
            change_type="increase",
            current_value=200.0,
            historical_value=100.0,
            absolute_change=100.0,
            percent_change=100.0,
        )
        msg = compose_message(trigger)
        assert "100" in msg
        assert "increase" in msg.lower() or "commit" in msg.lower()
        assert len(msg) <= 500

    def test_github_commits_decrease(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="github_commits",
            platform="github",
            change_type="decrease",
            current_value=50.0,
            historical_value=100.0,
            absolute_change=50.0,
            percent_change=-50.0,
        )
        msg = compose_message(trigger)
        assert "50" in msg
        assert "decrease" in msg.lower() or "decreas" in msg.lower()
        assert len(msg) <= 500

    def test_github_streak_broken(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="github_streak",
            platform="github",
            change_type="broken",
            current_value=0.0,
            historical_value=10.0,
            absolute_change=10.0,
        )
        msg = compose_message(trigger)
        assert "10" in msg
        assert "broken" in msg.lower() or "streak" in msg.lower()
        assert len(msg) <= 500

    def test_leetcode_solved_increase(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="leetcode_solved",
            platform="leetcode",
            change_type="increase",
            current_value=55.0,
            historical_value=37.0,
            absolute_change=18.0,
            percent_change=48.6,
        )
        msg = compose_message(trigger)
        assert "18" in msg
        assert len(msg) <= 500

    def test_difficulty_ratio_formats_as_percentage(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="leetcode_difficulty",
            platform="leetcode",
            change_type="increase",
            current_value=0.45,
            historical_value=0.32,
            absolute_change=0.13,
        )
        msg = compose_message(trigger)
        # Ratio metrics should display as percentages
        assert "%" in msg
        assert len(msg) <= 500

    def test_github_consistency_formats_as_percentage(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="github_consistency",
            platform="github",
            change_type="increase",
            current_value=0.75,
            historical_value=0.50,
            absolute_change=0.25,
        )
        msg = compose_message(trigger)
        assert "%" in msg
        assert len(msg) <= 500

    def test_score_overall_increase(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="score_overall",
            platform="system",
            change_type="increase",
            current_value=750.0,
            historical_value=650.0,
            absolute_change=100.0,
        )
        msg = compose_message(trigger)
        assert "100" in msg
        assert len(msg) <= 500

    def test_fallback_message_for_unknown_metric(self) -> None:
        trigger = InsightTriggerSchema(
            metric_name="unknown_metric",
            platform="system",
            change_type="increase",
            current_value=10.0,
            historical_value=5.0,
            absolute_change=5.0,
        )
        msg = compose_message(trigger)
        # Should not raise; should return a non-empty string
        assert isinstance(msg, str)
        assert len(msg) > 0
        assert len(msg) <= 500

    def test_message_truncated_to_500_chars(self) -> None:
        """Verify the composer never exceeds 500 characters."""
        trigger = InsightTriggerSchema(
            metric_name="github_commits",
            platform="github",
            change_type="increase",
            current_value=99999.0,
            historical_value=0.0,
            absolute_change=99999.0,
            percent_change=None,
        )
        msg = compose_message(trigger)
        assert len(msg) <= 500


# ---------------------------------------------------------------------------
# Tests: InsightGenerationService
# ---------------------------------------------------------------------------

class TestInsightGenerationService:
    """Integration-style unit tests for InsightGenerationService."""

    @pytest.mark.asyncio
    async def test_github_triggers_produce_insights(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_github_current: GitHubAnalysisResultSchema,
        sample_github_historical: GitHubAnalysisResultSchema,
    ) -> None:
        """Valid GitHub comparison data with sufficient change should persist insights."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=sample_github_current,
            historical_gh=sample_github_historical,
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        assert len(results) > 0
        for insight in results:
            assert insight.user_id == user_id
            assert insight.platform == "github"
            assert insight.rule_version == INSIGHT_RULE_VERSION
            assert insight.current_date == CURRENT_DATE
            assert insight.historical_date == HISTORICAL_DATE
            assert isinstance(insight.message, str)
            assert len(insight.message) > 0

    @pytest.mark.asyncio
    async def test_leetcode_triggers_produce_insights(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_leetcode_current: LeetCodeAnalysisResultSchema,
        sample_leetcode_historical: LeetCodeAnalysisResultSchema,
    ) -> None:
        """Valid LeetCode comparison data with sufficient change should persist insights."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=sample_leetcode_current,
            historical_lc=sample_leetcode_historical,
            current_score=None,
            historical_score=None,
        )
        assert len(results) > 0
        for insight in results:
            assert insight.platform == "leetcode"
            assert insight.rule_version == INSIGHT_RULE_VERSION

    @pytest.mark.asyncio
    async def test_score_triggers_produce_insights(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """Developer Score comparison with sufficient change should persist insights."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=sample_current_score,
            historical_score=sample_historical_score,
        )
        # overall (+100), consistency (+50), problem_solving (+60) should trigger
        metric_names = {r.metric_name for r in results}
        assert "score_overall" in metric_names
        assert "score_consistency" in metric_names
        assert "score_problem_solving" in metric_names
        # open_source delta is -10 which is below threshold → should NOT appear
        assert "score_open_source" not in metric_names

    @pytest.mark.asyncio
    async def test_multiple_triggers_produce_multiple_insights(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_github_current: GitHubAnalysisResultSchema,
        sample_github_historical: GitHubAnalysisResultSchema,
        sample_leetcode_current: LeetCodeAnalysisResultSchema,
        sample_leetcode_historical: LeetCodeAnalysisResultSchema,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """All platforms active → multiple triggers across platforms persisted."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=sample_github_current,
            historical_gh=sample_github_historical,
            current_lc=sample_leetcode_current,
            historical_lc=sample_leetcode_historical,
            current_score=sample_current_score,
            historical_score=sample_historical_score,
        )
        assert len(results) > 1
        platforms = {r.platform for r in results}
        # Should include triggers from multiple platforms
        assert len(platforms) > 1

    @pytest.mark.asyncio
    async def test_no_trigger_returns_empty_list(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
    ) -> None:
        """When no data is provided, no triggers are generated and nothing is persisted."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        assert results == []
        mock_insight_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_below_threshold_produces_no_insight(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
    ) -> None:
        """Small change below all thresholds → no insight generated."""
        user_id = uuid.uuid4()
        # Score change of 5 is below OVERALL_SCORE_CHANGE_THRESHOLD (50)
        current_score = DeveloperScoreResultSchema(
            overall_score=505,
            consistency_score=205,
            problem_solving_score=205,
            open_source_score=205,
            score_version="v1",
            subcomponents=ScoreSubcomponentSchema(),
        )
        historical_score = DeveloperScoreResultSchema(
            overall_score=500,
            consistency_score=200,
            problem_solving_score=200,
            open_source_score=200,
            score_version="v1",
            subcomponents=ScoreSubcomponentSchema(),
        )
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=current_score,
            historical_score=historical_score,
        )
        assert results == []
        mock_insight_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_historical_data_produces_no_insight(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_github_current: GitHubAnalysisResultSchema,
    ) -> None:
        """Only current data without historical data → comparator has no baseline → no insight."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=sample_github_current,
            historical_gh=None,           # No historical data
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        assert results == []
        mock_insight_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_current_data_produces_no_insight(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_github_historical: GitHubAnalysisResultSchema,
    ) -> None:
        """Only historical data without current data → comparator has no subject → no insight."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,              # No current data
            historical_gh=sample_github_historical,
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        assert results == []
        mock_insight_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_historical_baseline_triggers_insight(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
    ) -> None:
        """
        When historical_commits == 0 and current >= GITHUB_COMMIT_ABSOLUTE_THRESHOLD,
        an increase insight should be generated (percent_change must be None).
        """
        user_id = uuid.uuid4()
        zero_historical = GitHubAnalysisResultSchema(
            user_id=uuid.uuid4(),
            login="newuser",
            repo_stats=RepositoryStatsSchema(
                total_repositories=1,
                total_stars=0,
                total_forks=0,
                total_size=100,
                total_open_issues=0,
            ),
            language_distribution={},
            most_starred_repos=[],
            recently_updated_repositories=[],
            repository_growth=0,
            star_growth=0,
            fork_growth=0,
            total_commits=0,             # Zero baseline
            commit_frequency_per_day=0.0,
            active_days_count=0,
            contribution_consistency=None,
            current_streak=0,
            longest_streak=0,
        )
        current_active = GitHubAnalysisResultSchema(
            user_id=uuid.uuid4(),
            login="newuser",
            repo_stats=RepositoryStatsSchema(
                total_repositories=1,
                total_stars=2,
                total_forks=0,
                total_size=200,
                total_open_issues=0,
            ),
            language_distribution={},
            most_starred_repos=[],
            recently_updated_repositories=[],
            repository_growth=0,
            star_growth=2,
            fork_growth=0,
            total_commits=20,            # >= GITHUB_COMMIT_ABSOLUTE_THRESHOLD (10)
            commit_frequency_per_day=1.0,
            active_days_count=5,
            contribution_consistency=None,
            current_streak=2,
            longest_streak=2,
        )
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=current_active,
            historical_gh=zero_historical,
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        assert len(results) == 1
        insight = results[0]
        assert insight.metric_name == "github_commits"
        assert insight.change_type == "increase"
        assert insight.percent_change is None
        # Evidence should carry the baseline_zero flag from the trigger metadata
        assert insight.evidence is not None
        assert insight.evidence.get("baseline_zero") is True

    @pytest.mark.asyncio
    async def test_duplicate_invocation_skips_existing_records(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_github_current: GitHubAnalysisResultSchema,
        sample_github_historical: GitHubAnalysisResultSchema,
    ) -> None:
        """
        If a record with the same deduplication key already exists, the service
        must not create a second copy.
        """
        user_id = uuid.uuid4()
        # Simulate: ALL dedup queries return an existing record
        existing = Insight(
            user_id=user_id,
            platform="github",
            metric_name="github_commits",
            change_type="increase",
            message="already stored",
            current_value=200.0,
            historical_value=100.0,
            absolute_change=100.0,
            percent_change=None,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            rule_version=INSIGHT_RULE_VERSION,
        )
        mock_insight_repo.get_existing = AsyncMock(return_value=existing)

        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=sample_github_current,
            historical_gh=sample_github_historical,
            current_lc=None,
            historical_lc=None,
            current_score=None,
            historical_score=None,
        )
        # All triggers were duplicates → nothing new persisted
        assert results == []
        mock_insight_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_rule_version_persisted_correctly(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """Verify the rule_version constant is written to every persisted record."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=sample_current_score,
            historical_score=sample_historical_score,
        )
        assert len(results) > 0
        for insight in results:
            assert insight.rule_version == INSIGHT_RULE_VERSION

    @pytest.mark.asyncio
    async def test_numeric_evidence_persisted_correctly(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """Verify current_value, historical_value, absolute_change are stored from triggers."""
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=sample_current_score,
            historical_score=sample_historical_score,
        )
        overall_insight = next(r for r in results if r.metric_name == "score_overall")
        assert overall_insight.current_value == 750.0
        assert overall_insight.historical_value == 650.0
        assert overall_insight.absolute_change == 100.0

    @pytest.mark.asyncio
    async def test_repository_error_propagates(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """A database error from the repository must not be silently swallowed."""
        user_id = uuid.uuid4()
        mock_insight_repo.create = AsyncMock(side_effect=Exception("DB connection lost"))

        with pytest.raises(Exception, match="DB connection lost"):
            await insight_service.generate_and_persist(
                user_id=user_id,
                current_date=CURRENT_DATE,
                historical_date=HISTORICAL_DATE,
                current_gh=None,
                historical_gh=None,
                current_lc=None,
                historical_lc=None,
                current_score=sample_current_score,
                historical_score=sample_historical_score,
            )

    @pytest.mark.asyncio
    async def test_get_latest_insights(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
    ) -> None:
        """Verify get_latest_insights delegates to the repository with the given limit."""
        user_id = uuid.uuid4()
        fake_insights = [Insight(user_id=user_id, platform="github", metric_name="github_commits")]
        mock_insight_repo.get_latest_by_user_id = AsyncMock(return_value=fake_insights)

        result = await insight_service.get_latest_insights(user_id, limit=5)

        assert result == fake_insights
        mock_insight_repo.get_latest_by_user_id.assert_called_once_with(user_id, limit=5)

    @pytest.mark.asyncio
    async def test_evidence_empty_metadata_stored_as_none(
        self,
        insight_service: InsightGenerationService,
        mock_insight_repo: MagicMock,
        sample_current_score: DeveloperScoreResultSchema,
        sample_historical_score: DeveloperScoreResultSchema,
    ) -> None:
        """
        Triggers without metadata (empty dict {}) should store evidence=None
        rather than an empty JSON object.
        """
        user_id = uuid.uuid4()
        results = await insight_service.generate_and_persist(
            user_id=user_id,
            current_date=CURRENT_DATE,
            historical_date=HISTORICAL_DATE,
            current_gh=None,
            historical_gh=None,
            current_lc=None,
            historical_lc=None,
            current_score=sample_current_score,
            historical_score=sample_historical_score,
        )
        # Score triggers don't set metadata → evidence should be None
        for insight in results:
            assert insight.evidence is None
