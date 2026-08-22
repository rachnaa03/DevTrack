import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.services.analytics.trends import TrendQueryEngine
from app.utils.exceptions import InvalidMetricException

# --- Repository unit tests for get_recent_by_user_id ---

@pytest.mark.asyncio
async def test_github_repository_get_recent_by_user_id() -> None:
    """Verify get_recent_by_user_id executes query and returns recent records."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    mock_records = [
        GitHubHistory(user_id=uuid.uuid4(), date=date(2026, 8, 23)),
        GitHubHistory(user_id=uuid.uuid4(), date=date(2026, 8, 22))
    ]
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubHistoryRepository(mock_db)
    result = await repo.get_recent_by_user_id(user_uuid := uuid.uuid4(), limit=2)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()
    
    # Test invalid limit raises ValueError
    with pytest.raises(ValueError, match="Limit must be greater than zero."):
        await repo.get_recent_by_user_id(user_uuid, limit=0)

@pytest.mark.asyncio
async def test_leetcode_repository_get_recent_by_user_id() -> None:
    """Verify get_recent_by_user_id executes query and returns recent records."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    mock_records = [
        LeetCodeHistory(user_id=uuid.uuid4(), date=date(2026, 8, 23)),
        LeetCodeHistory(user_id=uuid.uuid4(), date=date(2026, 8, 22))
    ]
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = LeetCodeHistoryRepository(mock_db)
    result = await repo.get_recent_by_user_id(user_uuid := uuid.uuid4(), limit=2)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()
    
    # Test invalid limit raises ValueError
    with pytest.raises(ValueError, match="Limit must be greater than zero."):
        await repo.get_recent_by_user_id(user_uuid, limit=0)

# --- Service/Engine unit tests ---

@pytest.fixture
def mock_github_repo() -> MagicMock:
    return MagicMock(spec=GitHubHistoryRepository)

@pytest.fixture
def mock_leetcode_repo() -> MagicMock:
    return MagicMock(spec=LeetCodeHistoryRepository)

@pytest.fixture
def engine(mock_github_repo: MagicMock, mock_leetcode_repo: MagicMock) -> TrendQueryEngine:
    return TrendQueryEngine(mock_github_repo, mock_leetcode_repo)

@pytest.mark.asyncio
async def test_calculate_github_trends_success(engine: TrendQueryEngine, mock_github_repo: MagicMock) -> None:
    """Verify correct calculation of 'up', 'down', and 'unchanged' trends for GitHub."""
    user_uuid = uuid.uuid4()
    
    latest_rec = GitHubHistory(
        user_id=user_uuid,
        date=date(2026, 8, 23),
        commits=15,       # commits: up (15 vs 10)
        stars=3,          # stars: down (3 vs 5)
        forks=2,          # forks: unchanged (2 vs 2)
        repositories=4,   # repositories: up (4 vs 3)
        parsed_metrics={}
    )
    prev_rec = GitHubHistory(
        user_id=user_uuid,
        date=date(2026, 8, 22),
        commits=10,
        stars=5,
        forks=2,
        repositories=3,
        parsed_metrics={}
    )
    
    mock_github_repo.get_recent_by_user_id = AsyncMock(return_value=[latest_rec, prev_rec])
    
    summary = await engine.calculate_github_trends(user_uuid)
    
    assert summary.platform == "github"
    assert summary.user_id == user_uuid
    
    # commits trend
    assert summary.trends["commits"].latest_value == 15
    assert summary.trends["commits"].previous_value == 10
    assert summary.trends["commits"].absolute_change == 5
    assert summary.trends["commits"].direction == "up"
    assert summary.trends["commits"].latest_date == date(2026, 8, 23)
    assert summary.trends["commits"].previous_date == date(2026, 8, 22)
    
    # stars trend
    assert summary.trends["stars"].direction == "down"
    assert summary.trends["stars"].absolute_change == -2
    
    # forks trend
    assert summary.trends["forks"].direction == "unchanged"
    assert summary.trends["forks"].absolute_change == 0

@pytest.mark.asyncio
async def test_calculate_leetcode_trends_success(engine: TrendQueryEngine, mock_leetcode_repo: MagicMock) -> None:
    """Verify correct calculation of 'up', 'down', and 'unchanged' trends for LeetCode."""
    user_uuid = uuid.uuid4()
    
    latest_rec = LeetCodeHistory(
        user_id=user_uuid,
        date=date(2026, 8, 23),
        problems_solved=20, # up
        easy_solved=10,     # unchanged
        medium_solved=8,    # up
        hard_solved=2,      # down
        submissions=40,     # up
        parsed_metrics={}
    )
    prev_rec = LeetCodeHistory(
        user_id=user_uuid,
        date=date(2026, 8, 22),
        problems_solved=15,
        easy_solved=10,
        medium_solved=2,
        hard_solved=3,
        submissions=30,
        parsed_metrics={}
    )
    
    mock_leetcode_repo.get_recent_by_user_id = AsyncMock(return_value=[latest_rec, prev_rec])
    
    summary = await engine.calculate_leetcode_trends(user_uuid)
    
    assert summary.platform == "leetcode"
    assert summary.user_id == user_uuid
    
    assert summary.trends["problems_solved"].direction == "up"
    assert summary.trends["easy_solved"].direction == "unchanged"
    assert summary.trends["medium_solved"].direction == "up"
    assert summary.trends["hard_solved"].direction == "down"
    assert summary.trends["submissions"].direction == "up"

@pytest.mark.asyncio
async def test_calculate_trends_insufficient_data(engine: TrendQueryEngine, mock_github_repo: MagicMock) -> None:
    """Verify correct trend behavior when only one record is available."""
    user_uuid = uuid.uuid4()
    latest_rec = GitHubHistory(
        user_id=user_uuid,
        date=date(2026, 8, 23),
        commits=15,
        stars=3,
        forks=2,
        repositories=4,
        parsed_metrics={}
    )
    
    mock_github_repo.get_recent_by_user_id = AsyncMock(return_value=[latest_rec])
    summary = await engine.calculate_github_trends(user_uuid)
    
    assert summary.trends["commits"].latest_value == 15
    assert summary.trends["commits"].previous_value is None
    assert summary.trends["commits"].absolute_change is None
    assert summary.trends["commits"].direction == "insufficient_data"
    assert summary.trends["commits"].latest_date == date(2026, 8, 23)
    assert summary.trends["commits"].previous_date is None

@pytest.mark.asyncio
async def test_calculate_trends_zero_records(engine: TrendQueryEngine, mock_github_repo: MagicMock) -> None:
    """Verify correct trend behavior when no records are available."""
    user_uuid = uuid.uuid4()
    mock_github_repo.get_recent_by_user_id = AsyncMock(return_value=[])
    summary = await engine.calculate_github_trends(user_uuid)
    
    assert summary.platform == "github"
    assert summary.user_id == user_uuid
    assert summary.trends == {}

@pytest.mark.asyncio
async def test_calculate_trends_non_consecutive_dates(engine: TrendQueryEngine, mock_github_repo: MagicMock) -> None:
    """Verify latest-vs-previous comparison compares the latest two AVAILABLE records regardless of dates."""
    user_uuid = uuid.uuid4()
    latest_rec = GitHubHistory(
        user_id=user_uuid,
        date=date(2026, 8, 23),
        commits=15,
        stars=3,
        forks=2,
        repositories=4,
        parsed_metrics={}
    )
    prev_rec = GitHubHistory(
        user_id=user_uuid,
        date=date(2026, 8, 15), # 8 days prior
        commits=10,
        stars=5,
        forks=2,
        repositories=3,
        parsed_metrics={}
    )
    
    mock_github_repo.get_recent_by_user_id = AsyncMock(return_value=[latest_rec, prev_rec])
    summary = await engine.calculate_github_trends(user_uuid)
    
    assert summary.trends["commits"].latest_date == date(2026, 8, 23)
    assert summary.trends["commits"].previous_date == date(2026, 8, 15)
    assert summary.trends["commits"].direction == "up"

@pytest.mark.asyncio
async def test_invalid_metric_validation(engine: TrendQueryEngine) -> None:
    """Verify that requesting invalid or mixed metrics raises InvalidMetricException."""
    user_uuid = uuid.uuid4()
    
    # Invalid GitHub metric name
    with pytest.raises(InvalidMetricException, match="Metric 'invalid' is not supported for platform 'GitHub'"):
        await engine.calculate_github_trends(user_uuid, metrics=["commits", "invalid"])
        
    # Invalid LeetCode metric name
    with pytest.raises(InvalidMetricException, match="Metric 'invalid' is not supported for platform 'LeetCode'"):
        await engine.calculate_leetcode_trends(user_uuid, metrics=["problems_solved", "invalid"])

    # Mix checks: LeetCode metric used on GitHub raises InvalidMetricException
    with pytest.raises(InvalidMetricException, match="Metric 'problems_solved' is not supported for platform 'GitHub'"):
        await engine.calculate_github_trends(user_uuid, metrics=["problems_solved"])

    # GitHub metric used on LeetCode raises InvalidMetricException
    with pytest.raises(InvalidMetricException, match="Metric 'commits' is not supported for platform 'LeetCode'"):
        await engine.calculate_leetcode_trends(user_uuid, metrics=["commits"])

@pytest.mark.asyncio
async def test_history_range_delegation(
    engine: TrendQueryEngine,
    mock_github_repo: MagicMock,
    mock_leetcode_repo: MagicMock
) -> None:
    """Verify get_github_history and get_leetcode_history correctly delegate to their repos."""
    user_uuid = uuid.uuid4()
    start = date(2026, 8, 22)
    end = date(2026, 8, 23)
    
    mock_github_repo.get_history = AsyncMock(return_value=[])
    mock_leetcode_repo.get_history = AsyncMock(return_value=[])
    
    await engine.get_github_history(user_uuid, start, end)
    mock_github_repo.get_history.assert_called_once_with(user_id=user_uuid, start_date=start, end_date=end)
    
    await engine.get_leetcode_history(user_uuid, start, end)
    mock_leetcode_repo.get_history.assert_called_once_with(user_id=user_uuid, start_date=start, end_date=end)
