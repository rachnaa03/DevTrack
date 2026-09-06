"""
Milestone Service & Evaluator — Task 12.3

Evaluates and persists developer achievements and milestone badges
(API_SPECIFICATION.md Section 4.4, SRS Section 3.6).

Rules are deterministic and derived from existing stored metrics:
- LeetCode problem solving volume, difficulty milestones, and streaks.
- GitHub commit volume, repository count, and star achievements.
- Developer Score thresholds.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.models.github_analytics import GitHubAnalytics
from app.models.leetcode_analytics import LeetCodeAnalytics
from app.models.milestone import Milestone
from app.models.profile import Profile
from app.models.score import DeveloperScore
from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.milestone import MilestoneRepository
from app.repositories.profile import ProfileRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.dashboard import MilestoneSchema, MilestonesResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MilestoneRule:
    """Definition of a deterministic milestone badge rule."""
    name: str
    description: str
    badge_url: str


# Predefined standard milestone definitions
MILESTONE_FIRST_PROBLEM = MilestoneRule(
    name="First Problem Solved",
    description="Solved first LeetCode problem.",
    badge_url="https://assets.devtrack.com/badges/first_problem.png",
)
MILESTONE_FIRST_HARD = MilestoneRule(
    name="First Hard Problem Solved",
    description="Solved LeetCode Hard problem.",
    badge_url="https://assets.devtrack.com/badges/first_hard.png",
)
MILESTONE_LEETCODE_CENTURY = MilestoneRule(
    name="LeetCode Century",
    description="Solved 100 LeetCode problems.",
    badge_url="https://assets.devtrack.com/badges/leetcode_100.png",
)
MILESTONE_CONSISTENCY_CHAMPION = MilestoneRule(
    name="Consistency Champion",
    description="Maintain a LeetCode streak for 5 consecutive days.",
    badge_url="https://assets.devtrack.com/badges/consistency_5.png",
)
MILESTONE_COMMITS_CENTURY = MilestoneRule(
    name="Century of Commits",
    description="Reached 100 lifetime GitHub commits.",
    badge_url="https://assets.devtrack.com/badges/commits_100.png",
)
MILESTONE_REPO_BUILDER = MilestoneRule(
    name="Repository Builder",
    description="Created or contributed to 5 public GitHub repositories.",
    badge_url="https://assets.devtrack.com/badges/repos_5.png",
)
MILESTONE_STAR_COLLECTOR = MilestoneRule(
    name="Star Collector",
    description="Accumulated 10 stars across GitHub repositories.",
    badge_url="https://assets.devtrack.com/badges/stars_10.png",
)
MILESTONE_SCORE_MASTER = MilestoneRule(
    name="Score Master",
    description="Achieved a Developer Score of 700 or higher.",
    badge_url="https://assets.devtrack.com/badges/score_700.png",
)


class MilestoneEvaluator:
    """Pure evaluation helper for developer milestones."""

    @staticmethod
    def evaluate(
        gh: GitHubAnalytics | None,
        lc: LeetCodeAnalytics | None,
        score: DeveloperScore | None,
    ) -> list[MilestoneRule]:
        """
        Evaluate which milestone rules are satisfied by the current developer analytics.
        """
        achieved: list[MilestoneRule] = []

        if lc is not None:
            if lc.total_solved is not None and lc.total_solved >= 1:
                achieved.append(MILESTONE_FIRST_PROBLEM)
            if lc.hard_solved is not None and lc.hard_solved >= 1:
                achieved.append(MILESTONE_FIRST_HARD)
            if lc.total_solved is not None and lc.total_solved >= 100:
                achieved.append(MILESTONE_LEETCODE_CENTURY)
            streak = lc.current_streak or lc.longest_streak or 0
            if streak >= 5:
                achieved.append(MILESTONE_CONSISTENCY_CHAMPION)

        if gh is not None:
            if gh.total_commits is not None and gh.total_commits >= 100:
                achieved.append(MILESTONE_COMMITS_CENTURY)
            if gh.total_repositories is not None and gh.total_repositories >= 5:
                achieved.append(MILESTONE_REPO_BUILDER)
            if gh.total_stars is not None and gh.total_stars >= 10:
                achieved.append(MILESTONE_STAR_COLLECTOR)

        if score is not None:
            if score.overall_score is not None and score.overall_score >= 700:
                achieved.append(MILESTONE_SCORE_MASTER)

        return achieved


class MilestoneService:
    """
    Service responsible for milestone evaluation, persistence, and retrieval.
    """

    def __init__(
        self,
        milestone_repo: MilestoneRepository,
        timeline_repo: TimelineRepository,
        github_repo: GitHubAnalyticsRepository,
        leetcode_repo: LeetCodeAnalyticsRepository,
        score_repo: DeveloperScoreRepository,
    ) -> None:
        self.milestone_repo = milestone_repo
        self.timeline_repo = timeline_repo
        self.github_repo = github_repo
        self.leetcode_repo = leetcode_repo
        self.score_repo = score_repo

    async def get_milestones(self, user_id: UUID) -> MilestonesResponse:
        """
        Evaluate any newly earned milestones, persist them, and return all milestones.
        """
        # 1. Fetch current analytics and score
        gh = await self.github_repo.get_latest_by_user_id(user_id)
        lc = await self.leetcode_repo.get_latest_by_user_id(user_id)
        score = await self.score_repo.get_latest_by_user_id(user_id)

        # 2. Get existing milestone names to avoid duplicates
        existing_names = await self.milestone_repo.get_milestone_names_by_user_id(user_id)

        # 3. Evaluate rules
        qualified_rules = MilestoneEvaluator.evaluate(gh, lc, score)
        now = datetime.now(timezone.utc)

        for rule in qualified_rules:
            if rule.name not in existing_names:
                # Persist milestone
                await self.milestone_repo.create_milestone(
                    user_id=user_id,
                    name=rule.name,
                    description=rule.description,
                    badge_url=rule.badge_url,
                    achieved_at=now,
                )
                # Persist corresponding timeline event
                await self.timeline_repo.create_event(
                    user_id=user_id,
                    event_type="milestone_earned",
                    title=rule.name,
                    description=rule.description,
                    event_date=now.date(),
                )
                logger.info("Milestone '%s' awarded to user_id=%s", rule.name, user_id)

        # 4. Fetch all earned milestones
        all_milestones = await self.milestone_repo.get_milestones_by_user_id(user_id)

        return MilestonesResponse(
            milestones=[
                MilestoneSchema(
                    name=m.name,
                    description=m.description,
                    badge_url=m.badge_url,
                    achieved_at=m.achieved_at,
                )
                for m in all_milestones
            ]
        )
