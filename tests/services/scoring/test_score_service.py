import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.models.score import DeveloperScore
from app.repositories.score import DeveloperScoreRepository
from app.services.scoring.service import DeveloperScoreService
from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema

@pytest.fixture
def mock_score_repo() -> MagicMock:
    return MagicMock(spec=DeveloperScoreRepository)

@pytest.fixture
def score_service(mock_score_repo: MagicMock) -> DeveloperScoreService:
    return DeveloperScoreService(mock_score_repo)

@pytest.fixture
def sample_github_result() -> GitHubAnalysisResultSchema:
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
def sample_leetcode_result() -> LeetCodeAnalysisResultSchema:
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

@pytest.mark.asyncio
async def test_record_score_success_both_platforms(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock,
    sample_github_result: GitHubAnalysisResultSchema,
    sample_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify record_score runs calculator, maps fields, and creates a DeveloperScore record via repository."""
    user_uuid = uuid.uuid4()
    
    mock_score_repo.create = AsyncMock(side_effect=lambda x: x)  # Returns input directly
    
    result = await score_service.record_score(user_uuid, sample_github_result, sample_leetcode_result)
    
    assert result.user_id == user_uuid
    assert result.overall_score == 275  # Verified via pure calculator
    assert result.consistency_score == 143
    assert result.problem_solving_score == 37
    assert result.open_source_score == 95
    assert result.score_version == "v1"
    
    mock_score_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_record_score_success_github_only(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock,
    sample_github_result: GitHubAnalysisResultSchema
) -> None:
    """Verify record_score operates correctly with only GitHub connected."""
    user_uuid = uuid.uuid4()
    mock_score_repo.create = AsyncMock(side_effect=lambda x: x)
    
    result = await score_service.record_score(user_uuid, sample_github_result, None)
    
    assert result.user_id == user_uuid
    assert result.overall_score == 265  # Scaled consistency (170) + depth (0) + impact (95)
    assert result.consistency_score == 170
    assert result.problem_solving_score == 0
    assert result.open_source_score == 95
    
    mock_score_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_record_score_success_leetcode_only(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock,
    sample_leetcode_result: LeetCodeAnalysisResultSchema
) -> None:
    """Verify record_score operates correctly with only LeetCode connected."""
    user_uuid = uuid.uuid4()
    mock_score_repo.create = AsyncMock(side_effect=lambda x: x)
    
    result = await score_service.record_score(user_uuid, None, sample_leetcode_result)
    
    assert result.user_id == user_uuid
    assert result.overall_score == 153  # Scaled consistency (116) + depth (37) + impact (0)
    assert result.consistency_score == 116
    assert result.problem_solving_score == 37
    assert result.open_source_score == 0
    
    mock_score_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_record_score_neither_connected(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock
) -> None:
    """Verify record_score defaults to 0 scores when both are None."""
    user_uuid = uuid.uuid4()
    mock_score_repo.create = AsyncMock(side_effect=lambda x: x)
    
    result = await score_service.record_score(user_uuid, None, None)
    
    assert result.overall_score == 0
    assert result.consistency_score == 0
    assert result.problem_solving_score == 0
    assert result.open_source_score == 0
    
    mock_score_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_record_score_failure_rolls_back(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock,
    sample_github_result: GitHubAnalysisResultSchema
) -> None:
    """Verify that service propagates repository exception when persistence fails."""
    user_uuid = uuid.uuid4()
    mock_score_repo.create = AsyncMock(side_effect=Exception("Database persistence error"))
    
    with pytest.raises(Exception, match="Database persistence error"):
        await score_service.record_score(user_uuid, sample_github_result, None)
    
    mock_score_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_latest_score(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock
) -> None:
    """Verify get_latest_score fetches from the repository correctly."""
    user_uuid = uuid.uuid4()
    mock_score = DeveloperScore(user_id=user_uuid, overall_score=500)
    mock_score_repo.get_latest_by_user_id = AsyncMock(return_value=mock_score)
    
    result = await score_service.get_latest_score(user_uuid)
    
    assert result == mock_score
    mock_score_repo.get_latest_by_user_id.assert_called_once_with(user_uuid)

@pytest.mark.asyncio
async def test_get_score_history(
    score_service: DeveloperScoreService,
    mock_score_repo: MagicMock
) -> None:
    """Verify get_score_history fetches chronological scores from the repository using the limit."""
    user_uuid = uuid.uuid4()
    mock_scores = [DeveloperScore(user_id=user_uuid, overall_score=500)]
    mock_score_repo.get_history = AsyncMock(return_value=mock_scores)
    
    result = await score_service.get_score_history(user_uuid, limit=15)
    
    assert result == mock_scores
    mock_score_repo.get_history.assert_called_once_with(user_uuid, limit=15)
