from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field


class UserSyncSummary(BaseModel):
    """Execution summary for an individual user synchronization run."""

    user_id: UUID
    success: bool
    github_synced: bool = False
    leetcode_synced: bool = False
    score_calculated: bool = False
    insights_generated: int = 0
    recommendations_run: bool = False
    milestones_evaluated: bool = False
    errors: list[str] = Field(default_factory=list)


class BatchSyncSummary(BaseModel):
    """Execution summary for a batch synchronization run across all eligible users."""

    total_users: int = 0
    successful_users: int = 0
    failed_users: int = 0
    skipped_users: int = 0
    user_summaries: list[UserSyncSummary] = Field(default_factory=list)
