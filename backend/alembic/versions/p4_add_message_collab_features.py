"""Add collaboration fields to chat messages.

Revision ID: p4_add_message_collab_features
Revises: p3_add_shared_resource_capsule_prism
Create Date: 2025-01-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID

revision = 'p4_add_message_collab_features'
down_revision = 'p3_add_shared_resource_capsule_prism'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('group_messages') as batch_op:
        batch_op.add_column(sa.Column('thread_root_id', GUID(), nullable=True))
        batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reactions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('mention_user_ids', sa.JSON(), nullable=True))
        batch_op.create_index('idx_message_group_thread', ['group_id', 'thread_root_id', 'created_at'])
        batch_op.create_foreign_key(
            'group_messages_thread_root_id_fkey',
            'group_messages',
            ['thread_root_id'],
            ['id']
        )

    with op.batch_alter_table('private_messages') as batch_op:
        batch_op.add_column(sa.Column('thread_root_id', GUID(), nullable=True))
        batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reactions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('mention_user_ids', sa.JSON(), nullable=True))
        batch_op.create_index('idx_private_message_thread', ['sender_id', 'receiver_id', 'thread_root_id', 'created_at'])
        batch_op.create_foreign_key(
            'private_messages_thread_root_id_fkey',
            'private_messages',
            ['thread_root_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('private_messages') as batch_op:
        batch_op.drop_constraint('private_messages_thread_root_id_fkey', type_='foreignkey')
        batch_op.drop_index('idx_private_message_thread')
        batch_op.drop_column('mention_user_ids')
        batch_op.drop_column('reactions')
        batch_op.drop_column('edited_at')
        batch_op.drop_column('revoked_at')
        batch_op.drop_column('is_revoked')
        batch_op.drop_column('thread_root_id')

    with op.batch_alter_table('group_messages') as batch_op:
        batch_op.drop_constraint('group_messages_thread_root_id_fkey', type_='foreignkey')
        batch_op.drop_index('idx_message_group_thread')
        batch_op.drop_column('mention_user_ids')
        batch_op.drop_column('reactions')
        batch_op.drop_column('edited_at')
        batch_op.drop_column('revoked_at')
        batch_op.drop_column('is_revoked')
        batch_op.drop_column('thread_root_id')
