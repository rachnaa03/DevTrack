from datetime import datetime, timezone
from uuid import UUID
import logging

from app.repositories.profile import ProfileRepository
from app.services.integrations.leetcode import LeetCodeClient
from app.services.integrations.leetcode_parser import LeetCodeDataParser
from app.schemas.sync import LeetCodeSyncResult
from app.utils.exceptions import PlatformNotConnectedException

logger = logging.getLogger(__name__)

class LeetCodeSyncService:
    """Service responsible for orchestrating LeetCode synchronization pipeline."""
    
    def __init__(self, profile_repo: ProfileRepository, leetcode_client: LeetCodeClient):
        self.profile_repo = profile_repo
        self.leetcode_client = leetcode_client

    async def sync_leetcode_data(self, user_id: UUID) -> LeetCodeSyncResult:
        """
        Orchestrates loading user profile, fetching external payload, parsing metrics,
        and updating the internal database profile conditionally (non-destructively).
        """
        # 1. Retrieve the profile from database
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile or not profile.leetcode_username:
            raise PlatformNotConnectedException(platform="LeetCode")
            
        username = profile.leetcode_username
        logger.info(f"Starting LeetCode sync for user_id={user_id}, username={username}")
        
        # 2. Fetch raw payload from client (errors propagate)
        raw_payload = await self.leetcode_client.fetch_raw_data(username)
        
        # 3. Parse and validate the raw payload (validation errors raise PlatformValidationException)
        parsed_data = LeetCodeDataParser.parse(raw_payload)
        
        # 4. Compare and update profile fields non-destructively
        profile_updated = False
        
        # Only update if the incoming value is not null and differs from local DB
        if parsed_data.about_me is not None and profile.bio != parsed_data.about_me:
            profile.bio = parsed_data.about_me
            profile_updated = True
            
        if parsed_data.user_avatar is not None and profile.avatar_url != parsed_data.user_avatar:
            profile.avatar_url = parsed_data.user_avatar
            profile_updated = True
            
        # 5. Persist profile changes if any field was updated
        if profile_updated:
            logger.info(f"Persisting profile updates for user_id={user_id}")
            await self.profile_repo.update(profile)
        else:
            logger.info(f"No profile updates needed for user_id={user_id}")
            
        return LeetCodeSyncResult(
            success=True,
            timestamp=datetime.now(timezone.utc),
            leetcode_username=username,
            problems_solved=parsed_data.problems.total_solved,
            profile_updated=profile_updated,
        )
