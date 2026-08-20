import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegisterRequest(BaseModel):
    """Pydantic model representing registration request body."""
    email: EmailStr = Field(..., description="Valid user email address", max_length=255)
    password: str = Field(..., min_length=8, max_length=64, description="User password (8-64 characters)")

class UserRegisterResponse(BaseModel):
    """Pydantic model representing registration response body."""
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLoginRequest(BaseModel):
    """Pydantic model representing login request body."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class TokenResponse(BaseModel):
    """Pydantic model representing authentication tokens response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

