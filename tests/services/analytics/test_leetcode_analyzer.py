import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.models.leetcode_snapshot import LeetCodeSnapshot
from app.models.leetcode_history import LeetCodeHistory
from app.repositories.leetcode_snapshot import LeetCodeSnapshotRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.services.analytics.leetcode import LeetCodeAnalyzer

@pytest.fixture
def mock_snapshot_repo() -> MagicMock:
    return MagicMock(spec=LeetCodeSnapshotRepository)

@pytest.fixture
def mock_history_repo() -> MagicMock:
    return MagicMock(spec=LeetCodeHistoryRepository)

@pytest.fixture
def analyzer(mock_snapshot_repo: MagicMock, mock_history_repo: MagicMock) -> LeetCodeAnalyzer:
    return LeetCodeAnalyzer(mock_snapshot_repo, mock_history_repo)

# --- 1. Snapshot Handling ---

@pytest.mark.asyncio
async def test_analyze_no_snapshot_available(analyzer: LeetCodeAnalyzer, mock_snapshot_repo: MagicMock) -> None:
    """Verify ValueError is raised if no snapshot is available for the user."""
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="No LeetCode snapshot found for user."):
        await analyzer.analyze(uuid.uuid4())

@pytest.mark.asyncio
async def test_analyze_snapshot_derived_metrics(
    analyzer: LeetCodeAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify correct extraction of problem stats and topic aggregation with sorting and deduplication."""
    user_uuid = uuid.uuid4()
    raw_data = {
        "data": {
            "matchedUser": {
                "username": "lc_master",
                "profile": {
                    "realName": "Jane Doe",
                    "aboutMe": "Software dev",
                    "userAvatar": "https://avatar.com"
                },
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "Easy", "count": 30, "submissions": 60},
                        {"difficulty": "Medium", "count": 20, "submissions": 40},
                        {"difficulty": "Hard", "count": 10, "submissions": 20},
                        {"difficulty": "All", "count": 60, "submissions": 120}
                    ]
                },
                "tagProblemsSolved": {
                    "fundamental": [
                        {"tagName": "Array", "tagSlug": "array", "solvedCount": 5},
                        {"tagName": "String", "tagSlug": "string", "solvedCount": 3}
                    ],
                    "intermediate": [
                        {"tagName": "String", "tagSlug": "string", "solvedCount": 4},  # Duplicate tag slug!
                        {"tagName": "Hash Table", "tagSlug": "hash-table", "solvedCount": 10}
                    ],
                    "advanced": [
                        {"tagName": "Dynamic Programming", "tagSlug": "dynamic-programming", "solvedCount": 12},
                        {"tagName": "Graph", "tagSlug": "graph", "solvedCount": 8},
                        {"tagName": "Trie", "tagSlug": "trie", "solvedCount": 2}
                    ]
                }
            }
        }
    }

    mock_snapshot = LeetCodeSnapshot(user_id=user_uuid, raw_data=raw_data)
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)
    mock_history_repo.get_history = AsyncMock(return_value=[])

    result = await analyzer.analyze(user_uuid)

    assert result.username == "lc_master"
    assert result.problem_stats.easy_solved == 30
    assert result.problem_stats.medium_solved == 20
    assert result.problem_stats.hard_solved == 10
    assert result.problem_stats.total_solved == 60
    assert result.problem_stats.easy_submissions == 60
    assert result.problem_stats.medium_submissions == 40
    assert result.problem_stats.hard_submissions == 20
    assert result.problem_stats.total_submissions == 120

    # Topics: limit to 5, sorted by solved_count DESC, then tag_name ASC.
    # Deduplication check: "String" slug is fundamental (3 solved) and intermediate (4 solved).
    # Solved sum = 7. Difficulty priority: intermediate (2) > fundamental (1) -> intermediate.
    # Candidates:
    # - Dynamic Programming: 12 (advanced)
    # - Hash Table: 10 (intermediate)
    # - Graph: 8 (advanced)
    # - String: 7 (intermediate)
    # - Array: 5 (fundamental)
    # - Trie: 2 (advanced) - excluded due to limit of 5.
    assert len(result.most_practiced_topics) == 5
    topic_names = [t.tag_name for t in result.most_practiced_topics]
    assert topic_names == ["Dynamic Programming", "Hash Table", "Graph", "String", "Array"]
    
    string_tag = [t for t in result.most_practiced_topics if t.tag_slug == "string"][0]
    assert string_tag.solved_count == 7
    assert string_tag.difficulty_level == "intermediate"

# --- 2. Growth Metric Tests ---

@pytest.mark.asyncio
async def test_growth_metrics_history_ranges(
    analyzer: LeetCodeAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify growth calculation rules for 0, 1, 2, and negative growth cases."""
    user_uuid = uuid.uuid4()
    mock_snapshot = LeetCodeSnapshot(user_id=user_uuid, raw_data={"data": {"matchedUser": {"username": "lc_master", "submitStats": {"acSubmissionNum": []}, "profile": None, "tagProblemsSolved": None}}})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # 1. Zero history records -> Growth must be None
    mock_history_repo.get_history = AsyncMock(return_value=[])
    res_zero = await analyzer.analyze(user_uuid)
    assert res_zero.problems_solved_growth is None
    assert res_zero.submissions_growth is None

    # 2. One history record -> Growth must be None
    rec1 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 20), problems_solved=100, easy_solved=40, medium_solved=40, hard_solved=20, submissions=200, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1])
    res_one = await analyzer.analyze(user_uuid)
    assert res_one.problems_solved_growth is None
    assert res_one.submissions_growth is None

    # 3. Two or more history records -> Positive Growth
    rec2 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=110, easy_solved=45, medium_solved=42, hard_solved=23, submissions=230, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2])
    res_two = await analyzer.analyze(user_uuid)
    assert res_two.problems_solved_growth == 10
    assert res_two.easy_solved_growth == 5
    assert res_two.medium_solved_growth == 2
    assert res_two.hard_solved_growth == 3
    assert res_two.submissions_growth == 30

    # 4. Negative growth (endpoints legitimately decrease)
    rec_neg = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=90, easy_solved=35, medium_solved=38, hard_solved=17, submissions=180, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec_neg])
    res_neg = await analyzer.analyze(user_uuid)
    assert res_neg.problems_solved_growth == -10
    assert res_neg.easy_solved_growth == -5
    assert res_neg.medium_solved_growth == -2
    assert res_neg.hard_solved_growth == -3
    assert res_neg.submissions_growth == -20

# --- 3. Observed Transition Metrics ---

@pytest.mark.asyncio
async def test_observed_transition_metrics(
    analyzer: LeetCodeAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify transition metric aggregations (frequency, consistency) and exclusions."""
    user_uuid = uuid.uuid4()
    mock_snapshot = LeetCodeSnapshot(user_id=user_uuid, raw_data={"data": {"matchedUser": {"username": "lc_master", "submitStats": {"acSubmissionNum": []}, "profile": None, "tagProblemsSolved": None}}})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # 1. No valid transitions (fewer than 2 records)
    rec1 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 20), problems_solved=100, submissions=200, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1])
    res_none = await analyzer.analyze(user_uuid)
    assert res_none.problems_solved_frequency_per_day is None
    assert res_none.contribution_consistency is None
    assert res_none.active_days_count is None

    # 2. Positive & Zero transitions (consecutive days: 20 -> 21 -> 22)
    # 20 to 21: delta = 5 (active)
    # 21 to 22: delta = 0 (inactive)
    # Total valid consecutive transitions: 2. Active transitions: 1. Solved: 5.
    rec2 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 21), problems_solved=105, submissions=210, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec3 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 22), problems_solved=105, submissions=215, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2, rec3])
    res_valid = await analyzer.analyze(user_uuid)
    assert res_valid.problems_solved_frequency_per_day == 2.5
    assert res_valid.active_days_count == 1
    assert res_valid.contribution_consistency == 0.5

    # 3. Gaps & Negative deltas (excluded)
    # 20 to 21: delta = 5 (valid consecutive)
    # 21 to 23: missing 22 (gap, excluded)
    # 23 to 24: delta = -2 (negative transition, excluded)
    rec_gap = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=110, submissions=220, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec_neg = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 24), problems_solved=108, submissions=222, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2, rec_gap, rec_neg])
    res_excl = await analyzer.analyze(user_uuid)
    # Valid transitions: 1 (20 -> 21). Deltas sum: 5.
    assert res_excl.problems_solved_frequency_per_day == 5.0
    assert res_excl.active_days_count == 1
    assert res_excl.contribution_consistency == 1.0

# --- 4. Longest Streak ---

@pytest.mark.asyncio
async def test_longest_streak_calculations(
    analyzer: LeetCodeAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify longest streak rules for gaps, zeros, and negative deltas."""
    user_uuid = uuid.uuid4()
    mock_snapshot = LeetCodeSnapshot(user_id=user_uuid, raw_data={"data": {"matchedUser": {"username": "lc_master", "submitStats": {"acSubmissionNum": []}, "profile": None, "tagProblemsSolved": None}}})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # 1. No valid transitions -> None
    mock_history_repo.get_history = AsyncMock(return_value=[])
    res_empty = await analyzer.analyze(user_uuid)
    assert res_empty.longest_streak is None

    # 2. Streak checks (20 -> 21 -> 22 -> 23 -> 24)
    # 20 to 21: delta = 2 > 0 (streak = 1)
    # 21 to 22: delta = 3 > 0 (streak = 2)
    # 22 to 23: delta = 0 (streak breaks, reset)
    # 23 to 24: delta = 4 > 0 (streak = 1)
    rec1 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 20), problems_solved=100, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec2 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 21), problems_solved=102, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec3 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 22), problems_solved=105, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec4 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=105, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec5 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 24), problems_solved=109, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2, rec3, rec4, rec5])
    res = await analyzer.analyze(user_uuid)
    assert res.longest_streak == 2

    # 3. Missing date (22nd missing) breaks streak
    # 20 to 21: delta = 2 (streak = 1)
    # 21 to 23: missing 22 (streak breaks, reset)
    # 23 to 24: delta = 4 (streak = 1)
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2, rec4, rec5])
    res_gap = await analyzer.analyze(user_uuid)
    assert res_gap.longest_streak == 1

    # 4. Negative delta (22 to 23 has delta = -2) breaks streak
    rec4_neg = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=103, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec1, rec2, rec3, rec4_neg, rec5])
    res_neg = await analyzer.analyze(user_uuid)
    # 20->21 (1), 21->22 (2), 22->23 (neg, break), 23->24 (delta = 6, active, streak = 1)
    assert res_neg.longest_streak == 2

# --- 5. Current Streak ---

@pytest.mark.asyncio
async def test_current_streak_calculations(
    analyzer: LeetCodeAnalyzer,
    mock_snapshot_repo: MagicMock,
    mock_history_repo: MagicMock
) -> None:
    """Verify current streak boundary logic including anchor days, stale data, and negative deltas."""
    user_uuid = uuid.uuid4()
    mock_snapshot = LeetCodeSnapshot(user_id=user_uuid, raw_data={"data": {"matchedUser": {"username": "lc_master", "submitStats": {"acSubmissionNum": []}, "profile": None, "tagProblemsSolved": None}}})
    mock_snapshot_repo.get_latest_by_user_id = AsyncMock(return_value=mock_snapshot)

    # a. Stale history (no fresh anchor)
    rec_stale1 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 22), problems_solved=100, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec_stale2 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=105, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec_stale1, rec_stale2])
    res_stale = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res_stale.current_streak is None

    # b. Anchor today, positive transition
    # analysis_date = 25th. 24th and 25th exist. 25th delta = 3 > 0.
    rec23 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 23), problems_solved=100, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec24 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 24), problems_solved=102, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    rec25 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 25), problems_solved=105, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    
    mock_history_repo.get_history = AsyncMock(return_value=[rec23, rec24, rec25])
    res_today = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    # 25-24: 3 (1), 24-23: 2 (2) -> earliest reached (23rd)
    assert res_today.current_streak == 2

    # c. Anchor yesterday, today missing
    # analysis_date = 25th. 25th missing. 24th and 23rd exist. 24th delta = 2 > 0.
    # Today is missing date after anchor -> current streak is None (ambiguous).
    mock_history_repo.get_history = AsyncMock(return_value=[rec23, rec24])
    res_yesterday = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res_yesterday.current_streak is None

    # d. Anchor yesterday, today missing, but yesterday delta == 0
    # 24th delta = 0. Confirmed broken streak.
    rec24_zero = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 24), problems_solved=100, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec23, rec24_zero])
    res_yesterday_zero = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res_yesterday_zero.current_streak == 0

    # e. Missing required predecessor date inside tracing (e.g. 24th missing while tracing 25th)
    # 25th exists, 24th exists, but 23rd is missing (so transition 24 to 23 is missing).
    rec22 = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 22), problems_solved=95, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec22, rec24, rec25])
    res_gap = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res_gap.current_streak is None

    # f. Negative transition during tracing
    # 25th exists, 24th exists, 23rd exists.
    # 25-24: delta = 3 (active). 24-23: delta = -2 (negative transition).
    rec24_neg = LeetCodeHistory(user_id=user_uuid, date=date(2026, 8, 24), problems_solved=107, submissions=0, easy_solved=0, medium_solved=0, hard_solved=0, parsed_metrics={})
    mock_history_repo.get_history = AsyncMock(return_value=[rec23, rec24_neg, rec25])
    res_neg_trace = await analyzer.analyze(user_uuid, analysis_date=date(2026, 8, 25))
    assert res_neg_trace.current_streak is None
