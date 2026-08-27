from datetime import date
from uuid import UUID
from pydantic import BaseModel

class RepositoryStatsSchema(BaseModel):
    total_repositories: int
    total_stars: int
    total_forks: int
    total_size: int  # KB
    total_open_issues: int

class RepoSummarySchema(BaseModel):
    name: str
    full_name: str
    stars: int
    forks: int
    language: str | None = None
    pushed_at: date | None = None

class GitHubAnalysisResultSchema(BaseModel):
    user_id: UUID
    login: str
    
    # Snapshot-derived metrics
    repo_stats: RepositoryStatsSchema
    most_starred_repos: list[RepoSummarySchema]
    recently_updated_repositories: list[RepoSummarySchema]
    language_distribution: dict[str, int]
    
    # History-derived metrics
    repository_growth: int | None = None
    star_growth: int | None = None
    fork_growth: int | None = None
    total_commits: int | None = None
    commit_frequency_per_day: float | None = None
    active_days_count: int | None = None
    contribution_consistency: float | None = None
    current_streak: int | None = None
    longest_streak: int | None = None
