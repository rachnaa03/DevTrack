from datetime import date
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class InsightTriggerSchema(BaseModel):
    metric_name: str       # e.g., "github_commits", "leetcode_solved", "github_consistency", "leetcode_consistency", "leetcode_difficulty", "github_streak", "leetcode_streak", "score_overall", "score_consistency", "score_problem_solving", "score_open_source"
    platform: str          # "github", "leetcode", or "system"
    change_type: str       # "increase", "decrease", "broken"
    current_value: float
    historical_value: float
    percent_change: float | None = None
    absolute_change: float
    metadata: dict[str, Any] = Field(default_factory=dict)

class DeveloperComparisonResultSchema(BaseModel):
    user_id: UUID
    current_date: date
    historical_date: date
    triggers: list[InsightTriggerSchema]
