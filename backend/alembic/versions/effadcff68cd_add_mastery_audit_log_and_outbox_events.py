"""add_mastery_audit_log_and_outbox_events

Revision ID: effadcff68cd
Revises: p1_3_error_book_refactor
Create Date: 2026-01-03 13:33:07.803000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision: str = 'effadcff68cd'
down_revision: Union[str, None] = 'p1_3_error_book_refactor'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()
    # Create outbox_events table
    if not table_exists(inspector, "outbox_events"):
        op.create_table('outbox_events',
            sa.Column('id', sa.BigInteger(), nullable=False),
            sa.Column('aggregate_id', sa.UUID(), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "outbox_events", "idx_outbox_status"):
        op.create_index('idx_outbox_status', 'outbox_events', ['status'], unique=False, postgresql_where=sa.text("status = 'pending'"))

    # Create mastery_audit_log table
    if not table_exists(inspector, "mastery_audit_log"):
        op.create_table('mastery_audit_log',
            sa.Column('id', sa.BigInteger(), nullable=False),
            sa.Column('node_id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('old_mastery', sa.Integer(), nullable=False),
            sa.Column('new_mastery', sa.Integer(), nullable=False),
            sa.Column('reason', sa.String(length=50), nullable=False),
            sa.Column('ip_address', postgresql.INET(), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['node_id'], ['knowledge_nodes.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
        )
    if not index_exists(inspector, "mastery_audit_log", "idx_audit_log_node_id"):
        op.create_index('idx_audit_log_node_id', 'mastery_audit_log', ['node_id'], unique=False)
    if not index_exists(inspector, "mastery_audit_log", "idx_audit_log_user_id"):
        op.create_index('idx_audit_log_user_id', 'mastery_audit_log', ['user_id'], unique=False)
    if not index_exists(inspector, "mastery_audit_log", "idx_audit_log_created_at"):
        op.create_index('idx_audit_log_created_at', 'mastery_audit_log', ['created_at'], unique=False)


def downgrade() -> None:
    inspector = get_inspector()
    if table_exists(inspector, "mastery_audit_log"):
        if index_exists(inspector, "mastery_audit_log", "idx_audit_log_created_at"):
            op.drop_index('idx_audit_log_created_at', table_name='mastery_audit_log')
        if index_exists(inspector, "mastery_audit_log", "idx_audit_log_user_id"):
            op.drop_index('idx_audit_log_user_id', table_name='mastery_audit_log')
        if index_exists(inspector, "mastery_audit_log", "idx_audit_log_node_id"):
            op.drop_index('idx_audit_log_node_id', table_name='mastery_audit_log')
        op.drop_table('mastery_audit_log')
    if table_exists(inspector, "outbox_events"):
        if index_exists(inspector, "outbox_events", "idx_outbox_status"):
            op.drop_index('idx_outbox_status', table_name='outbox_events', postgresql_where=sa.text("status = 'pending'"))
        op.drop_table('outbox_events')
