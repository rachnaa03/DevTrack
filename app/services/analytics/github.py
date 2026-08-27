from datetime import date, timedelta
from uuid import UUID

from app.repositories.github_snapshot import GitHubSnapshotRepository
from app.repositories.github_history import GitHubHistoryRepository
from app.services.integrations.github_parser import GitHubDataParser
from app.schemas.github_analysis import (
    GitHubAnalysisResultSchema,
    RepositoryStatsSchema,
    RepoSummarySchema,
)

class GitHubAnalyzer:
    """Service responsible for converting structured GitHub histories and snapshots into developer analytics."""

    def __init__(
        self,
        snapshot_repo: GitHubSnapshotRepository,
        history_repo: GitHubHistoryRepository
    ):
        self.snapshot_repo = snapshot_repo
        self.history_repo = history_repo

    async def analyze(
        self,
        user_id: UUID,
        analysis_date: date | None = None
    ) -> GitHubAnalysisResultSchema:
        """
        Analyze raw snapshots and structured histories to compute statistics and trends.
        """
        # 1. Fetch latest raw snapshot
        snapshot = await self.snapshot_repo.get_latest_by_user_id(user_id)
        if snapshot is None:
            raise ValueError("No GitHub snapshot found for user.")

        # Parse raw snapshot using the existing parser
        parsed_data = GitHubDataParser.parse(snapshot.raw_data)

        # 2. Extract snapshot-derived metrics
        repo_stats = RepositoryStatsSchema(
            total_repositories=parsed_data.repositories_count,
            total_stars=parsed_data.total_stars,
            total_forks=parsed_data.total_forks,
            total_size=parsed_data.total_size,
            total_open_issues=parsed_data.total_open_issues
        )

        # Map list of repositories to RepoSummarySchema helper objects
        repo_summaries = [
            RepoSummarySchema(
                name=r.name,
                full_name=r.full_name,
                stars=r.stargazers_count,
                forks=r.forks_count,
                language=r.language,
                pushed_at=r.pushed_at.date() if r.pushed_at is not None else None
            )
            for r in parsed_data.repositories
        ]

        # Deterministic sorting for repositories list (limits to 5)
        # most_starred_repos: stars descending, then name ascending
        most_starred_repos = sorted(
            repo_summaries,
            key=lambda r: (-r.stars, r.name)
        )[:5]

        # recently_updated_repositories: whether pushed_at is None, then pushed_at descending, then name ascending
        recently_updated_repositories = sorted(
            repo_summaries,
            key=lambda r: (
                r.pushed_at is None,
                -r.pushed_at.toordinal() if r.pushed_at is not None else 0,
                r.name
            )
        )[:5]

        # 3. Retrieve chronological history
        history_records = await self.history_repo.get_history(user_id)
        history_dict = {r.date: r for r in history_records}

        # Initialize history-derived metrics
        repository_growth = None
        star_growth = None
        fork_growth = None
        total_commits = None
        commit_frequency_per_day = None
        active_days_count = None
        contribution_consistency = None
        current_streak = None
        longest_streak = None

        # 4. Growth calculations (Min 2 records)
        if len(history_records) >= 2:
            earliest_rec = history_records[0]
            latest_rec = history_records[-1]
            
            latest_repos = latest_rec.repositories if latest_rec.repositories is not None else 0
            earliest_repos = earliest_rec.repositories if earliest_rec.repositories is not None else 0
            repository_growth = latest_repos - earliest_repos

            latest_stars = latest_rec.stars if latest_rec.stars is not None else 0
            earliest_stars = earliest_rec.stars if earliest_rec.stars is not None else 0
            star_growth = latest_stars - earliest_stars

            latest_forks = latest_rec.forks if latest_rec.forks is not None else 0
            earliest_forks = earliest_rec.forks if earliest_rec.forks is not None else 0
            fork_growth = latest_forks - earliest_forks

        # 5. Observed-day metrics (Min 1 record)
        if len(history_records) >= 1:
            total_commits = sum(r.commits for r in history_records)
            active_days_count = sum(1 for r in history_records if r.commits > 0)
            
            num_obs = len(history_records)
            commit_frequency_per_day = total_commits / num_obs
            contribution_consistency = active_days_count / num_obs

            # 6. Longest streak calculation
            longest_streak = 0
            current_temp_streak = 0
            earliest_date = history_records[0].date
            latest_date = history_records[-1].date
            
            check_date = earliest_date
            while check_date <= latest_date:
                if check_date in history_dict:
                    record = history_dict[check_date]
                    if record.commits > 0:
                        current_temp_streak += 1
                        longest_streak = max(longest_streak, current_temp_streak)
                    else:
                        current_temp_streak = 0
                else:
                    # missing date breaks the streak
                    current_temp_streak = 0
                check_date = check_date + timedelta(days=1)

            # 7. Current streak calculation with anchor-day rules
            ref_date = analysis_date or date.today()
            anchor_date = None
            if ref_date in history_dict:
                anchor_date = ref_date
            elif (ref_date - timedelta(days=1)) in history_dict:
                anchor_date = ref_date - timedelta(days=1)

            if anchor_date is None:
                current_streak = None
            else:
                # If anchor date is analysis_date - 1, and yesterday has commits > 0:
                # then analysis_date (which is after anchor_date) is missing and represents unknown activity.
                # Thus, we cannot determine if the streak is active or broken, so return None.
                if anchor_date == ref_date - timedelta(days=1) and history_dict[anchor_date].commits > 0:
                    current_streak = None
                else:
                    check_date = anchor_date
                    streak_len = 0
                    while True:
                        if check_date < earliest_date:
                            # Reached before the start of tracked history; return accumulated streak
                            current_streak = streak_len
                            break
                        
                        if check_date in history_dict:
                            record = history_dict[check_date]
                            if record.commits > 0:
                                streak_len += 1
                                check_date = check_date - timedelta(days=1)
                            else:
                                # commits == 0
                                if check_date == anchor_date:
                                    current_streak = 0
                                else:
                                    current_streak = streak_len
                                break
                        else:
                            # missing date
                            if check_date == anchor_date:
                                current_streak = None
                            else:
                                # Ambiguous case: streak encounters a missing calendar date before reaching a zero-commit day
                                current_streak = None
                            break

        return GitHubAnalysisResultSchema(
            user_id=user_id,
            login=parsed_data.login,
            repo_stats=repo_stats,
            most_starred_repos=most_starred_repos,
            recently_updated_repositories=recently_updated_repositories,
            language_distribution=parsed_data.languages,
            repository_growth=repository_growth,
            star_growth=star_growth,
            fork_growth=fork_growth,
            total_commits=total_commits,
            commit_frequency_per_day=commit_frequency_per_day,
            active_days_count=active_days_count,
            contribution_consistency=contribution_consistency,
            current_streak=current_streak,
            longest_streak=longest_streak
        )
