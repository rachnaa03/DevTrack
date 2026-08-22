from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.schemas.sync import (
    GitHubProfileSyncSchema,
    GitHubRepoSyncSchema,
    validate_platform_data,
)
from app.utils.exceptions import PlatformValidationException

class ParsedGitHubRepo(BaseModel):
    """Parsed model representing a validated GitHub repository."""
    github_id: int
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    language: Optional[str] = None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    size: int
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime] = None
    is_fork: bool
    is_private: bool
    is_archived: bool

class ParsedGitHubData(BaseModel):
    """Aggregate model representing complete parsed GitHub profile and repositories."""
    login: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    repositories_count: int
    total_stars: int
    total_forks: int
    total_size: int
    total_open_issues: int
    languages: Dict[str, int]
    
    repositories: List[ParsedGitHubRepo]

class GitHubDataParser:
    """Parser for validating and converting raw GitHub API payloads into structured DevTrack formats."""
    
    @staticmethod
    def parse(raw_payload: Any) -> ParsedGitHubData:
        """
        Accept, validate, and parse raw GitHub payload containing profile and repository lists.
        Raises PlatformValidationException for malformed payloads.
        """
        if not isinstance(raw_payload, dict):
            raise PlatformValidationException(
                platform="GitHub",
                details="Raw payload must be a dictionary."
            )
            
        if "profile" not in raw_payload:
            raise PlatformValidationException(
                platform="GitHub",
                details="Raw payload is missing the 'profile' key."
            )
            
        if "repositories" not in raw_payload:
            raise PlatformValidationException(
                platform="GitHub",
                details="Raw payload is missing the 'repositories' key."
            )
            
        profile_raw = raw_payload["profile"]
        repos_raw = raw_payload["repositories"]
        
        if not isinstance(profile_raw, dict):
            raise PlatformValidationException(
                platform="GitHub",
                details="'profile' value must be a dictionary."
            )
            
        if not isinstance(repos_raw, list):
            raise PlatformValidationException(
                platform="GitHub",
                details="'repositories' value must be a list."
            )
            
        # 1. Validate Profile
        profile_schema = validate_platform_data(GitHubProfileSyncSchema, profile_raw, platform="GitHub")
        
        # 2. Loop and validate Repositories list
        parsed_repos: List[ParsedGitHubRepo] = []
        languages: Dict[str, int] = {}
        total_stars = 0
        total_forks = 0
        total_size = 0
        total_open_issues = 0
        
        for repo_raw in repos_raw:
            if not isinstance(repo_raw, dict):
                raise PlatformValidationException(
                    platform="GitHub",
                    details="Repository item must be a dictionary."
                )
                
            repo_schema = validate_platform_data(GitHubRepoSyncSchema, repo_raw, platform="GitHub")
            
            # Aggregate stats
            total_stars += repo_schema.stargazers_count
            total_forks += repo_schema.forks_count
            total_size += repo_schema.size
            total_open_issues += repo_schema.open_issues_count
            
            if repo_schema.language:
                languages[repo_schema.language] = languages.get(repo_schema.language, 0) + 1
                
            # Parse dates safely
            try:
                created_at = datetime.fromisoformat(repo_schema.created_at.replace("Z", "+00:00"))
                updated_at = datetime.fromisoformat(repo_schema.updated_at.replace("Z", "+00:00"))
                pushed_at = (
                    datetime.fromisoformat(repo_schema.pushed_at.replace("Z", "+00:00"))
                    if repo_schema.pushed_at else None
                )
            except ValueError as e:
                raise PlatformValidationException(
                    platform="GitHub",
                    details=f"Invalid ISO timestamp format: {e}"
                )
                
            parsed_repos.append(
                ParsedGitHubRepo(
                    github_id=repo_schema.id,
                    name=repo_schema.name,
                    full_name=repo_schema.full_name,
                    description=repo_schema.description,
                    html_url=repo_schema.html_url,
                    language=repo_schema.language,
                    stargazers_count=repo_schema.stargazers_count,
                    forks_count=repo_schema.forks_count,
                    open_issues_count=repo_schema.open_issues_count,
                    size=repo_schema.size,
                    created_at=created_at,
                    updated_at=updated_at,
                    pushed_at=pushed_at,
                    is_fork=repo_schema.fork,
                    is_private=repo_schema.private,
                    is_archived=repo_schema.archived,
                )
            )
            
        return ParsedGitHubData(
            login=profile_schema.login,
            avatar_url=profile_schema.avatar_url,
            bio=profile_schema.bio,
            repositories_count=len(parsed_repos),
            total_stars=total_stars,
            total_forks=total_forks,
            total_size=total_size,
            total_open_issues=total_open_issues,
            languages=languages,
            repositories=parsed_repos,
        )
