"""
Recommendation Orchestrator Service — Task 11.3

This module provides RecommendationService, which orchestrates the full
recommendation generation pipeline for a single user:

    1. Passes current analytics/score data to RecommendationEvaluator.
    2. Receives a list of RecommendationCandidateSchema objects.
    3. For each candidate, decides whether to INSERT, SKIP, or UPDATE
       an existing recommendation record.
    4. Resolves stale active recommendations whose rule no longer fires.
    5. Persists changes through RecommendationRepository.
    6. Returns a structured RecommendationRunResultSchema.

Idempotency contract
--------------------
The UNIQUE(user_id, rule_id, rule_version) DB constraint ensures that at most
one row per user per rule version ever exists. The orchestrator respects this:

  Rule fires | Existing row | Existing status | Action
  -----------+--------------+-----------------+-----------------------------
  Yes        | No           | —               | INSERT new active record
  Yes        | Yes          | active          | SKIP (already actionable)
  Yes        | Yes          | dismissed       | SKIP (user dismissed — respect choice)
  Yes        | Yes          | completed       | SKIP (user completed — respect choice)
  No         | Yes          | active          | UPDATE to completed (resolved)
  No         | Yes          | dismissed/cmplt | SKIP (terminal state, no action)

Stale recommendation resolution
---------------------------------
When a rule no longer fires AND an existing active recommendation exists,
the orchestrator updates the status to "completed". This signals that the
developer's improvement resolved the recommendation — a natural use of the
existing "completed" status that avoids introducing a new status value.

This decision is documented here because it was not explicitly specified
in DATABASE_DESIGN.md, and has a small impact on user-facing state.

Data availability
-----------------
None inputs for github_analysis, leetcode_analysis, or score_result are passed
through directly to RecommendationEvaluator without substitution. The rule
engine already handles None correctly — missing data never generates false
recommendations.
"""

import logging
from uuid import UUID

from app.models.recommendation import Recommendation
from app.repositories.recommendation import RecommendationRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.recommendation_result import RecommendationRunResultSchema
from app.schemas.recommendations import RecommendationCandidateSchema
from app.schemas.score import DeveloperScoreResultSchema
from app.services.recommendations.rules import RecommendationEvaluator

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Orchestrates the recommendation pipeline for a single user.

    This service coordinates three already-existing components:
      - RecommendationEvaluator (pure rule engine, Task 11.1)
      - RecommendationRepository (DB persistence, Task 11.2)
      - Recommendation ORM model (Task 11.2)

    It is deliberately free of:
      - Individual recommendation conditions (those live in rules.py)
      - Direct SQL execution (that belongs in the repository)
      - HTTP/API calls (those belong in platform clients)
      - FastAPI route logic
    """

    def __init__(self, recommendation_repo: RecommendationRepository) -> None:
        self.recommendation_repo = recommendation_repo

    async def generate_and_persist(
        self,
        user_id: UUID,
        github_analysis: GitHubAnalysisResultSchema | None,
        leetcode_analysis: LeetCodeAnalysisResultSchema | None,
        score_result: DeveloperScoreResultSchema | None,
    ) -> RecommendationRunResultSchema:
        """
        Run the recommendation rule engine and persist results for a user.

        This method is safe to call repeatedly with the same input data —
        subsequent calls will produce the same logical result without
        creating duplicate database records.

        Parameters
        ----------
        user_id : UUID
            The user to generate recommendations for.
        github_analysis : GitHubAnalysisResultSchema | None
            Latest computed GitHub analytics, or None if unavailable.
        leetcode_analysis : LeetCodeAnalysisResultSchema | None
            Latest computed LeetCode analytics, or None if unavailable.
        score_result : DeveloperScoreResultSchema | None
            Latest computed Developer Score, or None if unavailable.

        Returns
        -------
        RecommendationRunResultSchema
            A structured summary of what was created, skipped, and resolved.
        """
        # --- 1. Run the pure rule engine ---
        candidates: list[RecommendationCandidateSchema] = RecommendationEvaluator.evaluate(
            github_analysis=github_analysis,
            leetcode_analysis=leetcode_analysis,
            score_result=score_result,
        )

        logger.info(
            "RecommendationService: %d candidate(s) from rule engine for user_id=%s.",
            len(candidates),
            user_id,
        )

        # Build a set of rule IDs that fired this run — used for stale detection
        fired_rule_ids: set[str] = {c.rule_id for c in candidates}

        # --- 2. Process each candidate: INSERT or SKIP ---
        new_recommendations: list[RecommendationCandidateSchema] = []
        skipped_count = 0

        for candidate in candidates:
            existing = await self.recommendation_repo.get_by_rule_key(
                user_id=user_id,
                rule_id=candidate.rule_id,
                rule_version=candidate.rule_version,
            )

            if existing is not None:
                # A row already exists for this (user, rule_id, rule_version).
                # Regardless of its current status, we respect it — no duplicate insert.
                logger.debug(
                    "Skipping candidate rule_id=%s (existing record status=%s).",
                    candidate.rule_id,
                    existing.status,
                )
                skipped_count += 1
                continue

            # No existing record — insert a new active recommendation
            record = Recommendation(
                user_id=user_id,
                rule_id=candidate.rule_id,
                rule_version=candidate.rule_version,
                category=candidate.category,
                priority=candidate.priority,
                title=candidate.title,
                message=candidate.message,
                status="active",
                evidence=candidate.evidence if candidate.evidence else None,
            )
            await self.recommendation_repo.create(record)
            new_recommendations.append(candidate)

            logger.info(
                "Created new recommendation rule_id=%s priority=%s for user_id=%s.",
                candidate.rule_id,
                candidate.priority,
                user_id,
            )

        # --- 3. Resolve stale active recommendations ---
        # Active recommendations whose rule no longer fires indicate the
        # developer has resolved the underlying issue. Mark them completed.
        resolved_rule_ids: list[str] = []
        active_existing = await self.recommendation_repo.get_active_by_user(user_id)

        for active_rec in active_existing:
            if active_rec.rule_id not in fired_rule_ids:
                await self.recommendation_repo.update_status(active_rec, "completed")
                resolved_rule_ids.append(active_rec.rule_id)
                logger.info(
                    "Resolved stale recommendation rule_id=%s for user_id=%s.",
                    active_rec.rule_id,
                    user_id,
                )

        result = RecommendationRunResultSchema(
            user_id=user_id,
            total_candidates=len(candidates),
            new=len(new_recommendations),
            skipped=skipped_count,
            resolved=len(resolved_rule_ids),
            new_recommendations=new_recommendations,
            resolved_rule_ids=resolved_rule_ids,
        )

        logger.info(
            "RecommendationService complete for user_id=%s: "
            "candidates=%d new=%d skipped=%d resolved=%d.",
            user_id,
            result.total_candidates,
            result.new,
            result.skipped,
            result.resolved,
        )

        return result

    async def get_active_recommendations(
        self,
        user_id: UUID,
    ) -> list[Recommendation]:
        """Return all currently active recommendations for a user."""
        return await self.recommendation_repo.get_active_by_user(user_id)

    async def get_all_recommendations(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[Recommendation]:
        """Return all recommendations for a user (any status), newest-first."""
        return await self.recommendation_repo.get_all_by_user(user_id, limit=limit)
