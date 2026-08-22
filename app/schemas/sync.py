from datetime import datetime
from typing import Any, Mapping, Optional, TypeVar
from pydantic import BaseModel, StrictInt, ValidationError, Field
from app.utils.exceptions import PlatformValidationException

T = TypeVar("T", bound=BaseModel)

def validate_platform_data(
    schema: type[T],
    data: Mapping[str, Any],
    platform: str,
) -> T:
    """
    Validate raw platform data against a Pydantic schema.
    
    Raises PlatformValidationException if validation fails.
    """
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        # Format validation errors cleanly without exposing raw payloads
        errors = e.errors(include_url=False, include_context=False)
        error_details = "; ".join([f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors])
        raise PlatformValidationException(platform=platform, details=error_details)

class GitHubProfileSyncSchema(BaseModel):
    """Schema for validating GitHub profile payloads during synchronization."""
    id: StrictInt
    login: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class GitHubRepoSyncSchema(BaseModel):
    """Schema for validating GitHub repository payloads during synchronization."""
    id: StrictInt
    name: str
    full_name: str = ""
    description: Optional[str] = None
    html_url: str = ""
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    size: int = 0
    created_at: str = "1970-01-01T00:00:00Z"
    updated_at: str = "1970-01-01T00:00:00Z"
    pushed_at: Optional[str] = None
    fork: bool = False
    private: bool = False
    archived: bool = False

class GitHubSyncResult(BaseModel):
    """Result schema detailing execution metrics of the GitHub synchronization."""
    success: bool
    timestamp: datetime
    github_username: str
    repositories_fetched: int
    repositories_parsed: int
    profile_updated: bool

class LeetCodeUserProfileSchema(BaseModel):
    """Schema for validating LeetCode user profile details."""
    realName: Optional[str] = None
    aboutMe: Optional[str] = None
    userAvatar: Optional[str] = None

class LeetCodeAcSubmissionSchema(BaseModel):
    """Schema for validating LeetCode accepted submission count per difficulty."""
    difficulty: str
    count: int
    submissions: int

class LeetCodeSubmitStatsSchema(BaseModel):
    """Schema for validating LeetCode submission statistics."""
    acSubmissionNum: list[LeetCodeAcSubmissionSchema]

class LeetCodeTagSolvedSchema(BaseModel):
    """Schema for validating LeetCode tag solved count details."""
    tagName: str
    tagSlug: str
    solvedCount: int

class LeetCodeTagProblemsSolvedSchema(BaseModel):
    """Schema for validating LeetCode tag groups."""
    fundamental: list[LeetCodeTagSolvedSchema] = Field(default_factory=list)
    intermediate: list[LeetCodeTagSolvedSchema] = Field(default_factory=list)
    advanced: list[LeetCodeTagSolvedSchema] = Field(default_factory=list)

class LeetCodeMatchedUserSchema(BaseModel):
    """Schema for validating LeetCode matchedUser payload details."""
    username: str
    profile: Optional[LeetCodeUserProfileSchema] = None
    submitStats: LeetCodeSubmitStatsSchema
    tagProblemsSolved: Optional[LeetCodeTagProblemsSolvedSchema] = None

class LeetCodeDataContainerSchema(BaseModel):
    """Container schema for matchedUser."""
    matchedUser: Optional[LeetCodeMatchedUserSchema] = None

class LeetCodeResponseSchema(BaseModel):
    """Schema for validating LeetCode full GraphQL response payload."""
    data: LeetCodeDataContainerSchema

class LeetCodeSyncResult(BaseModel):
    """Result schema detailing execution metrics of the LeetCode synchronization."""
    success: bool
    timestamp: datetime
    leetcode_username: str
    problems_solved: int
    profile_updated: bool
