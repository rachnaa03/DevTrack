"""
Dashboard Summary Service — Task 12.1

Orchestrates the data retrieval required to build the dashboard summary
response for GET /api/v1/dashboard/summary.

Responsibilities
----------------
1. Retrieve the latest DeveloperScore for the user from DeveloperScoreRepository.
   If no score exists, signal 404 to the route handler.
2. Retrieve the latest GitHubAnalytics record (may be None).
3. Retrieve the latest LeetCodeAnalytics record (may be None).
4. Assemble a DashboardSummaryResponse without modifying any data.

This service does NOT:
  - calculate or modify scores
  - call GitHub or LeetCode APIs
  - create or update any records
  - apply any business logic beyond data assembly

Data availability
-----------------
GitHub or LeetCode analytics records may not exist (platform not connected,
or sync not yet run). In those cases the corresponding stats fields are None.
None is never converted to 0 — unavailable data is represented honestly.

Score mapping
-------------
DeveloperScore.problem_solving_score → DashboardScoreSchema.depth
DeveloperScore.open_source_score     → DashboardScoreSchema.impact
(See schemas/dashboard.py for the documented rationale.)
"""

import logging
from uuid import UUID

from app.models.github_analytics import GitHubAnalytics
from app.models.leetcode_analytics import LeetCodeAnalytics
from app.models.score import DeveloperScore
from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.score import DeveloperScoreRepository
from app.schemas.dashboard import (
    DashboardGitHubStatsSchema,
    DashboardLeetCodeStatsSchema,
    DashboardScoreSchema,
    DashboardStatsSchema,
    DashboardSummaryResponse,
)

logger = logging.getLogger(__name__)


class DashboardSummaryService:
    """
    Read-only service that assembles the dashboard summary for a single user.

    All three repositories are injected at construction time, following the
    same pattern used by ProfileService, InsightGenerationService, etc.
    """

    def __init__(
        self,
        score_repo: DeveloperScoreRepository,
        github_repo: GitHubAnalyticsRepository,
        leetcode_repo: LeetCodeAnalyticsRepository,
    ) -> None:
        self.score_repo = score_repo
        self.github_repo = github_repo
        self.leetcode_repo = leetcode_repo

    async def get_summary(self, user_id: UUID) -> DashboardSummaryResponse | None:
        """
        Retrieve and assemble the dashboard summary for a user.

        Returns None if no DeveloperScore has been computed yet.
        The route handler maps None → HTTP 404.

        Returns DashboardSummaryResponse on success. Platform stats sections
        are always present but their fields may be None if analytics data is
        unavailable for that platform.
        """
        # --- 1. Latest Developer Score (required) ---
        score: DeveloperScore | None = await self.score_repo.get_latest_by_user_id(user_id)
        if score is None:
            logger.info(
                "No DeveloperScore found for user_id=%s; returning None for 404.",
                user_id,
            )
            return None

        # --- 2. Latest GitHub analytics (optional) ---
        gh: GitHubAnalytics | None = await self.github_repo.get_latest_by_user_id(user_id)

        # --- 3. Latest LeetCode analytics (optional) ---
        lc: LeetCodeAnalytics | None = await self.leetcode_repo.get_latest_by_user_id(user_id)

        logger.debug(
            "Dashboard summary assembled for user_id=%s: "
            "score=%s github=%s leetcode=%s",
            user_id,
            score.id,
            gh.id if gh else None,
            lc.id if lc else None,
        )

        # --- 4. Build response ---
        return DashboardSummaryResponse(
            developer_score=self._build_score_schema(score),
            stats=DashboardStatsSchema(
                github=self._build_github_stats(gh),
                leetcode=self._build_leetcode_stats(lc),
            ),
        )

    # ------------------------------------------------------------------
    # Private assemblers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_score_schema(score: DeveloperScore) -> DashboardScoreSchema:
        return DashboardScoreSchema(
            overall=score.overall_score,
            consistency=score.consistency_score,
            depth=score.problem_solving_score,   # internal → API spec name
            impact=score.open_source_score,       # internal → API spec name
            computed_at=score.computed_at,
        )

    @staticmethod
    def _build_github_stats(gh: GitHubAnalytics | None) -> DashboardGitHubStatsSchema:
        if gh is None:
            return DashboardGitHubStatsSchema(
                total_commits=None,
                total_repositories=None,
                stars_earned=None,
                current_streak=None,
                longest_streak=None,
                contribution_consistency=None,
                primary_languages=None,
                data_as_of=None,
            )

        # Extract top 5 languages by usage percentage from the JSONB dict.
        # Languages are stored as {"Python": 72.5, "TypeScript": 27.5}.
        primary_languages: list[str] | None = None
        if gh.languages is not None:
            try:
                sorted_langs = sorted(
                    gh.languages.items(), key=lambda kv: kv[1], reverse=True
                )
                primary_languages = [lang for lang, _ in sorted_langs[:5]]
            except (AttributeError, TypeError):
                primary_languages = None

        return DashboardGitHubStatsSchema(
            total_commits=gh.total_commits,
            total_repositories=gh.total_repositories,
            stars_earned=gh.total_stars,
            current_streak=gh.current_streak,
            longest_streak=gh.longest_streak,
            contribution_consistency=gh.contribution_consistency,
            primary_languages=primary_languages,
            data_as_of=gh.date,
        )

    @staticmethod
    def _build_leetcode_stats(lc: LeetCodeAnalytics | None) -> DashboardLeetCodeStatsSchema:
        if lc is None:
            return DashboardLeetCodeStatsSchema(
                total_solved=None,
                easy_solved=None,
                medium_solved=None,
                hard_solved=None,
                active_streak=None,
                longest_streak=None,
                contribution_consistency=None,
                data_as_of=None,
            )

        return DashboardLeetCodeStatsSchema(
            total_solved=lc.total_solved,
            easy_solved=lc.easy_solved,
            medium_solved=lc.medium_solved,
            hard_solved=lc.hard_solved,
            active_streak=lc.current_streak,
            longest_streak=lc.longest_streak,
            contribution_consistency=lc.contribution_consistency,
            data_as_of=lc.date,
        )
