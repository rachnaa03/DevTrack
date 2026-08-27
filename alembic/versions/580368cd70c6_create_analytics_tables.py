"""create_analytics_tables

Revision ID: 580368cd70c6
Revises: bf37cdd39cb0
Create Date: 2026-08-27 20:16:07.194818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '580368cd70c6'
down_revision: Union[str, Sequence[str], None] = 'bf37cdd39cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('github_analytics',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_repositories', sa.Integer(), nullable=True),
        sa.Column('total_stars', sa.Integer(), nullable=True),
        sa.Column('total_forks', sa.Integer(), nullable=True),
        sa.Column('total_size', sa.Integer(), nullable=True),
        sa.Column('total_open_issues', sa.Integer(), nullable=True),
        sa.Column('repository_growth', sa.Integer(), nullable=True),
        sa.Column('star_growth', sa.Integer(), nullable=True),
        sa.Column('fork_growth', sa.Integer(), nullable=True),
        sa.Column('total_commits', sa.Integer(), nullable=True),
        sa.Column('commit_frequency_per_day', sa.Float(), nullable=True),
        sa.Column('active_days_count', sa.Integer(), nullable=True),
        sa.Column('contribution_consistency', sa.Float(), nullable=True),
        sa.Column('current_streak', sa.Integer(), nullable=True),
        sa.Column('longest_streak', sa.Integer(), nullable=True),
        sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('most_starred_repos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recently_updated_repos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('total_repositories >= 0', name='chk_github_analytics_total_repos'),
        sa.CheckConstraint('total_stars >= 0', name='chk_github_analytics_total_stars'),
        sa.CheckConstraint('total_forks >= 0', name='chk_github_analytics_total_forks'),
        sa.CheckConstraint('total_size >= 0', name='chk_github_analytics_total_size'),
        sa.CheckConstraint('total_open_issues >= 0', name='chk_github_analytics_total_open_issues'),
        sa.CheckConstraint('total_commits >= 0', name='chk_github_analytics_total_commits'),
        sa.CheckConstraint('commit_frequency_per_day >= 0.0', name='chk_github_analytics_commit_frequency'),
        sa.CheckConstraint('active_days_count >= 0', name='chk_github_analytics_active_days'),
        sa.CheckConstraint('contribution_consistency >= 0.0 AND contribution_consistency <= 1.0', name='chk_github_analytics_consistency'),
        sa.CheckConstraint('current_streak >= 0', name='chk_github_analytics_current_streak'),
        sa.CheckConstraint('longest_streak >= 0', name='chk_github_analytics_longest_streak'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_github_analytics_user_date')
    )
    op.create_index('idx_github_analytics_user_date', 'github_analytics', ['user_id', sa.literal_column('date DESC')], unique=False)

    op.create_table('leetcode_analytics',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('easy_solved', sa.Integer(), nullable=True),
        sa.Column('medium_solved', sa.Integer(), nullable=True),
        sa.Column('hard_solved', sa.Integer(), nullable=True),
        sa.Column('total_solved', sa.Integer(), nullable=True),
        sa.Column('easy_submissions', sa.Integer(), nullable=True),
        sa.Column('medium_submissions', sa.Integer(), nullable=True),
        sa.Column('hard_submissions', sa.Integer(), nullable=True),
        sa.Column('total_submissions', sa.Integer(), nullable=True),
        sa.Column('problems_solved_growth', sa.Integer(), nullable=True),
        sa.Column('easy_solved_growth', sa.Integer(), nullable=True),
        sa.Column('medium_solved_growth', sa.Integer(), nullable=True),
        sa.Column('hard_solved_growth', sa.Integer(), nullable=True),
        sa.Column('submissions_growth', sa.Integer(), nullable=True),
        sa.Column('problems_solved_frequency_per_day', sa.Float(), nullable=True),
        sa.Column('active_days_count', sa.Integer(), nullable=True),
        sa.Column('contribution_consistency', sa.Float(), nullable=True),
        sa.Column('current_streak', sa.Integer(), nullable=True),
        sa.Column('longest_streak', sa.Integer(), nullable=True),
        sa.Column('most_practiced_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('easy_solved >= 0', name='chk_leetcode_analytics_easy_solved'),
        sa.CheckConstraint('medium_solved >= 0', name='chk_leetcode_analytics_medium_solved'),
        sa.CheckConstraint('hard_solved >= 0', name='chk_leetcode_analytics_hard_solved'),
        sa.CheckConstraint('total_solved >= 0', name='chk_leetcode_analytics_total_solved'),
        sa.CheckConstraint('easy_submissions >= 0', name='chk_leetcode_analytics_easy_submissions'),
        sa.CheckConstraint('medium_submissions >= 0', name='chk_leetcode_analytics_medium_submissions'),
        sa.CheckConstraint('hard_submissions >= 0', name='chk_leetcode_analytics_hard_submissions'),
        sa.CheckConstraint('total_submissions >= 0', name='chk_leetcode_analytics_total_submissions'),
        sa.CheckConstraint('problems_solved_frequency_per_day >= 0.0', name='chk_leetcode_analytics_frequency'),
        sa.CheckConstraint('active_days_count >= 0', name='chk_leetcode_analytics_active_days'),
        sa.CheckConstraint('contribution_consistency >= 0.0 AND contribution_consistency <= 1.0', name='chk_leetcode_analytics_consistency'),
        sa.CheckConstraint('current_streak >= 0', name='chk_leetcode_analytics_current_streak'),
        sa.CheckConstraint('longest_streak >= 0', name='chk_leetcode_analytics_longest_streak'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_leetcode_analytics_user_date')
    )
    op.create_index('idx_leetcode_analytics_user_date', 'leetcode_analytics', ['user_id', sa.literal_column('date DESC')], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_leetcode_analytics_user_date', table_name='leetcode_analytics')
    op.drop_table('leetcode_analytics')
    op.drop_index('idx_github_analytics_user_date', table_name='github_analytics')
    op.drop_table('github_analytics')
