"""create recommendations table

Revision ID: a1b2c3d4e5f6
Revises: 184790d05ece
Create Date: 2026-09-06 00:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "184790d05ece"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # Rule identification
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column(
            "rule_version",
            sa.String(50),
            server_default="v1",
            nullable=False,
        ),
        # Classification
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        # Human-readable output
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        # Mutable lifecycle state
        sa.Column(
            "status",
            sa.String(20),
            server_default="active",
            nullable=False,
        ),
        # Machine-readable evidence (why the rule fired)
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        # Timestamps
        sa.Column(
            "generated_at",
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
        # Constraints
        sa.CheckConstraint(
            "priority IN ('HIGH', 'MEDIUM', 'LOW')",
            name="chk_recommendations_priority",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'dismissed', 'completed')",
            name="chk_recommendations_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "rule_id",
            "rule_version",
            name="uq_recommendations_user_rule",
        ),
    )

    # Index: newest recommendations for a user (primary retrieval)
    op.create_index(
        "idx_recommendations_user_generated",
        "recommendations",
        ["user_id", sa.text("generated_at DESC")],
    )

    # Index: filter by status per user (active vs dismissed)
    op.create_index(
        "idx_recommendations_user_status",
        "recommendations",
        ["user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_recommendations_user_status", table_name="recommendations")
    op.drop_index("idx_recommendations_user_generated", table_name="recommendations")
    op.drop_table("recommendations")
