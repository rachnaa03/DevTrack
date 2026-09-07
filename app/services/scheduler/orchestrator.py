"""
Synchronizer Orchestrator Workflow — Task 13.2

Provides the master orchestration pipeline for periodic developer-data synchronization
and subsequent analytics processing across all supported platforms (GitHub, LeetCode).

Executes 7 coordinated stages per user in isolated database sessions:
  1. Platform Synchronization (fetch external raw payloads, persist snapshots, update profiles)
  2. Daily History Population (upsert structured history records)
  3. Analytics Calculation & Persistence (compute metrics, trends, streaks; upsert analytics)
  4. Developer Score Calculation (compute multi-component Developer Score; persist score)
  5. Insight Generation (delta comparison against historical baseline; persist insights)
  6. Recommendation Generation (evaluate 14 rule engine triggers; resolve/persist recommendations)
  7. Milestone / Timeline Evaluation (evaluate achievement badges; record milestones & events)
"""

import logging
from datetime import date, timedelta
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.repositories.github_analytics import GitHubAnalyticsRepository
from app.repositories.github_history import GitHubHistoryRepository
from app.repositories.github_snapshot import GitHubSnapshotRepository
from app.repositories.insight import InsightRepository
from app.repositories.leetcode_analytics import LeetCodeAnalyticsRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.repositories.leetcode_snapshot import LeetCodeSnapshotRepository
from app.repositories.milestone import MilestoneRepository
from app.repositories.profile import ProfileRepository
from app.repositories.recommendation import RecommendationRepository
from app.repositories.score import DeveloperScoreRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.score import DeveloperScoreResultSchema
from app.schemas.sync_orchestrator import BatchSyncSummary, UserSyncSummary
from app.services.analytics.github import GitHubAnalyzer
from app.services.analytics.leetcode import LeetCodeAnalyzer
from app.services.dashboard.milestones import MilestoneService
from app.services.insights.service import InsightGenerationService
from app.services.integrations.github import GitHubClient
from app.services.integrations.github_parser import GitHubDataParser
from app.services.integrations.github_sync import GitHubSyncService
from app.services.integrations.leetcode import LeetCodeClient
from app.services.integrations.leetcode_parser import LeetCodeDataParser
from app.services.integrations.leetcode_sync import LeetCodeSyncService
from app.services.recommendations.service import RecommendationService
from app.services.scoring.calculator import DeveloperScoreCalculator
from app.services.scoring.service import DeveloperScoreService

logger = logging.getLogger("devtrack.sync_orchestrator")


class SyncOrchestrator:
    """
    Coordinates end-to-end synchronization and processing for connected developers.

    Maintains strict per-user database session isolation so that a failure for
    one user does not corrupt or roll back processing for other users.
    """

    async def sync_user(
        self,
        user_id: UUID,
        analysis_date: date | None = None,
    ) -> UserSyncSummary:
        """
        Execute the 7-stage synchronization and analytics pipeline for a single user.

        Owns and manages an isolated database session for the entire execution.
        """
        today = analysis_date or date.today()
        summary = UserSyncSummary(user_id=user_id, success=False)

        async with AsyncSessionLocal() as session:
            try:
                # -----------------------------------------------------------
                # Repositories & Services bound to this user's session
                # -----------------------------------------------------------
                profile_repo = ProfileRepository(session)
                gh_snapshot_repo = GitHubSnapshotRepository(session)
                lc_snapshot_repo = LeetCodeSnapshotRepository(session)
                gh_history_repo = GitHubHistoryRepository(session)
                lc_history_repo = LeetCodeHistoryRepository(session)
                gh_analytics_repo = GitHubAnalyticsRepository(session)
                lc_analytics_repo = LeetCodeAnalyticsRepository(session)
                score_repo = DeveloperScoreRepository(session)
                insight_repo = InsightRepository(session)
                rec_repo = RecommendationRepository(session)
                milestone_repo = MilestoneRepository(session)
                timeline_repo = TimelineRepository(session)

                gh_client = GitHubClient()
                lc_client = LeetCodeClient()

                gh_sync_service = GitHubSyncService(profile_repo, gh_client, gh_snapshot_repo)
                lc_sync_service = LeetCodeSyncService(profile_repo, lc_client, lc_snapshot_repo)

                gh_analyzer = GitHubAnalyzer(gh_snapshot_repo, gh_history_repo)
                lc_analyzer = LeetCodeAnalyzer(lc_snapshot_repo, lc_history_repo)

                score_service = DeveloperScoreService(score_repo)
                insight_service = InsightGenerationService(insight_repo)
                rec_service = RecommendationService(rec_repo)
                milestone_service = MilestoneService(
                    milestone_repo=milestone_repo,
                    timeline_repo=timeline_repo,
                    github_repo=gh_analytics_repo,
                    leetcode_repo=lc_analytics_repo,
                    score_repo=score_repo,
                )

                # -----------------------------------------------------------
                # Check Profile & Platform Connection Handles
                # -----------------------------------------------------------
                profile = await profile_repo.get_by_user_id(user_id)
                if not profile:
                    logger.warning("Profile not found for user_id=%s during sync", user_id)
                    summary.errors.append("Profile not found")
                    return summary

                has_gh = bool(profile.github_username)
                has_lc = bool(profile.leetcode_username)

                if not has_gh and not has_lc:
                    logger.info("No connected platforms for user_id=%s; skipping sync", user_id)
                    summary.success = True
                    return summary

                gh_analysis: GitHubAnalysisResultSchema | None = None
                lc_analysis: LeetCodeAnalysisResultSchema | None = None

                # ===========================================================
                # STAGE 1 & 2 & 3: GitHub Pipeline
                # ===========================================================
                if has_gh:
                    try:
                        # Stage 1: Platform Synchronization
                        logger.info("Starting GitHub sync for user_id=%s", user_id)
                        gh_sync_res = await gh_sync_service.sync_github_data(user_id)
                        summary.github_synced = gh_sync_res.success

                        # Stage 2: Daily History Population
                        latest_gh_snap = await gh_snapshot_repo.get_latest_by_user_id(user_id)
                        if latest_gh_snap:
                            parsed_gh = GitHubDataParser.parse(latest_gh_snap.raw_data)
                            await gh_history_repo.create_or_update(
                                user_id=user_id,
                                history_date=today,
                                commits=0,
                                stars=parsed_gh.total_stars,
                                forks=parsed_gh.total_forks,
                                repositories=parsed_gh.repositories_count,
                                parsed_metrics=parsed_gh.model_dump(mode="json"),
                            )

                        # Stage 3: Analytics Calculation & Persistence
                        gh_analysis = await gh_analyzer.analyze(user_id, analysis_date=today)
                        await gh_analytics_repo.create_or_update(user_id, today, gh_analysis)
                    except Exception as gh_exc:
                        logger.exception(
                            "GitHub sync/analysis failed for user_id=%s: %s",
                            user_id,
                            gh_exc,
                        )
                        summary.errors.append(f"GitHub: {gh_exc}")
                        gh_analysis = None

                # ===========================================================
                # STAGE 1 & 2 & 3: LeetCode Pipeline
                # ===========================================================
                if has_lc:
                    try:
                        # Stage 1: Platform Synchronization
                        logger.info("Starting LeetCode sync for user_id=%s", user_id)
                        lc_sync_res = await lc_sync_service.sync_leetcode_data(user_id)
                        summary.leetcode_synced = lc_sync_res.success

                        # Stage 2: Daily History Population
                        latest_lc_snap = await lc_snapshot_repo.get_latest_by_user_id(user_id)
                        if latest_lc_snap:
                            parsed_lc = LeetCodeDataParser.parse(latest_lc_snap.raw_data)
                            await lc_history_repo.create_or_update(
                                user_id=user_id,
                                history_date=today,
                                problems_solved=parsed_lc.problems.total_solved,
                                easy_solved=parsed_lc.problems.easy_solved,
                                medium_solved=parsed_lc.problems.medium_solved,
                                hard_solved=parsed_lc.problems.hard_solved,
                                submissions=parsed_lc.problems.total_submissions,
                                parsed_metrics=parsed_lc.model_dump(mode="json"),
                            )

                        # Stage 3: Analytics Calculation & Persistence
                        lc_analysis = await lc_analyzer.analyze(user_id, analysis_date=today)
                        await lc_analytics_repo.create_or_update(user_id, today, lc_analysis)
                    except Exception as lc_exc:
                        logger.exception(
                            "LeetCode sync/analysis failed for user_id=%s: %s",
                            user_id,
                            lc_exc,
                        )
                        summary.errors.append(f"LeetCode: {lc_exc}")
                        lc_analysis = None

                # ===========================================================
                # STAGE 4: Developer Score Calculation
                # ===========================================================
                score_schema: DeveloperScoreResultSchema | None = None
                if gh_analysis is not None or lc_analysis is not None:
                    try:
                        logger.info("Calculating Developer Score for user_id=%s", user_id)
                        await score_service.record_score(
                            user_id=user_id,
                            github_analysis=gh_analysis,
                            leetcode_analysis=lc_analysis,
                        )
                        score_schema = DeveloperScoreCalculator.calculate(
                            github_analysis=gh_analysis,
                            leetcode_analysis=lc_analysis,
                        )
                        summary.score_calculated = True
                    except Exception as score_exc:
                        logger.exception(
                            "Score calculation failed for user_id=%s: %s",
                            user_id,
                            score_exc,
                        )
                        summary.errors.append(f"Scoring: {score_exc}")

                # ===========================================================
                # STAGE 5: Insight Generation
                # ===========================================================
                if gh_analysis is not None or lc_analysis is not None or score_schema is not None:
                    try:
                        # Retrieve previous score for delta comparison if available
                        score_history = await score_repo.get_history(user_id, limit=2)
                        historical_score: DeveloperScoreResultSchema | None = None
                        historical_date = today - timedelta(days=1)

                        if len(score_history) > 1:
                            prev_score = score_history[1]
                            historical_date = prev_score.computed_at.date()
                            historical_score = DeveloperScoreResultSchema(
                                overall_score=prev_score.overall_score,
                                consistency_score=prev_score.consistency_score,
                                problem_solving_score=prev_score.problem_solving_score,
                                open_source_score=prev_score.open_source_score,
                                score_version=prev_score.score_version,
                            )

                        insights = await insight_service.generate_and_persist(
                            user_id=user_id,
                            current_date=today,
                            historical_date=historical_date,
                            current_gh=gh_analysis,
                            historical_gh=None,
                            current_lc=lc_analysis,
                            historical_lc=None,
                            current_score=score_schema,
                            historical_score=historical_score,
                        )
                        summary.insights_generated = len(insights)
                    except Exception as insight_exc:
                        logger.exception(
                            "Insight generation failed for user_id=%s: %s",
                            user_id,
                            insight_exc,
                        )
                        summary.errors.append(f"Insights: {insight_exc}")

                # ===========================================================
                # STAGE 6: Recommendation Generation
                # ===========================================================
                try:
                    await rec_service.generate_and_persist(
                        user_id=user_id,
                        github_analysis=gh_analysis,
                        leetcode_analysis=lc_analysis,
                        score_result=score_schema,
                    )
                    summary.recommendations_run = True
                except Exception as rec_exc:
                    logger.exception(
                        "Recommendation generation failed for user_id=%s: %s",
                        user_id,
                        rec_exc,
                    )
                    summary.errors.append(f"Recommendations: {rec_exc}")

                # ===========================================================
                # STAGE 7: Milestone / Timeline Evaluation
                # ===========================================================
                try:
                    await milestone_service.get_milestones(user_id=user_id)
                    summary.milestones_evaluated = True
                except Exception as ms_exc:
                    logger.exception(
                        "Milestone evaluation failed for user_id=%s: %s",
                        user_id,
                        ms_exc,
                    )
                    summary.errors.append(f"Milestones: {ms_exc}")

                # Mark user success if at least one stage succeeded without critical unhandled crash
                summary.success = len(summary.errors) == 0 or (
                    summary.github_synced or summary.leetcode_synced or summary.score_calculated
                )
                return summary

            except Exception as unhandled_exc:
                logger.exception("Unexpected error processing user_id=%s: %s", user_id, unhandled_exc)
                summary.errors.append(f"Unhandled: {unhandled_exc}")
                summary.success = False
                return summary


    async def sync_all_users(
        self,
        analysis_date: date | None = None,
    ) -> BatchSyncSummary:
        """
        Query all connected developer user IDs and execute synchronization independently per user.
        """
        today = analysis_date or date.today()
        batch_summary = BatchSyncSummary()

        # Step 1: Query eligible user IDs using a short-lived session
        user_ids: list[UUID] = []
        async with AsyncSessionLocal() as session:
            profile_repo = ProfileRepository(session)
            user_ids = await profile_repo.get_connected_user_ids()

        batch_summary.total_users = len(user_ids)

        if not user_ids:
            logger.info("No connected developer profiles found for synchronization.")
            return batch_summary

        logger.info("Starting batch synchronization for %d connected user(s)", len(user_ids))

        # Step 2: Process each user in isolation
        for user_id in user_ids:
            try:
                user_summary = await self.sync_user(user_id=user_id, analysis_date=today)
                batch_summary.user_summaries.append(user_summary)

                if user_summary.success:
                    batch_summary.successful_users += 1
                else:
                    batch_summary.failed_users += 1
            except Exception as exc:
                logger.exception("Critical error during sync for user_id=%s: %s", user_id, exc)
                batch_summary.failed_users += 1
                batch_summary.user_summaries.append(
                    UserSyncSummary(
                        user_id=user_id,
                        success=False,
                        errors=[f"Critical batch error: {exc}"],
                    )
                )

        logger.info(
            "Completed batch synchronization: total=%d, success=%d, failed=%d",
            batch_summary.total_users,
            batch_summary.successful_users,
            batch_summary.failed_users,
        )
        return batch_summary


async def run_scheduled_sync() -> BatchSyncSummary:
    """
    Top-level entry point called by APScheduler for periodic synchronization.
    """
    logger.info("APScheduler triggered periodic developer synchronization workflow.")
    orchestrator = SyncOrchestrator()
    return await orchestrator.sync_all_users()
