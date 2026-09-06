"""
Pydantic schemas for the Recommendation Engine output.

RecommendationCandidateSchema is the structured output produced by the rule engine
and consumed by Task 11.3 (the Recommendation Orchestrator Service) for persistence.

Design notes:
- Recommendations are identified by a stable rule_id string (e.g., "LC-DIFF-001").
  This allows de-duplication and versioning in the orchestrator layer.
- priority is one of "HIGH", "MEDIUM", "LOW" — strings rather than an Enum to
  follow the existing project convention (InsightTriggerSchema uses plain strings
  for change_type / platform).
- evidence is a free-form dict for machine-readable context about why the rule fired
  (threshold values, actual values, etc.). This supports debugging and audit trails.
- Neither database IDs nor user_id are included here; this schema represents a
  pre-persistence candidate. The orchestrator (Task 11.3) will attach user_id and
  persist records into the recommendations table.
"""

from typing import Any
from pydantic import BaseModel


class RecommendationCandidateSchema(BaseModel):
    """
    A single actionable recommendation produced by the rule engine.

    One rule evaluation may produce zero or one candidate.
    The orchestrator collects all candidates across all rules, de-duplicates
    by rule_id, and persists the result.
    """

    # Stable identifier for the rule that produced this recommendation.
    # Format: <CATEGORY_PREFIX>-<SEQUENCE> (e.g., "LC-DIFF-001", "GH-CONS-001").
    # Used by the orchestrator for idempotent upsert / de-duplication.
    rule_id: str

    # Semantic version of the rule logic. Increment when thresholds change.
    rule_version: str

    # Broad category grouping (e.g., "leetcode_difficulty", "github_consistency").
    category: str

    # Priority used by the orchestrator and frontend to rank recommendations.
    # One of: "HIGH", "MEDIUM", "LOW"
    priority: str

    # Short, action-oriented headline shown in the dashboard.
    title: str

    # Full human-readable recommendation message.
    message: str

    # Machine-readable evidence: actual metric values, thresholds, etc.
    # Allows debugging and powers future adaptive thresholds.
    evidence: dict[str, Any]
