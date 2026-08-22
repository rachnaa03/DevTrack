import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class LeetCodeSnapshot(Base):
    """
    SQLAlchemy database model for the LeetCodeSnapshot entity.
    Stores daily raw responses from the LeetCode GraphQL API.
    """
    __tablename__ = "leetcode_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # N:1 relationship mapping back to User
    user: Mapped["User"] = relationship("User", back_populates="leetcode_snapshots")

    __table_args__ = (
        Index("idx_leetcode_snapshots_user_fetch", "user_id", "fetched_at"),
    )
