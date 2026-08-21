from typing import Any, Mapping, TypeVar
from pydantic import BaseModel, StrictInt, ValidationError
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

class GitHubRepoSyncSchema(BaseModel):
    """Schema for validating GitHub repository payloads during synchronization."""
    id: StrictInt
    name: str
