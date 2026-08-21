from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest, PlatformConnectionRequest
from app.repositories.profile import ProfileRepository
from app.services.profile import ProfileService

router = APIRouter(tags=["Profile"])

async def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))

@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
) -> Profile:
    """Retrieve the currently authenticated developer's profile."""
    return await profile_service.get_or_create_profile(current_user.id)

@router.put("/", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
) -> Profile:
    """Update the currently authenticated developer's profile."""
    update_data = body.model_dump(exclude_unset=True)
    return await profile_service.update_profile(current_user.id, update_data)

@router.put("/connect", response_model=ProfileResponse)
async def connect_platforms(
    body: PlatformConnectionRequest,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
) -> Profile:
    """Connect or update the authenticated developer's platform usernames."""
    update_data = body.model_dump(exclude_unset=True)
    return await profile_service.connect_platforms(current_user.id, update_data)
