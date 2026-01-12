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

revision = 'p5_community_advanced_features'
down_revision = 'p4_add_message_collab_features'
branch_labels = None
depends_on = None


def upgrade():
    # ============ 1. User Encryption Keys ============
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
    op.create_index('idx_user_encryption_keys_user', 'user_encryption_keys', ['user_id', 'is_active'])

    # ============ 2. E2E Encryption Fields for Messages ============
    with op.batch_alter_table('group_messages') as batch_op:
        batch_op.add_column(sa.Column('encrypted_content', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('content_signature', sa.String(512), nullable=True))
        batch_op.add_column(sa.Column('encryption_version', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('topic', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('forwarded_from_id', GUID(), nullable=True))
        batch_op.add_column(sa.Column('forward_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.create_index('idx_message_topic', ['group_id', 'topic'])
        batch_op.create_foreign_key(
            'group_messages_forwarded_from_id_fkey',
            'group_messages',
            ['forwarded_from_id'],
            ['id']
        )

    with op.batch_alter_table('private_messages') as batch_op:
        batch_op.add_column(sa.Column('encrypted_content', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('content_signature', sa.String(512), nullable=True))
        batch_op.add_column(sa.Column('encryption_version', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('topic', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('forwarded_from_id', GUID(), nullable=True))
        batch_op.add_column(sa.Column('forward_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.create_foreign_key(
            'private_messages_forwarded_from_id_fkey',
            'private_messages',
            ['forwarded_from_id'],
            ['id']
        )

    # ============ 3. Group Moderation Features ============
    with op.batch_alter_table('groups') as batch_op:
        batch_op.add_column(sa.Column('announcement', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('announcement_updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('keyword_filters', sa.JSON(), nullable=True))  # ["敏感词1", "敏感词2"]
        batch_op.add_column(sa.Column('mute_all', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('slow_mode_seconds', sa.Integer(), server_default='0', nullable=False))

    with op.batch_alter_table('group_members') as batch_op:
        batch_op.add_column(sa.Column('mute_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('warn_count', sa.Integer(), server_default='0', nullable=False))

    # ============ 4. Message Reports ============
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
    op.create_index('idx_message_reports_status', 'message_reports', ['status'])
    op.create_index('idx_message_reports_group_msg', 'message_reports', ['group_message_id'])

    # ============ 5. Message Favorites ============
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
    op.create_index('idx_message_favorites_user', 'message_favorites', ['user_id'])

    # ============ 6. Cross-Group Broadcast ============
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
    op.create_index('idx_offline_queue_user_status', 'offline_message_queue', ['user_id', 'status'])
    op.create_index('idx_offline_queue_nonce', 'offline_message_queue', ['user_id', 'client_nonce'], unique=True)

    # ============ 8. Full-Text Search Index ============
    # Create GIN index for full-text search on message content
    op.execute("""
        CREATE INDEX idx_group_messages_content_fts
        ON group_messages
        USING GIN (to_tsvector('simple', COALESCE(content, '')))
        WHERE is_revoked = false
    """)

    op.execute("""
        CREATE INDEX idx_private_messages_content_fts
        ON private_messages
        USING GIN (to_tsvector('simple', COALESCE(content, '')))
        WHERE is_revoked = false
    """)


def downgrade():
    # Drop FTS indexes
    op.execute("DROP INDEX IF EXISTS idx_private_messages_content_fts")
    op.execute("DROP INDEX IF EXISTS idx_group_messages_content_fts")

    # Drop tables
    op.drop_table('offline_message_queue')
    op.drop_table('broadcast_messages')
    op.drop_table('message_favorites')
    op.drop_table('message_reports')

    # Remove group moderation fields
    with op.batch_alter_table('group_members') as batch_op:
        batch_op.drop_column('warn_count')
        batch_op.drop_column('mute_until')

    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_column('slow_mode_seconds')
        batch_op.drop_column('mute_all')
        batch_op.drop_column('keyword_filters')
        batch_op.drop_column('announcement_updated_at')
        batch_op.drop_column('announcement')

    # Remove E2E and topic fields from messages
    with op.batch_alter_table('private_messages') as batch_op:
        batch_op.drop_constraint('private_messages_forwarded_from_id_fkey', type_='foreignkey')
        batch_op.drop_column('forward_count')
        batch_op.drop_column('forwarded_from_id')
        batch_op.drop_column('tags')
        batch_op.drop_column('topic')
        batch_op.drop_column('encryption_version')
        batch_op.drop_column('content_signature')
        batch_op.drop_column('encrypted_content')

    with op.batch_alter_table('group_messages') as batch_op:
        batch_op.drop_constraint('group_messages_forwarded_from_id_fkey', type_='foreignkey')
        batch_op.drop_index('idx_message_topic')
        batch_op.drop_column('forward_count')
        batch_op.drop_column('forwarded_from_id')
        batch_op.drop_column('tags')
        batch_op.drop_column('topic')
        batch_op.drop_column('encryption_version')
        batch_op.drop_column('content_signature')
        batch_op.drop_column('encrypted_content')

    # Drop encryption keys table
    op.drop_table('user_encryption_keys')
