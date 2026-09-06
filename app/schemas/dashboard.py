"""
Pydantic response schemas for the Dashboard API (Task 12.1).

These schemas define the public response contracts for dashboard endpoints.
They deliberately separate the API response shape from the internal ORM models.

Mapping notes
-------------
The API specification (API_SPECIFICATION.md, Section 4.1) uses:
  - "depth"  → maps to DeveloperScore.problem_solving_score internally
  - "impact" → maps to DeveloperScore.open_source_score internally

This mapping keeps the API spec language (depth/impact, which is
user-meaningful) separate from the internal implementation detail
(problem_solving_score / open_source_score).

All nullable fields represent unavailable data — they are never silently
converted to zero. Callers should interpret None as "data not yet available".
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Developer Score block
# ---------------------------------------------------------------------------

class DashboardScoreSchema(BaseModel):
    """
    The current Developer Score for the dashboard header.

    Scores use the same scale as the scoring engine:
      overall_score ∈ [0, 1000]
      consistency   ∈ [0, 250]
      depth         ∈ [0, 375]   (= problem_solving_score internally)
      impact        ∈ [0, 375]   (= open_source_score internally)

    computed_at is the timestamp of the last scoring run — useful for the
    frontend to show "score last updated N minutes ago".
    """

    overall: int
    consistency: int
    depth: int    # problem_solving_score
    impact: int   # open_source_score
    computed_at: datetime


# ---------------------------------------------------------------------------
# GitHub stats block
# ---------------------------------------------------------------------------

class DashboardGitHubStatsSchema(BaseModel):
    """
    Key GitHub statistics for the dashboard stats panel.

    All fields are nullable: if GitHub has not been synced yet, the entire
    block will still be present but with null values — this lets the frontend
    clearly distinguish "platform not connected" from "synced but zero".

    data_as_of: the date of the latest analytics record (not the sync time).
    primary_languages: ordered from most to least used (from the stored JSONB).
    """

    total_commits: int | None
    total_repositories: int | None
    stars_earned: int | None
    current_streak: int | None
    longest_streak: int | None
    contribution_consistency: float | None
    primary_languages: list[str] | None
    data_as_of: date | None


# ---------------------------------------------------------------------------
# LeetCode stats block
# ---------------------------------------------------------------------------

class DashboardLeetCodeStatsSchema(BaseModel):
    """
    Key LeetCode statistics for the dashboard stats panel.

    data_as_of: the date of the latest analytics record.
    """

    total_solved: int | None
    easy_solved: int | None
    medium_solved: int | None
    hard_solved: int | None
    active_streak: int | None
    longest_streak: int | None
    contribution_consistency: float | None
    data_as_of: date | None


# ---------------------------------------------------------------------------
# Combined stats block
# ---------------------------------------------------------------------------

class DashboardStatsSchema(BaseModel):
    """Combined platform stats for the dashboard summary response."""

    github: DashboardGitHubStatsSchema
    leetcode: DashboardLeetCodeStatsSchema


# ---------------------------------------------------------------------------
# Top-level dashboard summary response
# ---------------------------------------------------------------------------

class DashboardSummaryResponse(BaseModel):
    """
    Response schema for GET /api/v1/dashboard/summary.

    This is the primary data contract used by the frontend dashboard header.

    The `developer_score` block is always present when the endpoint returns 200.
    The platform stats blocks are always present but their fields may be null
    when analytics data has not yet been computed for that platform.

    HTTP 404 is returned (not a null score) when no score has ever been
    computed for the user — consistent with API_SPECIFICATION.md Section 4.1.
    """

    developer_score: DashboardScoreSchema
    stats: DashboardStatsSchema


# ---------------------------------------------------------------------------
# Historical Charts block (Task 12.2)
# ---------------------------------------------------------------------------

class DashboardChartPointSchema(BaseModel):
    """
    Single data point in the historical chart series (API_SPECIFICATION.md Section 4.2).

    Represents daily counts for commits and problems solved on a specific date.
    Fields are nullable if a platform has no recorded activity or snapshot on that date.
    """

    date: date
    commits: int | None = None
    problems_solved: int | None = None


class DashboardChartsResponse(BaseModel):
    """
    Response schema for GET /api/v1/dashboard/charts (API_SPECIFICATION.md Section 4.2).

    Provides chronological daily history points for frontend chart rendering.
    """

    interval_days: int
    history: list[DashboardChartPointSchema]

