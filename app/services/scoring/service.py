from uuid import UUID

from app.models.score import DeveloperScore
from app.repositories.score import DeveloperScoreRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.services.scoring.calculator import DeveloperScoreCalculator

class DeveloperScoreService:
    """Service layer coordinating Developer Score calculation and database persistence."""

    def __init__(self, score_repo: DeveloperScoreRepository):
        self.score_repo = score_repo

    async def record_score(
        self,
        user_id: UUID,
        github_analysis: GitHubAnalysisResultSchema | None,
        leetcode_analysis: LeetCodeAnalysisResultSchema | None
    ) -> DeveloperScore:
        """
        Calculate score and persist a new DeveloperScore record.
        Always logs a new record to preserve history.
        """
        # 1. Run pure calculator logic
        result = DeveloperScoreCalculator.calculate(github_analysis, leetcode_analysis)

        # 2. Build the database record
        score_record = DeveloperScore(
            user_id=user_id,
            overall_score=result.overall_score,
            consistency_score=result.consistency_score,
            problem_solving_score=result.problem_solving_score,
            open_source_score=result.open_source_score,
            score_version=result.score_version
        )

        # 3. Persist record to database via repository
        return await self.score_repo.create(score_record)

    async def get_latest_score(self, user_id: UUID) -> DeveloperScore | None:
        """Fetch the latest score record computed for the user."""
        return await self.score_repo.get_latest_by_user_id(user_id)

    async def get_score_history(self, user_id: UUID, limit: int = 10) -> list[DeveloperScore]:
        """Fetch chronological score history records, ordered by computed_at DESC."""
        return await self.score_repo.get_history(user_id, limit=limit)
