import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.leetcode_analytics import LeetCodeAnalytics
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema, TopicSummarySchema
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository

@pytest.fixture
def sample_leetcode_result() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid.uuid4(),
        username="testuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=10,
            medium_solved=5,
            hard_solved=2,
            total_solved=17,
            easy_submissions=20,
            medium_submissions=10,
            hard_submissions=4,
            total_submissions=34
        ),
        most_practiced_topics=[
            TopicSummarySchema(tag_name="Array", tag_slug="array", solved_count=5, difficulty_level="fundamental")
        ],
        problems_solved_growth=2,
        easy_solved_growth=1,
        medium_solved_growth=1,
        hard_solved_growth=0,
        submissions_growth=4,
        problems_solved_frequency_per_day=0.5,
        active_days_count=2,
        contribution_consistency=0.4,
        current_streak=1,
        longest_streak=2
    )

@pytest.mark.asyncio
async def test_leetcode_analytics_create_or_update_success(sample_leetcode_result: LeetCodeAnalysisResultSchema) -> None:
    """Verify create_or_update executes query, commits, and returns the analytics record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    
    mock_record = LeetCodeAnalytics(
        user_id=user_uuid,
        date=analysis_date,
        easy_solved=10,
        medium_solved=5,
        hard_solved=2,
        total_solved=17,
        easy_submissions=20,
        medium_submissions=10,
        hard_submissions=4,
        total_submissions=34,
        problems_solved_growth=2,
        easy_solved_growth=1,
        medium_solved_growth=1,
        hard_solved_growth=0,
        submissions_growth=4,
        problems_solved_frequency_per_day=0.5,
        active_days_count=2,
        contribution_consistency=0.4,
        current_streak=1,
        longest_streak=2,
        most_practiced_topics=[{"tag_name": "Array", "tag_slug": "array", "solved_count": 5, "difficulty_level": "fundamental"}]
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().one.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = LeetCodeAnalyticsRepository(mock_db)
    result = await repo.create_or_update(
        user_id=user_uuid,
        analysis_date=analysis_date,
        result=sample_leetcode_result
    )
    
    assert result == mock_record
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

@pytest.mark.asyncio
async def test_leetcode_analytics_create_or_update_failure_rolls_back(sample_leetcode_result: LeetCodeAnalysisResultSchema) -> None:
    """Verify create_or_update rolls back the transaction and re-raises the exception on DB failure."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    
    repo = LeetCodeAnalyticsRepository(mock_db)
    with pytest.raises(Exception, match="Database error"):
        await repo.create_or_update(
            user_id=user_uuid,
            analysis_date=analysis_date,
            result=sample_leetcode_result
        )
        
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_leetcode_analytics_get_by_user_id_and_date() -> None:
    """Verify get_by_user_id_and_date retrieves the correct analytics record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    analysis_date = date(2026, 8, 23)
    mock_record = LeetCodeAnalytics(user_id=user_uuid, date=analysis_date)
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = LeetCodeAnalyticsRepository(mock_db)
    result = await repo.get_by_user_id_and_date(user_uuid, analysis_date)
    
    assert result == mock_record
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_leetcode_analytics_get_latest_by_user_id() -> None:
    """Verify get_latest_by_user_id retrieves the latest user record sorted by date DESC."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_record = LeetCodeAnalytics(user_id=user_uuid, date=date(2026, 8, 23))
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_record
    mock_db.execute.return_value = mock_execute_result
    
    repo = LeetCodeAnalyticsRepository(mock_db)
    result = await repo.get_latest_by_user_id(user_uuid)
    
    assert result == mock_record
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_leetcode_analytics_get_history_no_filters() -> None:
    """Verify get_history correctly retrieves all user records without date filters."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_records = [
        LeetCodeAnalytics(user_id=user_uuid, date=date(2026, 8, 22)),
        LeetCodeAnalytics(user_id=user_uuid, date=date(2026, 8, 23))
    ]
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = LeetCodeAnalyticsRepository(mock_db)
    result = await repo.get_history(user_id=user_uuid)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_leetcode_analytics_get_history_filters() -> None:
    """Verify get_history handles start_date, end_date, and both filters correctly."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    user_uuid = uuid.uuid4()
    repo = LeetCodeAnalyticsRepository(mock_db)
    
    # 1. Start date filter only
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22))
    assert mock_db.execute.call_count == 1
    
    # 2. End date filter only
    await repo.get_history(user_id=user_uuid, end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 2
    
    # 3. Both start and end filters
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22), end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 3
