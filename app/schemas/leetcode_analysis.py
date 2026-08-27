from datetime import date
from uuid import UUID
from pydantic import BaseModel

class LeetCodeProblemStatsSchema(BaseModel):
    easy_solved: int
    medium_solved: int
    hard_solved: int
    total_solved: int
    easy_submissions: int
    medium_submissions: int
    hard_submissions: int
    total_submissions: int

class TopicSummarySchema(BaseModel):
    tag_name: str
    tag_slug: str
    solved_count: int
    difficulty_level: str

class LeetCodeAnalysisResultSchema(BaseModel):
    user_id: UUID
    username: str
    
    # Snapshot-derived metrics
    problem_stats: LeetCodeProblemStatsSchema
    most_practiced_topics: list[TopicSummarySchema]
    
    # History-derived growth metrics
    problems_solved_growth: int | None = None
    easy_solved_growth: int | None = None
    medium_solved_growth: int | None = None
    hard_solved_growth: int | None = None
    submissions_growth: int | None = None
    
    # Observed transition metrics
    problems_solved_frequency_per_day: float | None = None
    active_days_count: int | None = None
    contribution_consistency: float | None = None
    
    # Streak metrics
    current_streak: int | None = None
    longest_streak: int | None = None
