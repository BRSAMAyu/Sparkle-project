"""add_composite_indexes_for_hot_paths

Revision ID: comp_idx_20260508
Revises: ac07dc579128
Create Date: 2026-05-08
"""
from alembic import op

revision = 'comp_idx_20260508'
down_revision = 'ac07dc579128'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_group_members_composite
        ON group_members (group_id, user_id);
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_likes_composite
        ON post_likes (user_id, post_id);
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_group_members_composite;")
    op.execute("DROP INDEX IF EXISTS idx_post_likes_composite;")
