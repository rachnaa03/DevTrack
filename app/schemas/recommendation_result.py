"""
Pydantic schema for the Recommendation Orchestrator's structured result.

Returned by RecommendationService.generate_and_persist() so that callers
(background jobs, API routes) can report what happened without parsing
database records directly.
"""

from uuid import UUID
from pydantic import BaseModel

from app.schemas.recommendations import RecommendationCandidateSchema


class RecommendationRunResultSchema(BaseModel):
    """
    Summary of one recommendation generation run for a single user.

    counts:
      new             — recommendations inserted (status=active)
      skipped         — candidates that matched an existing row and were left unchanged
      resolved        — previously-active recommendations whose rule no longer fired,
                        now marked completed
      total_candidates — number of candidates produced by the rule engine

    new_recommendations — the full candidate schemas for newly created records,
                          useful for logging and API responses.
    resolved_rule_ids   — rule IDs that were auto-completed due to condition resolution.
    """

    user_id: UUID

    # Counts
    total_candidates: int
    new: int
    skipped: int
    resolved: int

    # Detail
    new_recommendations: list[RecommendationCandidateSchema]
    resolved_rule_ids: list[str]
