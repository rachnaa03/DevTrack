"""
Rule-Based Recommendation Engine — Task 11.1

Design philosophy
-----------------
Each recommendation rule is a pure static method on RecommendationEvaluator.
Rules receive already-computed analytics schemas and return a
RecommendationCandidateSchema when their condition is met, or None otherwise.

This mirrors the AnalyticsComparator pattern from app/services/insights/rules.py:
- No database calls
- No HTTP calls
- No FastAPI dependencies
- Fully testable with mock inputs
- Deterministic: same inputs → same outputs

Rule naming convention
----------------------
Rule IDs follow the pattern:  <CATEGORY-PREFIX>-<SEQUENCE>

  LC   = LeetCode
  GH   = GitHub
  SC   = Developer Score
  DEV  = Cross-platform developer consistency

  Examples: LC-DIFF-001, GH-CONS-001, SC-OVERALL-001

Data availability guard
-----------------------
Rules only fire when the required input data is present and not stale/zero in a
misleading way.

For history-derived fields (e.g., contribution_consistency, total_commits) that
are Optional[...] in the analysis schemas, a rule must explicitly check for None
before making any comparison. A None field means the data is unavailable —
not that the metric is zero.

Priority determination
----------------------
Priority is assigned per-rule based on the severity of the gap:
  HIGH   — Strong evidence of a significant skill gap or sustained inactivity
  MEDIUM — Moderate evidence of weakness that warrants attention
  LOW    — Minor improvement opportunity, good hygiene suggestion

Rule version
------------
RECOMMENDATION_RULE_VERSION is a module-level constant, analogous to
INSIGHT_RULE_VERSION in the insights service.  Increment this string when
thresholds or rule conditions change so the orchestrator can identify which
rules produced which recommendations.

Adding a new rule
-----------------
1. Add a new static method following the _evaluate_<rule_id> naming convention.
2. Add the method call inside evaluate().
3. Add a unit test in tests/services/recommendations/test_rules.py.
4. If the threshold is significant, document it in the THRESHOLDS block below.
"""

import logging
from dataclasses import dataclass

from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.recommendations import RecommendationCandidateSchema
from app.schemas.score import DeveloperScoreResultSchema

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule version — increment when thresholds or conditions change
# ---------------------------------------------------------------------------
RECOMMENDATION_RULE_VERSION = "v1"

# ---------------------------------------------------------------------------
# Centralized Thresholds
# All numeric decision points live here to make future tuning straightforward.
# ---------------------------------------------------------------------------

# LeetCode difficulty
LC_HARD_RATIO_WEAK_THRESHOLD = 0.08        # Hard/(Easy+Medium+Hard) ratio below this is "low hard exposure"
LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD = 0.30 # (Medium+Hard)/Total below this is "easy-heavy"
LC_MIN_TOTAL_FOR_RATIO = 10                # Need at least this many solved before ratios are meaningful

# LeetCode activity
LC_LOW_FREQUENCY_THRESHOLD = 0.3           # problems solved per day below this triggers recommendation
LC_MIN_ACTIVE_DAYS_FOR_FREQUENCY = 7       # only evaluate frequency if we have enough history
LC_ZERO_SOLVED_THRESHOLD = 0               # total_solved == 0 → no activity at all

# LeetCode consistency
LC_CONSISTENCY_WEAK_THRESHOLD = 0.40       # contribution_consistency below this is "low"

# LeetCode streak
LC_STREAK_BROKEN_THRESHOLD = 0             # current_streak == 0 AND longest_streak >= minimum
LC_STREAK_HISTORY_MINIMUM = 5              # must have had a meaningful streak to trigger broken-streak rec

# GitHub activity
GH_LOW_COMMIT_THRESHOLD = 20              # total_commits below this over the analysis period is "low"
GH_MIN_ACTIVE_DAYS_FOR_COMMITS = 7        # only evaluate commits if we have enough history

# GitHub consistency
GH_CONSISTENCY_WEAK_THRESHOLD = 0.30      # contribution_consistency below this is "low"

# GitHub streak
GH_STREAK_BROKEN_THRESHOLD = 0           # current_streak == 0
GH_STREAK_HISTORY_MINIMUM = 5            # must have had a meaningful streak

# GitHub open source impact
GH_LOW_STAR_THRESHOLD = 5                # total_stars below this → low visibility
GH_LOW_REPO_THRESHOLD = 3               # total_repositories below this → limited portfolio

# Developer Score
SC_OVERALL_WEAK_THRESHOLD = 400          # overall score below this is "needs attention"
SC_CATEGORY_WEAK_THRESHOLD = 80          # any category score below this is "weak"
SC_CONSISTENCY_MAX = 300
SC_PROBLEM_SOLVING_MAX = 350
SC_OPEN_SOURCE_MAX = 350

# ---------------------------------------------------------------------------
# Internal result carrier — keeps evaluate() readable
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _RuleResult:
    candidate: RecommendationCandidateSchema | None


# ---------------------------------------------------------------------------
# Main evaluator class
# ---------------------------------------------------------------------------
class RecommendationEvaluator:
    """
    Pure rule-based recommendation engine.

    Call evaluate() with the user's current analytics snapshots.
    Returns a list of RecommendationCandidateSchema objects — one per triggered rule.
    The list may be empty if no rules fire.

    The engine does NOT persist anything.  Persistence and deduplication are the
    responsibility of the Recommendation Orchestrator Service (Task 11.3).
    """

    @staticmethod
    def evaluate(
        github_analysis: GitHubAnalysisResultSchema | None,
        leetcode_analysis: LeetCodeAnalysisResultSchema | None,
        score_result: DeveloperScoreResultSchema | None,
    ) -> list[RecommendationCandidateSchema]:
        """
        Evaluate all recommendation rules against the provided analytics data.

        Parameters
        ----------
        github_analysis : GitHubAnalysisResultSchema | None
            Latest computed GitHub analytics for the user, or None if GitHub
            is not connected or analytics are unavailable.
        leetcode_analysis : LeetCodeAnalysisResultSchema | None
            Latest computed LeetCode analytics for the user, or None if LeetCode
            is not connected or analytics are unavailable.
        score_result : DeveloperScoreResultSchema | None
            Latest computed Developer Score, or None if unavailable.

        Returns
        -------
        list[RecommendationCandidateSchema]
            All triggered recommendation candidates, ordered by priority
            (HIGH → MEDIUM → LOW) then by rule ID for deterministic output.
        """
        candidates: list[RecommendationCandidateSchema] = []

        # --- LeetCode rules ---
        _apply(candidates, RecommendationEvaluator._lc_diff_001(leetcode_analysis))
        _apply(candidates, RecommendationEvaluator._lc_diff_002(leetcode_analysis))
        _apply(candidates, RecommendationEvaluator._lc_act_001(leetcode_analysis))
        _apply(candidates, RecommendationEvaluator._lc_cons_001(leetcode_analysis))
        _apply(candidates, RecommendationEvaluator._lc_streak_001(leetcode_analysis))

        # --- GitHub rules ---
        _apply(candidates, RecommendationEvaluator._gh_act_001(github_analysis))
        _apply(candidates, RecommendationEvaluator._gh_cons_001(github_analysis))
        _apply(candidates, RecommendationEvaluator._gh_streak_001(github_analysis))
        _apply(candidates, RecommendationEvaluator._gh_impact_001(github_analysis))
        _apply(candidates, RecommendationEvaluator._gh_portfolio_001(github_analysis))

        # --- Developer Score rules ---
        _apply(candidates, RecommendationEvaluator._sc_overall_001(score_result))
        _apply(candidates, RecommendationEvaluator._sc_consistency_001(score_result))
        _apply(candidates, RecommendationEvaluator._sc_problem_solving_001(score_result))
        _apply(candidates, RecommendationEvaluator._sc_open_source_001(score_result))

        # Sort deterministically: HIGH first, then MEDIUM, then LOW, then by rule_id
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        candidates.sort(key=lambda c: (priority_order.get(c.priority, 99), c.rule_id))

        logger.info("RecommendationEvaluator produced %d candidate(s).", len(candidates))
        return candidates

    # -------------------------------------------------------------------------
    # LeetCode Rules
    # -------------------------------------------------------------------------

    @staticmethod
    def _lc_diff_001(
        lc: LeetCodeAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        LC-DIFF-001: Low Hard Problem Exposure

        Condition:
          LeetCode data is available AND total_solved >= LC_MIN_TOTAL_FOR_RATIO
          AND hard/(total_solved) < LC_HARD_RATIO_WEAK_THRESHOLD

        Priority: HIGH
        Rationale: Hard problems are the primary signal of problem-solving depth
        in the Developer Score and in technical interview contexts.
        """
        if lc is None:
            return None
        stats = lc.problem_stats
        if stats is None:
            return None
        total = stats.total_solved
        hard = stats.hard_solved
        if total < LC_MIN_TOTAL_FOR_RATIO:
            return None
        ratio = hard / total
        if ratio >= LC_HARD_RATIO_WEAK_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="LC-DIFF-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="leetcode_difficulty",
            priority="HIGH",
            title="Increase Hard Problem Practice",
            message=(
                f"Only {ratio * 100:.1f}% of your solved problems are Hard difficulty "
                f"({hard} out of {total}). Aim to solve at least "
                f"{int(LC_HARD_RATIO_WEAK_THRESHOLD * 100)}% Hard problems to strengthen "
                f"your algorithmic depth and improve your Developer Score."
            ),
            evidence={
                "hard_solved": hard,
                "total_solved": total,
                "hard_ratio": round(ratio, 4),
                "threshold": LC_HARD_RATIO_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _lc_diff_002(
        lc: LeetCodeAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        LC-DIFF-002: Easy-Heavy Problem Distribution

        Condition:
          LeetCode data is available AND total_solved >= LC_MIN_TOTAL_FOR_RATIO
          AND (medium + hard) / total < LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD

        Priority: MEDIUM
        Rationale: A portfolio dominated by Easy problems signals over-reliance on
        trivial difficulty levels. Medium and Hard problems develop the reasoning
        skills measured by the Developer Score.
        """
        if lc is None:
            return None
        stats = lc.problem_stats
        if stats is None:
            return None
        total = stats.total_solved
        medium = stats.medium_solved
        hard = stats.hard_solved
        if total < LC_MIN_TOTAL_FOR_RATIO:
            return None
        medium_hard_ratio = (medium + hard) / total
        if medium_hard_ratio >= LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="LC-DIFF-002",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="leetcode_difficulty",
            priority="MEDIUM",
            title="Balance Difficulty Distribution",
            message=(
                f"Only {medium_hard_ratio * 100:.1f}% of your solved problems are Medium or Hard "
                f"({medium + hard} out of {total}). Try to shift at least "
                f"{int(LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD * 100)}% of your practice "
                f"toward Medium and Hard problems."
            ),
            evidence={
                "medium_solved": medium,
                "hard_solved": hard,
                "total_solved": total,
                "medium_hard_ratio": round(medium_hard_ratio, 4),
                "threshold": LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _lc_act_001(
        lc: LeetCodeAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        LC-ACT-001: Low LeetCode Solving Frequency

        Condition:
          LeetCode data is available
          AND active_days_count >= LC_MIN_ACTIVE_DAYS_FOR_FREQUENCY
          AND problems_solved_frequency_per_day < LC_LOW_FREQUENCY_THRESHOLD

        Priority: MEDIUM
        Rationale: Consistency is a key component of both Developer Score and
        long-term skill development. Low frequency over a meaningful period signals
        insufficient practice.

        Note: We require active_days_count >= threshold to avoid penalising users
        who simply started recently and have little history.
        """
        if lc is None:
            return None
        freq = lc.problems_solved_frequency_per_day
        active_days = lc.active_days_count
        if freq is None or active_days is None:
            return None
        if active_days < LC_MIN_ACTIVE_DAYS_FOR_FREQUENCY:
            return None
        if freq >= LC_LOW_FREQUENCY_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="LC-ACT-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="leetcode_activity",
            priority="MEDIUM",
            title="Increase LeetCode Practice Frequency",
            message=(
                f"You are solving approximately {freq:.2f} problems per day over "
                f"your tracked period. Aim for at least {LC_LOW_FREQUENCY_THRESHOLD} "
                f"problems per day to build consistent problem-solving habits."
            ),
            evidence={
                "problems_solved_frequency_per_day": round(freq, 4),
                "active_days_count": active_days,
                "threshold": LC_LOW_FREQUENCY_THRESHOLD,
            },
        )

    @staticmethod
    def _lc_cons_001(
        lc: LeetCodeAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        LC-CONS-001: Low LeetCode Contribution Consistency

        Condition:
          LeetCode data is available
          AND contribution_consistency is not None
          AND contribution_consistency < LC_CONSISTENCY_WEAK_THRESHOLD

        Priority: MEDIUM
        Rationale: Consistency (measured as the proportion of active days in the
        tracked window) directly feeds the Developer Score consistency component.
        """
        if lc is None:
            return None
        consistency = lc.contribution_consistency
        if consistency is None:
            return None
        if consistency >= LC_CONSISTENCY_WEAK_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="LC-CONS-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="leetcode_consistency",
            priority="MEDIUM",
            title="Improve LeetCode Consistency",
            message=(
                f"Your LeetCode contribution consistency is {consistency * 100:.1f}%, "
                f"which is below the {LC_CONSISTENCY_WEAK_THRESHOLD * 100:.0f}% target. "
                f"Try to solve at least one problem every day to build a consistent habit."
            ),
            evidence={
                "contribution_consistency": round(consistency, 4),
                "threshold": LC_CONSISTENCY_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _lc_streak_001(
        lc: LeetCodeAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        LC-STREAK-001: LeetCode Streak Broken

        Condition:
          LeetCode data is available
          AND current_streak == 0
          AND longest_streak >= LC_STREAK_HISTORY_MINIMUM

        Priority: LOW
        Rationale: A broken streak after a meaningful history indicates a lapse in
        consistency. This is a motivational nudge rather than a critical alert.
        """
        if lc is None:
            return None
        current = lc.current_streak
        longest = lc.longest_streak
        if current is None or longest is None:
            return None
        if current != 0:
            return None
        if longest < LC_STREAK_HISTORY_MINIMUM:
            return None
        return RecommendationCandidateSchema(
            rule_id="LC-STREAK-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="leetcode_consistency",
            priority="LOW",
            title="Restart Your LeetCode Streak",
            message=(
                f"Your LeetCode streak has been broken. Your longest streak was "
                f"{longest} days — try to solve at least one problem today to restart it."
            ),
            evidence={
                "current_streak": current,
                "longest_streak": longest,
                "minimum_history": LC_STREAK_HISTORY_MINIMUM,
            },
        )

    # -------------------------------------------------------------------------
    # GitHub Rules
    # -------------------------------------------------------------------------

    @staticmethod
    def _gh_act_001(
        gh: GitHubAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        GH-ACT-001: Low GitHub Commit Activity

        Condition:
          GitHub data is available
          AND active_days_count >= GH_MIN_ACTIVE_DAYS_FOR_COMMITS
          AND total_commits is not None
          AND total_commits < GH_LOW_COMMIT_THRESHOLD

        Priority: MEDIUM
        Rationale: Commit depth is directly scored in the Open Source Impact
        component of the Developer Score (up to 100 points for 500 commits).
        Low commit volume is a concrete, actionable weakness.
        """
        if gh is None:
            return None
        commits = gh.total_commits
        active_days = gh.active_days_count
        if commits is None or active_days is None:
            return None
        if active_days < GH_MIN_ACTIVE_DAYS_FOR_COMMITS:
            return None
        if commits >= GH_LOW_COMMIT_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="GH-ACT-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="github_activity",
            priority="MEDIUM",
            title="Increase GitHub Commit Activity",
            message=(
                f"You have made {commits} commits over your tracked period. "
                f"Regular commits to public repositories improve your Developer Score "
                f"and demonstrate active development. Aim for daily or near-daily contributions."
            ),
            evidence={
                "total_commits": commits,
                "active_days_count": active_days,
                "threshold": GH_LOW_COMMIT_THRESHOLD,
            },
        )

    @staticmethod
    def _gh_cons_001(
        gh: GitHubAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        GH-CONS-001: Low GitHub Contribution Consistency

        Condition:
          GitHub data is available
          AND contribution_consistency is not None
          AND contribution_consistency < GH_CONSISTENCY_WEAK_THRESHOLD

        Priority: MEDIUM
        Rationale: Contribution consistency measures the proportion of tracked days
        with at least one commit. It directly drives the GitHub component of the
        Coding Consistency score.
        """
        if gh is None:
            return None
        consistency = gh.contribution_consistency
        if consistency is None:
            return None
        if consistency >= GH_CONSISTENCY_WEAK_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="GH-CONS-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="github_consistency",
            priority="MEDIUM",
            title="Improve GitHub Contribution Consistency",
            message=(
                f"Your GitHub contribution consistency is {consistency * 100:.1f}%, "
                f"below the {GH_CONSISTENCY_WEAK_THRESHOLD * 100:.0f}% target. "
                f"Try to commit code to public repositories more regularly."
            ),
            evidence={
                "contribution_consistency": round(consistency, 4),
                "threshold": GH_CONSISTENCY_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _gh_streak_001(
        gh: GitHubAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        GH-STREAK-001: GitHub Contribution Streak Broken

        Condition:
          GitHub data is available
          AND current_streak == 0
          AND longest_streak >= GH_STREAK_HISTORY_MINIMUM

        Priority: LOW
        Rationale: A previously established streak being broken suggests a recent
        period of inactivity after consistent work.
        """
        if gh is None:
            return None
        current = gh.current_streak
        longest = gh.longest_streak
        if current is None or longest is None:
            return None
        if current != 0:
            return None
        if longest < GH_STREAK_HISTORY_MINIMUM:
            return None
        return RecommendationCandidateSchema(
            rule_id="GH-STREAK-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="github_consistency",
            priority="LOW",
            title="Restart Your GitHub Streak",
            message=(
                f"Your GitHub contribution streak has been broken. "
                f"Your longest streak was {longest} days — make a commit today to restart it."
            ),
            evidence={
                "current_streak": current,
                "longest_streak": longest,
                "minimum_history": GH_STREAK_HISTORY_MINIMUM,
            },
        )

    @staticmethod
    def _gh_impact_001(
        gh: GitHubAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        GH-IMPACT-001: Low Repository Star Count

        Condition:
          GitHub data is available
          AND total_stars < GH_LOW_STAR_THRESHOLD

        Priority: LOW
        Rationale: Stars are the primary visibility signal in the Open Source Impact
        scoring component (up to 120 points for 50 stars).  Low star count
        suggests limited project visibility.

        Note: This is a LOW priority — star counts depend heavily on promotion
        and topic choice, which are outside the developer's direct daily control.
        """
        if gh is None:
            return None
        stats = gh.repo_stats
        if stats is None:
            return None
        stars = stats.total_stars
        if stars >= GH_LOW_STAR_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="GH-IMPACT-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="github_open_source_impact",
            priority="LOW",
            title="Improve Repository Visibility",
            message=(
                f"Your public repositories have {stars} total stars. "
                f"Consider writing README documentation, adding topics/tags, and "
                f"sharing your projects to improve visibility."
            ),
            evidence={
                "total_stars": stars,
                "threshold": GH_LOW_STAR_THRESHOLD,
            },
        )

    @staticmethod
    def _gh_portfolio_001(
        gh: GitHubAnalysisResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        GH-PORTFOLIO-001: Limited Public Repository Portfolio

        Condition:
          GitHub data is available
          AND total_repositories < GH_LOW_REPO_THRESHOLD

        Priority: LOW
        Rationale: Repository volume feeds the repo_volume_points component
        of the Open Source Impact score (up to 50 points for 10+ repos).
        A limited portfolio also reduces project-area diversity signals.
        """
        if gh is None:
            return None
        stats = gh.repo_stats
        if stats is None:
            return None
        repos = stats.total_repositories
        if repos >= GH_LOW_REPO_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="GH-PORTFOLIO-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="github_open_source_impact",
            priority="LOW",
            title="Expand Your Public Portfolio",
            message=(
                f"You have {repos} public repositories. "
                f"Publishing more projects — even small tools or utilities — "
                f"strengthens your public portfolio and improves your Developer Score."
            ),
            evidence={
                "total_repositories": repos,
                "threshold": GH_LOW_REPO_THRESHOLD,
            },
        )

    # -------------------------------------------------------------------------
    # Developer Score Rules
    # -------------------------------------------------------------------------

    @staticmethod
    def _sc_overall_001(
        score: DeveloperScoreResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        SC-OVERALL-001: Low Overall Developer Score

        Condition:
          Score data is available
          AND overall_score < SC_OVERALL_WEAK_THRESHOLD

        Priority: HIGH
        Rationale: An overall score below 400/1000 (40%) indicates broad weakness
        across multiple dimensions and warrants a top-level recommendation.
        """
        if score is None:
            return None
        overall = score.overall_score
        if overall >= SC_OVERALL_WEAK_THRESHOLD:
            return None
        return RecommendationCandidateSchema(
            rule_id="SC-OVERALL-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="developer_score",
            priority="HIGH",
            title="Improve Your Developer Score",
            message=(
                f"Your Developer Score is {overall}/1000. "
                f"Focus on improving your coding consistency (daily commits and LeetCode streaks), "
                f"problem-solving depth (Medium and Hard LeetCode problems), and "
                f"open-source impact (public repository engagement) to increase your score."
            ),
            evidence={
                "overall_score": overall,
                "threshold": SC_OVERALL_WEAK_THRESHOLD,
                "max_score": 1000,
            },
        )

    @staticmethod
    def _sc_consistency_001(
        score: DeveloperScoreResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        SC-CONSISTENCY-001: Weak Consistency Score Category

        Condition:
          Score data is available
          AND consistency_score < SC_CATEGORY_WEAK_THRESHOLD

        Priority: HIGH
        Rationale: The Coding Consistency category (max 300) directly reflects
        daily habits.  A score below 80 (26% of maximum) indicates very low
        engagement across both platforms.
        """
        if score is None:
            return None
        cat_score = score.consistency_score
        if cat_score >= SC_CATEGORY_WEAK_THRESHOLD:
            return None
        pct = round(cat_score / SC_CONSISTENCY_MAX * 100, 1)
        return RecommendationCandidateSchema(
            rule_id="SC-CONSISTENCY-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="developer_score",
            priority="HIGH",
            title="Build Daily Coding Habits",
            message=(
                f"Your Coding Consistency score is {cat_score}/{SC_CONSISTENCY_MAX} "
                f"({pct}%). Establish a daily practice: commit code to GitHub and solve "
                f"at least one LeetCode problem every day to raise this score."
            ),
            evidence={
                "consistency_score": cat_score,
                "max_score": SC_CONSISTENCY_MAX,
                "threshold": SC_CATEGORY_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _sc_problem_solving_001(
        score: DeveloperScoreResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        SC-PS-001: Weak Problem-Solving Depth Score Category

        Condition:
          Score data is available
          AND problem_solving_score < SC_CATEGORY_WEAK_THRESHOLD

        Priority: HIGH
        Rationale: Problem-solving depth (max 350) is the heaviest-weighted
        individual category.  A weak score here has the largest impact on
        overall Developer Score.
        """
        if score is None:
            return None
        cat_score = score.problem_solving_score
        if cat_score >= SC_CATEGORY_WEAK_THRESHOLD:
            return None
        pct = round(cat_score / SC_PROBLEM_SOLVING_MAX * 100, 1)
        return RecommendationCandidateSchema(
            rule_id="SC-PS-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="developer_score",
            priority="HIGH",
            title="Solve More LeetCode Problems",
            message=(
                f"Your Problem-Solving Depth score is {cat_score}/{SC_PROBLEM_SOLVING_MAX} "
                f"({pct}%). Connect your LeetCode account and solve Medium and Hard problems "
                f"to increase this score, which is the largest single contributor to your "
                f"Developer Score."
            ),
            evidence={
                "problem_solving_score": cat_score,
                "max_score": SC_PROBLEM_SOLVING_MAX,
                "threshold": SC_CATEGORY_WEAK_THRESHOLD,
            },
        )

    @staticmethod
    def _sc_open_source_001(
        score: DeveloperScoreResultSchema | None,
    ) -> RecommendationCandidateSchema | None:
        """
        SC-OS-001: Weak Open Source Impact Score Category

        Condition:
          Score data is available
          AND open_source_score < SC_CATEGORY_WEAK_THRESHOLD

        Priority: MEDIUM
        Rationale: Open Source Impact (max 350) reflects repository engagement.
        A weak score here indicates limited public project contribution — a more
        gradual, medium-priority improvement compared with daily habits.
        """
        if score is None:
            return None
        cat_score = score.open_source_score
        if cat_score >= SC_CATEGORY_WEAK_THRESHOLD:
            return None
        pct = round(cat_score / SC_OPEN_SOURCE_MAX * 100, 1)
        return RecommendationCandidateSchema(
            rule_id="SC-OS-001",
            rule_version=RECOMMENDATION_RULE_VERSION,
            category="developer_score",
            priority="MEDIUM",
            title="Increase Open Source Impact",
            message=(
                f"Your Open Source Impact score is {cat_score}/{SC_OPEN_SOURCE_MAX} "
                f"({pct}%). Create more public repositories, accumulate stars and forks, "
                f"and increase your commit volume to improve this category."
            ),
            evidence={
                "open_source_score": cat_score,
                "max_score": SC_OPEN_SOURCE_MAX,
                "threshold": SC_CATEGORY_WEAK_THRESHOLD,
            },
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _apply(
    candidates: list[RecommendationCandidateSchema],
    result: RecommendationCandidateSchema | None,
) -> None:
    """Append a candidate to the list if it is not None."""
    if result is not None:
        candidates.append(result)
