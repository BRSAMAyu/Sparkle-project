"""create community tables

Revision ID: a1b2c3d4e5f6
Revises: fb11f8afb34c
Create Date: 2025-12-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fb11f8afb34c'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    # Posts
    if not table_exists(inspector, "posts"):
        op.create_table('posts',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('image_urls', sa.JSON(), nullable=True),
            sa.Column('topic', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "posts", "idx_posts_created_at"):
        op.create_index('idx_posts_created_at', 'posts', ['created_at'], unique=False)
    if not index_exists(inspector, "posts", "idx_posts_user_id"):
        op.create_index('idx_posts_user_id', 'posts', ['user_id'], unique=False)

    # Post Likes
    if not table_exists(inspector, "post_likes"):
        op.create_table('post_likes',
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id', 'post_id')
        )
    if not index_exists(inspector, "post_likes", "idx_post_likes_post_id"):
        op.create_index('idx_post_likes_post_id', 'post_likes', ['post_id'], unique=False)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "post_likes"):
        op.drop_table('post_likes')
    if table_exists(inspector, "posts"):
        op.drop_table('posts')
