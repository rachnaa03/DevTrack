"""
Unit tests for MilestoneEvaluator and MilestoneService (Task 12.3).

Verifies:
- Deterministic milestone evaluations across all criteria (LeetCode, GitHub, DeveloperScore).
- Null/empty analytics handling.
- Boundary condition checks.
- Deduplication: already earned milestones are not re-inserted.
- Synchronization of timeline events on newly earned milestones.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.github_analytics import GitHubAnalytics
from app.models.leetcode_analytics import LeetCodeAnalytics
from app.models.milestone import Milestone
from app.models.score import DeveloperScore
from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.milestone import MilestoneRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.dashboard import MilestonesResponse
from app.services.dashboard.milestones import (
    MILESTONE_COMMITS_CENTURY,
    MILESTONE_CONSISTENCY_CHAMPION,
    MILESTONE_FIRST_HARD,
    MILESTONE_FIRST_PROBLEM,
    MILESTONE_LEETCODE_CENTURY,
    MILESTONE_REPO_BUILDER,
    MILESTONE_SCORE_MASTER,
    MILESTONE_STAR_COLLECTOR,
    MilestoneEvaluator,
    MilestoneService,
)

USER_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Evaluator Unit Tests
# ---------------------------------------------------------------------------

def test_milestone_evaluator_all_none() -> None:
    """Empty inputs should yield no milestones."""
    result = MilestoneEvaluator.evaluate(gh=None, lc=None, score=None)
    assert result == []


def test_milestone_evaluator_leetcode_rules() -> None:
    """Verify LeetCode specific milestones."""
    lc = MagicMock(spec=LeetCodeAnalytics)
    lc.total_solved = 150
    lc.hard_solved = 5
    lc.current_streak = 7
    lc.longest_streak = 10

    achieved = MilestoneEvaluator.evaluate(gh=None, lc=lc, score=None)
    names = {r.name for r in achieved}

    assert MILESTONE_FIRST_PROBLEM.name in names
    assert MILESTONE_FIRST_HARD.name in names
    assert MILESTONE_LEETCODE_CENTURY.name in names
    assert MILESTONE_CONSISTENCY_CHAMPION.name in names


def test_milestone_evaluator_github_rules() -> None:
    """Verify GitHub specific milestones."""
    gh = MagicMock(spec=GitHubAnalytics)
    gh.total_commits = 200
    gh.total_repositories = 10
    gh.total_stars = 25

    achieved = MilestoneEvaluator.evaluate(gh=gh, lc=None, score=None)
    names = {r.name for r in achieved}

    assert MILESTONE_COMMITS_CENTURY.name in names
    assert MILESTONE_REPO_BUILDER.name in names
    assert MILESTONE_STAR_COLLECTOR.name in names


def test_milestone_evaluator_score_rules() -> None:
    """Verify Developer Score milestone."""
    score = MagicMock(spec=DeveloperScore)
    score.overall_score = 750

    achieved = MilestoneEvaluator.evaluate(gh=None, lc=None, score=score)
    names = {r.name for r in achieved}

    assert MILESTONE_SCORE_MASTER.name in names


def test_milestone_evaluator_boundary_conditions() -> None:
    """Verify values below threshold do not trigger milestones."""
    lc = MagicMock(spec=LeetCodeAnalytics)
    lc.total_solved = 0
    lc.hard_solved = 0
    lc.current_streak = 4
    lc.longest_streak = 4

    gh = MagicMock(spec=GitHubAnalytics)
    gh.total_commits = 99
    gh.total_repositories = 4
    gh.total_stars = 9

    score = MagicMock(spec=DeveloperScore)
    score.overall_score = 699

    achieved = MilestoneEvaluator.evaluate(gh=gh, lc=lc, score=score)
    assert achieved == []


# ---------------------------------------------------------------------------
# Service Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_milestone_service_awards_new_milestones() -> None:
    """Verify new qualifying milestones are created and saved alongside timeline events."""
    milestone_repo = MagicMock(spec=MilestoneRepository)
    milestone_repo.get_milestone_names_by_user_id = AsyncMock(return_value=set())
    milestone_repo.create_milestone = AsyncMock()

    m_obj = MagicMock(spec=Milestone)
    m_obj.name = "First Problem Solved"
    m_obj.description = "Solved first LeetCode problem."
    m_obj.badge_url = "https://assets.devtrack.com/badges/first_problem.png"
    m_obj.achieved_at = datetime.now(timezone.utc)
    milestone_repo.get_milestones_by_user_id = AsyncMock(return_value=[m_obj])

    timeline_repo = MagicMock(spec=TimelineRepository)
    timeline_repo.create_event = AsyncMock()

    gh_repo = MagicMock(spec=GitHubAnalyticsRepository)
    gh_repo.get_latest_by_user_id = AsyncMock(return_value=None)

    lc_obj = MagicMock(spec=LeetCodeAnalytics)
    lc_obj.total_solved = 1
    lc_obj.hard_solved = 0
    lc_obj.current_streak = 0
    lc_obj.longest_streak = 0
    lc_repo = MagicMock(spec=LeetCodeAnalyticsRepository)
    lc_repo.get_latest_by_user_id = AsyncMock(return_value=lc_obj)

    score_repo = MagicMock(spec=DeveloperScoreRepository)
    score_repo.get_latest_by_user_id = AsyncMock(return_value=None)

    service = MilestoneService(
        milestone_repo=milestone_repo,
        timeline_repo=timeline_repo,
        github_repo=gh_repo,
        leetcode_repo=lc_repo,
        score_repo=score_repo,
    )

    result = await service.get_milestones(USER_ID)
    assert isinstance(result, MilestonesResponse)
    assert len(result.milestones) == 1
    assert result.milestones[0].name == "First Problem Solved"

    milestone_repo.create_milestone.assert_awaited_once()
    timeline_repo.create_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_milestone_service_deduplication() -> None:
    """Verify already existing milestones are not re-inserted."""
    milestone_repo = MagicMock(spec=MilestoneRepository)
    milestone_repo.get_milestone_names_by_user_id = AsyncMock(
        return_value={"First Problem Solved"}
    )
    milestone_repo.create_milestone = AsyncMock()
    milestone_repo.get_milestones_by_user_id = AsyncMock(return_value=[])

    timeline_repo = MagicMock(spec=TimelineRepository)
    timeline_repo.create_event = AsyncMock()

    gh_repo = MagicMock(spec=GitHubAnalyticsRepository)
    gh_repo.get_latest_by_user_id = AsyncMock(return_value=None)

    lc_obj = MagicMock(spec=LeetCodeAnalytics)
    lc_obj.total_solved = 1
    lc_obj.hard_solved = 0
    lc_obj.current_streak = 0
    lc_obj.longest_streak = 0
    lc_repo = MagicMock(spec=LeetCodeAnalyticsRepository)
    lc_repo.get_latest_by_user_id = AsyncMock(return_value=lc_obj)

    score_repo = MagicMock(spec=DeveloperScoreRepository)
    score_repo.get_latest_by_user_id = AsyncMock(return_value=None)

    service = MilestoneService(
        milestone_repo=milestone_repo,
        timeline_repo=timeline_repo,
        github_repo=gh_repo,
        leetcode_repo=lc_repo,
        score_repo=score_repo,
    )

    await service.get_milestones(USER_ID)

    milestone_repo.create_milestone.assert_not_awaited()
    timeline_repo.create_event.assert_not_awaited()
