import uuid
from datetime import date
import pytest

from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema
from app.services.scoring.calculator import DeveloperScoreCalculator

@pytest.fixture
def base_github_result() -> GitHubAnalysisResultSchema:
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
        total_commits=150,
        commit_frequency_per_day=1.5,
        active_days_count=3,
        contribution_consistency=0.6,
        current_streak=7,
        longest_streak=10
    )

@pytest.fixture
def base_leetcode_result() -> LeetCodeAnalysisResultSchema:
    return LeetCodeAnalysisResultSchema(
        user_id=uuid.uuid4(),
        username="testuser",
        problem_stats=LeetCodeProblemStatsSchema(
            easy_solved=10,
            medium_solved=5,
            hard_solved=2,
            total_solved=17,
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
        contribution_consistency=0.4,
        current_streak=5,
        longest_streak=6
    )

def test_score_both_platforms_connected(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify scoring behavior with both platforms connected."""
    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    
    # 1. Consistency:
    # GitHub Consistency: (0.6 * 100) + (7 / 14 * 50) = 60 + 25 = 85
    # LeetCode Consistency: (0.4 * 100) + (5 / 14 * 50) = 40 + 17.857 = 57.857
    # Consistency raw: 85 + 57.857 = 142.857 -> round(142.857) = 143
    assert result.consistency_score == 143

    # 2. Depth:
    # Easy Solved: min(10, 50) * 1 = 10
    # Medium Solved: min(5, 50) * 3 = 15
    # Hard Solved: min(2, 25) * 6 = 12
    # Depth raw: 10 + 15 + 12 = 37 -> round(37) = 37
    assert result.problem_solving_score == 37

    # 3. Impact:
    # Repos: min(5, 10)/10 * 50 = 25
    # Commits: min(150, 500)/500 * 100 = 30
    # Stars: min(10, 50)/50 * 120 = 24
    # Forks: min(2, 10)/10 * 80 = 16
    # Impact raw: 25 + 30 + 24 + 16 = 95 -> round(95) = 95
    assert result.open_source_score == 95

    # Overall: 143 + 37 + 95 = 275
    assert result.overall_score == 275

def test_score_only_github_connected(base_github_result: GitHubAnalysisResultSchema) -> None:
    """Verify consistency normalization scales up GitHub consistency when LeetCode is missing."""
    result = DeveloperScoreCalculator.calculate(base_github_result, None)
    
    # GitHub Consistency: (0.6 * 100) + (7 / 14 * 50) = 85
    # Scaled consistency: 85 * 2 = 170
    assert result.consistency_score == 170
    # Depth is 0 because LeetCode is None
    assert result.problem_solving_score == 0
    # Open Source Impact: 95
    assert result.open_source_score == 95
    assert result.overall_score == 265

def test_score_only_leetcode_connected(base_leetcode_result: LeetCodeAnalysisResultSchema) -> None:
    """Verify consistency normalization scales up LeetCode consistency when GitHub is missing."""
    result = DeveloperScoreCalculator.calculate(None, base_leetcode_result)
    
    # LeetCode Consistency: (0.4 * 100) + (5 / 14 * 50) = 57.857
    # Scaled consistency: 57.857 * 2 = 115.714 -> round(115.714) = 116
    assert result.consistency_score == 116
    # Depth: 37
    assert result.problem_solving_score == 37
    # Impact: 0
    assert result.open_source_score == 0
    assert result.overall_score == 153

def test_score_neither_connected() -> None:
    """Verify that if both inputs are None, the calculator defaults cleanly to a score of 0."""
    result = DeveloperScoreCalculator.calculate(None, None)
    assert result.overall_score == 0
    assert result.consistency_score == 0
    assert result.problem_solving_score == 0
    assert result.open_source_score == 0

def test_score_all_zero_metrics(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify that zero metrics yield 0 scores cleanly."""
    base_github_result.contribution_consistency = 0.0
    base_github_result.current_streak = 0
    base_github_result.total_commits = 0
    base_github_result.repo_stats.total_repositories = 0
    base_github_result.repo_stats.total_stars = 0
    base_github_result.repo_stats.total_forks = 0

    base_leetcode_result.contribution_consistency = 0.0
    base_leetcode_result.current_streak = 0
    base_leetcode_result.problem_stats.easy_solved = 0
    base_leetcode_result.problem_stats.medium_solved = 0
    base_leetcode_result.problem_stats.hard_solved = 0

    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    assert result.overall_score == 0
    assert result.consistency_score == 0
    assert result.problem_solving_score == 0
    assert result.open_source_score == 0

def test_score_above_maximum_clamping(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify that scores clamp exactly to their category caps and maximum overall limits."""
    base_github_result.contribution_consistency = 2.0  # Above 1.0 limit
    base_github_result.current_streak = 25  # Above 14 limit
    base_github_result.total_commits = 1000  # Above 500 limit
    base_github_result.repo_stats.total_repositories = 20  # Above 10 limit
    base_github_result.repo_stats.total_stars = 100  # Above 50 limit
    base_github_result.repo_stats.total_forks = 20  # Above 10 limit

    base_leetcode_result.contribution_consistency = 1.5  # Above 1.0 limit
    base_leetcode_result.current_streak = 30  # Above 14 limit
    base_leetcode_result.problem_stats.easy_solved = 100  # Above 50 limit
    base_leetcode_result.problem_stats.medium_solved = 100  # Above 50 limit
    base_leetcode_result.problem_stats.hard_solved = 50  # Above 25 limit

    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    assert result.consistency_score == 300
    assert result.problem_solving_score == 350
    assert result.open_source_score == 350
    assert result.overall_score == 1000

def test_score_none_values(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify that None values default safely to 0 and do not raise errors."""
    base_github_result.contribution_consistency = None
    base_github_result.current_streak = None
    base_github_result.total_commits = None
    base_github_result.repo_stats.total_repositories = None
    base_github_result.repo_stats.total_stars = None
    base_github_result.repo_stats.total_forks = None

    base_leetcode_result.contribution_consistency = None
    base_leetcode_result.current_streak = None
    base_leetcode_result.problem_stats.easy_solved = None
    base_leetcode_result.problem_stats.medium_solved = None
    base_leetcode_result.problem_stats.hard_solved = None

    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    assert result.overall_score == 0
    assert result.consistency_score == 0
    assert result.problem_solving_score == 0
    assert result.open_source_score == 0

def test_score_negative_values(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify that negative inputs clamp to 0 and do not yield negative scores."""
    base_github_result.contribution_consistency = -0.5
    base_github_result.current_streak = -10
    base_github_result.total_commits = -5
    base_github_result.repo_stats.total_repositories = -20
    base_github_result.repo_stats.total_stars = -150
    base_github_result.repo_stats.total_forks = -10

    base_leetcode_result.contribution_consistency = -1.0
    base_leetcode_result.current_streak = -50
    base_leetcode_result.problem_stats.easy_solved = -5
    base_leetcode_result.problem_stats.medium_solved = -10
    base_leetcode_result.problem_stats.hard_solved = -1

    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    assert result.overall_score == 0
    assert result.consistency_score == 0
    assert result.problem_solving_score == 0
    assert result.open_source_score == 0

def test_roadmap_examples(
    base_github_result: GitHubAnalysisResultSchema,
    base_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify the calculations for the exact examples described in the roadmap specification."""
    
    # Example A: Balanced Active User (Both connected)
    # GitHub: consistency = 0.8, current_streak = 7, repos = 12, commits = 600, stars = 15, forks = 2
    # LeetCode: consistency = 0.6, current_streak = 5, easy = 45, medium = 20, hard = 5
    base_github_result.contribution_consistency = 0.8
    base_github_result.current_streak = 7
    base_github_result.repo_stats.total_repositories = 12
    base_github_result.total_commits = 600
    base_github_result.repo_stats.total_stars = 15
    base_github_result.repo_stats.total_forks = 2

    base_leetcode_result.contribution_consistency = 0.6
    base_leetcode_result.current_streak = 5
    base_leetcode_result.problem_stats.easy_solved = 45
    base_leetcode_result.problem_stats.medium_solved = 20
    base_leetcode_result.problem_stats.hard_solved = 5

    result = DeveloperScoreCalculator.calculate(base_github_result, base_leetcode_result)
    assert result.consistency_score == 183
    assert result.problem_solving_score == 135
    assert result.open_source_score == 202
    assert result.overall_score == 520

    # Example B: User with only LeetCode connected (GitHub missing)
    result_b = DeveloperScoreCalculator.calculate(None, base_leetcode_result)
    assert result_b.consistency_score == 156
    assert result_b.problem_solving_score == 135
    assert result_b.open_source_score == 0
    assert result_b.overall_score == 291
