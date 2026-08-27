import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, DateTime, Date, Integer, Float, Index, UniqueConstraint, CheckConstraint, desc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class GitHubAnalytics(Base):
    """
    SQLAlchemy database model for the GitHubAnalytics entity.
    Stores daily calculated analytics for a user's GitHub activity.
    """
    __tablename__ = "github_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    # Scalar Metrics
    total_repositories: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_stars: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_forks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_open_issues: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    repository_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    star_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    fork_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    total_commits: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    commit_frequency_per_day: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )
    active_days_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    contribution_consistency: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )
    current_streak: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    longest_streak: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # JSONB Metrics
    languages: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True
    )
    most_starred_repos: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True
    )
    recently_updated_repos: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="github_analytics")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_github_analytics_user_date"),
        Index("idx_github_analytics_user_date", "user_id", desc("date")),
        CheckConstraint("total_repositories >= 0", name="chk_github_analytics_total_repos"),
        CheckConstraint("total_stars >= 0", name="chk_github_analytics_total_stars"),
        CheckConstraint("total_forks >= 0", name="chk_github_analytics_total_forks"),
        CheckConstraint("total_size >= 0", name="chk_github_analytics_total_size"),
        CheckConstraint("total_open_issues >= 0", name="chk_github_analytics_total_open_issues"),
        CheckConstraint("total_commits >= 0", name="chk_github_analytics_total_commits"),
        CheckConstraint("commit_frequency_per_day >= 0.0", name="chk_github_analytics_commit_frequency"),
        CheckConstraint("active_days_count >= 0", name="chk_github_analytics_active_days"),
        CheckConstraint("contribution_consistency >= 0.0 AND contribution_consistency <= 1.0", name="chk_github_analytics_consistency"),
        CheckConstraint("current_streak >= 0", name="chk_github_analytics_current_streak"),
        CheckConstraint("longest_streak >= 0", name="chk_github_analytics_longest_streak"),
    )
