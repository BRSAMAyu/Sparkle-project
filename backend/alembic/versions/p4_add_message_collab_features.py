"""Add collaboration fields to chat messages.

Revision ID: p4_add_message_collab_features
Revises: p3_add_shared_resource_capsule_prism
Create Date: 2025-01-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID
from app.utils.migration_helpers import column_exists, foreign_key_exists, get_inspector, index_exists, table_exists

revision = 'p4_add_message_collab_features'
down_revision = 'p3_shared_rsrc_prism'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    if table_exists(inspector, "group_messages"):
        with op.batch_alter_table('group_messages') as batch_op:
            if not column_exists(inspector, "group_messages", "thread_root_id"):
                batch_op.add_column(sa.Column('thread_root_id', GUID(), nullable=True))
            if not column_exists(inspector, "group_messages", "is_revoked"):
                batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            if not column_exists(inspector, "group_messages", "revoked_at"):
                batch_op.add_column(sa.Column('revoked_at', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "group_messages", "edited_at"):
                batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "group_messages", "reactions"):
                batch_op.add_column(sa.Column('reactions', sa.JSON(), nullable=True))
            if not column_exists(inspector, "group_messages", "mention_user_ids"):
                batch_op.add_column(sa.Column('mention_user_ids', sa.JSON(), nullable=True))
            if not index_exists(inspector, "group_messages", "idx_message_group_thread"):
                batch_op.create_index('idx_message_group_thread', ['group_id', 'thread_root_id', 'created_at'])
            if not foreign_key_exists(inspector, "group_messages", "group_messages_thread_root_id_fkey"):
                batch_op.create_foreign_key(
                    'group_messages_thread_root_id_fkey',
                    'group_messages',
                    ['thread_root_id'],
                    ['id']
                )

    if table_exists(inspector, "private_messages"):
        with op.batch_alter_table('private_messages') as batch_op:
            if not column_exists(inspector, "private_messages", "thread_root_id"):
                batch_op.add_column(sa.Column('thread_root_id', GUID(), nullable=True))
            if not column_exists(inspector, "private_messages", "is_revoked"):
                batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            if not column_exists(inspector, "private_messages", "revoked_at"):
                batch_op.add_column(sa.Column('revoked_at', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "private_messages", "edited_at"):
                batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "private_messages", "reactions"):
                batch_op.add_column(sa.Column('reactions', sa.JSON(), nullable=True))
            if not column_exists(inspector, "private_messages", "mention_user_ids"):
                batch_op.add_column(sa.Column('mention_user_ids', sa.JSON(), nullable=True))
            if not index_exists(inspector, "private_messages", "idx_private_message_thread"):
                batch_op.create_index('idx_private_message_thread', ['sender_id', 'receiver_id', 'thread_root_id', 'created_at'])
            if not foreign_key_exists(inspector, "private_messages", "private_messages_thread_root_id_fkey"):
                batch_op.create_foreign_key(
                    'private_messages_thread_root_id_fkey',
                    'private_messages',
                    ['thread_root_id'],
                    ['id']
                )


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "private_messages"):
        with op.batch_alter_table('private_messages') as batch_op:
            if foreign_key_exists(inspector, "private_messages", "private_messages_thread_root_id_fkey"):
                batch_op.drop_constraint('private_messages_thread_root_id_fkey', type_='foreignkey')
            if index_exists(inspector, "private_messages", "idx_private_message_thread"):
                batch_op.drop_index('idx_private_message_thread')
            if column_exists(inspector, "private_messages", "mention_user_ids"):
                batch_op.drop_column('mention_user_ids')
            if column_exists(inspector, "private_messages", "reactions"):
                batch_op.drop_column('reactions')
            if column_exists(inspector, "private_messages", "edited_at"):
                batch_op.drop_column('edited_at')
            if column_exists(inspector, "private_messages", "revoked_at"):
                batch_op.drop_column('revoked_at')
            if column_exists(inspector, "private_messages", "is_revoked"):
                batch_op.drop_column('is_revoked')
            if column_exists(inspector, "private_messages", "thread_root_id"):
                batch_op.drop_column('thread_root_id')

    if table_exists(inspector, "group_messages"):
        with op.batch_alter_table('group_messages') as batch_op:
            if foreign_key_exists(inspector, "group_messages", "group_messages_thread_root_id_fkey"):
                batch_op.drop_constraint('group_messages_thread_root_id_fkey', type_='foreignkey')
            if index_exists(inspector, "group_messages", "idx_message_group_thread"):
                batch_op.drop_index('idx_message_group_thread')
            if column_exists(inspector, "group_messages", "mention_user_ids"):
                batch_op.drop_column('mention_user_ids')
            if column_exists(inspector, "group_messages", "reactions"):
                batch_op.drop_column('reactions')
            if column_exists(inspector, "group_messages", "edited_at"):
                batch_op.drop_column('edited_at')
            if column_exists(inspector, "group_messages", "revoked_at"):
                batch_op.drop_column('revoked_at')
            if column_exists(inspector, "group_messages", "is_revoked"):
                batch_op.drop_column('is_revoked')
            if column_exists(inspector, "group_messages", "thread_root_id"):
                batch_op.drop_column('thread_root_id')
