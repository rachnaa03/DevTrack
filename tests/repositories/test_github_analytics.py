import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.github_analytics import GitHubAnalytics
from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.repositories.github_analytics import GitHubAnalyticsRepository

@pytest.fixture
def sample_analysis_result() -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=uuid.uuid4(),
        login="testuser",
        repo_stats=RepositoryStatsSchema(
            total_repositories=5,
            total_stars=10,
            total_forks=2,
            total_size=1024,
            total_open_issues=1
        ),
        language_distribution={"Python": 80, "JavaScript": 20},
        most_starred_repos=[],
        recently_updated_repositories=[],
        repository_growth=1,
        star_growth=2,
        fork_growth=0,
        total_commits=15,
        commit_frequency_per_day=1.5,
        active_days_count=3,
        contribution_consistency=0.6,
        current_streak=2,
        longest_streak=3
    )

@pytest.mark.asyncio
async def test_github_analytics_create_or_update_success(sample_analysis_result: GitHubAnalysisResultSchema) -> None:
    """Verify create_or_update executes query, commits, and returns the analytics record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    
    mock_record = GitHubAnalytics(
        user_id=user_uuid,
        date=analysis_date,
        total_repositories=5,
        total_stars=10,
        total_forks=2,
        total_size=1024,
        total_open_issues=1,
        repository_growth=1,
        star_growth=2,
        fork_growth=0,
        total_commits=15,
        commit_frequency_per_day=1.5,
        active_days_count=3,
        contribution_consistency=0.6,
        current_streak=2,
        longest_streak=3,
        languages={"Python": 0.8, "JavaScript": 0.2},
        most_starred_repos=[],
        recently_updated_repos=[]
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().one.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubAnalyticsRepository(mock_db)
    result = await repo.create_or_update(
        user_id=user_uuid,
        analysis_date=analysis_date,
        result=sample_analysis_result
    )
    
    assert result == mock_record
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

@pytest.mark.asyncio
async def test_github_analytics_create_or_update_failure_rolls_back(sample_analysis_result: GitHubAnalysisResultSchema) -> None:
    """Verify create_or_update rolls back the transaction and re-raises the exception on DB failure."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    
    repo = GitHubAnalyticsRepository(mock_db)
    with pytest.raises(Exception, match="Database error"):
        await repo.create_or_update(
            user_id=user_uuid,
            analysis_date=analysis_date,
            result=sample_analysis_result
        )
        
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_github_analytics_get_by_user_id_and_date() -> None:
    """Verify get_by_user_id_and_date retrieves the correct analytics record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    mock_record = GitHubAnalytics(user_id=user_uuid, date=analysis_date)
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubAnalyticsRepository(mock_db)
    result = await repo.get_by_user_id_and_date(user_uuid, analysis_date)
    
    assert result == mock_record
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_github_analytics_get_latest_by_user_id() -> None:
    """Verify get_latest_by_user_id retrieves the latest user record sorted by date DESC."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_record = GitHubAnalytics(user_id=user_uuid, date=date(2026, 8, 23))
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubAnalyticsRepository(mock_db)
    result = await repo.get_latest_by_user_id(user_uuid)
    
    assert result == mock_record
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_github_analytics_get_history_no_filters() -> None:
    """Verify get_history correctly retrieves all user records without date filters."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_records = [
        GitHubAnalytics(user_id=user_uuid, date=date(2026, 8, 22)),
        GitHubAnalytics(user_id=user_uuid, date=date(2026, 8, 23))
    ]
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubAnalyticsRepository(mock_db)
    result = await repo.get_history(user_id=user_uuid)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_github_analytics_get_history_filters() -> None:
    """Verify get_history handles start_date, end_date, and both filters correctly."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    user_uuid = uuid.uuid4()
    repo = GitHubAnalyticsRepository(mock_db)
    
    # 1. Start date filter only
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22))
    assert mock_db.execute.call_count == 1
    
    # 2. End date filter only
    await repo.get_history(user_id=user_uuid, end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 2
    
    # 3. Both start and end filters
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22), end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 3
