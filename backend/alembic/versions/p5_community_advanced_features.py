"""Add advanced community features: E2E encryption, moderation, topics, favorites.

Revision ID: p5_community_advanced_features
Revises: p4_add_message_collab_features
Create Date: 2025-12-29 10:00:00.000000

Features:
- E2E encryption support (encrypted_content, signature, public_key)
- Group moderation (announcements, mute_until, reports, keyword filters)
- Message topics/tags
- Message forwarding & favorites
- Full-text search index
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.base import GUID
from app.utils.migration_helpers import (
    column_exists,
    foreign_key_exists,
    get_inspector,
    index_exists,
    table_exists,
)

revision = 'p5_community_advanced_features'
down_revision = 'p4_add_message_collab_features'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    # ============ 1. User Encryption Keys ============
    if not table_exists(inspector, "user_encryption_keys"):
        op.create_table('user_encryption_keys',
            sa.Column('id', GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('user_id', GUID(), nullable=False),
            sa.Column('public_key', sa.Text(), nullable=False),  # Base64 encoded public key
            sa.Column('key_type', sa.String(50), nullable=False, server_default='x25519'),  # x25519, rsa, etc.
            sa.Column('device_id', sa.String(100), nullable=True),  # Optional device binding
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "user_encryption_keys", "idx_user_encryption_keys_user"):
        op.create_index('idx_user_encryption_keys_user', 'user_encryption_keys', ['user_id', 'is_active'])

    # ============ 2. E2E Encryption Fields for Messages ============
    if table_exists(inspector, "group_messages"):
        with op.batch_alter_table('group_messages') as batch_op:
            if not column_exists(inspector, "group_messages", "encrypted_content"):
                batch_op.add_column(sa.Column('encrypted_content', sa.Text(), nullable=True))
            if not column_exists(inspector, "group_messages", "content_signature"):
                batch_op.add_column(sa.Column('content_signature', sa.String(512), nullable=True))
            if not column_exists(inspector, "group_messages", "encryption_version"):
                batch_op.add_column(sa.Column('encryption_version', sa.Integer(), nullable=True))
            if not column_exists(inspector, "group_messages", "topic"):
                batch_op.add_column(sa.Column('topic', sa.String(100), nullable=True))
            if not column_exists(inspector, "group_messages", "tags"):
                batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))
            if not column_exists(inspector, "group_messages", "forwarded_from_id"):
                batch_op.add_column(sa.Column('forwarded_from_id', GUID(), nullable=True))
            if not column_exists(inspector, "group_messages", "forward_count"):
                batch_op.add_column(sa.Column('forward_count', sa.Integer(), server_default='0', nullable=False))
            if not index_exists(inspector, "group_messages", "idx_message_topic"):
                batch_op.create_index('idx_message_topic', ['group_id', 'topic'])
            if not foreign_key_exists(inspector, "group_messages", "group_messages_forwarded_from_id_fkey"):
                batch_op.create_foreign_key(
                    'group_messages_forwarded_from_id_fkey',
                    'group_messages',
                    ['forwarded_from_id'],
                    ['id']
                )

    if table_exists(inspector, "private_messages"):
        with op.batch_alter_table('private_messages') as batch_op:
            if not column_exists(inspector, "private_messages", "encrypted_content"):
                batch_op.add_column(sa.Column('encrypted_content', sa.Text(), nullable=True))
            if not column_exists(inspector, "private_messages", "content_signature"):
                batch_op.add_column(sa.Column('content_signature', sa.String(512), nullable=True))
            if not column_exists(inspector, "private_messages", "encryption_version"):
                batch_op.add_column(sa.Column('encryption_version', sa.Integer(), nullable=True))
            if not column_exists(inspector, "private_messages", "topic"):
                batch_op.add_column(sa.Column('topic', sa.String(100), nullable=True))
            if not column_exists(inspector, "private_messages", "tags"):
                batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))
            if not column_exists(inspector, "private_messages", "forwarded_from_id"):
                batch_op.add_column(sa.Column('forwarded_from_id', GUID(), nullable=True))
            if not column_exists(inspector, "private_messages", "forward_count"):
                batch_op.add_column(sa.Column('forward_count', sa.Integer(), server_default='0', nullable=False))
            if not foreign_key_exists(inspector, "private_messages", "private_messages_forwarded_from_id_fkey"):
                batch_op.create_foreign_key(
                    'private_messages_forwarded_from_id_fkey',
                    'private_messages',
                    ['forwarded_from_id'],
                    ['id']
                )

    # ============ 3. Group Moderation Features ============
    if table_exists(inspector, "groups"):
        with op.batch_alter_table('groups') as batch_op:
            if not column_exists(inspector, "groups", "announcement"):
                batch_op.add_column(sa.Column('announcement', sa.Text(), nullable=True))
            if not column_exists(inspector, "groups", "announcement_updated_at"):
                batch_op.add_column(sa.Column('announcement_updated_at', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "groups", "keyword_filters"):
                batch_op.add_column(sa.Column('keyword_filters', sa.JSON(), nullable=True))  # ["敏感词1", "敏感词2"]
            if not column_exists(inspector, "groups", "mute_all"):
                batch_op.add_column(sa.Column('mute_all', sa.Boolean(), server_default=sa.text('false'), nullable=False))
            if not column_exists(inspector, "groups", "slow_mode_seconds"):
                batch_op.add_column(sa.Column('slow_mode_seconds', sa.Integer(), server_default='0', nullable=False))

    if table_exists(inspector, "group_members"):
        with op.batch_alter_table('group_members') as batch_op:
            if not column_exists(inspector, "group_members", "mute_until"):
                batch_op.add_column(sa.Column('mute_until', sa.DateTime(), nullable=True))
            if not column_exists(inspector, "group_members", "warn_count"):
                batch_op.add_column(sa.Column('warn_count', sa.Integer(), server_default='0', nullable=False))

    # ============ 4. Message Reports ============
    if not table_exists(inspector, "message_reports"):
        op.create_table('message_reports',
        sa.Column('id', GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('reporter_id', GUID(), nullable=False),
        sa.Column('group_message_id', GUID(), nullable=True),
        sa.Column('private_message_id', GUID(), nullable=True),
        sa.Column('reason', sa.String(50), nullable=False),  # spam, harassment, violence, etc.
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),  # pending, reviewed, dismissed, actioned
        sa.Column('reviewed_by', GUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('action_taken', sa.String(50), nullable=True),  # warn, mute, kick, ban
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_message_id'], ['group_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['private_message_id'], ['private_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "message_reports", "idx_message_reports_status"):
        op.create_index('idx_message_reports_status', 'message_reports', ['status'])
    if not index_exists(inspector, "message_reports", "idx_message_reports_group_msg"):
        op.create_index('idx_message_reports_group_msg', 'message_reports', ['group_message_id'])

    # ============ 5. Message Favorites ============
    if not table_exists(inspector, "message_favorites"):
        op.create_table('message_favorites',
        sa.Column('id', GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('group_message_id', GUID(), nullable=True),
        sa.Column('private_message_id', GUID(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),  # User's personal note
        sa.Column('tags', sa.JSON(), nullable=True),  # User's custom tags
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_message_id'], ['group_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['private_message_id'], ['private_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "message_favorites", "idx_message_favorites_user"):
        op.create_index('idx_message_favorites_user', 'message_favorites', ['user_id'])

    # ============ 6. Cross-Group Broadcast ============
    if not table_exists(inspector, "broadcast_messages"):
        op.create_table('broadcast_messages',
        sa.Column('id', GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('sender_id', GUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_data', sa.JSON(), nullable=True),
        sa.Column('target_group_ids', sa.JSON(), nullable=False),  # List of group IDs
        sa.Column('delivered_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )

    # ============ 7. Offline Message Queue ============
    if not table_exists(inspector, "offline_message_queue"):
        op.create_table('offline_message_queue',
        sa.Column('id', GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('client_nonce', sa.String(100), nullable=False),  # For deduplication
        sa.Column('message_type', sa.String(50), nullable=False),  # group, private
        sa.Column('target_id', GUID(), nullable=False),  # group_id or receiver_id
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),  # pending, sent, failed, expired
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_retry_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "offline_message_queue", "idx_offline_queue_user_status"):
        op.create_index('idx_offline_queue_user_status', 'offline_message_queue', ['user_id', 'status'])
    if not index_exists(inspector, "offline_message_queue", "idx_offline_queue_nonce"):
        op.create_index('idx_offline_queue_nonce', 'offline_message_queue', ['user_id', 'client_nonce'], unique=True)

    # ============ 8. Full-Text Search Index ============
    # Create GIN index for full-text search on message content
    if table_exists(inspector, "group_messages"):
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_content_fts
            ON group_messages
            USING GIN (to_tsvector('simple', COALESCE(content, '')))
            WHERE is_revoked = false
        """)

    if table_exists(inspector, "private_messages"):
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_private_messages_content_fts
            ON private_messages
            USING GIN (to_tsvector('simple', COALESCE(content, '')))
            WHERE is_revoked = false
        """)


def downgrade():
    inspector = get_inspector()
    # Drop FTS indexes
    op.execute("DROP INDEX IF EXISTS idx_private_messages_content_fts")
    op.execute("DROP INDEX IF EXISTS idx_group_messages_content_fts")

    # Drop tables
    if table_exists(inspector, "offline_message_queue"):
        op.drop_table('offline_message_queue')
    if table_exists(inspector, "broadcast_messages"):
        op.drop_table('broadcast_messages')
    if table_exists(inspector, "message_favorites"):
        op.drop_table('message_favorites')
    if table_exists(inspector, "message_reports"):
        op.drop_table('message_reports')

    # Remove group moderation fields
    if table_exists(inspector, "group_members"):
        with op.batch_alter_table('group_members') as batch_op:
            if column_exists(inspector, "group_members", "warn_count"):
                batch_op.drop_column('warn_count')
            if column_exists(inspector, "group_members", "mute_until"):
                batch_op.drop_column('mute_until')

    if table_exists(inspector, "groups"):
        with op.batch_alter_table('groups') as batch_op:
            if column_exists(inspector, "groups", "slow_mode_seconds"):
                batch_op.drop_column('slow_mode_seconds')
            if column_exists(inspector, "groups", "mute_all"):
                batch_op.drop_column('mute_all')
            if column_exists(inspector, "groups", "keyword_filters"):
                batch_op.drop_column('keyword_filters')
            if column_exists(inspector, "groups", "announcement_updated_at"):
                batch_op.drop_column('announcement_updated_at')
            if column_exists(inspector, "groups", "announcement"):
                batch_op.drop_column('announcement')

    # Remove E2E and topic fields from messages
    if table_exists(inspector, "private_messages"):
        with op.batch_alter_table('private_messages') as batch_op:
            if foreign_key_exists(inspector, "private_messages", "private_messages_forwarded_from_id_fkey"):
                batch_op.drop_constraint('private_messages_forwarded_from_id_fkey', type_='foreignkey')
            if column_exists(inspector, "private_messages", "forward_count"):
                batch_op.drop_column('forward_count')
            if column_exists(inspector, "private_messages", "forwarded_from_id"):
                batch_op.drop_column('forwarded_from_id')
            if column_exists(inspector, "private_messages", "tags"):
                batch_op.drop_column('tags')
            if column_exists(inspector, "private_messages", "topic"):
                batch_op.drop_column('topic')
            if column_exists(inspector, "private_messages", "encryption_version"):
                batch_op.drop_column('encryption_version')
            if column_exists(inspector, "private_messages", "content_signature"):
                batch_op.drop_column('content_signature')
            if column_exists(inspector, "private_messages", "encrypted_content"):
                batch_op.drop_column('encrypted_content')

    if table_exists(inspector, "group_messages"):
        with op.batch_alter_table('group_messages') as batch_op:
            if foreign_key_exists(inspector, "group_messages", "group_messages_forwarded_from_id_fkey"):
                batch_op.drop_constraint('group_messages_forwarded_from_id_fkey', type_='foreignkey')
            if index_exists(inspector, "group_messages", "idx_message_topic"):
                batch_op.drop_index('idx_message_topic')
            if column_exists(inspector, "group_messages", "forward_count"):
                batch_op.drop_column('forward_count')
            if column_exists(inspector, "group_messages", "forwarded_from_id"):
                batch_op.drop_column('forwarded_from_id')
            if column_exists(inspector, "group_messages", "tags"):
                batch_op.drop_column('tags')
            if column_exists(inspector, "group_messages", "topic"):
                batch_op.drop_column('topic')
            if column_exists(inspector, "group_messages", "encryption_version"):
                batch_op.drop_column('encryption_version')
            if column_exists(inspector, "group_messages", "content_signature"):
                batch_op.drop_column('content_signature')
            if column_exists(inspector, "group_messages", "encrypted_content"):
                batch_op.drop_column('encrypted_content')

    # Drop encryption keys table
    if table_exists(inspector, "user_encryption_keys"):
        if index_exists(inspector, "user_encryption_keys", "idx_user_encryption_keys_user"):
            op.drop_index('idx_user_encryption_keys_user', table_name='user_encryption_keys')
        op.drop_table('user_encryption_keys')
