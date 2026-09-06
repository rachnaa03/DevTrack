"""
Unit tests for RecommendationService (Task 11.3).

All tests are pure — no database, no HTTP, no FastAPI dependencies.

Strategy
--------
- RecommendationRepository is fully mocked using AsyncMock so each test
  specifies exactly what the repository returns.
- RecommendationEvaluator is NOT mocked — we use real analytics schemas
  to produce real candidates, ensuring integration between Task 11.1 and
  Task 11.3 is exercised.
- Recommendation ORM model is NOT mocked — we use real instances with the
  correct status field to test lifecycle behavior.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.models.recommendation import Recommendation
from app.repositories.recommendation import RecommendationRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema, RepositoryStatsSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema, LeetCodeProblemStatsSchema
from app.schemas.recommendation_result import RecommendationRunResultSchema
from app.schemas.recommendations import RecommendationCandidateSchema
from app.schemas.score import DeveloperScoreResultSchema, ScoreSubcomponentSchema
from app.services.recommendations.service import RecommendationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def _make_repo(
    get_by_rule_key_return=None,
    get_active_by_user_return=None,
    create_side_effect=None,
    update_status_side_effect=None,
) -> RecommendationRepository:
    """Build a fully-mocked RecommendationRepository."""
    repo = MagicMock(spec=RecommendationRepository)
    repo.get_by_rule_key = AsyncMock(return_value=get_by_rule_key_return)
    repo.get_active_by_user = AsyncMock(return_value=get_active_by_user_return or [])
    repo.get_all_by_user = AsyncMock(return_value=[])
    repo.create = AsyncMock(side_effect=create_side_effect or (lambda r: r))
    repo.update_status = AsyncMock(
        side_effect=update_status_side_effect or (lambda r, s: setattr(r, "status", s) or r)
    )
    return repo


def _existing_rec(rule_id: str, status: str = "active") -> Recommendation:
    """Build a mock Recommendation ORM record in a given status."""
    rec = MagicMock(spec=Recommendation)
    rec.rule_id = rule_id
    rec.rule_version = "v1"
    rec.status = status
    rec.user_id = USER_ID
    return rec


def _github(
    total_repositories: int = 10,
    total_stars: int = 20,
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
            total_forks=5,
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
        commit_frequency_per_day=None,
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


def _make_service(repo: RecommendationRepository) -> RecommendationService:
    return RecommendationService(recommendation_repo=repo)


# ---------------------------------------------------------------------------
# Test: No rules fire
# ---------------------------------------------------------------------------

class TestNoRulesFire:
    @pytest.mark.asyncio
    async def test_no_candidates_no_db_writes(self) -> None:
        """When no rules trigger, no records are created or resolved."""
        repo = _make_repo(get_active_by_user_return=[])
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(),
            leetcode_analysis=_leetcode(),
            score_result=_score(),
        )

        assert isinstance(result, RecommendationRunResultSchema)
        assert result.user_id == USER_ID
        assert result.total_candidates == 0
        assert result.new == 0
        assert result.skipped == 0
        assert result.resolved == 0
        assert result.new_recommendations == []
        assert result.resolved_rule_ids == []
        repo.create.assert_not_called()
        repo.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_data_at_all_no_db_writes(self) -> None:
        """All analytics None → no candidates → no writes."""
        repo = _make_repo()
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=None,
            leetcode_analysis=None,
            score_result=None,
        )

        assert result.total_candidates == 0
        assert result.new == 0
        repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# Test: One rule fires, no existing record
# ---------------------------------------------------------------------------

class TestSingleNewRecommendation:
    @pytest.mark.asyncio
    async def test_one_candidate_creates_one_record(self) -> None:
        """A single fired rule with no existing record creates exactly one DB row."""
        repo = _make_repo(
            get_by_rule_key_return=None,  # no existing record
            get_active_by_user_return=[],
        )
        service = _make_service(repo)

        # LC-DIFF-001 fires: hard ratio too low
        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=None,
            leetcode_analysis=lc,
            score_result=None,
        )

        assert result.new >= 1
        assert result.skipped == 0
        assert result.resolved == 0
        assert len(result.new_recommendations) == result.new
        repo.create.assert_called()

    @pytest.mark.asyncio
    async def test_created_recommendation_has_correct_fields(self) -> None:
        """The Recommendation record created must carry all candidate fields."""
        captured_records = []

        async def capture_create(rec):
            captured_records.append(rec)
            return rec

        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        repo.create = AsyncMock(side_effect=capture_create)
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=None,
            leetcode_analysis=lc,
            score_result=None,
        )

        assert len(captured_records) >= 1
        rec = captured_records[0]
        assert rec.user_id == USER_ID
        assert rec.rule_id != ""
        assert rec.rule_version == "v1"
        assert rec.status == "active"
        assert rec.title != ""
        assert rec.message != ""
        assert rec.category != ""
        assert rec.priority in {"HIGH", "MEDIUM", "LOW"}

    @pytest.mark.asyncio
    async def test_rule_id_and_version_persisted_correctly(self) -> None:
        """rule_id and rule_version on the persisted record must match the candidate."""
        captured = []

        async def capture_create(rec):
            captured.append(rec)
            return rec

        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        repo.create = AsyncMock(side_effect=capture_create)
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        for i, candidate in enumerate(result.new_recommendations):
            rec = captured[i]
            assert rec.rule_id == candidate.rule_id
            assert rec.rule_version == candidate.rule_version


# ---------------------------------------------------------------------------
# Test: Multiple candidates
# ---------------------------------------------------------------------------

class TestMultipleCandidates:
    @pytest.mark.asyncio
    async def test_multiple_candidates_all_new(self) -> None:
        """Multiple triggered rules all create new records when none exist."""
        # Every get_by_rule_key call returns None → all should be created
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        # Weak profile triggers several rules
        lc = _leetcode(
            easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60,
            contribution_consistency=0.20,
        )
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        assert result.new >= 2  # At least LC-DIFF-001 and LC-DIFF-002 or LC-CONS-001
        assert result.total_candidates == result.new + result.skipped
        assert repo.create.call_count == result.new

    @pytest.mark.asyncio
    async def test_results_include_priority_ordering_info(self) -> None:
        """new_recommendations should be in HIGH→MEDIUM→LOW order (from evaluator)."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        sc = _score(overall_score=300, consistency_score=50, problem_solving_score=40, open_source_score=50)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=None, score_result=sc
        )

        priorities = [c.priority for c in result.new_recommendations]
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        assert priorities == sorted(priorities, key=lambda p: priority_order[p])


# ---------------------------------------------------------------------------
# Test: Idempotency — existing record present
# ---------------------------------------------------------------------------

class TestIdempotency:
    @pytest.mark.asyncio
    async def test_existing_active_recommendation_is_skipped(self) -> None:
        """When a rule fires and an active record already exists, skip it."""
        existing = _existing_rec("LC-DIFF-001", status="active")
        repo = _make_repo(get_by_rule_key_return=existing, get_active_by_user_return=[existing])
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        assert result.skipped >= 1
        # create should not be called for the skipped candidate
        # (it may be called for other candidates if any; but LC-DIFF-001 should not call it)
        assert result.new == 0 or all(
            c.rule_id != "LC-DIFF-001" for c in result.new_recommendations
        )

    @pytest.mark.asyncio
    async def test_existing_dismissed_recommendation_is_skipped(self) -> None:
        """When a rule fires and a dismissed record exists, respect the dismissal (skip)."""
        existing = _existing_rec("LC-DIFF-001", status="dismissed")
        repo = _make_repo(get_by_rule_key_return=existing, get_active_by_user_return=[])
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        assert result.skipped >= 1

    @pytest.mark.asyncio
    async def test_existing_completed_recommendation_is_skipped(self) -> None:
        """When a rule fires and a completed record exists, skip it."""
        existing = _existing_rec("LC-DIFF-001", status="completed")
        repo = _make_repo(get_by_rule_key_return=existing, get_active_by_user_return=[])
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        assert result.skipped >= 1

    @pytest.mark.asyncio
    async def test_second_run_with_same_data_is_idempotent(self) -> None:
        """
        Calling generate_and_persist twice with identical data should produce
        new=0 on the second call.
        """
        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)

        # First run: nothing exists
        created = []

        async def capture_create(rec):
            created.append(rec)
            return rec

        first_repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        first_repo.create = AsyncMock(side_effect=capture_create)
        service = _make_service(first_repo)
        first_result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )
        assert first_result.new >= 1

        # Second run: all records now exist (simulate by returning created recs)
        created_mock = _existing_rec("anything", "active")
        second_repo = _make_repo(
            get_by_rule_key_return=created_mock,  # always returns existing
            get_active_by_user_return=[created_mock],
        )
        service2 = _make_service(second_repo)
        second_result = await service2.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )
        second_repo.create.assert_not_called()
        assert second_result.new == 0


# ---------------------------------------------------------------------------
# Test: Stale / resolved recommendations
# ---------------------------------------------------------------------------

class TestStaleResolution:
    @pytest.mark.asyncio
    async def test_stale_active_recommendation_is_resolved(self) -> None:
        """
        An active recommendation whose rule no longer fires should be
        marked completed (resolved).
        """
        stale_rec = _existing_rec("GH-ACT-001", status="active")
        # GH-ACT-001 requires low commits + sufficient history; strong profile won't trigger it
        repo = _make_repo(
            get_by_rule_key_return=None,
            get_active_by_user_return=[stale_rec],
        )
        service = _make_service(repo)

        # Strong profile — GH-ACT-001 will NOT fire
        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(total_commits=200, active_days_count=30),
            leetcode_analysis=None,
            score_result=None,
        )

        assert "GH-ACT-001" in result.resolved_rule_ids
        assert result.resolved >= 1
        repo.update_status.assert_called_once_with(stale_rec, "completed")

    @pytest.mark.asyncio
    async def test_dismissed_stale_recommendation_is_not_resolved(self) -> None:
        """
        A dismissed recommendation whose rule no longer fires must NOT be
        touched — it is already in a terminal state chosen by the user.
        """
        dismissed_rec = _existing_rec("GH-ACT-001", status="dismissed")
        # get_active_by_user returns only ACTIVE recs — dismissed are excluded
        repo = _make_repo(
            get_by_rule_key_return=None,
            get_active_by_user_return=[],  # dismissed not in active list
        )
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(total_commits=200),
            leetcode_analysis=None,
            score_result=None,
        )

        assert result.resolved == 0
        repo.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_active_recommendation_that_still_fires_is_not_resolved(self) -> None:
        """
        An active recommendation whose rule still fires should not be resolved.
        """
        # LC-DIFF-001 still fires (low hard ratio)
        active_lc_diff = _existing_rec("LC-DIFF-001", status="active")
        repo = _make_repo(
            get_by_rule_key_return=active_lc_diff,  # exists, so skipped
            get_active_by_user_return=[active_lc_diff],  # still active
        )
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        # LC-DIFF-001 was in fired_rule_ids, so it is NOT resolved
        assert "LC-DIFF-001" not in result.resolved_rule_ids

    @pytest.mark.asyncio
    async def test_multiple_stale_recommendations_all_resolved(self) -> None:
        """Multiple stale active recommendations whose rules do not fire are all resolved."""
        stale1 = _existing_rec("GH-ACT-001", status="active")
        stale2 = _existing_rec("GH-CONS-001", status="active")

        repo = _make_repo(
            get_by_rule_key_return=None,
            get_active_by_user_return=[stale1, stale2],
        )
        service = _make_service(repo)

        # Strong profile — neither GH rule fires
        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(total_commits=200, contribution_consistency=0.80),
            leetcode_analysis=None,
            score_result=None,
        )

        assert result.resolved == 2
        assert "GH-ACT-001" in result.resolved_rule_ids
        assert "GH-CONS-001" in result.resolved_rule_ids
        assert repo.update_status.call_count == 2


# ---------------------------------------------------------------------------
# Test: Missing analytics data
# ---------------------------------------------------------------------------

class TestMissingData:
    @pytest.mark.asyncio
    async def test_missing_github_does_not_produce_github_recommendations(self) -> None:
        """No GitHub data → no GitHub rules fire."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=None,
            leetcode_analysis=_leetcode(),
            score_result=_score(),
        )

        for candidate in result.new_recommendations:
            assert not candidate.rule_id.startswith("GH-"), (
                f"GitHub rule {candidate.rule_id} fired without GitHub data"
            )

    @pytest.mark.asyncio
    async def test_missing_leetcode_does_not_produce_lc_recommendations(self) -> None:
        """No LeetCode data → no LeetCode rules fire."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(),
            leetcode_analysis=None,
            score_result=_score(),
        )

        for candidate in result.new_recommendations:
            assert not candidate.rule_id.startswith("LC-"), (
                f"LeetCode rule {candidate.rule_id} fired without LeetCode data"
            )

    @pytest.mark.asyncio
    async def test_missing_score_does_not_produce_score_recommendations(self) -> None:
        """No score data → no SC rules fire."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(),
            leetcode_analysis=_leetcode(),
            score_result=None,
        )

        sc_rules = {"SC-OVERALL-001", "SC-CONSISTENCY-001", "SC-PS-001", "SC-OS-001"}
        for candidate in result.new_recommendations:
            assert candidate.rule_id not in sc_rules, (
                f"Score rule {candidate.rule_id} fired without score data"
            )

    @pytest.mark.asyncio
    async def test_all_none_inputs_no_db_interaction_except_active_query(self) -> None:
        """All None inputs: no creates, no updates. Only the active-query may be called."""
        repo = _make_repo(get_active_by_user_return=[])
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=None,
            leetcode_analysis=None,
            score_result=None,
        )

        assert result.new == 0
        assert result.resolved == 0
        repo.create.assert_not_called()
        repo.update_status.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Repository failure behavior
# ---------------------------------------------------------------------------

class TestRepositoryFailure:
    @pytest.mark.asyncio
    async def test_create_failure_propagates_exception(self) -> None:
        """If the repository raises on create(), the service lets the exception propagate."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        repo.create = AsyncMock(side_effect=RuntimeError("DB connection lost"))
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)

        with pytest.raises(RuntimeError, match="DB connection lost"):
            await service.generate_and_persist(
                user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
            )

    @pytest.mark.asyncio
    async def test_update_status_failure_propagates_exception(self) -> None:
        """If repository.update_status() raises, the service lets the exception propagate."""
        stale = _existing_rec("GH-ACT-001", "active")
        repo = _make_repo(
            get_by_rule_key_return=None,
            get_active_by_user_return=[stale],
        )
        repo.update_status = AsyncMock(side_effect=RuntimeError("Timeout"))
        service = _make_service(repo)

        with pytest.raises(RuntimeError, match="Timeout"):
            await service.generate_and_persist(
                user_id=USER_ID,
                github_analysis=_github(total_commits=500),
                leetcode_analysis=None,
                score_result=None,
            )


# ---------------------------------------------------------------------------
# Test: User ownership
# ---------------------------------------------------------------------------

class TestUserOwnership:
    @pytest.mark.asyncio
    async def test_user_id_is_set_on_created_record(self) -> None:
        """The user_id on every created record must match the parameter."""
        captured = []

        async def capture(rec):
            captured.append(rec)
            return rec

        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        repo.create = AsyncMock(side_effect=capture)
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        for rec in captured:
            assert rec.user_id == USER_ID

    @pytest.mark.asyncio
    async def test_result_user_id_matches_input(self) -> None:
        repo = _make_repo()
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=OTHER_USER_ID,
            github_analysis=None,
            leetcode_analysis=None,
            score_result=None,
        )

        assert result.user_id == OTHER_USER_ID


# ---------------------------------------------------------------------------
# Test: Result schema completeness
# ---------------------------------------------------------------------------

class TestResultSchema:
    @pytest.mark.asyncio
    async def test_result_counts_are_consistent(self) -> None:
        """new + skipped must equal total_candidates."""
        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        service = _make_service(repo)

        lc = _leetcode(
            easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60,
            contribution_consistency=0.20,
        )
        result = await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        assert result.new + result.skipped == result.total_candidates
        assert len(result.new_recommendations) == result.new

    @pytest.mark.asyncio
    async def test_resolved_rule_ids_match_resolved_count(self) -> None:
        stale = _existing_rec("GH-ACT-001", "active")
        repo = _make_repo(
            get_by_rule_key_return=None,
            get_active_by_user_return=[stale],
        )
        service = _make_service(repo)

        result = await service.generate_and_persist(
            user_id=USER_ID,
            github_analysis=_github(total_commits=500),
            leetcode_analysis=None,
            score_result=None,
        )

        assert len(result.resolved_rule_ids) == result.resolved

    @pytest.mark.asyncio
    async def test_evidence_dict_preserved_on_new_recommendations(self) -> None:
        """Evidence from the candidate must be stored on the Recommendation record."""
        captured = []

        async def capture(rec):
            captured.append(rec)
            return rec

        repo = _make_repo(get_by_rule_key_return=None, get_active_by_user_return=[])
        repo.create = AsyncMock(side_effect=capture)
        service = _make_service(repo)

        lc = _leetcode(easy_solved=58, medium_solved=1, hard_solved=1, total_solved=60)
        await service.generate_and_persist(
            user_id=USER_ID, github_analysis=None, leetcode_analysis=lc, score_result=None
        )

        # Every created record should have non-empty evidence
        for rec in captured:
            assert isinstance(rec.evidence, dict)
            assert len(rec.evidence) > 0


# ---------------------------------------------------------------------------
# Test: Retrieval helpers
# ---------------------------------------------------------------------------

class TestRetrievalHelpers:
    @pytest.mark.asyncio
    async def test_get_active_recommendations_delegates_to_repo(self) -> None:
        active = [_existing_rec("LC-DIFF-001", "active")]
        repo = _make_repo(get_active_by_user_return=active)
        service = _make_service(repo)

        result = await service.get_active_recommendations(USER_ID)

        repo.get_active_by_user.assert_called_once_with(USER_ID)
        assert result == active

    @pytest.mark.asyncio
    async def test_get_all_recommendations_delegates_to_repo(self) -> None:
        all_recs = [_existing_rec("LC-DIFF-001", "active"), _existing_rec("GH-CONS-001", "dismissed")]
        repo = _make_repo()
        repo.get_all_by_user = AsyncMock(return_value=all_recs)
        service = _make_service(repo)

        result = await service.get_all_recommendations(USER_ID, limit=10)

        repo.get_all_by_user.assert_called_once_with(USER_ID, limit=10)
        assert result == all_recs
