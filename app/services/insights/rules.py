from datetime import date
from uuid import UUID

from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.score import DeveloperScoreResultSchema
from app.schemas.insights import DeveloperComparisonResultSchema, InsightTriggerSchema

# Centralized Business Thresholds
GITHUB_COMMIT_ABSOLUTE_THRESHOLD = 10
GITHUB_COMMIT_PERCENT_THRESHOLD = 20.0
CONSISTENCY_CHANGE_THRESHOLD = 0.15
LEETCODE_SOLVED_ABSOLUTE_THRESHOLD = 5
LEETCODE_SOLVED_PERCENT_THRESHOLD = 15.0
DIFFICULTY_RATIO_CHANGE_THRESHOLD = 0.08
OVERALL_SCORE_CHANGE_THRESHOLD = 50
CATEGORY_SCORE_CHANGE_THRESHOLD = 25
STREAK_BREAK_MINIMUM = 5
STREAK_SURGE_THRESHOLD = 5

class AnalyticsComparator:
    """Pure business logic comparator for identifying developer progress trends over time."""

    @staticmethod
    def compare(
        user_id: UUID,
        current_gh: GitHubAnalysisResultSchema | None,
        historical_gh: GitHubAnalysisResultSchema | None,
        current_lc: LeetCodeAnalysisResultSchema | None,
        historical_lc: LeetCodeAnalysisResultSchema | None,
        current_score: DeveloperScoreResultSchema | None,
        historical_score: DeveloperScoreResultSchema | None,
        current_date: date,
        historical_date: date
    ) -> DeveloperComparisonResultSchema:
        """
        Evaluate changes between current metrics and historical reference metrics.
        Returns a structured schema holding comparison triggers.
        """
        triggers: list[InsightTriggerSchema] = []

        # --- 1. GitHub Comparisons ---
        if current_gh is not None and historical_gh is not None:
            # Commit Volume
            curr_commits = current_gh.total_commits
            hist_commits = historical_gh.total_commits
            if curr_commits is not None and hist_commits is not None:
                diff = curr_commits - hist_commits
                abs_change = float(abs(diff))
                if hist_commits == 0:
                    if curr_commits >= GITHUB_COMMIT_ABSOLUTE_THRESHOLD:
                        triggers.append(InsightTriggerSchema(
                            metric_name="github_commits",
                            platform="github",
                            change_type="increase",
                            current_value=float(curr_commits),
                            historical_value=float(hist_commits),
                            percent_change=None,
                            absolute_change=abs_change,
                            metadata={"baseline_zero": True}
                        ))
                else:
                    pct = (diff / hist_commits) * 100.0
                    if abs_change >= GITHUB_COMMIT_ABSOLUTE_THRESHOLD:
                        if pct >= GITHUB_COMMIT_PERCENT_THRESHOLD:
                            triggers.append(InsightTriggerSchema(
                                metric_name="github_commits",
                                platform="github",
                                change_type="increase",
                                current_value=float(curr_commits),
                                historical_value=float(hist_commits),
                                percent_change=pct,
                                absolute_change=abs_change
                            ))
                        elif pct <= -GITHUB_COMMIT_PERCENT_THRESHOLD:
                            triggers.append(InsightTriggerSchema(
                                metric_name="github_commits",
                                platform="github",
                                change_type="decrease",
                                current_value=float(curr_commits),
                                historical_value=float(hist_commits),
                                percent_change=pct,
                                absolute_change=abs_change
                            ))

            # GitHub Consistency
            curr_cons = current_gh.contribution_consistency
            hist_cons = historical_gh.contribution_consistency
            if curr_cons is not None and hist_cons is not None:
                diff = curr_cons - hist_cons
                if diff >= CONSISTENCY_CHANGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="github_consistency",
                        platform="github",
                        change_type="increase",
                        current_value=float(curr_cons),
                        historical_value=float(hist_cons),
                        absolute_change=float(abs(diff))
                    ))
                elif diff <= -CONSISTENCY_CHANGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="github_consistency",
                        platform="github",
                        change_type="decrease",
                        current_value=float(curr_cons),
                        historical_value=float(hist_cons),
                        absolute_change=float(abs(diff))
                    ))

            # GitHub Streak
            curr_streak = current_gh.current_streak
            hist_streak = historical_gh.current_streak
            if curr_streak is not None and hist_streak is not None:
                if hist_streak >= STREAK_BREAK_MINIMUM and curr_streak == 0:
                    triggers.append(InsightTriggerSchema(
                        metric_name="github_streak",
                        platform="github",
                        change_type="broken",
                        current_value=float(curr_streak),
                        historical_value=float(hist_streak),
                        absolute_change=float(hist_streak)
                    ))
                elif curr_streak - hist_streak >= STREAK_SURGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="github_streak",
                        platform="github",
                        change_type="increase",
                        current_value=float(curr_streak),
                        historical_value=float(hist_streak),
                        absolute_change=float(curr_streak - hist_streak)
                    ))

        # --- 2. LeetCode Comparisons ---
        if current_lc is not None and historical_lc is not None:
            curr_stats = current_lc.problem_stats
            hist_stats = historical_lc.problem_stats

            if curr_stats is not None and hist_stats is not None:
                # Solved Volume
                curr_solved = curr_stats.total_solved
                hist_solved = hist_stats.total_solved
                if curr_solved is not None and hist_solved is not None:
                    diff = curr_solved - hist_solved
                    abs_change = float(abs(diff))
                    if hist_solved == 0:
                        if curr_solved >= LEETCODE_SOLVED_ABSOLUTE_THRESHOLD:
                            triggers.append(InsightTriggerSchema(
                                metric_name="leetcode_solved",
                                platform="leetcode",
                                change_type="increase",
                                current_value=float(curr_solved),
                                historical_value=float(hist_solved),
                                percent_change=None,
                                absolute_change=abs_change,
                                metadata={"baseline_zero": True}
                            ))
                    else:
                        pct = (diff / hist_solved) * 100.0
                        if abs_change >= LEETCODE_SOLVED_ABSOLUTE_THRESHOLD:
                            if pct >= LEETCODE_SOLVED_PERCENT_THRESHOLD:
                                triggers.append(InsightTriggerSchema(
                                    metric_name="leetcode_solved",
                                    platform="leetcode",
                                    change_type="increase",
                                    current_value=float(curr_solved),
                                    historical_value=float(hist_solved),
                                    percent_change=pct,
                                    absolute_change=abs_change
                                ))
                            elif pct <= -LEETCODE_SOLVED_PERCENT_THRESHOLD:
                                triggers.append(InsightTriggerSchema(
                                    metric_name="leetcode_solved",
                                    platform="leetcode",
                                    change_type="decrease",
                                    current_value=float(curr_solved),
                                    historical_value=float(hist_solved),
                                    percent_change=pct,
                                    absolute_change=abs_change
                                ))

                # Difficulty Progression
                curr_total = curr_stats.total_solved
                hist_total = hist_stats.total_solved
                if curr_total is not None and hist_total is not None and curr_total > 0 and hist_total > 0:
                    curr_med = curr_stats.medium_solved or 0
                    curr_hard = curr_stats.hard_solved or 0
                    hist_med = hist_stats.medium_solved or 0
                    hist_hard = hist_stats.hard_solved or 0

                    curr_ratio = (curr_med + curr_hard) / curr_total
                    hist_ratio = (hist_med + hist_hard) / hist_total
                    diff = curr_ratio - hist_ratio
                    if diff >= DIFFICULTY_RATIO_CHANGE_THRESHOLD:
                        triggers.append(InsightTriggerSchema(
                            metric_name="leetcode_difficulty",
                            platform="leetcode",
                            change_type="increase",
                            current_value=curr_ratio,
                            historical_value=hist_ratio,
                            absolute_change=abs(diff)
                        ))
                    elif diff <= -DIFFICULTY_RATIO_CHANGE_THRESHOLD:
                        triggers.append(InsightTriggerSchema(
                            metric_name="leetcode_difficulty",
                            platform="leetcode",
                            change_type="decrease",
                            current_value=curr_ratio,
                            historical_value=hist_ratio,
                            absolute_change=abs(diff)
                        ))

            # LeetCode Consistency
            curr_cons = current_lc.contribution_consistency
            hist_cons = historical_lc.contribution_consistency
            if curr_cons is not None and hist_cons is not None:
                diff = curr_cons - hist_cons
                if diff >= CONSISTENCY_CHANGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="leetcode_consistency",
                        platform="leetcode",
                        change_type="increase",
                        current_value=float(curr_cons),
                        historical_value=float(hist_cons),
                        absolute_change=float(abs(diff))
                    ))
                elif diff <= -CONSISTENCY_CHANGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="leetcode_consistency",
                        platform="leetcode",
                        change_type="decrease",
                        current_value=float(curr_cons),
                        historical_value=float(hist_cons),
                        absolute_change=float(abs(diff))
                    ))

            # LeetCode Streak
            curr_streak = current_lc.current_streak
            hist_streak = historical_lc.current_streak
            if curr_streak is not None and hist_streak is not None:
                if hist_streak >= STREAK_BREAK_MINIMUM and curr_streak == 0:
                    triggers.append(InsightTriggerSchema(
                        metric_name="leetcode_streak",
                        platform="leetcode",
                        change_type="broken",
                        current_value=float(curr_streak),
                        historical_value=float(hist_streak),
                        absolute_change=float(hist_streak)
                    ))
                elif curr_streak - hist_streak >= STREAK_SURGE_THRESHOLD:
                    triggers.append(InsightTriggerSchema(
                        metric_name="leetcode_streak",
                        platform="leetcode",
                        change_type="increase",
                        current_value=float(curr_streak),
                        historical_value=float(hist_streak),
                        absolute_change=float(curr_streak - hist_streak)
                    ))

        # --- 3. Developer Score Comparisons ---
        if current_score is not None and historical_score is not None:
            # Overall Score
            curr_overall = current_score.overall_score
            hist_overall = historical_score.overall_score
            diff = curr_overall - hist_overall
            if diff >= OVERALL_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_overall",
                    platform="system",
                    change_type="increase",
                    current_value=float(curr_overall),
                    historical_value=float(hist_overall),
                    absolute_change=float(abs(diff))
                ))
            elif diff <= -OVERALL_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_overall",
                    platform="system",
                    change_type="decrease",
                    current_value=float(curr_overall),
                    historical_value=float(hist_overall),
                    absolute_change=float(abs(diff))
                ))

            # Category Score - Consistency
            curr_c = current_score.consistency_score
            hist_c = historical_score.consistency_score
            diff = curr_c - hist_c
            if diff >= CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_consistency",
                    platform="system",
                    change_type="increase",
                    current_value=float(curr_c),
                    historical_value=float(hist_c),
                    absolute_change=float(abs(diff))
                ))
            elif diff <= -CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_consistency",
                    platform="system",
                    change_type="decrease",
                    current_value=float(curr_c),
                    historical_value=float(hist_c),
                    absolute_change=float(abs(diff))
                ))

            # Category Score - Problem Solving
            curr_ps = current_score.problem_solving_score
            hist_ps = historical_score.problem_solving_score
            diff = curr_ps - hist_ps
            if diff >= CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_problem_solving",
                    platform="system",
                    change_type="increase",
                    current_value=float(curr_ps),
                    historical_value=float(hist_ps),
                    absolute_change=float(abs(diff))
                ))
            elif diff <= -CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_problem_solving",
                    platform="system",
                    change_type="decrease",
                    current_value=float(curr_ps),
                    historical_value=float(hist_ps),
                    absolute_change=float(abs(diff))
                ))

            # Category Score - Open Source
            curr_os = current_score.open_source_score
            hist_os = historical_score.open_source_score
            diff = curr_os - hist_os
            if diff >= CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_open_source",
                    platform="system",
                    change_type="increase",
                    current_value=float(curr_os),
                    historical_value=float(hist_os),
                    absolute_change=float(abs(diff))
                ))
            elif diff <= -CATEGORY_SCORE_CHANGE_THRESHOLD:
                triggers.append(InsightTriggerSchema(
                    metric_name="score_open_source",
                    platform="system",
                    change_type="decrease",
                    current_value=float(curr_os),
                    historical_value=float(hist_os),
                    absolute_change=float(abs(diff))
                ))

        return DeveloperComparisonResultSchema(
            user_id=user_id,
            current_date=current_date,
            historical_date=historical_date,
            triggers=triggers
        )
