import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.score import DeveloperScore
from app.repositories.score import DeveloperScoreRepository

@pytest.mark.asyncio
async def test_score_repository_create_success() -> None:
    """Verify create adds, commits, and returns the score record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_score = DeveloperScore(
        user_id=user_uuid,
        overall_score=500,
        consistency_score=150,
        problem_solving_score=150,
        open_source_score=200,
        score_version="v1"
    )
    
    repo = DeveloperScoreRepository(mock_db)
    result = await repo.create(mock_score)
    
    assert result == mock_score
    mock_db.add.assert_called_once_with(mock_score)
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

@pytest.mark.asyncio
async def test_score_repository_create_failure_rolls_back() -> None:
    """Verify create rolls back the transaction and re-raises the exception on DB failure."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.commit = AsyncMock(side_effect=Exception("Database error"))
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_score = DeveloperScore(user_id=user_uuid, overall_score=500)
    
    repo = DeveloperScoreRepository(mock_db)
    with pytest.raises(Exception, match="Database error"):
        await repo.create(mock_score)
        
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_score_repository_get_by_id() -> None:
    """Verify get_by_id retrieves the correct record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    score_uuid = uuid.uuid4()
    mock_score = DeveloperScore(id=score_uuid, overall_score=500)
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_score
    mock_db.execute.return_value = mock_execute_result
    
    repo = DeveloperScoreRepository(mock_db)
    result = await repo.get_by_id(score_uuid)
    
    assert result == mock_score
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_score_repository_get_latest_by_user_id() -> None:
    """Verify get_latest_by_user_id retrieves the latest user record sorted by computed_at DESC."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_score = DeveloperScore(user_id=user_uuid, overall_score=500)
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_score
    mock_db.execute.return_value = mock_execute_result
    
    repo = DeveloperScoreRepository(mock_db)
    result = await repo.get_latest_by_user_id(user_uuid)
    
    assert result == mock_score
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_score_repository_get_history_limit() -> None:
    """Verify get_history correctly retrieves user history with limits."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_records = [
        DeveloperScore(user_id=user_uuid, overall_score=500),
        DeveloperScore(user_id=user_uuid, overall_score=510)
    ]
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = DeveloperScoreRepository(mock_db)
    result = await repo.get_history(user_id=user_uuid, limit=5)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()
    
    with pytest.raises(ValueError, match="Limit must be greater than zero."):
        await repo.get_history(user_id=user_uuid, limit=0)
