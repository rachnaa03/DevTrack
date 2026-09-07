from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SyncJobSchema(BaseModel):
    """Schema representing an individual synchronization job execution."""

    id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "success", "partial_failure", "failed"]
    total_users: int = 0
    successful_users: int = 0
    failed_users: int = 0
    skipped_users: int = 0
    error_summary: str | None = None
    duration_seconds: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SyncStatusResponse(BaseModel):
    """Schema for authenticated sync status endpoint."""

    is_running: bool = Field(..., description="Whether a synchronization is currently executing.")
    scheduler_running: bool = Field(..., description="Whether APScheduler is currently active.")
    latest_job: SyncJobSchema | None = Field(default=None, description="The most recent sync job.")


class SyncHealthResponse(BaseModel):
    """Schema for public sync health endpoint."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall sync system health state."
    )
    scheduler_status: Literal["running", "stopped"] = Field(
        ..., description="Current APScheduler operational state."
    )
    last_sync_status: Literal["success", "partial_failure", "failed", "running", "never_run"] = Field(
        ..., description="Execution status of the most recent sync job."
    )
    last_sync_timestamp: datetime | None = Field(
        default=None, description="Start timestamp of the most recent sync job."
    )
