import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.leetcode_snapshot import LeetCodeSnapshot
from app.repositories.leetcode_snapshot import LeetCodeSnapshotRepository

def test_leetcode_snapshot_model_attributes() -> None:
    """Verify that LeetCodeSnapshot database model attributes and constraints are defined correctly."""
    assert LeetCodeSnapshot.__tablename__ == "leetcode_snapshots"
    
    # Verify expected columns are present
    assert hasattr(LeetCodeSnapshot, "id")
    assert hasattr(LeetCodeSnapshot, "user_id")
    assert hasattr(LeetCodeSnapshot, "raw_data")
    assert hasattr(LeetCodeSnapshot, "fetched_at")
    assert hasattr(LeetCodeSnapshot, "user")

    # Verify table index constraints
    indexes = LeetCodeSnapshot.__table__.indexes
    fetch_index = next((idx for idx in indexes if idx.name == "idx_leetcode_snapshots_user_fetch"), None)
    assert fetch_index is not None
    assert fetch_index.unique is False
    assert len(fetch_index.columns) == 2
    cols = [col.name for col in fetch_index.columns]
    assert "user_id" in cols
    assert "fetched_at" in cols

def test_user_leetcode_snapshots_relationship() -> None:
    """Verify SQLAlchemy 1:N relationship attributes are configured correctly on both models."""
    assert hasattr(User, "leetcode_snapshots")
    assert hasattr(LeetCodeSnapshot, "user")
    
    # Verify User side configuration
    user_rel = User.leetcode_snapshots.property
    assert user_rel.uselist is True
    assert user_rel.back_populates == "user"
    assert "delete" in user_rel.cascade
    assert "delete-orphan" in user_rel.cascade

    # Verify LeetCodeSnapshot side configuration
    snapshot_rel = LeetCodeSnapshot.user.property
    assert snapshot_rel.uselist is False
    assert snapshot_rel.back_populates == "leetcode_snapshots"

@pytest.mark.asyncio
async def test_snapshot_repository_create() -> None:
    """Verify LeetCodeSnapshotRepository.create adds to session and commits successfully."""
    mock_db = MagicMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    repo = LeetCodeSnapshotRepository(mock_db)
    snapshot = LeetCodeSnapshot(user_id=uuid.uuid4(), raw_data={"username": "leetcode_coder"})
    
    result = await repo.create(snapshot)
    
    assert result == snapshot
    mock_db.add.assert_called_once_with(snapshot)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(snapshot)

@pytest.mark.asyncio
async def test_snapshot_repository_get_latest() -> None:
    """Verify LeetCodeSnapshotRepository.get_latest_by_user_id executes query and returns latest snapshot."""
    mock_db = MagicMock(spec=AsyncSession)
    
    mock_execute_result = MagicMock()
    mock_snapshot = LeetCodeSnapshot(user_id=uuid.uuid4(), raw_data={"username": "leetcode_coder"})
    mock_execute_result.scalars().first.return_value = mock_snapshot
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    repo = LeetCodeSnapshotRepository(mock_db)
    user_uuid = uuid.uuid4()
    
    result = await repo.get_latest_by_user_id(user_uuid)
    
    assert result == mock_snapshot
    mock_db.execute.assert_called_once()
