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


import re
from typing import Self
from pydantic import model_validator

GITHUB_REGEX = re.compile(r"^(?!-)(?!.*--)[A-Za-z0-9-]{1,39}(?<!-)$")
LEETCODE_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")

class PlatformConnectionRequest(BaseModel):
    """Pydantic model representing platform connection request body."""
    github_username: Optional[str] = Field(None, description="GitHub username")
    leetcode_username: Optional[str] = Field(None, description="LeetCode username")

    @model_validator(mode="after")
    def validate_connection_payload(self) -> Self:
        github = self.github_username
        leetcode = self.leetcode_username

        if github is None and leetcode is None:
            raise ValueError("At least one platform username must be provided")

        if github is not None:
            if not github.strip():
                raise ValueError("github_username cannot be empty or whitespace")
            if " " in github or "\t" in github or "\n" in github or "\r" in github:
                raise ValueError("github_username cannot contain whitespace")
            if not GITHUB_REGEX.match(github):
                raise ValueError("Invalid GitHub username format")

        if leetcode is not None:
            if not leetcode.strip():
                raise ValueError("leetcode_username cannot be empty or whitespace")
            if " " in leetcode or "\t" in leetcode or "\n" in leetcode or "\r" in leetcode:
                raise ValueError("leetcode_username cannot contain whitespace")
            if not LEETCODE_REGEX.match(leetcode):
                raise ValueError("Invalid LeetCode username format")

        return self

    model_config = ConfigDict(extra="forbid")

