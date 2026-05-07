"""add_post_comments_table

Revision ID: 7f807dcd4e5f
Revises: r8_fix_achievementtype_enum_duplicate
Create Date: 2026-05-07 10:11:05.274566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1 FROM post_comments LIMIT 1;"
#   backfill_plan: "n/a"
#   owner: "platform"
#   ticket: "COM-P0-03"

revision: str = '7f807dcd4e5f'
down_revision: Union[str, None] = 'r8_fix_achievementtype_enum_duplicate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'post_comments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('post_id', UUID(as_uuid=True), sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_post_comment_post', 'post_comments', ['post_id'])
    op.create_index('idx_post_comment_user', 'post_comments', ['user_id'])


def downgrade() -> None:
    op.drop_table('post_comments')
