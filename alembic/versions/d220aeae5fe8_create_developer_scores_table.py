"""create_developer_scores_table

Revision ID: d220aeae5fe8
Revises: 580368cd70c6
Create Date: 2026-08-27 20:36:19.717886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd220aeae5fe8'
down_revision: Union[str, Sequence[str], None] = '580368cd70c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('developer_scores',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('consistency_score', sa.Integer(), nullable=False),
        sa.Column('problem_solving_score', sa.Integer(), nullable=False),
        sa.Column('open_source_score', sa.Integer(), nullable=False),
        sa.Column('score_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('overall_score BETWEEN 0 AND 1000', name='chk_developer_scores_overall'),
        sa.CheckConstraint('consistency_score BETWEEN 0 AND 300', name='chk_developer_scores_consistency'),
        sa.CheckConstraint('problem_solving_score BETWEEN 0 AND 350', name='chk_developer_scores_problem_solving'),
        sa.CheckConstraint('open_source_score BETWEEN 0 AND 350', name='chk_developer_scores_open_source'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_developer_scores_user_computed', 'developer_scores', ['user_id', sa.literal_column('computed_at DESC')], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_developer_scores_user_computed', table_name='developer_scores')
    op.drop_table('developer_scores')
