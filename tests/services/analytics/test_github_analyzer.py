import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.models.github_snapshot import GitHubSnapshot
from app.models.github_history import GitHubHistory
from app.repositories.github_snapshot import GitHubSnapshotRepository
from app.repositories.github_history import GitHubHistoryRepository
from app.services.analytics.github import GitHubAnalyzer

@pytest.fixture
def mock_snapshot_repo() -> MagicMock:
    return MagicMock(spec=GitHubSnapshotRepository)

@pytest.fixture
def mock_history_repo() -> MagicMock:
    return MagicMock(spec=GitHubHistoryRepository)

@pytest.fixture
def analyzer(mock_snapshot_repo: MagicMock, mock_history_repo: MagicMock) -> GitHubAnalyzer:
    return GitHubAnalyzer(mock_snapshot_repo, mock_history_repo)

# --- 1. Snapshot Data Tests ---

@pytest.mark.asyncio
async def test_analyze_no_snapshot_available(analyzer: GitHubAnalyzer, mock_snapshot_repo: MagicMock) -> None:
    """Verify ValueError is raised if no snapshot is available for the user."""
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="No GitHub snapshot found for user."):
        await analyzer.analyze(uuid.uuid4())

@pytest.mark.asyncio
async def test_analyze_repository_statistics_and_languages(
    analyzer: GitHubAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify repo stats aggregation and language distribution are computed correctly."""
    user_uuid = uuid.uuid4()
    raw_data = {
        "profile": {"id": 12345, "login": "octocat", "bio": "Bio"},
        "repositories": [
            {
                "id": 1, "name": "r1", "full_name": "octocat/r1", "stargazers_count": 10,
                "forks_count": 2, "size": 100, "open_issues_count": 1, "language": "Python",
                "created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-08-02T00:00:00Z",
                "pushed_at": "2026-08-20T12:00:00Z"
            },
            {
                "id": 2, "name": "r2", "full_name": "octocat/r2", "stargazers_count": 5,
                "forks_count": 0, "size": 50, "open_issues_count": 0, "language": "Python",
                "created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-08-02T00:00:00Z",
                "pushed_at": "2026-08-21T12:00:00Z"
            },
            {
                "id": 3, "name": "r3", "full_name": "octocat/r3", "stargazers_count": 1,
                "forks_count": 1, "size": 200, "open_issues_count": 3, "language": None,
                "created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-08-02T00:00:00Z",
                "pushed_at": None
            }
        ]
    }
    
    mock_snapshot = GitHubSnapshot(user_id=user_uuid, raw_data=raw_data)
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)
    mock_history_repo.get_history = AsyncMock(return_value=[])

    result = await analyzer.analyze(user_uuid)
    
    # Stats checks
    assert result.login == "octocat"
    assert result.repo_stats.total_repositories == 3
    assert result.repo_stats.total_stars == 16
    assert result.repo_stats.total_forks == 3
    assert result.repo_stats.total_size == 350
    assert result.repo_stats.total_open_issues == 4

    # Language distribution
    assert result.language_distribution == {"Python": 2}

@pytest.mark.asyncio
async def test_analyze_repo_sorting_and_limits(
    analyzer: GitHubAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify repo sorting priorities and limit constraints (limit to 5)."""
    user_uuid = uuid.uuid4()
    
    raw_repos = []
    for i in range(1, 7):
        stars = 20 if i in (2, 3, 6) else (10 if i == 1 else (5 if i == 4 else 0))
        pushed = "2026-08-25T12:00:00Z" if i in (3, 4, 6) else ("2026-08-20T12:00:00Z" if i == 2 else ("2026-08-22T12:00:00Z" if i == 5 else None))
        
        raw_repos.append({
            "id": i, "name": f"repo{i}", "full_name": f"octocat/repo{i}", "stargazers_count": stars,
            "forks_count": 0, "size": 10, "open_issues_count": 0, "language": "Go",
            "created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-08-02T00:00:00Z",
            "pushed_at": pushed
        })
        
    mock_snapshot = GitHubSnapshot(user_id=user_uuid, raw_data={"profile": {"id": 1, "login": "octocat"}, "repositories": raw_repos})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)
    mock_history_repo.get_history = AsyncMock(return_value=[])

    result = await analyzer.analyze(user_uuid)
    
    assert len(result.most_starred_repos) == 5
    assert len(result.recently_updated_repositories) == 5

    # Starred sort order: stars DESC, name ASC
    starred_names = [r.name for r in result.most_starred_repos]
    assert starred_names == ["repo2", "repo3", "repo6", "repo1", "repo4"]

    # Recent sort order: pushed_at is None (last), pushed_at DESC, name ASC
    recent_names = [r.name for r in result.recently_updated_repositories]
    assert recent_names == ["repo3", "repo4", "repo6", "repo5", "repo2"]

# --- 2. Growth Metric Tests ---

@pytest.mark.asyncio
async def test_analyze_growth_metrics_ranges(
    analyzer: GitHubAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify growth calculation constraints for 0, 1, 2, and negative growth cases."""
    user_uuid = uuid.uuid4()
    mock_snapshot = GitHubSnapshot(user_id=user_uuid, raw_data={"profile": {"id": 1, "login": "octocat"}, "repositories": []})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # 1. Zero history records -> Growth must be None
    mock_history_repo.get_history = AsyncMock(return_value=[])
    res_zero = await analyzer.analyze(user_uuid)
    assert res_zero.repository_growth is None
    assert res_zero.star_growth is None
    assert res_zero.fork_growth is None

    # 2. One history record -> Growth must be None
    rec1 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 20), repositories=5, stars=10, forks=2, commits=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec1])
    res_one = await analyzer.analyze(user_uuid)
    assert res_one.repository_growth is None
    assert res_one.star_growth is None
    assert res_one.fork_growth is None

    # 3. Two history records -> Positive Growth
    rec2 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), repositories=7, stars=15, forks=3, commits=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2])
    res_two = await analyzer.analyze(user_uuid)
    assert res_two.repository_growth == 2
    assert res_two.star_growth == 5
    assert res_two.fork_growth == 1

    # 4. Negative growth
    rec_neg = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), repositories=3, stars=8, forks=1, commits=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec_neg])
    res_neg = await analyzer.analyze(user_uuid)
    assert res_neg.repository_growth == -2
    assert res_neg.star_growth == -2
    assert res_neg.fork_growth == -1

# --- 3. Observed-Day Metrics ---

@pytest.mark.asyncio
async def test_analyze_observed_day_metrics(
    analyzer: GitHubAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify observed-day metrics for single and multiple records, including calendar gaps."""
    user_uuid = uuid.uuid4()
    mock_snapshot = GitHubSnapshot(user_id=user_uuid, raw_data={"profile": {"id": 1, "login": "octocat"}, "repositories": []})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # 1. Single active history record
    rec_active = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), commits=5, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec_active])
    res_act = await analyzer.analyze(user_uuid)
    assert res_act.total_commits == 5
    assert res_act.active_days_count == 1
    assert res_act.commit_frequency_per_day == 5.0
    assert res_act.contribution_consistency == 1.0

    # 2. Single inactive history record
    rec_inactive = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), commits=0, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec_inactive])
    res_inact = await analyzer.analyze(user_uuid)
    assert res_inact.total_commits == 0
    assert res_inact.active_days_count == 0
    assert res_inact.commit_frequency_per_day == 0.0
    assert res_inact.contribution_consistency == 0.0

    # 3. Multiple observed records with gaps (e.g. 20 and 22, missing 21)
    rec_gap1 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 20), commits=10, repositories=0, stars=0, forks=0)
    rec_gap2 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 22), commits=2, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec_gap1, rec_gap2])
    res_gap = await analyzer.analyze(user_uuid)
    assert res_gap.total_commits == 12
    assert res_gap.active_days_count == 2
    assert res_gap.commit_frequency_per_day == 6.0
    assert res_gap.contribution_consistency == 1.0

# --- 4. Streak Calculation Tests ---

@pytest.mark.asyncio
async def test_streak_calculations(
    analyzer: GitHubAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify streak behaviors across boundary configurations, staleness, and missing dates."""
    user_uuid = uuid.uuid4()
    mock_snapshot = GitHubSnapshot(user_id=user_uuid, raw_data={"profile": {"id": 1, "login": "octocat"}, "repositories": []})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # a. Single active day
    rec1 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 25), commits=3, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec1])
    
    res1 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res1.current_streak == 1
    assert res1.longest_streak == 1

    # b. Consecutive active days
    rec2 = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 24), commits=2, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec2, rec1])
    
    res2 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res2.current_streak == 2
    assert res2.longest_streak == 2

    # c. Zero commit day breaks the streak
    rec_zero = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), commits=0, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec_zero, rec2, rec1])
    
    res3 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res3.current_streak == 2
    assert res3.longest_streak == 2

    # d. Missing calendar date breaks the streak
    rec_gap = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23), commits=5, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec_gap, rec1])
    
    res4 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res4.current_streak is None
    assert res4.longest_streak == 1

    # e. Stale history returning current_streak = None
    mock_history_repo.get_history = AsyncMock(return_value=[rec_gap])
    res5 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res5.current_streak is None

    # f. Fresh confirmed broken streak returning 0
    rec24_zero = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 24), commits=0, repositories=0, stars=0, forks=0)
    rec25_zero = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 25), commits=0, repositories=0, stars=0, forks=0)
    mock_history_repo.get_history = AsyncMock(return_value=[rec24_zero, rec25_zero])
    
    res6 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res6.current_streak == 0

    # g. Ambiguous missing-date scenario returning None rather than incorrectly returning 0
    mock_history_repo.get_history = AsyncMock(return_value=[rec2])
    res7 = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res7.current_streak is None
