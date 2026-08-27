from datetime import date, timedelta
from uuid import UUID

from app.repositories.leetcode_snapshot import LeetCodeSnapshotRepository
from app.repositories.leetcode_history import LeetCodeHistoryRepository
from app.services.integrations.leetcode_parser import LeetCodeDataParser
from app.schemas.leetcode_analysis import (
    LeetCodeAnalysisResultSchema,
    LeetCodeProblemStatsSchema,
    TopicSummarySchema,
)

class LeetCodeAnalyzer:
    """Service responsible for converting structured LeetCode histories and snapshots into developer analytics."""

    def __init__(
        self,
        snapshot_repo: LeetCodeSnapshotRepository,
        history_repo: LeetCodeHistoryRepository
    ):
        self.snapshot_repo = snapshot_repo
        self.history_repo = history_repo

    async def analyze(
        self,
        user_id: UUID,
        analysis_date: date | None = None
    ) -> LeetCodeAnalysisResultSchema:
        """
        Analyze raw LeetCode snapshots and structured histories to compute statistics and trends.
        """
        # 1. Fetch latest raw snapshot
        snapshot = await self.snapshot_repo.get_latest_by_user_id(user_id)
        if snapshot is None:
            raise ValueError("No LeetCode snapshot found for user.")

        # Parse raw snapshot using the existing parser
        parsed_data = LeetCodeDataParser.parse(snapshot.raw_data)

        # 2. Extract snapshot-derived problem stats
        problem_stats = LeetCodeProblemStatsSchema(
            easy_solved=parsed_data.problems.easy_solved,
            medium_solved=parsed_data.problems.medium_solved,
            hard_solved=parsed_data.problems.hard_solved,
            total_solved=parsed_data.problems.total_solved,
            easy_submissions=parsed_data.problems.easy_submissions,
            medium_submissions=parsed_data.problems.medium_submissions,
            hard_submissions=parsed_data.problems.hard_submissions,
            total_submissions=parsed_data.problems.total_submissions
        )

        # 3. Aggregate and deduplicate topics/tags
        # Priority mapping: advanced > intermediate > fundamental
        group_priorities = {"advanced": 3, "intermediate": 2, "fundamental": 1}
        merged_tags = {}  # tag_slug -> dict

        def add_tags_group(tag_list, difficulty_name):
            for t in tag_list:
                slug = t.tag_slug
                if slug not in merged_tags:
                    merged_tags[slug] = {
                        "tag_name": t.tag_name,
                        "tag_slug": slug,
                        "solved_count": t.solved_count,
                        "difficulty_level": difficulty_name
                    }
                else:
                    merged_tags[slug]["solved_count"] += t.solved_count
                    # Determine difficulty level using priority
                    current_diff = merged_tags[slug]["difficulty_level"]
                    if group_priorities[difficulty_name] > group_priorities[current_diff]:
                        merged_tags[slug]["difficulty_level"] = difficulty_name

        add_tags_group(parsed_data.tags.fundamental, "fundamental")
        add_tags_group(parsed_data.tags.intermediate, "intermediate")
        add_tags_group(parsed_data.tags.advanced, "advanced")

        # Map to TopicSummarySchema objects
        topic_summaries = [
            TopicSummarySchema(
                tag_name=info["tag_name"],
                tag_slug=info["tag_slug"],
                solved_count=info["solved_count"],
                difficulty_level=info["difficulty_level"]
            )
            for info in merged_tags.values()
        ]

        # Deterministic sorting: 1. solved_count DESC, 2. tag_name ASC, 3. tag_slug ASC
        most_practiced_topics = sorted(
            topic_summaries,
            key=lambda t: (-t.solved_count, t.tag_name, t.tag_slug)
        )[:5]

        # 4. Retrieve chronological history
        history_records = await self.history_repo.get_history(user_id)
        history_dict = {r.date: r for r in history_records}

        # Initialize history-derived metrics
        problems_solved_growth = None
        easy_solved_growth = None
        medium_solved_growth = None
        hard_solved_growth = None
        submissions_growth = None
        
        problems_solved_frequency_per_day = None
        active_days_count = None
        contribution_consistency = None
        
        current_streak = None
        longest_streak = None

        if len(history_records) >= 1:
            earliest_date = history_records[0].date
            latest_date = history_records[-1].date

            # Growth metrics (Min 2 records)
            if len(history_records) >= 2:
                earliest_rec = history_records[0]
                latest_rec = history_records[-1]
                
                problems_solved_growth = latest_rec.problems_solved - earliest_rec.problems_solved
                easy_solved_growth = latest_rec.easy_solved - earliest_rec.easy_solved
                medium_solved_growth = latest_rec.medium_solved - earliest_rec.medium_solved
                hard_solved_growth = latest_rec.hard_solved - earliest_rec.hard_solved
                submissions_growth = latest_rec.submissions - earliest_rec.submissions

            # Observed daily transitions (Min 2 records)
            valid_transitions = []
            for i in range(1, len(history_records)):
                prev = history_records[i - 1]
                curr = history_records[i]
                if (curr.date - prev.date).days == 1:
                    delta = curr.problems_solved - prev.problems_solved
                    if delta >= 0:
                        valid_transitions.append((prev, curr, delta))

            if len(valid_transitions) > 0:
                total_valid_solved = sum(delta for _, _, delta in valid_transitions)
                problems_solved_frequency_per_day = total_valid_solved / len(valid_transitions)
                active_days_count = sum(1 for _, _, delta in valid_transitions if delta > 0)
                contribution_consistency = active_days_count / len(valid_transitions)

            # Longest streak calculation from consecutive valid transitions
            if len(history_records) >= 2:
                longest_streak = 0
                current_temp_streak = 0
                check_date = earliest_date + timedelta(days=1)
                while check_date <= latest_date:
                    prev_date = check_date - timedelta(days=1)
                    if check_date in history_dict and prev_date in history_dict:
                        prev_rec = history_dict[prev_date]
                        curr_rec = history_dict[check_date]
                        delta = curr_rec.problems_solved - prev_rec.problems_solved
                        if delta > 0:
                            current_temp_streak += 1
                            longest_streak = max(longest_streak, current_temp_streak)
                        else:
                            current_temp_streak = 0
                    else:
                        current_temp_streak = 0
                    check_date = check_date + timedelta(days=1)

            # Current streak calculation with anchor-day and cumulative transition rules
            ref_date = analysis_date or date.today()
            anchor_date = None
            
            if ref_date in history_dict and (ref_date - timedelta(days=1)) in history_dict:
                anchor_date = ref_date
            elif (ref_date - timedelta(days=1)) in history_dict and (ref_date - timedelta(days=2)) in history_dict:
                anchor_date = ref_date - timedelta(days=1)

            if anchor_date is None:
                current_streak = None
            else:
                anchor_delta = history_dict[anchor_date].problems_solved - history_dict[anchor_date - timedelta(days=1)].problems_solved
                
                if anchor_date == ref_date - timedelta(days=1) and anchor_delta > 0:
                    current_streak = None
                elif anchor_delta < 0:
                    current_streak = None
                elif anchor_delta == 0:
                    current_streak = 0
                else:
                    # anchor_delta > 0: trace backwards
                    streak_len = 0
                    check_date = anchor_date
                    while True:
                        prev_date = check_date - timedelta(days=1)
                        if prev_date < earliest_date:
                            # Reached before the start of tracked history; return accumulated streak
                            current_streak = streak_len
                            break
                            
                        if check_date in history_dict and prev_date in history_dict:
                            delta = history_dict[check_date].problems_solved - history_dict[prev_date].problems_solved
                            if delta > 0:
                                streak_len += 1
                                check_date = prev_date
                            elif delta == 0:
                                current_streak = streak_len
                                break
                            else:
                                # negative delta: invalid transition
                                current_streak = None
                                break
                        else:
                            # missing date
                            if check_date == anchor_date:
                                current_streak = None
                            else:
                                current_streak = None
                            break

        return LeetCodeAnalysisResultSchema(
            user_id=user_id,
            username=parsed_data.username,
            problem_stats=problem_stats,
            most_practiced_topics=most_practiced_topics,
            problems_solved_growth=problems_solved_growth,
            easy_solved_growth=easy_solved_growth,
            medium_solved_growth=medium_solved_growth,
            hard_solved_growth=hard_solved_growth,
            submissions_growth=submissions_growth,
            problems_solved_frequency_per_day=problems_solved_frequency_per_day,
            active_days_count=active_days_count,
            contribution_consistency=contribution_consistency,
            current_streak=current_streak,
            longest_streak=longest_streak
        )
