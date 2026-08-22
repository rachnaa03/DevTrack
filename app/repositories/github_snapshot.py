from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.github_snapshot import GitHubSnapshot

class GitHubSnapshotRepository:
    """Repository class encapsulating database operations for the GitHubSnapshot model."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, snapshot: GitHubSnapshot) -> GitHubSnapshot:
        """Persist a GitHubSnapshot instance and commit the transaction."""
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_by_user_id(self, user_id: UUID) -> GitHubSnapshot | None:
        """Retrieve the user's latest GitHub snapshot sorted by fetched_at DESC."""
        result = await self.db.execute(
            select(GitHubSnapshot)
            .filter(GitHubSnapshot.user_id == user_id)
            .order_by(GitHubSnapshot.fetched_at.desc())
            .limit(1)
        )
        return result.scalars().first()
