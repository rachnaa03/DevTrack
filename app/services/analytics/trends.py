from datetime import date
from uuid import UUID
from typing import Any

from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory
from app.schemas.trends import MetricTrendResult, PlatformTrendSummary
from app.utils.exceptions import InvalidMetricException

class TrendQueryEngine:
    """Service layer coordinating historical query range retrievals and platform trend calculations."""

    def __init__(
        self,
        github_history_repo: GitHubHistoryRepository,
        leetcode_history_repo: LeetCodeHistoryRepository
    ):
        self.github_history_repo = github_history_repo
        self.leetcode_history_repo = leetcode_history_repo

        self._allowed_github_metrics = {"commits", "stars", "forks", "repositories"}
        self._allowed_leetcode_metrics = {
            "problems_solved",
            "easy_solved",
            "medium_solved",
            "hard_solved",
            "submissions"
        }

    async def get_github_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[GitHubHistory]:
        """
        Retrieve chronological history for a user, optionally filtered by date range.
        Delegates database queries to GitHubHistoryRepository.
        """
        return await self.github_history_repo.get_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

    async def get_leetcode_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[LeetCodeHistory]:
        """
        Retrieve chronological history for a user, optionally filtered by date range.
        Delegates database queries to LeetCodeHistoryRepository.
        """
        return await self.leetcode_history_repo.get_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

    async def calculate_github_trends(
        self,
        user_id: UUID,
        metrics: list[str] | None = None
    ) -> PlatformTrendSummary:
        """
        Calculate trend deltas and directions for requested or all GitHub history metrics.
        """
        target_metrics = list(self._allowed_github_metrics) if metrics is None else metrics
        self._validate_metrics(target_metrics, self._allowed_github_metrics, "GitHub")

        records = await self.github_history_repo.get_recent_by_user_id(user_id, limit=2)
        trends: dict[str, MetricTrendResult] = {}

        if len(records) == 0:
            return PlatformTrendSummary(platform="github", user_id=user_id, trends={})

        latest_record = records[0]
        has_previous = len(records) > 1
        previous_record = records[1] if has_previous else None

        for metric in target_metrics:
            latest_val = int(getattr(latest_record, metric))
            prev_val = int(getattr(previous_record, metric)) if previous_record is not None else None
            
            if prev_val is not None:
                change = latest_val - prev_val
                if change > 0:
                    direction = "up"
                elif change < 0:
                    direction = "down"
                else:
                    direction = "unchanged"
            else:
                change = None
                direction = "insufficient_data"

            trends[metric] = MetricTrendResult(
                metric_name=metric,
                latest_value=latest_val,
                previous_value=prev_val,
                absolute_change=change,
                direction=direction,
                latest_date=latest_record.date,
                previous_date=previous_record.date if previous_record is not None else None
            )

        return PlatformTrendSummary(platform="github", user_id=user_id, trends=trends)

    async def calculate_leetcode_trends(
        self,
        user_id: UUID,
        metrics: list[str] | None = None
    ) -> PlatformTrendSummary:
        """
        Calculate trend deltas and directions for requested or all LeetCode history metrics.
        """
        target_metrics = list(self._allowed_leetcode_metrics) if metrics is None else metrics
        self._validate_metrics(target_metrics, self._allowed_leetcode_metrics, "LeetCode")

        records = await self.leetcode_history_repo.get_recent_by_user_id(user_id, limit=2)
        trends: dict[str, MetricTrendResult] = {}

        if len(records) == 0:
            return PlatformTrendSummary(platform="leetcode", user_id=user_id, trends={})

        latest_record = records[0]
        has_previous = len(records) > 1
        previous_record = records[1] if has_previous else None

        for metric in target_metrics:
            latest_val = int(getattr(latest_record, metric))
            prev_val = int(getattr(previous_record, metric)) if previous_record is not None else None
            
            if prev_val is not None:
                change = latest_val - prev_val
                if change > 0:
                    direction = "up"
                elif change < 0:
                    direction = "down"
                else:
                    direction = "unchanged"
            else:
                change = None
                direction = "insufficient_data"

            trends[metric] = MetricTrendResult(
                metric_name=metric,
                latest_value=latest_val,
                previous_value=prev_val,
                absolute_change=change,
                direction=direction,
                latest_date=latest_record.date,
                previous_date=previous_record.date if previous_record is not None else None
            )

        return PlatformTrendSummary(platform="leetcode", user_id=user_id, trends=trends)

    def _validate_metrics(self, requested: list[str], allowed: set[str], platform: str) -> None:
        """Validate that all requested metrics are supported for the given platform."""
        for metric in requested:
            if metric not in allowed:
                raise InvalidMetricException(platform=platform, metric=metric)
