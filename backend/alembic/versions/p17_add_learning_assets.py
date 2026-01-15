"""p17_add_learning_assets

Revision ID: p17_learning_assets
Revises: merge_template_safe_p15_feedback
Create Date: 2026-01-16 10:00:00.000000

Learning Assets MVP:
- learning_assets table for vocabulary/sentence/concept storage
- asset_suggestion_logs table for suggestion audit trail
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base
from app.utils.migration_helpers import get_inspector, table_exists, index_exists

# revision identifiers, used by Alembic.
revision: str = 'p17_learning_assets'
down_revision: Union[str, None] = 'merge_template_safe_p15_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create learning_assets and asset_suggestion_logs tables"""
    inspector = get_inspector()

    # 1. Create learning_assets table
    if not table_exists(inspector, "learning_assets"):
        op.create_table(
            'learning_assets',
            # Base columns
            sa.Column('id', app.models.base.GUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),

            # Foreign keys
            sa.Column('user_id', app.models.base.GUID(), nullable=False),
            sa.Column('source_file_id', app.models.base.GUID(), nullable=True),

            # Status & Type
            sa.Column('status', sa.String(length=20), nullable=False, server_default='INBOX'),
            sa.Column('asset_kind', sa.String(length=20), nullable=False, server_default='WORD'),

            # Core Content (Relational)
            sa.Column('headword', sa.String(length=255), nullable=False),
            sa.Column('definition', sa.Text(), nullable=True),
            sa.Column('translation', sa.Text(), nullable=True),
            sa.Column('example', sa.Text(), nullable=True),
            sa.Column('language_code', sa.String(length=10), nullable=False, server_default='en'),

            # Inbox Decay
            sa.Column('inbox_expires_at', sa.DateTime(), nullable=True),

            # Snapshot (Immutable)
            sa.Column('snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
            sa.Column('snapshot_schema_version', sa.Integer(), nullable=False, server_default='1'),

            # Provenance (Mutable)
            sa.Column('provenance_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
            sa.Column('provenance_updated_at', sa.DateTime(), nullable=True),

            # Fingerprints
            sa.Column('selection_fp', sa.String(length=64), nullable=True),
            sa.Column('anchor_fp', sa.String(length=64), nullable=True),
            sa.Column('doc_fp', sa.String(length=64), nullable=True),
            sa.Column('norm_version', sa.String(length=20), nullable=False, server_default='v1'),
            sa.Column('match_profile', sa.String(length=50), nullable=True),

            # Review Scheduling
            sa.Column('review_due_at', sa.DateTime(), nullable=True),
            sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('review_success_rate', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('last_seen_at', sa.DateTime(), nullable=True),

            # Statistics
            sa.Column('lookup_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('star_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('ignored_count', sa.Integer(), nullable=False, server_default='0'),

            # Constraints
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_file_id'], ['stored_files.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

    # Create indexes for learning_assets
    if not index_exists(inspector, "learning_assets", "idx_learning_assets_user_status"):
        op.create_index(
            'idx_learning_assets_user_status',
            'learning_assets',
            ['user_id', 'status'],
            unique=False
        )

    if not index_exists(inspector, "learning_assets", "idx_learning_assets_headword"):
        op.create_index(
            'idx_learning_assets_headword',
            'learning_assets',
            ['headword'],
            unique=False
        )

    if not index_exists(inspector, "learning_assets", "idx_learning_assets_user_id"):
        op.create_index(
            'idx_learning_assets_user_id',
            'learning_assets',
            ['user_id'],
            unique=False
        )

    if not index_exists(inspector, "learning_assets", "idx_learning_assets_source_file"):
        op.create_index(
            'idx_learning_assets_source_file',
            'learning_assets',
            ['source_file_id'],
            unique=False
        )

    if not index_exists(inspector, "learning_assets", "idx_learning_assets_selection_fp"):
        op.create_index(
            'idx_learning_assets_selection_fp',
            'learning_assets',
            ['user_id', 'selection_fp'],
            unique=False
        )

    if not index_exists(inspector, "learning_assets", "idx_learning_assets_deleted_at"):
        op.create_index(
            'idx_learning_assets_deleted_at',
            'learning_assets',
            ['deleted_at'],
            unique=False
        )

    # Partial index for inbox expiry scan (PostgreSQL specific)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_assets_inbox_expires
        ON learning_assets (inbox_expires_at)
        WHERE status = 'INBOX'
    """)

    # Partial index for review scheduling
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_assets_review_due
        ON learning_assets (user_id, review_due_at)
        WHERE status = 'ACTIVE' AND review_due_at IS NOT NULL
    """)

    # 2. Create asset_suggestion_logs table
    if not table_exists(inspector, "asset_suggestion_logs"):
        op.create_table(
            'asset_suggestion_logs',
            # Base columns (HardDeleteBaseModel - no deleted_at)
            sa.Column('id', app.models.base.GUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),

            # Context
            sa.Column('user_id', app.models.base.GUID(), nullable=False),
            sa.Column('session_id', sa.String(length=64), nullable=True),
            sa.Column('policy_id', sa.String(length=50), nullable=False),
            sa.Column('trigger_event', sa.String(length=100), nullable=False),

            # Evidence
            sa.Column('evidence_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

            # Decision
            sa.Column('decision', sa.String(length=20), nullable=False),
            sa.Column('decision_reason', sa.String(length=255), nullable=True),

            # User Response
            sa.Column('user_response', sa.String(length=20), nullable=True, server_default='PENDING'),
            sa.Column('response_at', sa.DateTime(), nullable=True),

            # Cooldown
            sa.Column('cooldown_until', sa.DateTime(), nullable=True),

            # Reference
            sa.Column('asset_id', app.models.base.GUID(), nullable=True),

            # Constraints
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['asset_id'], ['learning_assets.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

    # Create indexes for asset_suggestion_logs
    if not index_exists(inspector, "asset_suggestion_logs", "idx_suggestion_log_user_created"):
        op.create_index(
            'idx_suggestion_log_user_created',
            'asset_suggestion_logs',
            ['user_id', 'created_at'],
            unique=False
        )

    if not index_exists(inspector, "asset_suggestion_logs", "idx_suggestion_log_policy"):
        op.create_index(
            'idx_suggestion_log_policy',
            'asset_suggestion_logs',
            ['policy_id'],
            unique=False
        )


def downgrade() -> None:
    """Drop learning_assets and asset_suggestion_logs tables"""

    # Drop asset_suggestion_logs indexes first
    op.drop_index('idx_suggestion_log_policy', table_name='asset_suggestion_logs')
    op.drop_index('idx_suggestion_log_user_created', table_name='asset_suggestion_logs')
    op.drop_table('asset_suggestion_logs')

    # Drop learning_assets partial indexes
    op.execute('DROP INDEX IF EXISTS idx_learning_assets_review_due')
    op.execute('DROP INDEX IF EXISTS idx_learning_assets_inbox_expires')

    # Drop learning_assets indexes
    op.drop_index('idx_learning_assets_deleted_at', table_name='learning_assets')
    op.drop_index('idx_learning_assets_selection_fp', table_name='learning_assets')
    op.drop_index('idx_learning_assets_source_file', table_name='learning_assets')
    op.drop_index('idx_learning_assets_user_id', table_name='learning_assets')
    op.drop_index('idx_learning_assets_headword', table_name='learning_assets')
    op.drop_index('idx_learning_assets_user_status', table_name='learning_assets')

    # Drop learning_assets table
    op.drop_table('learning_assets')
