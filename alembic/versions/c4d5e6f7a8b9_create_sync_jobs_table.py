"""create sync_jobs table

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-09-07 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("total_users", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_users", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_users", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_users", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sync_jobs_started_at",
        "sync_jobs",
        ["started_at"],
    )
    op.create_index(
        "idx_sync_jobs_status",
        "sync_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("idx_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("idx_sync_jobs_started_at", table_name="sync_jobs")
    op.drop_table("sync_jobs")
