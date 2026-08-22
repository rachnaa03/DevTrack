from sqlalchemy import desc

from app.models.user import User
from app.models.github_history import GitHubHistory
from app.models.leetcode_history import LeetCodeHistory

def test_github_history_model_attributes() -> None:
    """Verify that GitHubHistory database model attributes and constraints are defined correctly."""
    assert GitHubHistory.__tablename__ == "github_histories"
    
    assert hasattr(GitHubHistory, "id")
    assert hasattr(GitHubHistory, "user_id")
    assert hasattr(GitHubHistory, "date")
    assert hasattr(GitHubHistory, "commits")
    assert hasattr(GitHubHistory, "stars")
    assert hasattr(GitHubHistory, "forks")
    assert hasattr(GitHubHistory, "repositories")
    assert hasattr(GitHubHistory, "parsed_metrics")
    assert hasattr(GitHubHistory, "created_at")
    assert hasattr(GitHubHistory, "user")

    # Verify table args (index, unique constraint, checks)
    table_args = GitHubHistory.__table_args__
    uq = next((arg for arg in table_args if hasattr(arg, "name") and arg.name == "uq_github_histories_user_date"), None)
    assert uq is not None

    idx = next((arg for arg in table_args if hasattr(arg, "name") and arg.name == "idx_github_histories_user_date"), None)
    assert idx is not None

def test_leetcode_history_model_attributes() -> None:
    """Verify that LeetCodeHistory database model attributes and constraints are defined correctly."""
    assert LeetCodeHistory.__tablename__ == "leetcode_histories"
    
    assert hasattr(LeetCodeHistory, "id")
    assert hasattr(LeetCodeHistory, "user_id")
    assert hasattr(LeetCodeHistory, "date")
    assert hasattr(LeetCodeHistory, "problems_solved")
    assert hasattr(LeetCodeHistory, "easy_solved")
    assert hasattr(LeetCodeHistory, "medium_solved")
    assert hasattr(LeetCodeHistory, "hard_solved")
    assert hasattr(LeetCodeHistory, "submissions")
    assert hasattr(LeetCodeHistory, "parsed_metrics")
    assert hasattr(LeetCodeHistory, "created_at")
    assert hasattr(LeetCodeHistory, "user")

    # Verify table args
    table_args = LeetCodeHistory.__table_args__
    uq = next((arg for arg in table_args if hasattr(arg, "name") and arg.name == "uq_leetcode_histories_user_date"), None)
    assert uq is not None

    idx = next((arg for arg in table_args if hasattr(arg, "name") and arg.name == "idx_leetcode_histories_user_date"), None)
    assert idx is not None

def test_user_history_relationships() -> None:
    """Verify relationship properties on User model for history tables."""
    assert hasattr(User, "github_histories")
    assert hasattr(User, "leetcode_histories")

    # Check GitHubHistory relationship properties
    github_rel = User.github_histories.property
    assert github_rel.uselist is True
    assert github_rel.back_populates == "user"
    assert "delete" in github_rel.cascade
    assert "delete-orphan" in github_rel.cascade

    # Check LeetCodeHistory relationship properties
    leetcode_rel = User.leetcode_histories.property
    assert leetcode_rel.uselist is True
    assert leetcode_rel.back_populates == "user"
    assert "delete" in leetcode_rel.cascade
    assert "delete-orphan" in leetcode_rel.cascade
