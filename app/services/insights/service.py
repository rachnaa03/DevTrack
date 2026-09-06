import logging
from datetime import date
from uuid import UUID

from app.models.insight import Insight
from app.repositories.insight import InsightRepository
from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.insights import DeveloperComparisonResultSchema, InsightTriggerSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.score import DeveloperScoreResultSchema
from app.services.insights.rules import AnalyticsComparator

logger = logging.getLogger(__name__)

# Rule version emitted on every generated Insight record.
# Increment this when comparison thresholds or trigger logic changes.
INSIGHT_RULE_VERSION = "v1"

# ---------------------------------------------------------------------------
# Human-readable message templates
# ---------------------------------------------------------------------------
# Templates are keyed by (metric_name, change_type).
# Placeholders:
#   {abs_change}     — formatted absolute delta
#   {pct_change}     — formatted percentage delta (may be absent for some metrics)
#   {current}        — formatted current value
#   {historical}     — formatted historical value
# ---------------------------------------------------------------------------

_MESSAGE_TEMPLATES: dict[tuple[str, str], str] = {
    # GitHub
    ("github_commits", "increase"): (
        "GitHub commit activity increased by {abs_change} commits compared with the previous period."
    ),
    ("github_commits", "decrease"): (
        "GitHub commit activity decreased by {abs_change} commits compared with the previous period."
    ),
    ("github_consistency", "increase"): (
        "GitHub contribution consistency improved from {historical} to {current}."
    ),
    ("github_consistency", "decrease"): (
        "GitHub contribution consistency declined from {historical} to {current}."
    ),
    ("github_streak", "increase"): (
        "Your GitHub coding streak grew by {abs_change} days."
    ),
    ("github_streak", "broken"): (
        "Your GitHub coding streak of {historical} days was broken."
    ),
    # LeetCode
    ("leetcode_solved", "increase"): (
        "LeetCode problem-solving activity increased by {abs_change} problems compared with the previous period."
    ),
    ("leetcode_solved", "decrease"): (
        "LeetCode problem-solving activity decreased by {abs_change} problems compared with the previous period."
    ),
    ("leetcode_difficulty", "increase"): (
        "Your LeetCode Medium/Hard problem ratio improved from {historical} to {current}."
    ),
    ("leetcode_difficulty", "decrease"): (
        "Your LeetCode Medium/Hard problem ratio decreased from {historical} to {current}."
    ),
    ("leetcode_consistency", "increase"): (
        "LeetCode contribution consistency improved from {historical} to {current}."
    ),
    ("leetcode_consistency", "decrease"): (
        "LeetCode contribution consistency declined from {historical} to {current}."
    ),
    ("leetcode_streak", "increase"): (
        "Your LeetCode solving streak grew by {abs_change} days."
    ),
    ("leetcode_streak", "broken"): (
        "Your LeetCode solving streak of {historical} days was broken."
    ),
    # Developer Score
    ("score_overall", "increase"): (
        "Your Developer Score increased by {abs_change} points."
    ),
    ("score_overall", "decrease"): (
        "Your Developer Score decreased by {abs_change} points."
    ),
    ("score_consistency", "increase"): (
        "Your consistency score improved by {abs_change} points."
    ),
    ("score_consistency", "decrease"): (
        "Your consistency score dropped by {abs_change} points."
    ),
    ("score_problem_solving", "increase"): (
        "Your problem-solving score improved by {abs_change} points."
    ),
    ("score_problem_solving", "decrease"): (
        "Your problem-solving score dropped by {abs_change} points."
    ),
    ("score_open_source", "increase"): (
        "Your open-source impact score improved by {abs_change} points."
    ),
    ("score_open_source", "decrease"): (
        "Your open-source impact score dropped by {abs_change} points."
    ),
}

_FALLBACK_TEMPLATE = (
    "{metric_name} {change_type}d: current value {current}, historical value {historical}."
)


def _format_value(value: float, metric_name: str) -> str:
    """
    Format a numeric value for display in a human-readable message.

    Ratio-based metrics (consistency, difficulty) are rendered as percentages.
    Integer metrics (commits, streaks, solved, scores) are rendered as whole numbers.
    """
    ratio_metrics = {
        "github_consistency",
        "leetcode_consistency",
        "leetcode_difficulty",
    }
    if metric_name in ratio_metrics:
        return f"{value * 100:.1f}%"
    return str(int(round(value)))


def compose_message(trigger: InsightTriggerSchema) -> str:
    """
    Generate a deterministic, human-readable insight message from a trigger.

    Falls back to a generic template for any unrecognised metric/change_type pair.
    The message is always ≤ 500 characters to respect the model column constraint.
    """
    key = (trigger.metric_name, trigger.change_type)
    template = _MESSAGE_TEMPLATES.get(key)

    if template is None:
        logger.warning(
            "No message template found for metric=%s change_type=%s; using fallback.",
            trigger.metric_name,
            trigger.change_type,
        )
        message = _FALLBACK_TEMPLATE.format(
            metric_name=trigger.metric_name,
            change_type=trigger.change_type,
            current=_format_value(trigger.current_value, trigger.metric_name),
            historical=_format_value(trigger.historical_value, trigger.metric_name),
        )
    else:
        abs_str = _format_value(trigger.absolute_change, trigger.metric_name)
        cur_str = _format_value(trigger.current_value, trigger.metric_name)
        hist_str = _format_value(trigger.historical_value, trigger.metric_name)
        pct_str = (
            f"{trigger.percent_change:.1f}%" if trigger.percent_change is not None else "N/A"
        )
        message = template.format(
            abs_change=abs_str,
            current=cur_str,
            historical=hist_str,
            pct_change=pct_str,
        )

    # Guard against exceeding the DB column constraint (500 chars)
    return message[:500]


class InsightGenerationService:
    """
    Orchestrates Insights Engine execution for a single user.

    Responsibilities:
    1. Accept current and historical analytics/score data.
    2. Invoke AnalyticsComparator to determine meaningful changes.
    3. Convert each trigger into a persisted Insight record.
    4. Skip duplicate records (same comparison key already exists in DB).
    5. Return the list of newly persisted Insight records.

    This service deliberately does not call external APIs or re-implement
    comparison threshold logic — those belong to AnalyticsComparator.
    """

    def __init__(self, insight_repo: InsightRepository):
        self.insight_repo = insight_repo

    async def generate_and_persist(
        self,
        user_id: UUID,
        current_date: date,
        historical_date: date,
        current_gh: GitHubAnalysisResultSchema | None,
        historical_gh: GitHubAnalysisResultSchema | None,
        current_lc: LeetCodeAnalysisResultSchema | None,
        historical_lc: LeetCodeAnalysisResultSchema | None,
        current_score: DeveloperScoreResultSchema | None,
        historical_score: DeveloperScoreResultSchema | None,
    ) -> list[Insight]:
        """
        Run the comparison engine and persist significant insight triggers.

        Returns the list of newly created Insight records.
        Skips any trigger for which an identical record already exists
        (same user, platform, metric, current_date, historical_date, rule_version).

        If no triggers are generated, an empty list is returned — no record is written.
        """
        # --- 1. Run pure comparison logic (no DB) ---
        comparison: DeveloperComparisonResultSchema = AnalyticsComparator.compare(
            user_id=user_id,
            current_gh=current_gh,
            historical_gh=historical_gh,
            current_lc=current_lc,
            historical_lc=historical_lc,
            current_score=current_score,
            historical_score=historical_score,
            current_date=current_date,
            historical_date=historical_date,
        )

        if not comparison.triggers:
            logger.info(
                "No significant triggers found for user_id=%s (current=%s, historical=%s).",
                user_id,
                current_date,
                historical_date,
            )
            return []

        logger.info(
            "Comparator produced %d trigger(s) for user_id=%s.",
            len(comparison.triggers),
            user_id,
        )

        # --- 2. Convert triggers to Insight records, deduplicating per run ---
        persisted: list[Insight] = []

        for trigger in comparison.triggers:
            # Deduplication: skip if an identical record already exists
            existing = await self.insight_repo.get_existing(
                user_id=user_id,
                platform=trigger.platform,
                metric_name=trigger.metric_name,
                current_date=current_date,
                historical_date=historical_date,
                rule_version=INSIGHT_RULE_VERSION,
            )
            if existing is not None:
                logger.debug(
                    "Skipping duplicate insight: user_id=%s metric=%s platform=%s.",
                    user_id,
                    trigger.metric_name,
                    trigger.platform,
                )
                continue

            # Build the ORM record
            message = compose_message(trigger)
            record = Insight(
                user_id=user_id,
                platform=trigger.platform,
                metric_name=trigger.metric_name,
                change_type=trigger.change_type,
                message=message,
                current_value=trigger.current_value,
                historical_value=trigger.historical_value,
                absolute_change=trigger.absolute_change,
                percent_change=trigger.percent_change,
                current_date=current_date,
                historical_date=historical_date,
                rule_version=INSIGHT_RULE_VERSION,
                evidence=trigger.metadata if trigger.metadata else None,
            )

            persisted_record = await self.insight_repo.create(record)
            persisted.append(persisted_record)
            logger.info(
                "Persisted insight id=%s metric=%s change_type=%s for user_id=%s.",
                persisted_record.id,
                trigger.metric_name,
                trigger.change_type,
                user_id,
            )

        return persisted

    async def get_latest_insights(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[Insight]:
        """Retrieve the user's most recent insight records."""
        return await self.insight_repo.get_latest_by_user_id(user_id, limit=limit)
