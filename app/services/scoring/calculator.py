from app.schemas.github_analysis import GitHubAnalysisResultSchema
from app.schemas.leetcode_analysis import LeetCodeAnalysisResultSchema
from app.schemas.score import DeveloperScoreResultSchema, ScoreSubcomponentSchema

class DeveloperScoreCalculator:
    """Pure business logic service responsible for calculating the custom Developer Score v1."""

    @staticmethod
    def calculate(
        github_analysis: GitHubAnalysisResultSchema | None,
        leetcode_analysis: LeetCodeAnalysisResultSchema | None
    ) -> DeveloperScoreResultSchema:
        """
        Calculate the Developer Score (out of 1000) based on GitHub and LeetCode analysis.
        """
        # --- 1. Coding Consistency (Max 300) ---
        github_consistency_raw = None
        leetcode_consistency_raw = None
        
        has_github = github_analysis is not None
        has_leetcode = leetcode_analysis is not None

        if has_github:
            c = github_analysis.contribution_consistency
            s = github_analysis.current_streak
            github_consistency_raw = DeveloperScoreCalculator._calculate_platform_consistency(c, s)

        if has_leetcode:
            c = leetcode_analysis.contribution_consistency
            s = leetcode_analysis.current_streak
            leetcode_consistency_raw = DeveloperScoreCalculator._calculate_platform_consistency(c, s)

        if not has_github and not has_leetcode:
            consistency_raw = 0.0
        elif has_github and has_leetcode:
            # Both connected: sum of both (each max 150)
            consistency_raw = (github_consistency_raw or 0.0) + (leetcode_consistency_raw or 0.0)
        else:
            # Only one connected: scale up connected platform by 2
            connected_pts = github_consistency_raw if has_github else leetcode_consistency_raw
            consistency_raw = (connected_pts or 0.0) * 2.0

        consistency_raw = max(0.0, min(consistency_raw, 300.0))
        consistency_score = round(consistency_raw)

        # --- 2. Problem-Solving Depth (Max 350) ---
        easy_points = 0.0
        medium_points = 0.0
        hard_points = 0.0

        if has_leetcode and leetcode_analysis.problem_stats is not None:
            stats = leetcode_analysis.problem_stats
            easy = DeveloperScoreCalculator._get_non_negative_val(stats.easy_solved)
            medium = DeveloperScoreCalculator._get_non_negative_val(stats.medium_solved)
            hard = DeveloperScoreCalculator._get_non_negative_val(stats.hard_solved)

            easy_points = float(min(easy, 50) * 1)
            medium_points = float(min(medium, 50) * 3)
            hard_points = float(min(hard, 25) * 6)

        depth_raw = easy_points + medium_points + hard_points
        depth_raw = max(0.0, min(depth_raw, 350.0))
        problem_solving_score = round(depth_raw)

        # --- 3. Open Source Impact (Max 350) ---
        repo_volume_points = 0.0
        commit_depth_points = 0.0
        stars_points = 0.0
        forks_points = 0.0

        if has_github:
            repos = 0
            stars = 0
            forks = 0
            if github_analysis.repo_stats is not None:
                stats_gh = github_analysis.repo_stats
                repos = DeveloperScoreCalculator._get_non_negative_val(stats_gh.total_repositories)
                stars = DeveloperScoreCalculator._get_non_negative_val(stats_gh.total_stars)
                forks = DeveloperScoreCalculator._get_non_negative_val(stats_gh.total_forks)

            commits = DeveloperScoreCalculator._get_non_negative_val(github_analysis.total_commits)

            repo_volume_points = (min(repos, 10) / 10.0) * 50.0
            commit_depth_points = (min(commits, 500) / 500.0) * 100.0
            stars_points = (min(stars, 50) / 50.0) * 120.0
            forks_points = (min(forks, 10) / 10.0) * 80.0

        impact_raw = repo_volume_points + commit_depth_points + stars_points + forks_points
        impact_raw = max(0.0, min(impact_raw, 350.0))
        open_source_score = round(impact_raw)

        # --- 4. Overall Score & Subcomponents ---
        overall_score = consistency_score + problem_solving_score + open_source_score
        overall_score = max(0, min(overall_score, 1000))

        subcomponents = ScoreSubcomponentSchema(
            github_consistency_raw=github_consistency_raw,
            leetcode_consistency_raw=leetcode_consistency_raw,
            easy_points=easy_points,
            medium_points=medium_points,
            hard_points=hard_points,
            repo_volume_points=repo_volume_points,
            commit_depth_points=commit_depth_points,
            stars_points=stars_points,
            forks_points=forks_points
        )

        return DeveloperScoreResultSchema(
            overall_score=overall_score,
            consistency_score=consistency_score,
            problem_solving_score=problem_solving_score,
            open_source_score=open_source_score,
            score_version="v1",
            subcomponents=subcomponents
        )

    @staticmethod
    def _calculate_platform_consistency(consistency: float | None, streak: int | None) -> float:
        c = 0.0 if consistency is None else consistency
        c = max(0.0, min(c, 1.0))
        c_pts = c * 100.0

        s = 0 if streak is None else streak
        s = max(0, min(s, 14))
        s_pts = (s / 14.0) * 50.0

        return c_pts + s_pts

    @staticmethod
    def _get_non_negative_val(val: int | None) -> int:
        if val is None:
            return 0
        return max(0, val)
