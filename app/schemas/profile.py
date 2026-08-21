import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ProfileResponse(BaseModel):
    """Pydantic model representing profile response payload."""
    id: uuid.UUID
    user_id: uuid.UUID
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None
    leetcode_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProfileUpdateRequest(BaseModel):
    """Pydantic model representing profile update request body."""
    bio: Optional[str] = Field(None, max_length=1000, description="Brief biography")
    avatar_url: Optional[str] = Field(None, max_length=1024, description="Profile avatar link")

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "":
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("avatar_url must start with http:// or https://")
        return v

    model_config = ConfigDict(extra="forbid")
