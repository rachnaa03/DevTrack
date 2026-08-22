import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.github_history import GitHubHistory
from app.repositories.github_history import GitHubHistoryRepository

@pytest.mark.asyncio
async def test_github_history_create_or_update_success() -> None:
    """Verify create_or_update executes query, commits, and returns the history record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    history_date = date(2026, 8, 23)
    parsed_metrics = {"languages": {"Python": 1}}
    
    mock_history = GitHubHistory(
        user_id=user_uuid,
        date=history_date,
        commits=10,
        stars=5,
        forks=2,
        repositories=3,
        parsed_metrics=parsed_metrics
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().one.return_value = mock_history
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubHistoryRepository(mock_db)
    result = await repo.create_or_update(
        user_id=user_uuid,
        history_date=history_date,
        commits=10,
        stars=5,
        forks=2,
        repositories=3,
        parsed_metrics=parsed_metrics
    )
    
    assert result == mock_history
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

@pytest.mark.asyncio
async def test_github_history_create_or_update_failure_rolls_back() -> None:
    """Verify create_or_update rolls back the transaction and re-raises the exception on DB failure."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    user_uuid = uuid.uuid4()
    history_date = date(2026, 8, 23)
    
    repo = GitHubHistoryRepository(mock_db)
    with pytest.raises(Exception, match="Database error"):
        await repo.create_or_update(
            user_id=user_uuid,
            history_date=history_date,
            commits=10,
            stars=5,
            forks=2,
            repositories=3,
            parsed_metrics={}
        )
        
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_github_history_get_history_no_filters() -> None:
    """Verify get_history correctly retrieves all user records without date filters."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_records = [
        GitHubHistory(user_id=user_uuid, date=date(2026, 8, 22)),
        GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23))
    ]
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = mock_records
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubHistoryRepository(mock_db)
    result = await repo.get_history(user_id=user_uuid)
    
    assert result == mock_records
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_github_history_get_history_filters() -> None:
    """Verify get_history handles start_date, end_date, and both filters correctly."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    user_uuid = uuid.uuid4()
    repo = GitHubHistoryRepository(mock_db)
    
    # 1. Start date filter only
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22))
    assert mock_db.execute.call_count == 1
    
    # 2. End date filter only
    await repo.get_history(user_id=user_uuid, end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 2
    
    # 3. Both start and end filters
    await repo.get_history(user_id=user_uuid, start_date=date(2026, 8, 22), end_date=date(2026, 8, 23))
    assert mock_db.execute.call_count == 3

@pytest.mark.asyncio
async def test_github_history_get_latest_success() -> None:
    """Verify get_latest_by_user_id retrieves latest user record."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    user_uuid = uuid.uuid4()
    mock_history = GitHubHistory(user_id=user_uuid, date=date(2026, 8, 23))
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = mock_history
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubHistoryRepository(mock_db)
    result = await repo.get_latest_by_user_id(user_uuid)
    
    assert result == mock_history
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_github_history_get_latest_none() -> None:
    """Verify get_latest_by_user_id returns None if no history exists."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars().first.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    repo = GitHubHistoryRepository(mock_db)
    result = await repo.get_latest_by_user_id(uuid.uuid4())
    
    assert result is None
