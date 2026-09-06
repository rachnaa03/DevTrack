"""create_insights_table

Revision ID: 184790d05ece
Revises: d220aeae5fe8
Create Date: 2026-09-05 18:35:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '184790d05ece'
down_revision: Union[str, Sequence[str], None] = 'd220aeae5fe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the insights table."""
    op.create_table(
        'insights',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('historical_value', sa.Float(), nullable=False),
        sa.Column('absolute_change', sa.Float(), nullable=False),
        sa.Column('percent_change', sa.Float(), nullable=True),
        sa.Column('current_date', sa.Date(), nullable=False),
        sa.Column('historical_date', sa.Date(), nullable=False),
        sa.Column('rule_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_insights_user_generated', 'insights', ['user_id', sa.literal_column('generated_at DESC')], unique=False)
    op.create_index('idx_insights_user_platform', 'insights', ['user_id', 'platform'], unique=False)


def downgrade() -> None:
    """Drop the insights table."""
    op.drop_index('idx_insights_user_platform', table_name='insights')
    op.drop_index('idx_insights_user_generated', table_name='insights')
    op.drop_table('insights')
