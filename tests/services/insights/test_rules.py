import uuid
from datetime import date
import pytest

from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema
from app.schemas.score import DeveloperScoreResultSchema, ScoreSubcomponentSchema
from app.services.insights.rules import AnalyticsComparator

@pytest.fixture
def base_github() -> GitHubAnalysisResultSchema:
    return GitHubAnalysisResultSchema(
        user_id=uuid.uuid4(),
        login="testuser",
        repo_stats=RepositoryStatsSchema(
            total_repositories=5,
            total_stars=10,
            total_forks=2,
            total_size=1024,
            total_open_issues=1
        ),
        language_distribution={"Python": 100},
        most_starred_repos=[],
        recently_updated_repositories=[],
        repository_growth=1,
        star_growth=2,
        fork_growth=0,
        total_commits=100,
        commit_frequency_per_day=1.5,
        active_days_count=3,
        contribution_consistency=0.5,
        current_streak=3,
        longest_streak=10
    )

@pytest.fixture
def base_leetcode() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid.uuid4(),
        username="testuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=10,
            medium_solved=10,
            hard_solved=10,
            total_solved=30,
            easy_submissions=20,
            medium_submissions=10,
            hard_submissions=4,
            total_submissions=34
        ),
        most_practiced_topics=[],
        problems_solved_growth=2,
        easy_solved_growth=1,
        medium_solved_growth=1,
        hard_solved_growth=0,
        submissions_growth=4,
        problems_solved_frequency_per_day=0.5,
        active_days_count=2,
        contribution_consistency=0.5,
        current_streak=3,
        longest_streak=6
    )

@pytest.fixture
def base_score() -> DeveloperScoreResultSchema:
    return DeveloperScoreResultSchema(
        overall_score=500,
        consistency_score=150,
        problem_solving_score=150,
        open_source_score=200,
        score_version="v1",
        subcomponents=ScoreSubcomponentSchema()
    )

def test_github_commits_increase(base_github: GitHubAnalysisResultSchema) -> None:
    """1. GitHub commit increase above both thresholds."""
    current = base_github.model_copy(update={"total_commits": 130}) # +30 commits (+30%, above 20% & 10 absolute)
    result = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=current,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(result.triggers) == 1
    trigger = result.triggers[0]
    assert trigger.metric_name == "github_commits"
    assert trigger.change_type == "increase"
    assert trigger.percent_change == 30.0
    assert trigger.absolute_change == 30.0

def test_github_commits_decrease(base_github: GitHubAnalysisResultSchema) -> None:
    """2. GitHub commit decrease above both thresholds."""
    current = base_github.model_copy(update={"total_commits": 75}) # -25 commits (-25%, above 20% & 10 absolute)
    result = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=current,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(result.triggers) == 1
    trigger = result.triggers[0]
    assert trigger.metric_name == "github_commits"
    assert trigger.change_type == "decrease"
    assert trigger.percent_change == -25.0
    assert trigger.absolute_change == 25.0

def test_github_commits_baseline_zero(base_github: GitHubAnalysisResultSchema) -> None:
    """3. GitHub historical commits = 0 and current commits above absolute threshold."""
    hist = base_github.model_copy(update={"total_commits": 0})
    curr = base_github.model_copy(update={"total_commits": 15}) # +15 commits (above absolute 10)
    result = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=curr,
        historical_gh=hist,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(result.triggers) == 1
    trigger = result.triggers[0]
    assert trigger.metric_name == "github_commits"
    assert trigger.change_type == "increase"
    assert trigger.percent_change is None
    assert trigger.absolute_change == 15.0
    assert trigger.metadata.get("baseline_zero") is True

def test_github_commits_below_threshold(base_github: GitHubAnalysisResultSchema) -> None:
    """4. GitHub change below threshold produces no trigger."""
    current = base_github.model_copy(update={"total_commits": 105}) # +5 commits (+5%, below thresholds)
    result = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=current,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(result.triggers) == 0

def test_github_consistency(base_github: GitHubAnalysisResultSchema) -> None:
    """5. GitHub consistency increase and decrease."""
    # Consistency increase: +0.20
    curr_inc = base_github.model_copy(update={"contribution_consistency": 0.70})
    res_inc = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=curr_inc,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_inc.triggers) == 1
    assert res_inc.triggers[0].metric_name == "github_consistency"
    assert res_inc.triggers[0].change_type == "increase"

    # Consistency decrease: -0.20
    curr_dec = base_github.model_copy(update={"contribution_consistency": 0.30})
    res_dec = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=curr_dec,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_dec.triggers) == 1
    assert res_dec.triggers[0].metric_name == "github_consistency"
    assert res_dec.triggers[0].change_type == "decrease"

def test_github_streak_broken(base_github: GitHubAnalysisResultSchema) -> None:
    """6. GitHub streak broken when historical streak >= 5 and current streak == 0."""
    hist = base_github.model_copy(update={"current_streak": 6})
    curr = base_github.model_copy(update={"current_streak": 0})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=curr,
        historical_gh=hist,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res.triggers) == 1
    assert res.triggers[0].metric_name == "github_streak"
    assert res.triggers[0].change_type == "broken"

def test_leetcode_solved_volume(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """7. LeetCode solved increase and decrease."""
    # Increase: +10 solved (+33.3%, above thresholds)
    curr_stats_inc = base_leetcode.problem_stats.model_copy(update={"total_solved": 40})
    curr_inc = base_leetcode.model_copy(update={"problem_stats": curr_stats_inc})
    res_inc = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr_inc,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    trigger = next((t for t in res_inc.triggers if t.metric_name == "leetcode_solved"), None)
    assert trigger is not None
    assert trigger.change_type == "increase"

    # Decrease: -10 solved (-33.3%, above thresholds)
    curr_stats_dec = base_leetcode.problem_stats.model_copy(update={"total_solved": 20})
    curr_dec = base_leetcode.model_copy(update={"problem_stats": curr_stats_dec})
    res_dec = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr_dec,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    trigger_dec = next((t for t in res_dec.triggers if t.metric_name == "leetcode_solved"), None)
    assert trigger_dec is not None
    assert trigger_dec.change_type == "decrease"

def test_leetcode_solved_baseline_zero(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """8. LeetCode historical solved count = 0 and current count above threshold."""
    hist_stats = base_leetcode.problem_stats.model_copy(update={"total_solved": 0})
    hist = base_leetcode.model_copy(update={"problem_stats": hist_stats})
    curr_stats = base_leetcode.problem_stats.model_copy(update={"total_solved": 8})
    curr = base_leetcode.model_copy(update={"problem_stats": curr_stats})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr,
        historical_lc=hist,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    trigger = next((t for t in res.triggers if t.metric_name == "leetcode_solved"), None)
    assert trigger is not None
    assert trigger.change_type == "increase"
    assert trigger.percent_change is None
    assert trigger.absolute_change == 8.0
    assert trigger.metadata.get("baseline_zero") is True

def test_leetcode_difficulty_ratio_increase(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """9. LeetCode difficulty ratio increase."""
    # Historical ratio: (10 + 10)/30 = 0.667
    # Current: Easy = 10, Medium = 15, Hard = 15, Total = 40 -> Ratio = 30/40 = 0.75 (+0.083, above 0.08 threshold)
    curr_stats = base_leetcode.problem_stats.model_copy(update={
        "total_solved": 40,
        "medium_solved": 15,
        "hard_solved": 15
    })
    curr = base_leetcode.model_copy(update={"problem_stats": curr_stats})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    trigger = next((t for t in res.triggers if t.metric_name == "leetcode_difficulty"), None)
    assert trigger is not None
    assert trigger.change_type == "increase"

def test_leetcode_difficulty_ratio_decrease(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """10. LeetCode difficulty ratio decrease."""
    # Historical ratio: (10 + 10)/30 = 0.667
    # Current: Easy = 22, Medium = 10, Hard = 8, Total = 40 -> Ratio = 18/40 = 0.45 (-0.217, below -0.08 threshold)
    curr_stats = base_leetcode.problem_stats.model_copy(update={
        "total_solved": 40,
        "easy_solved": 22,
        "medium_solved": 10,
        "hard_solved": 8
    })
    curr = base_leetcode.model_copy(update={"problem_stats": curr_stats})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    trigger = next((t for t in res.triggers if t.metric_name == "leetcode_difficulty"), None)
    assert trigger is not None
    assert trigger.change_type == "decrease"

def test_leetcode_difficulty_with_zero_solved(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """11. LeetCode difficulty calculation with total_solved = 0 (should not produce trigger)."""
    curr_stats = base_leetcode.problem_stats.model_copy(update={"total_solved": 0})
    curr = base_leetcode.model_copy(update={"problem_stats": curr_stats})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    # total_solved = 0 is safe, no difficulty triggers
    assert not any(t.metric_name == "leetcode_difficulty" for t in res.triggers)

def test_leetcode_consistency(base_leetcode: LeetCodeAnalysisResultSchema) -> None:
    """12. LeetCode consistency changes."""
    # Consistency increase: +0.20
    curr_inc = base_leetcode.model_copy(update={"contribution_consistency": 0.70})
    res_inc = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=curr_inc,
        historical_lc=base_leetcode,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_inc.triggers) == 1
    assert res_inc.triggers[0].metric_name == "leetcode_consistency"
    assert res_inc.triggers[0].change_type == "increase"

def test_overall_score_changes(base_score: DeveloperScoreResultSchema) -> None:
    """13. Overall developer score increase and decrease."""
    # Increase: +60 (above 50 threshold)
    curr_inc = base_score.model_copy(update={"overall_score": 560})
    res_inc = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=curr_inc,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_inc.triggers) == 1
    assert res_inc.triggers[0].metric_name == "score_overall"
    assert res_inc.triggers[0].change_type == "increase"

    # Decrease: -60
    curr_dec = base_score.model_copy(update={"overall_score": 440})
    res_dec = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=curr_dec,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_dec.triggers) == 1
    assert res_dec.triggers[0].metric_name == "score_overall"
    assert res_dec.triggers[0].change_type == "decrease"

def test_category_scores_independent(base_score: DeveloperScoreResultSchema) -> None:
    """14. Each category score comparison independently: score_consistency, score_problem_solving, score_open_source."""
    # consistency increase: +30 (above 25 threshold)
    curr_c = base_score.model_copy(update={"consistency_score": 180})
    res_c = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=curr_c,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_c.triggers) == 1
    assert res_c.triggers[0].metric_name == "score_consistency"
    assert res_c.triggers[0].change_type == "increase"

    # problem solving decrease: -30
    curr_ps = base_score.model_copy(update={"problem_solving_score": 120})
    res_ps = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=curr_ps,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_ps.triggers) == 1
    assert res_ps.triggers[0].metric_name == "score_problem_solving"
    assert res_ps.triggers[0].change_type == "decrease"

    # open source increase: +30
    curr_os = base_score.model_copy(update={"open_source_score": 230})
    res_os = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=curr_os,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_os.triggers) == 1
    assert res_os.triggers[0].metric_name == "score_open_source"
    assert res_os.triggers[0].change_type == "increase"

def test_missing_data_handling(
    base_github: GitHubAnalysisResultSchema,
    base_leetcode: LeetCodeAnalysisResultSchema,
    base_score: DeveloperScoreResultSchema
) -> None:
    """15, 16, 17. Missing data (None) is safely skipped without false triggers."""
    res_gh = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_gh.triggers) == 0

    res_lc = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=base_leetcode,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_lc.triggers) == 0

    res_score = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=None,
        historical_gh=None,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=base_score,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res_score.triggers) == 0

def test_percent_change_and_insignificant_changes(base_github: GitHubAnalysisResultSchema) -> None:
    """18, 19. Check percent change math and ensure insignificant changes produce no triggers."""
    # 10% change is below 20% percent threshold (commits 100 -> 110: +10 absolute is met, but only 10.0% is not met)
    current = base_github.model_copy(update={"total_commits": 110})
    res = AnalyticsComparator.compare(
        user_id=uuid.uuid4(),
        current_gh=current,
        historical_gh=base_github,
        current_lc=None,
        historical_lc=None,
        current_score=None,
        historical_score=None,
        current_date=date(2026, 8, 27),
        historical_date=date(2026, 8, 20)
    )
    assert len(res.triggers) == 0
