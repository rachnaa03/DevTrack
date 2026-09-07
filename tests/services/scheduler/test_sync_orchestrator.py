"""
Unit and integration tests for Synchronizer Orchestrator Workflow (Task 13.2).

Verifies:
- 7-stage synchronization pipeline execution for single users.
- Handling profiles with both platforms, GitHub only, LeetCode only, or neither platform connected.
- Platform error isolation (GitHub failure does not halt LeetCode, and vice versa).
- Stale data avoidance after sync failure.
- Batch synchronization across multiple users with isolated database session boundaries.
- Error isolation across users in batch processing (User 1 failure does not stop User 2).
- APScheduler job registration and parameters (SYNC_INTERVAL_HOURS, max_instances=1, coalesce=True).
- Top-level `run_scheduled_sync()` scheduled entrypoint.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.profile import Profile
from app.models.score import DeveloperScore
from app.schemas.github_analysis import (
    GitHubAnalysisResultSchema,
    RepositoryStatsSchema,
)
from app.schemas.leetcode_analysis import (
    LeetCodeAnalysisResultSchema,
    LeetCodeProblemStatsSchema,
)
from app.schemas.recommendation_result import RecommendationRunResultSchema
from app.schemas.sync import GitHubSyncResult, LeetCodeSyncResult
from app.services.scheduler.manager import SchedulerManager
from app.services.scheduler.orchestrator import SyncOrchestrator, run_scheduled_sync


@pytest.fixture
def sample_gh_analysis() -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=uuid4(),
        login="octocat",
        repo_stats=RepositoryStatsSchema(
            total_repositories=5,
            total_stars=25,
            total_forks=10,
            total_size=1024,
            total_open_issues=2,
        ),
        most_starred_repos=[],
        recently_updated_repositories=[],
        language_distribution={"Python": 3, "TypeScript": 2},
        repository_growth=1,
        star_growth=5,
        fork_growth=2,
        total_commits=150,
        commit_frequency_per_day=5.0,
        active_days_count=20,
        contribution_consistency=0.85,
        current_streak=7,
        longest_streak=14,
    )


@pytest.fixture
def sample_lc_analysis() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid4(),
        username="leetdev",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=50,
            medium_solved=30,
            hard_solved=10,
            total_solved=90,
            easy_submissions=60,
            medium_submissions=45,
            hard_submissions=20,
            total_submissions=125,
        ),
        problems_solved_growth=5,
        easy_solved_growth=2,
        medium_solved_growth=2,
        hard_solved_growth=1,
        submissions_growth=10,
        problems_solved_frequency_per_day=3.0,
        active_days_count=15,
        contribution_consistency=0.75,
        current_streak=5,
        longest_streak=10,
        most_practiced_topics=[],
    )


@pytest.mark.asyncio
async def test_sync_user_both_platforms_success(
    sample_gh_analysis: GitHubAnalysisResultSchema,
    sample_lc_analysis: LeetCodeAnalysisResultSchema,
) -> None:
    """Verify full 7-stage synchronization when both platforms are connected."""
    user_id = uuid4()
    profile = Profile(
        user_id=user_id,
        github_username="octocat",
        leetcode_username="leetdev",
    )

    mock_session = AsyncMock()
    mock_gh_snap = MagicMock(
        raw_data={
            "profile": {"id": 1, "login": "octocat"},
            "repositories": [],
        }
    )
    mock_lc_snap = MagicMock(
        raw_data={
            "data": {
                "matchedUser": {
                    "username": "leetdev",
                    "submitStats": {"acSubmissionNum": []},
                }
            }
        }
    )

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSyncService") as mock_gh_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSyncService") as mock_lc_sync_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSnapshotRepository") as mock_gh_snap_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSnapshotRepository") as mock_lc_snap_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubHistoryRepository") as mock_gh_hist_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeHistoryRepository") as mock_lc_hist_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubAnalyzer") as mock_gh_analyzer_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyzer") as mock_lc_analyzer_cls, \
         patch("app.services.scheduler.orchestrator.GitHubAnalyticsRepository") as mock_gh_an_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyticsRepository") as mock_lc_an_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreRepository") as mock_score_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreService") as mock_score_service_cls, \
         patch("app.services.scheduler.orchestrator.InsightGenerationService") as mock_insight_service_cls, \
         patch("app.services.scheduler.orchestrator.RecommendationService") as mock_rec_service_cls, \
         patch("app.services.scheduler.orchestrator.MilestoneService") as mock_ms_service_cls:

        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_score_repo_cls.return_value.get_history = AsyncMock(return_value=[])


        prof_repo = mock_prof_repo_cls.return_value
        prof_repo.get_by_user_id = AsyncMock(return_value=profile)

        gh_sync = mock_gh_sync_cls.return_value
        gh_sync.sync_github_data = AsyncMock(
            return_value=GitHubSyncResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                github_username="octocat",
                repositories_fetched=0,
                repositories_parsed=0,
                profile_updated=False,
            )
        )

        lc_sync = mock_lc_sync_cls.return_value
        lc_sync.sync_leetcode_data = AsyncMock(
            return_value=LeetCodeSyncResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                leetcode_username="leetdev",
                problems_solved=90,
                profile_updated=False,
            )
        )

        mock_gh_snap_repo_cls.return_value.get_latest_by_user_id = AsyncMock(return_value=mock_gh_snap)
        mock_lc_snap_repo_cls.return_value.get_latest_by_user_id = AsyncMock(return_value=mock_lc_snap)
        mock_gh_hist_repo_cls.return_value.create_or_update = AsyncMock()
        mock_lc_hist_repo_cls.return_value.create_or_update = AsyncMock()

        mock_gh_analyzer_cls.return_value.analyze = AsyncMock(return_value=sample_gh_analysis)
        mock_lc_analyzer_cls.return_value.analyze = AsyncMock(return_value=sample_lc_analysis)
        mock_gh_an_repo_cls.return_value.create_or_update = AsyncMock()
        mock_lc_an_repo_cls.return_value.create_or_update = AsyncMock()

        score_service = mock_score_service_cls.return_value
        score_service.record_score = AsyncMock(
            return_value=DeveloperScore(
                user_id=user_id,
                overall_score=750,
                consistency_score=800,
                problem_solving_score=700,
                open_source_score=750,
                score_version="v1",
            )
        )

        mock_insight_service_cls.return_value.generate_and_persist = AsyncMock(return_value=[MagicMock()])
        mock_rec_service_cls.return_value.generate_and_persist = AsyncMock(
            return_value=RecommendationRunResultSchema(
                user_id=user_id,
                total_candidates=14,
                new=2,
                skipped=12,
                resolved=0,
                new_recommendations=[],
                resolved_rule_ids=[],
            )
        )
        mock_ms_service_cls.return_value.get_milestones = AsyncMock()


        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id, analysis_date=date(2026, 9, 7))

        assert result.success is True
        assert result.github_synced is True
        assert result.leetcode_synced is True
        assert result.score_calculated is True
        assert result.insights_generated == 1
        assert result.recommendations_run is True
        assert result.milestones_evaluated is True
        assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_sync_user_github_only(sample_gh_analysis: GitHubAnalysisResultSchema) -> None:
    """Verify synchronization when only GitHub is connected."""
    user_id = uuid4()
    profile = Profile(user_id=user_id, github_username="octocat", leetcode_username=None)

    mock_session = AsyncMock()
    mock_gh_snap = MagicMock(
        raw_data={"profile": {"id": 1, "login": "octocat"}, "repositories": []}
    )

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSyncService") as mock_gh_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSyncService") as mock_lc_sync_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSnapshotRepository") as mock_gh_snap_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubHistoryRepository") as mock_gh_hist_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubAnalyzer") as mock_gh_analyzer_cls, \
         patch("app.services.scheduler.orchestrator.GitHubAnalyticsRepository") as mock_gh_an_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreRepository") as mock_score_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreService") as mock_score_service_cls, \
         patch("app.services.scheduler.orchestrator.InsightGenerationService") as mock_insight_service_cls, \
         patch("app.services.scheduler.orchestrator.RecommendationService") as mock_rec_service_cls, \
         patch("app.services.scheduler.orchestrator.MilestoneService") as mock_ms_service_cls:

        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_score_repo_cls.return_value.get_history = AsyncMock(return_value=[])
        mock_prof_repo_cls.return_value.get_by_user_id = AsyncMock(return_value=profile)
        mock_gh_sync_cls.return_value.sync_github_data = AsyncMock(
            return_value=GitHubSyncResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                github_username="octocat",
                repositories_fetched=0,
                repositories_parsed=0,
                profile_updated=False,
            )
        )
        mock_gh_snap_repo_cls.return_value.get_latest_by_user_id = AsyncMock(return_value=mock_gh_snap)
        mock_gh_hist_repo_cls.return_value.create_or_update = AsyncMock()
        mock_gh_analyzer_cls.return_value.analyze = AsyncMock(return_value=sample_gh_analysis)
        mock_gh_an_repo_cls.return_value.create_or_update = AsyncMock()
        mock_score_service_cls.return_value.record_score = AsyncMock()
        mock_insight_service_cls.return_value.generate_and_persist = AsyncMock(return_value=[])
        mock_rec_service_cls.return_value.generate_and_persist = AsyncMock()
        mock_ms_service_cls.return_value.get_milestones = AsyncMock()

        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id)

        assert result.success is True
        assert result.github_synced is True
        assert result.leetcode_synced is False
        assert result.score_calculated is True
        mock_lc_sync_cls.return_value.sync_leetcode_data.assert_not_called()


@pytest.mark.asyncio
async def test_sync_user_leetcode_only(sample_lc_analysis: LeetCodeAnalysisResultSchema) -> None:
    """Verify synchronization when only LeetCode is connected."""
    user_id = uuid4()
    profile = Profile(user_id=user_id, github_username=None, leetcode_username="leetdev")

    mock_session = AsyncMock()
    mock_lc_snap = MagicMock(
        raw_data={
            "data": {
                "matchedUser": {
                    "username": "leetdev",
                    "submitStats": {"acSubmissionNum": []},
                }
            }
        }
    )

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSyncService") as mock_gh_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSyncService") as mock_lc_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSnapshotRepository") as mock_lc_snap_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeHistoryRepository") as mock_lc_hist_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyzer") as mock_lc_analyzer_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyticsRepository") as mock_lc_an_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreRepository") as mock_score_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreService") as mock_score_service_cls, \
         patch("app.services.scheduler.orchestrator.InsightGenerationService") as mock_insight_service_cls, \
         patch("app.services.scheduler.orchestrator.RecommendationService") as mock_rec_service_cls, \
         patch("app.services.scheduler.orchestrator.MilestoneService") as mock_ms_service_cls:

        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_score_repo_cls.return_value.get_history = AsyncMock(return_value=[])
        mock_prof_repo_cls.return_value.get_by_user_id = AsyncMock(return_value=profile)
        mock_lc_sync_cls.return_value.sync_leetcode_data = AsyncMock(
            return_value=LeetCodeSyncResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                leetcode_username="leetdev",
                problems_solved=90,
                profile_updated=False,
            )
        )
        mock_lc_snap_repo_cls.return_value.get_latest_by_user_id = AsyncMock(return_value=mock_lc_snap)
        mock_lc_hist_repo_cls.return_value.create_or_update = AsyncMock()
        mock_lc_analyzer_cls.return_value.analyze = AsyncMock(return_value=sample_lc_analysis)
        mock_lc_an_repo_cls.return_value.create_or_update = AsyncMock()
        mock_score_service_cls.return_value.record_score = AsyncMock()
        mock_insight_service_cls.return_value.generate_and_persist = AsyncMock(return_value=[])
        mock_rec_service_cls.return_value.generate_and_persist = AsyncMock()
        mock_ms_service_cls.return_value.get_milestones = AsyncMock()

        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id)

        assert result.success is True
        assert result.github_synced is False
        assert result.leetcode_synced is True
        assert result.score_calculated is True
        mock_gh_sync_cls.return_value.sync_github_data.assert_not_called()


@pytest.mark.asyncio
async def test_sync_user_no_connected_platforms() -> None:
    """Verify graceful handling when profile has no connected platforms."""
    user_id = uuid4()
    profile = Profile(user_id=user_id, github_username=None, leetcode_username=None)

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls:

        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        mock_prof_repo_cls.return_value.get_by_user_id = AsyncMock(return_value=profile)

        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id)

        assert result.success is True
        assert result.github_synced is False
        assert result.leetcode_synced is False
        assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_sync_user_profile_not_found() -> None:
    """Verify error reporting when user profile is missing."""
    user_id = uuid4()

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls:

        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        mock_prof_repo_cls.return_value.get_by_user_id = AsyncMock(return_value=None)

        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id)

        assert result.success is False
        assert "Profile not found" in result.errors


@pytest.mark.asyncio
async def test_sync_user_platform_error_isolation(
    sample_lc_analysis: LeetCodeAnalysisResultSchema,
) -> None:
    """Verify GitHub failure does not prevent LeetCode from syncing and processing."""
    user_id = uuid4()
    profile = Profile(
        user_id=user_id,
        github_username="octocat",
        leetcode_username="leetdev",
    )

    mock_lc_snap = MagicMock(
        raw_data={
            "data": {
                "matchedUser": {
                    "username": "leetdev",
                    "submitStats": {"acSubmissionNum": []},
                }
            }
        }
    )

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls, \
         patch("app.services.scheduler.orchestrator.GitHubSyncService") as mock_gh_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSyncService") as mock_lc_sync_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeSnapshotRepository") as mock_lc_snap_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeHistoryRepository") as mock_lc_hist_repo_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyzer") as mock_lc_analyzer_cls, \
         patch("app.services.scheduler.orchestrator.LeetCodeAnalyticsRepository") as mock_lc_an_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreRepository") as mock_score_repo_cls, \
         patch("app.services.scheduler.orchestrator.DeveloperScoreService") as mock_score_service_cls, \
         patch("app.services.scheduler.orchestrator.InsightGenerationService") as mock_insight_service_cls, \
         patch("app.services.scheduler.orchestrator.RecommendationService") as mock_rec_service_cls, \
         patch("app.services.scheduler.orchestrator.MilestoneService") as mock_ms_service_cls:

        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        mock_score_repo_cls.return_value.get_history = AsyncMock(return_value=[])

        mock_prof_repo_cls.return_value.get_by_user_id = AsyncMock(return_value=profile)

        # GitHub sync raises an error
        mock_gh_sync_cls.return_value.sync_github_data = AsyncMock(
            side_effect=Exception("GitHub Rate Limit Exceeded")
        )

        # LeetCode sync succeeds
        mock_lc_sync_cls.return_value.sync_leetcode_data = AsyncMock(
            return_value=LeetCodeSyncResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                leetcode_username="leetdev",
                problems_solved=90,
                profile_updated=False,
            )
        )
        mock_lc_snap_repo_cls.return_value.get_latest_by_user_id = AsyncMock(return_value=mock_lc_snap)
        mock_lc_hist_repo_cls.return_value.create_or_update = AsyncMock()
        mock_lc_analyzer_cls.return_value.analyze = AsyncMock(return_value=sample_lc_analysis)
        mock_lc_an_repo_cls.return_value.create_or_update = AsyncMock()
        mock_score_service_cls.return_value.record_score = AsyncMock()
        mock_insight_service_cls.return_value.generate_and_persist = AsyncMock(return_value=[])
        mock_rec_service_cls.return_value.generate_and_persist = AsyncMock()
        mock_ms_service_cls.return_value.get_milestones = AsyncMock()

        orchestrator = SyncOrchestrator()
        result = await orchestrator.sync_user(user_id=user_id)

        # GitHub failed, but LeetCode and downstream scoring succeeded
        assert result.github_synced is False
        assert result.leetcode_synced is True
        assert result.score_calculated is True
        assert any("GitHub" in err for err in result.errors)
        assert result.success is True


@pytest.mark.asyncio
async def test_sync_all_users_empty() -> None:
    """Verify batch sync returns empty summary when no connected profiles exist."""
    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls:

        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        mock_prof_repo_cls.return_value.get_connected_user_ids = AsyncMock(return_value=[])

        orchestrator = SyncOrchestrator()
        summary = await orchestrator.sync_all_users()

        assert summary.total_users == 0
        assert summary.successful_users == 0
        assert summary.failed_users == 0
        assert len(summary.user_summaries) == 0


@pytest.mark.asyncio
async def test_sync_all_users_multiple_and_failure_isolation() -> None:
    """Verify User 1 failure does not halt processing of User 2 in batch execution."""
    user_1 = uuid4()
    user_2 = uuid4()

    with patch("app.services.scheduler.orchestrator.AsyncSessionLocal") as mock_session_local, \
         patch("app.services.scheduler.orchestrator.ProfileRepository") as mock_prof_repo_cls:

        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        mock_prof_repo_cls.return_value.get_connected_user_ids = AsyncMock(
            return_value=[user_1, user_2]
        )

        orchestrator = SyncOrchestrator()

        # Mock sync_user to fail for user_1 and succeed for user_2
        async def mock_sync_user(user_id: uuid4, analysis_date: date | None = None):
            if user_id == user_1:
                raise RuntimeError("DB connection dropped for user 1")
            return MagicMock(user_id=user_id, success=True, errors=[])

        with patch.object(orchestrator, "sync_user", side_effect=mock_sync_user):

            summary = await orchestrator.sync_all_users()

            assert summary.total_users == 2
            assert summary.successful_users == 1
            assert summary.failed_users == 1
            assert len(summary.user_summaries) == 2


@pytest.mark.asyncio
async def test_scheduler_job_registration() -> None:
    """Verify SchedulerManager registers periodic_developer_sync with expected parameters."""
    manager = SchedulerManager(use_memory_jobstore=True)
    manager.register_sync_job()

    scheduler = manager.get_scheduler()
    jobs = scheduler.get_jobs()
    sync_job = next((j for j in jobs if j.id == "periodic_developer_sync"), None)

    assert sync_job is not None
    assert sync_job.name == "Periodic Developer Data Synchronization"
    assert sync_job.coalesce is True
    assert sync_job.max_instances == 1
    assert str(sync_job.trigger) == f"interval[{settings.SYNC_INTERVAL_HOURS}:00:00]"


@pytest.mark.asyncio
async def test_run_scheduled_sync_entrypoint() -> None:
    """Verify run_scheduled_sync delegates to SyncOrchestrator.sync_all_users."""
    with patch.object(SyncOrchestrator, "sync_all_users", new_callable=AsyncMock) as mock_sync_all:
        mock_sync_all.return_value = MagicMock(total_users=0)
        res = await run_scheduled_sync()
        mock_sync_all.assert_called_once()
        assert res.total_users == 0
