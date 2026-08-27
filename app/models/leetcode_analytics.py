import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, DateTime, Date, Integer, Float, Index, UniqueConstraint, CheckConstraint, desc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class LeetCodeAnalytics(Base):
    """
    SQLAlchemy database model for the LeetCodeAnalytics entity.
    Stores daily calculated analytics for a user's LeetCode activity.
    """
    __tablename__ = "leetcode_analytics"

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
    easy_solved: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    medium_solved: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    hard_solved: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_solved: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    easy_submissions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    medium_submissions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    hard_submissions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    total_submissions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    problems_solved_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    easy_solved_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    medium_solved_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    hard_solved_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    submissions_growth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    problems_solved_frequency_per_day: Mapped[float | None] = mapped_column(
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
    most_practiced_topics: Mapped[list[Any] | None] = mapped_column(
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
    user: Mapped["User"] = relationship("User", back_populates="leetcode_analytics")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_leetcode_analytics_user_date"),
        Index("idx_leetcode_analytics_user_date", "user_id", desc("date")),
        CheckConstraint("easy_solved >= 0", name="chk_leetcode_analytics_easy_solved"),
        CheckConstraint("medium_solved >= 0", name="chk_leetcode_analytics_medium_solved"),
        CheckConstraint("hard_solved >= 0", name="chk_leetcode_analytics_hard_solved"),
        CheckConstraint("total_solved >= 0", name="chk_leetcode_analytics_total_solved"),
        CheckConstraint("easy_submissions >= 0", name="chk_leetcode_analytics_easy_submissions"),
        CheckConstraint("medium_submissions >= 0", name="chk_leetcode_analytics_medium_submissions"),
        CheckConstraint("hard_submissions >= 0", name="chk_leetcode_analytics_hard_submissions"),
        CheckConstraint("total_submissions >= 0", name="chk_leetcode_analytics_total_submissions"),
        CheckConstraint("problems_solved_frequency_per_day >= 0.0", name="chk_leetcode_analytics_frequency"),
        CheckConstraint("active_days_count >= 0", name="chk_leetcode_analytics_active_days"),
        CheckConstraint("contribution_consistency >= 0.0 AND contribution_consistency <= 1.0", name="chk_leetcode_analytics_consistency"),
        CheckConstraint("current_streak >= 0", name="chk_leetcode_analytics_current_streak"),
        CheckConstraint("longest_streak >= 0", name="chk_leetcode_analytics_longest_streak"),
    )
