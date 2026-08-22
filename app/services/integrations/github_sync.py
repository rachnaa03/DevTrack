from datetime import datetime, timezone
from uuid import UUID
import logging

from app.repositories.profile import ProfileRepository
from app.services.integrations.github import GitHubClient
from app.services.integrations.github_parser import GitHubDataParser
from app.schemas.sync import GitHubSyncResult
from app.utils.exceptions import PlatformNotConnectedException

logger = logging.getLogger(__name__)

class GitHubSyncService:
    """Service responsible for orchestrating GitHub synchronization pipeline."""
    
    def __init__(self, profile_repo: ProfileRepository, github_client: GitHubClient):
        self.profile_repo = profile_repo
        self.github_client = github_client

    async def sync_github_data(self, user_id: UUID) -> GitHubSyncResult:
        """
        Orchestrates loading user profile, fetching external payload, parsing metrics,
        and updating the internal database profile conditionally (non-destructively).
        """
        # 1. Retrieve the profile from database
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile or not profile.github_username:
            raise PlatformNotConnectedException(platform="GitHub")
            
        username = profile.github_username
        logger.info(f"Starting GitHub sync for user_id={user_id}, username={username}")
        
        # 2. Fetch raw payload from client (errors propagate)
        raw_payload = await self.github_client.fetch_raw_data(username)
        
        # 3. Parse and validate the raw payload (validation errors raise PlatformValidationException)
        parsed_data = GitHubDataParser.parse(raw_payload)
        
        # 4. Compare and update profile fields non-destructively
        profile_updated = False
        
        # Only update if the incoming value is not null and differs from local DB
        if parsed_data.bio is not None and profile.bio != parsed_data.bio:
            profile.bio = parsed_data.bio
            profile_updated = True
            
        if parsed_data.avatar_url is not None and profile.avatar_url != parsed_data.avatar_url:
            profile.avatar_url = parsed_data.avatar_url
            profile_updated = True
            
        # 5. Persist profile changes if any field was updated
        if profile_updated:
            logger.info(f"Persisting profile updates for user_id={user_id}")
            await self.profile_repo.update(profile)
        else:
            logger.info(f"No profile updates needed for user_id={user_id}")
            
        return GitHubSyncResult(
            success=True,
            timestamp=datetime.now(timezone.utc),
            github_username=username,
            repositories_fetched=len(raw_payload.get("repositories", [])),
            repositories_parsed=parsed_data.repositories_count,
            profile_updated=profile_updated,
        )
