"""P1: Add post visibility field for access control

This migration addresses a critical access control gap identified in the 2025 Tech Audit:
- posts.visibility: Controls who can see a post (public, private, friends_only)
- Default: public (backward compatible)
- Used to enforce post visibility in GetPost and GetFeed queries

Revision ID: p1_post_visibility
Revises: p0_vector_indexes
Create Date: 2025-12-28

"""
from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, table_exists

# revision identifiers, used by Alembic.
revision = 'p1_post_visibility'
down_revision = 'p0_vector_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # P1: Add visibility field to posts table
    # This enables access control for community posts
    inspector = get_inspector()
    if table_exists(inspector, "posts") and not column_exists(inspector, "posts", "visibility"):
        op.execute("""
            ALTER TABLE posts
            ADD COLUMN visibility VARCHAR(20) DEFAULT 'public'
            CHECK (visibility IN ('public', 'private', 'friends_only'));
        """)

    # Create index for visibility filtering in GetFeed queries
    if table_exists(inspector, "posts"):
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_visibility_created
            ON public.posts (visibility, created_at DESC)
            WHERE visibility = 'public';
        """)

    # Add comment for documentation
    op.execute("""
        COMMENT ON COLUMN posts.visibility IS
        'Controls post visibility: public (default), private (creator only), friends_only (creator + friends)';
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_posts_visibility_created;")
    inspector = get_inspector()
    if table_exists(inspector, "posts") and column_exists(inspector, "posts", "visibility"):
        op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS visibility;")
