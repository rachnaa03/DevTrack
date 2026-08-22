import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, DateTime, Date, Integer, Index, UniqueConstraint, CheckConstraint, desc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class GitHubHistory(Base):
    """
    SQLAlchemy database model for the GitHubHistory entity.
    Stores daily parsed relational records representing commit totals and repository metrics.
    """
    __tablename__ = "github_histories"

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
    commits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    stars: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    forks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    repositories: Mapped[int] = mapped_column(
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
    user: Mapped["User"] = relationship("User", back_populates="github_histories")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_github_histories_user_date"),
        Index("idx_github_histories_user_date", "user_id", desc("date")),
        CheckConstraint("commits >= 0", name="chk_github_histories_commits"),
        CheckConstraint("stars >= 0", name="chk_github_histories_stars"),
        CheckConstraint("forks >= 0", name="chk_github_histories_forks"),
        CheckConstraint("repositories >= 0", name="chk_github_histories_repositories"),
    )
