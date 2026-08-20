from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import UserRegisterRequest, UserRegisterResponse, UserLoginRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()

@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> UserRegisterResponse:
    """Register a new developer account on DevTrack."""
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    
    created_user = await auth_service.register_user(
        email=payload.email,
        password=payload.password
    )
    return created_user

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Verify credentials and return session tokens."""
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    
    tokens = await auth_service.authenticate_user(
        email=payload.email,
        password=payload.password
    )
    return tokens
