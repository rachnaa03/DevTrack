import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, DateTime, Date, Integer, Index, UniqueConstraint, CheckConstraint, desc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class LeetCodeHistory(Base):
    """
    SQLAlchemy database model for the LeetCodeHistory entity.
    Stores daily parsed relational records representing LeetCode problem counts and stats.
    """
    __tablename__ = "leetcode_histories"

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
    problems_solved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    easy_solved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    medium_solved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    hard_solved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    submissions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    parsed_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # N:1 relationship mapping back to User
    user: Mapped["User"] = relationship("User", back_populates="leetcode_histories")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_leetcode_histories_user_date"),
        Index("idx_leetcode_histories_user_date", "user_id", desc("date")),
        CheckConstraint("problems_solved >= 0", name="chk_leetcode_histories_problems_solved"),
        CheckConstraint("easy_solved >= 0", name="chk_leetcode_histories_easy_solved"),
        CheckConstraint("medium_solved >= 0", name="chk_leetcode_histories_medium_solved"),
        CheckConstraint("hard_solved >= 0", name="chk_leetcode_histories_hard_solved"),
        CheckConstraint("submissions >= 0", name="chk_leetcode_histories_submissions"),
    )
