"""
Dashboard Historical Charts Service — Task 12.2

Orchestrates historical data retrieval for frontend chart components
(API_SPECIFICATION.md Section 4.2).

Responsibilities:
1. Query daily historical records from GitHubHistoryRepository and LeetCodeHistoryRepository.
2. Filter within the requested interval (e.g. past N days up to today UTC).
3. Merge records across both platforms by date into chronologically ordered chart points.
4. Format output into DashboardChartsResponse without mutating records or calculating new statistics.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.schemas.dashboard import DashboardChartPointSchema, DashboardChartsResponse

logger = logging.getLogger(__name__)


class DashboardChartService:
    """
    Read-only service that compiles historical time-series data for developer charts.

    Repositories are injected at instantiation to maintain testability and
    separation of concerns.
    """

    def __init__(
        self,
        github_history_repo: GitHubHistoryRepository,
        leetcode_history_repo: LeetCodeHistoryRepository,
    ) -> None:
        self.github_history_repo = github_history_repo
        self.leetcode_history_repo = leetcode_history_repo

    async def get_historical_charts(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> DashboardChartsResponse:
        """
        Retrieve chronological daily metrics for GitHub commits and LeetCode problems solved.

        :param user_id: Authenticated user UUID.
        :param days: Lookback window in calendar days (1-365).
        :return: DashboardChartsResponse with sorted daily points.
        """
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)

        logger.debug(
            "Querying historical charts for user_id=%s, days=%d, start_date=%s, end_date=%s",
            user_id,
            days,
            start_date,
            end_date,
        )

        gh_records: list[GitHubHistory] = await self.github_history_repo.get_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        lc_records: list[LeetCodeHistory] = await self.leetcode_history_repo.get_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Merge records by date preserving nullability when a platform has no entry
        date_map: dict[datetime.date, dict[str, int | None]] = {}

        for gh in gh_records:
            if gh.date not in date_map:
                date_map[gh.date] = {"commits": None, "problems_solved": None}
            date_map[gh.date]["commits"] = gh.commits

        for lc in lc_records:
            if lc.date not in date_map:
                date_map[lc.date] = {"commits": None, "problems_solved": None}
            date_map[lc.date]["problems_solved"] = lc.problems_solved

        # Assemble sorted chronological data points
        sorted_dates = sorted(date_map.keys())
        history: list[DashboardChartPointSchema] = [
            DashboardChartPointSchema(
                date=d,
                commits=date_map[d]["commits"],
                problems_solved=date_map[d]["problems_solved"],
            )
            for d in sorted_dates
        ]

        logger.info(
            "Historical charts assembled for user_id=%s: %d total data points over %d days",
            user_id,
            len(history),
            days,
        )

        return DashboardChartsResponse(
            interval_days=days,
            history=history,
        )
