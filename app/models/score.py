import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Integer, String, Index, CheckConstraint, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class DeveloperScore(Base):
    """
    SQLAlchemy database model for the DeveloperScore entity.
    Stores historical calculated scores for users.
    """
    __tablename__ = "developer_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    overall_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    consistency_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    problem_solving_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    open_source_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    score_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1",
        server_default="v1"
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="developer_scores")

    __table_args__ = (
        Index("idx_developer_scores_user_computed", "user_id", desc("computed_at")),
        CheckConstraint("overall_score BETWEEN 0 AND 1000", name="chk_developer_scores_overall"),
        CheckConstraint("consistency_score BETWEEN 0 AND 300", name="chk_developer_scores_consistency"),
        CheckConstraint("problem_solving_score BETWEEN 0 AND 350", name="chk_developer_scores_problem_solving"),
        CheckConstraint("open_source_score BETWEEN 0 AND 350", name="chk_developer_scores_open_source"),
    )
