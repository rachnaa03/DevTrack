import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class WeeklyReport(Base):
    """
    SQLAlchemy database model for Weekly Retrospective Reports.
    Stores precomputed weekly metrics, score deltas, and qualitative summaries for a user.
    """
    __tablename__ = "weekly_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    week_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    report_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="weekly_reports")

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_reports_user_week_start"),
    )
