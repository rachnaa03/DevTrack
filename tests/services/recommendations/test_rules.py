"""
Unit tests for RecommendationEvaluator (Task 11.1).

All tests are pure — no database, no HTTP, no FastAPI dependencies.
Input schemas are constructed directly using real schema classes to ensure
field names remain in sync with the implementation.
"""

import uuid

import pytest

from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema
from app.schemas.score import DeveloperScoreResultSchema, ScoreSubcomponentSchema
from app.services.recommendations.rules import (
    RECOMMENDATION_RULE_VERSION,
    GH_CONSISTENCY_WEAK_THRESHOLD,
    GH_LOW_COMMIT_THRESHOLD,
    GH_LOW_REPO_THRESHOLD,
    GH_LOW_STAR_THRESHOLD,
    GH_MIN_ACTIVE_DAYS_FOR_COMMITS,
    GH_STREAK_HISTORY_MINIMUM,
    LC_CONSISTENCY_WEAK_THRESHOLD,
    LC_HARD_RATIO_WEAK_THRESHOLD,
    LC_LOW_FREQUENCY_THRESHOLD,
    LC_MEDIUM_HARD_RATIO_WEAK_THRESHOLD,
    LC_MIN_ACTIVE_DAYS_FOR_FREQUENCY,
    LC_MIN_TOTAL_FOR_RATIO,
    LC_STREAK_HISTORY_MINIMUM,
    SC_CATEGORY_WEAK_THRESHOLD,
    SC_OVERALL_WEAK_THRESHOLD,
    RecommendationEvaluator,
)

# ---------------------------------------------------------------------------
# Fixtures — base "good" analytics snapshots used as starting points
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()


def _github(
    total_repositories: int = 10,
    total_stars: int = 20,
    total_forks: int = 5,
    total_commits: int | None = 150,
    active_days_count: int | None = 30,
    contribution_consistency: float | None = 0.65,
    current_streak: int | None = 7,
    longest_streak: int | None = 14,
) -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=USER_ID,
        login="devuser",
        repo_stats=RepositoryStatsSchema(
            total_repositories=total_repositories,
            total_stars=total_stars,
            total_forks=total_forks,
            total_size=2048,
            total_open_issues=3,
        ),
        language_distribution={"Python": 100},
        most_starred_repos=[],
        recently_updated_repositories=[],
        repository_growth=1,
        star_growth=2,
        fork_growth=0,
        total_commits=total_commits,
        commit_frequency_per_day=None if total_commits is None else total_commits / max(active_days_count or 1, 1),
        active_days_count=active_days_count,
        contribution_consistency=contribution_consistency,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )


def _leetcode(
    easy_solved: int = 30,
    medium_solved: int = 20,
    hard_solved: int = 10,
    total_solved: int = 60,
    problems_solved_frequency_per_day: float | None = 0.8,
    active_days_count: int | None = 30,
    contribution_consistency: float | None = 0.70,
    current_streak: int | None = 5,
    longest_streak: int | None = 10,
) -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=USER_ID,
        username="devuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=easy_solved,
            medium_solved=medium_solved,
            hard_solved=hard_solved,
            total_solved=total_solved,
            easy_submissions=easy_solved * 2,
            medium_submissions=medium_solved * 2,
            hard_submissions=hard_solved * 2,
            total_submissions=total_solved * 2,
        ),
        most_practiced_topics=[],
        problems_solved_growth=5,
        easy_solved_growth=2,
        medium_solved_growth=2,
        hard_solved_growth=1,
        submissions_growth=10,
        problems_solved_frequency_per_day=problems_solved_frequency_per_day,
        active_days_count=active_days_count,
        contribution_consistency=contribution_consistency,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )


def _score(
    overall_score: int = 600,
    consistency_score: int = 180,
    problem_solving_score: int = 200,
    open_source_score: int = 220,
) -> DeveloperScoreResultSchema:
    return DeveloperScoreResultSchema(
        overall_score=overall_score,
        consistency_score=consistency_score,
        problem_solving_score=problem_solving_score,
        open_source_score=open_source_score,
        score_version="v1",
        subcomponents=ScoreSubcomponentSchema(),
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _rule_ids(candidates) -> set[str]:
    return {c.rule_id for c in candidates}


# ---------------------------------------------------------------------------
# Tests: evaluate() with good data — no recommendations
# ---------------------------------------------------------------------------

class TestNoRecommendationsWhenDataIsGood:
    def test_strong_profile_produces_no_recommendations(self) -> None:
        """A developer with good metrics across all dimensions should get no recommendations."""
        result = RecommendationEvaluator.evaluate(
            github_analysis=_github(),
            leetcode_analysis=_leetcode(),
            score_result=_score(),
        )
        assert result == []

    def test_no_data_at_all_produces_no_recommendations(self) -> None:
        """When all platforms are None, no rule should fire."""
        result = RecommendationEvaluator.evaluate(
            github_analysis=None,
            leetcode_analysis=None,
            score_result=None,
        )
        assert result == []


# ---------------------------------------------------------------------------
# Tests: LeetCode rules
# ---------------------------------------------------------------------------

class TestLeetCodeDifficultyRules:
    def test_lc_diff_001_fires_when_hard_ratio_low(self) -> None:
        """LC-DIFF-001 fires when hard/total < threshold and total >= minimum."""
        lc = _leetcode(easy_solved=50, medium_solved=8, hard_solved=2, total_solved=60)
        # hard_ratio = 2/60 ≈ 0.033 < 0.08
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-001" in _rule_ids(result)

    def test_lc_diff_001_does_not_fire_when_hard_ratio_ok(self) -> None:
        lc = _leetcode(easy_solved=20, medium_solved=20, hard_solved=20, total_solved=60)
        # hard_ratio = 20/60 ≈ 0.33 > 0.08
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-001" not in _rule_ids(result)

    def test_lc_diff_001_does_not_fire_when_total_below_minimum(self) -> None:
        """If total_solved < LC_MIN_TOTAL_FOR_RATIO, do not fire (insufficient data)."""
        lc = _leetcode(easy_solved=3, medium_solved=1, hard_solved=0, total_solved=4)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-001" not in _rule_ids(result)

    def test_lc_diff_002_fires_when_easy_heavy(self) -> None:
        """LC-DIFF-002 fires when (medium+hard)/total < 0.30."""
        lc = _leetcode(easy_solved=55, medium_solved=4, hard_solved=1, total_solved=60)
        # ratio = 5/60 ≈ 0.08 < 0.30
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-002" in _rule_ids(result)

    def test_lc_diff_002_does_not_fire_when_distribution_balanced(self) -> None:
        lc = _leetcode(easy_solved=20, medium_solved=25, hard_solved=15, total_solved=60)
        # ratio = 40/60 ≈ 0.67 > 0.30
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-002" not in _rule_ids(result)

    def test_lc_diff_001_priority_is_high(self) -> None:
        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        diff_recs = [c for c in result if c.rule_id == "LC-DIFF-001"]
        assert diff_recs[0].priority == "HIGH"

    def test_lc_diff_002_priority_is_medium(self) -> None:
        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        diff_recs = [c for c in result if c.rule_id == "LC-DIFF-002"]
        assert diff_recs[0].priority == "MEDIUM"

    def test_lc_diff_001_does_not_fire_when_lc_none(self) -> None:
        result = RecommendationEvaluator.evaluate(None, None, None)
        assert "LC-DIFF-001" not in _rule_ids(result)


class TestLeetCodeActivityRules:
    def test_lc_act_001_fires_when_frequency_low_and_sufficient_history(self) -> None:
        lc = _leetcode(
            problems_solved_frequency_per_day=0.1,
            active_days_count=15,  # >= 7
        )
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-ACT-001" in _rule_ids(result)

    def test_lc_act_001_does_not_fire_when_frequency_ok(self) -> None:
        lc = _leetcode(problems_solved_frequency_per_day=0.5, active_days_count=15)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-ACT-001" not in _rule_ids(result)

    def test_lc_act_001_does_not_fire_when_insufficient_history(self) -> None:
        """Avoid penalising new users with < LC_MIN_ACTIVE_DAYS_FOR_FREQUENCY history."""
        lc = _leetcode(problems_solved_frequency_per_day=0.05, active_days_count=4)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-ACT-001" not in _rule_ids(result)

    def test_lc_act_001_does_not_fire_when_frequency_is_none(self) -> None:
        lc = _leetcode(problems_solved_frequency_per_day=None, active_days_count=15)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-ACT-001" not in _rule_ids(result)

    def test_lc_act_001_does_not_fire_when_active_days_is_none(self) -> None:
        lc = _leetcode(problems_solved_frequency_per_day=0.1, active_days_count=None)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-ACT-001" not in _rule_ids(result)


class TestLeetCodeConsistencyRules:
    def test_lc_cons_001_fires_when_consistency_low(self) -> None:
        lc = _leetcode(contribution_consistency=0.20)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-CONS-001" in _rule_ids(result)

    def test_lc_cons_001_does_not_fire_when_consistency_ok(self) -> None:
        lc = _leetcode(contribution_consistency=0.60)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-CONS-001" not in _rule_ids(result)

    def test_lc_cons_001_does_not_fire_when_none(self) -> None:
        lc = _leetcode(contribution_consistency=None)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-CONS-001" not in _rule_ids(result)

    def test_lc_streak_001_fires_when_streak_broken(self) -> None:
        lc = _leetcode(current_streak=0, longest_streak=10)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-STREAK-001" in _rule_ids(result)

    def test_lc_streak_001_does_not_fire_when_streak_active(self) -> None:
        lc = _leetcode(current_streak=5, longest_streak=10)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-STREAK-001" not in _rule_ids(result)

    def test_lc_streak_001_does_not_fire_when_longest_streak_below_minimum(self) -> None:
        """Do not penalise new users with a very short history."""
        lc = _leetcode(current_streak=0, longest_streak=2)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-STREAK-001" not in _rule_ids(result)

    def test_lc_streak_001_priority_is_low(self) -> None:
        lc = _leetcode(current_streak=0, longest_streak=10)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        rec = next(c for c in result if c.rule_id == "LC-STREAK-001")
        assert rec.priority == "LOW"


# ---------------------------------------------------------------------------
# Tests: GitHub rules
# ---------------------------------------------------------------------------

class TestGitHubActivityRules:
    def test_gh_act_001_fires_when_commits_low(self) -> None:
        gh = _github(total_commits=5, active_days_count=15)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-ACT-001" in _rule_ids(result)

    def test_gh_act_001_does_not_fire_when_commits_ok(self) -> None:
        gh = _github(total_commits=200, active_days_count=15)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-ACT-001" not in _rule_ids(result)

    def test_gh_act_001_does_not_fire_when_commits_none(self) -> None:
        gh = _github(total_commits=None, active_days_count=15)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-ACT-001" not in _rule_ids(result)

    def test_gh_act_001_does_not_fire_when_insufficient_history(self) -> None:
        gh = _github(total_commits=5, active_days_count=3)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-ACT-001" not in _rule_ids(result)


class TestGitHubConsistencyRules:
    def test_gh_cons_001_fires_when_consistency_low(self) -> None:
        gh = _github(contribution_consistency=0.10)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-CONS-001" in _rule_ids(result)

    def test_gh_cons_001_does_not_fire_when_consistency_ok(self) -> None:
        gh = _github(contribution_consistency=0.50)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-CONS-001" not in _rule_ids(result)

    def test_gh_cons_001_does_not_fire_when_none(self) -> None:
        gh = _github(contribution_consistency=None)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-CONS-001" not in _rule_ids(result)

    def test_gh_streak_001_fires_when_streak_broken(self) -> None:
        gh = _github(current_streak=0, longest_streak=10)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-STREAK-001" in _rule_ids(result)

    def test_gh_streak_001_does_not_fire_when_streak_active(self) -> None:
        gh = _github(current_streak=3, longest_streak=10)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-STREAK-001" not in _rule_ids(result)

    def test_gh_streak_001_does_not_fire_when_no_meaningful_history(self) -> None:
        gh = _github(current_streak=0, longest_streak=2)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-STREAK-001" not in _rule_ids(result)


class TestGitHubImpactRules:
    def test_gh_impact_001_fires_when_stars_low(self) -> None:
        gh = _github(total_stars=2)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-IMPACT-001" in _rule_ids(result)

    def test_gh_impact_001_does_not_fire_when_stars_ok(self) -> None:
        gh = _github(total_stars=20)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-IMPACT-001" not in _rule_ids(result)

    def test_gh_portfolio_001_fires_when_repos_low(self) -> None:
        gh = _github(total_repositories=1)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-PORTFOLIO-001" in _rule_ids(result)

    def test_gh_portfolio_001_does_not_fire_when_repos_ok(self) -> None:
        gh = _github(total_repositories=8)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert "GH-PORTFOLIO-001" not in _rule_ids(result)

    def test_impact_rules_priority_is_low(self) -> None:
        gh = _github(total_stars=2, total_repositories=1)
        result = RecommendationEvaluator.evaluate(gh, None, None)
        impact_rec = next(c for c in result if c.rule_id == "GH-IMPACT-001")
        portfolio_rec = next(c for c in result if c.rule_id == "GH-PORTFOLIO-001")
        assert impact_rec.priority == "LOW"
        assert portfolio_rec.priority == "LOW"


# ---------------------------------------------------------------------------
# Tests: Developer Score rules
# ---------------------------------------------------------------------------

class TestDeveloperScoreRules:
    def test_sc_overall_001_fires_when_overall_low(self) -> None:
        sc = _score(overall_score=300)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-OVERALL-001" in _rule_ids(result)

    def test_sc_overall_001_does_not_fire_when_score_ok(self) -> None:
        sc = _score(overall_score=500)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-OVERALL-001" not in _rule_ids(result)

    def test_sc_overall_001_priority_is_high(self) -> None:
        sc = _score(overall_score=300)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        rec = next(c for c in result if c.rule_id == "SC-OVERALL-001")
        assert rec.priority == "HIGH"

    def test_sc_consistency_001_fires_when_weak(self) -> None:
        sc = _score(consistency_score=50)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-CONSISTENCY-001" in _rule_ids(result)

    def test_sc_consistency_001_does_not_fire_when_ok(self) -> None:
        sc = _score(consistency_score=150)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-CONSISTENCY-001" not in _rule_ids(result)

    def test_sc_problem_solving_001_fires_when_weak(self) -> None:
        sc = _score(problem_solving_score=40)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-PS-001" in _rule_ids(result)

    def test_sc_problem_solving_001_does_not_fire_when_ok(self) -> None:
        sc = _score(problem_solving_score=200)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-PS-001" not in _rule_ids(result)

    def test_sc_open_source_001_fires_when_weak(self) -> None:
        sc = _score(open_source_score=50)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        assert "SC-OS-001" in _rule_ids(result)

    def test_sc_open_source_001_priority_is_medium(self) -> None:
        sc = _score(open_source_score=50)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        rec = next(c for c in result if c.rule_id == "SC-OS-001")
        assert rec.priority == "MEDIUM"

    def test_sc_score_none_produces_no_score_recommendations(self) -> None:
        result = RecommendationEvaluator.evaluate(None, None, None)
        score_rules = {"SC-OVERALL-001", "SC-CONSISTENCY-001", "SC-PS-001", "SC-OS-001"}
        assert _rule_ids(result).isdisjoint(score_rules)


# ---------------------------------------------------------------------------
# Tests: Priority ordering and structural guarantees
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_output_sorted_high_before_medium_before_low(self) -> None:
        """evaluate() must return candidates sorted HIGH → MEDIUM → LOW."""
        gh = _github(
            total_stars=2,                   # LOW: GH-IMPACT-001
            contribution_consistency=0.10,   # MEDIUM: GH-CONS-001
        )
        sc = _score(overall_score=300, consistency_score=50)  # HIGH: SC-OVERALL-001, SC-CONSISTENCY-001
        result = RecommendationEvaluator.evaluate(gh, None, sc)
        priorities = [c.priority for c in result]
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        assert priorities == sorted(priorities, key=lambda p: order[p])

    def test_rule_version_on_all_candidates(self) -> None:
        """Every candidate must carry the current rule version."""
        lc = _leetcode(
            easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60,
            contribution_consistency=0.20,
        )
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert len(result) > 0
        for candidate in result:
            assert candidate.rule_version == RECOMMENDATION_RULE_VERSION

    def test_evidence_dict_present_on_all_candidates(self) -> None:
        sc = _score(overall_score=300)
        result = RecommendationEvaluator.evaluate(None, None, sc)
        for candidate in result:
            assert isinstance(candidate.evidence, dict)
            assert len(candidate.evidence) > 0

    def test_rule_ids_are_unique_per_evaluation(self) -> None:
        """Each rule should appear at most once per evaluation call."""
        gh = _github(
            total_commits=5,
            total_stars=2,
            total_repositories=1,
            contribution_consistency=0.10,
            current_streak=0,
            longest_streak=10,
        )
        lc = _leetcode(
            easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60,
            contribution_consistency=0.20,
            current_streak=0,
            longest_streak=8,
            problems_solved_frequency_per_day=0.1,
            active_days_count=15,
        )
        sc = _score(overall_score=300, consistency_score=50, problem_solving_score=40, open_source_score=50)
        result = RecommendationEvaluator.evaluate(gh, lc, sc)
        ids = [c.rule_id for c in result]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs detected in a single evaluation"

    def test_all_candidates_have_non_empty_title_and_message(self) -> None:
        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        for candidate in result:
            assert candidate.title.strip() != ""
            assert candidate.message.strip() != ""

    def test_mixed_none_and_present_data_safe(self) -> None:
        """Partial data (only some analytics available) must not raise."""
        gh = _github()
        result = RecommendationEvaluator.evaluate(gh, None, None)
        assert isinstance(result, list)

    def test_determinism_same_inputs_same_outputs(self) -> None:
        """Calling evaluate() twice with the same inputs must return the same result."""
        lc = _leetcode(easy_solved=55, medium_solved=4, hard_solved=1, total_solved=60)
        result_a = RecommendationEvaluator.evaluate(None, lc, None)
        result_b = RecommendationEvaluator.evaluate(None, lc, None)
        assert [c.rule_id for c in result_a] == [c.rule_id for c in result_b]


# ---------------------------------------------------------------------------
# Tests: Data availability guards
# ---------------------------------------------------------------------------

class TestDataAvailabilityGuards:
    def test_none_optional_fields_do_not_trigger_rules(self) -> None:
        """Rules that require history-derived Optional fields must not fire when those are None."""
        # contribution_consistency=None → LC-CONS-001 and GH-CONS-001 should NOT fire
        gh = _github(contribution_consistency=None, total_commits=None, current_streak=None, longest_streak=None)
        lc = _leetcode(contribution_consistency=None, problems_solved_frequency_per_day=None, active_days_count=None, current_streak=None, longest_streak=None)
        result = RecommendationEvaluator.evaluate(gh, lc, None)
        triggered = _rule_ids(result)
        assert "LC-CONS-001" not in triggered
        assert "GH-CONS-001" not in triggered
        assert "LC-ACT-001" not in triggered
        assert "GH-ACT-001" not in triggered
        assert "LC-STREAK-001" not in triggered
        assert "GH-STREAK-001" not in triggered

    def test_zero_total_solved_below_minimum_does_not_trigger_ratio_rules(self) -> None:
        """
        If total_solved < LC_MIN_TOTAL_FOR_RATIO, ratio-based rules must not fire.
        Zero activity ≠ "bad Hard ratio".
        """
        lc = _leetcode(easy_solved=0, medium_solved=0, hard_solved=0, total_solved=0)
        result = RecommendationEvaluator.evaluate(None, lc, None)
        assert "LC-DIFF-001" not in _rule_ids(result)
        assert "LC-DIFF-002" not in _rule_ids(result)
