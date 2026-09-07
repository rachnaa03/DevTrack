"""
Weekly Summary Aggregation Service — Task 14.2

Orchestrates weekly retrospective report generation for users.
Aggregates activity metrics from GitHub, LeetCode, and Developer Scores over a Monday-Sunday week,
generates deterministic qualitative summaries, and idempotently persists reports.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from app.models.weekly_report import WeeklyReport
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.weekly_report import WeeklyReportRepository
from app.schemas.reports import WeeklyReportDataSchema, WeeklySubscoresSchema

logger = logging.getLogger(__name__)


class WeeklyReportService:
    """
    Service responsible for calculating and persisting weekly retrospective reports.
    """

    def __init__(
        self,
        weekly_report_repo: WeeklyReportRepository,
        github_history_repo: GitHubHistoryRepository,
        leetcode_history_repo: LeetCodeHistoryRepository,
        score_repo: DeveloperScoreRepository,
        leetcode_analytics_repo: LeetCodeAnalyticsRepository | None = None,
    ) -> None:
        self.weekly_report_repo = weekly_report_repo
        self.github_history_repo = github_history_repo
        self.leetcode_history_repo = leetcode_history_repo
        self.score_repo = score_repo
        self.leetcode_analytics_repo = leetcode_analytics_repo

    def resolve_week_bounds(self, week_start: date | None = None) -> tuple[date, date]:
        """
        Resolve the Monday-Sunday date boundary for the weekly report.
        If week_start is None, defaults to the most recent completed week (last Monday to last Sunday).
        If week_start is provided, aligns it to Monday and calculates the corresponding Sunday.
        """
        if week_start is None:
            today = datetime.now(timezone.utc).date()
            current_monday = today - timedelta(days=today.weekday())
            resolved_start = current_monday - timedelta(days=7)
        else:
            resolved_start = week_start - timedelta(days=week_start.weekday())

        resolved_end = resolved_start + timedelta(days=6)
        return resolved_start, resolved_end

    async def _calculate_github_commits(
        self,
        user_id: UUID,
        week_start: date,
        week_end: date,
    ) -> int:
        """
        Calculate total GitHub commits across the week.
        GitHubHistory.commits stores daily counts, so we sum records within [week_start, week_end].
        """
        gh_records = await self.github_history_repo.get_history(
            user_id=user_id,
            start_date=week_start,
            end_date=week_end,
        )
        return sum(r.commits for r in gh_records)

    async def _calculate_leetcode_problems_solved(
        self,
        user_id: UUID,
        week_start: date,
        week_end: date,
    ) -> int:
        """
        Calculate total LeetCode problems solved during the week.
        LeetCodeHistory.problems_solved is cumulative, so we compare the latest record
        up to week_end with the baseline record prior to week_start (or earliest in week).
        """
        lc_records = await self.leetcode_history_repo.get_history(
            user_id=user_id,
            end_date=week_end,
        )
        records_up_to_end = [r for r in lc_records if r.date <= week_end]
        if not records_up_to_end:
            return 0

        rec_end = records_up_to_end[-1]
        baseline_records = [r for r in records_up_to_end if r.date < week_start]

        if baseline_records:
            rec_baseline = baseline_records[-1]
            return max(0, rec_end.problems_solved - rec_baseline.problems_solved)

        # If no baseline exists prior to the week, check records within the week
        week_records = [r for r in records_up_to_end if week_start <= r.date <= week_end]
        if len(week_records) >= 2:
            return max(0, rec_end.problems_solved - week_records[0].problems_solved)

        return 0

    async def _calculate_score_delta_and_subscores(
        self,
        user_id: UUID,
        week_start: date,
        week_end: date,
    ) -> tuple[int, WeeklySubscoresSchema]:
        """
        Calculate the Developer Score delta and end-of-week subscores.
        Maps problem_solving_score to depth and open_source_score to impact.
        """
        start_dt = datetime.combine(week_start, time.min, tzinfo=timezone.utc)
        baseline_dt = start_dt - timedelta(microseconds=1)
        end_dt = datetime.combine(week_end, time.max, tzinfo=timezone.utc)

        score_end = await self.score_repo.get_latest_before(user_id, end_dt)
        score_baseline = await self.score_repo.get_latest_before(user_id, baseline_dt)

        if score_end is None:
            return 0, WeeklySubscoresSchema(consistency=0, depth=0, impact=0)

        subscores = WeeklySubscoresSchema(
            consistency=score_end.consistency_score,
            depth=score_end.problem_solving_score,
            impact=score_end.open_source_score,
        )

        if score_baseline is not None:
            score_delta = score_end.overall_score - score_baseline.overall_score
        else:
            week_scores = await self.score_repo.get_scores_by_date_range(user_id, start_dt, end_dt)
            if len(week_scores) >= 2:
                score_delta = week_scores[-1].overall_score - week_scores[0].overall_score
            else:
                score_delta = 0

        return score_delta, subscores

    def _determine_weak_topics(self) -> list[str]:
        """
        Determine weak topics for the weekly report.
        Defaults to an empty list as no explicit topic weakness classification rule exists.
        """
        return []

    def _generate_summary_text(
        self,
        commits_count: int,
        problems_solved: int,
        score_delta: int,
        week_start: date,
        week_end: date,
    ) -> str:
        """
        Generate a deterministic summary text for the retrospective report.
        """
        if commits_count == 0 and problems_solved == 0 and score_delta == 0:
            return f"No platform activity was recorded for the week of {week_start} to {week_end}."

        delta_sign = f"+{score_delta}" if score_delta > 0 else f"{score_delta}"
        return (
            f"Weekly retrospective for {week_start} to {week_end}: "
            f"{commits_count} commits pushed, {problems_solved} problems solved, "
            f"Developer Score changed by {delta_sign}."
        )

    async def generate_weekly_report(
        self,
        user_id: UUID,
        week_start: date | None = None,
    ) -> WeeklyReport:
        """
        Generate and persist an aggregated weekly retrospective report for a user.

        :param user_id: UUID of the user.
        :param week_start: Optional starting date of the week (will align to Monday).
        :return: Persisted WeeklyReport instance.
        """
        resolved_start, resolved_end = self.resolve_week_bounds(week_start)

        logger.info(
            "Generating weekly report for user_id=%s, week_start=%s, week_end=%s",
            user_id,
            resolved_start,
            resolved_end,
        )

        # 1. Aggregate metrics from repositories
        commits_count = await self._calculate_github_commits(user_id, resolved_start, resolved_end)
        problems_solved = await self._calculate_leetcode_problems_solved(user_id, resolved_start, resolved_end)
        score_delta, subscores = await self._calculate_score_delta_and_subscores(
            user_id, resolved_start, resolved_end
        )
        weak_topics = self._determine_weak_topics()

        # 2. Build deterministic summary
        summary_text = self._generate_summary_text(
            commits_count=commits_count,
            problems_solved=problems_solved,
            score_delta=score_delta,
            week_start=resolved_start,
            week_end=resolved_end,
        )

        # 3. Assemble validated report_data payload
        report_data_schema = WeeklyReportDataSchema(
            commits_count=commits_count,
            problems_solved=problems_solved,
            score_delta=score_delta,
            summary=summary_text,
            weekly_subscores=subscores,
            weak_topics=weak_topics,
        )
        report_data_payload: dict[str, Any] = report_data_schema.model_dump(mode="json")

        # 4. Idempotently persist report
        persisted_report = await self.weekly_report_repo.create_or_update(
            user_id=user_id,
            week_start=resolved_start,
            week_end=resolved_end,
            report_data=report_data_payload,
        )

        logger.info(
            "Weekly report successfully persisted for user_id=%s, week_start=%s (report_id=%s)",
            user_id,
            resolved_start,
            persisted_report.id,
        )

        return persisted_report
