import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Milestone(Base):
    """
    SQLAlchemy database model for earned milestone badges.
    Records achievement badges earned by the developer.
    """
    __tablename__ = "milestones"

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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    badge_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="milestones")

    __table_args__ = (
        Index("idx_milestones_user_achieved", "user_id", "achieved_at"),
        UniqueConstraint("user_id", "name", name="uq_milestones_user_name"),
    )
