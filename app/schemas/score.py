from pydantic import BaseModel

class ScoreSubcomponentSchema(BaseModel):
    github_consistency_raw: float | None = None
    leetcode_consistency_raw: float | None = None
    easy_points: float | None = None
    medium_points: float | None = None
    hard_points: float | None = None
    repo_volume_points: float | None = None
    commit_depth_points: float | None = None
    stars_points: float | None = None
    forks_points: float | None = None

class DeveloperScoreResultSchema(BaseModel):
    overall_score: int
    consistency_score: int
    problem_solving_score: int
    open_source_score: int
    score_version: str = "v1"
    subcomponents: ScoreSubcomponentSchema
