from uuid import UUID
from app.models.profile import Profile
from app.repositories.profile import ProfileRepository

class ProfileService:
    """Service class executing profile-related business logic."""
    
    def __init__(self, profile_repo: ProfileRepository):
        self.profile_repo = profile_repo

    async def get_or_create_profile(self, user_id: UUID) -> Profile:
        """Retrieve the user's Profile, creating an empty one lazily if it doesn't exist."""
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = Profile(user_id=user_id)
            profile = await self.profile_repo.create(profile)
        return profile

    async def update_profile(self, user_id: UUID, update_data: dict) -> Profile:
        """Update profile fields partially for the given user, creating the profile lazily if needed."""
        profile = await self.get_or_create_profile(user_id)
        
        for key, value in update_data.items():
            setattr(profile, key, value)
            
        return await self.profile_repo.update(profile)
