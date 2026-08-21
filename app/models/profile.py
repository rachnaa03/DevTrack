import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Profile(Base):
    """
    SQLAlchemy database model for the Profile entity.
    Stores linked handles and user bio attributes in a 1-to-1 relationship with User.
    """
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True
    )
    github_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    leetcode_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
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

    # 1:1 bidirectional relationship mapping back to User
    user: Mapped["User"] = relationship("User", back_populates="profile")

    __table_args__ = (
        Index("idx_profiles_user_id", "user_id", unique=True),
    )
