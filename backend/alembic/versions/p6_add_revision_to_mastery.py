"""add_revision_to_mastery

Revision ID: p6_add_revision_to_mastery
Revises: p5_community_advanced_features
Create Date: 2026-01-03 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, index_exists, table_exists
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p6_add_revision_to_mastery'
down_revision: Union[str, None] = 'p5_community_advanced_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()
    # Add revision to user_node_status
    if table_exists(inspector, "user_node_status") and not column_exists(inspector, "user_node_status", "revision"):
        op.add_column('user_node_status', sa.Column('revision', sa.BigInteger(), server_default='0', nullable=False))
    
    # Add revision and request_id to mastery_audit_log
    if table_exists(inspector, "mastery_audit_log"):
        if not column_exists(inspector, "mastery_audit_log", "revision"):
            op.add_column('mastery_audit_log', sa.Column('revision', sa.BigInteger(), server_default='0', nullable=False))
        if not column_exists(inspector, "mastery_audit_log", "request_id"):
            op.add_column('mastery_audit_log', sa.Column('request_id', sa.String(length=100), nullable=True))
        if not index_exists(inspector, "mastery_audit_log", "idx_audit_log_request_id"):
            op.create_index('idx_audit_log_request_id', 'mastery_audit_log', ['request_id'], unique=False)


def downgrade() -> None:
    inspector = get_inspector()
    if table_exists(inspector, "mastery_audit_log"):
        if index_exists(inspector, "mastery_audit_log", "idx_audit_log_request_id"):
            op.drop_index('idx_audit_log_request_id', table_name='mastery_audit_log')
        if column_exists(inspector, "mastery_audit_log", "request_id"):
            op.drop_column('mastery_audit_log', 'request_id')
        if column_exists(inspector, "mastery_audit_log", "revision"):
            op.drop_column('mastery_audit_log', 'revision')
    if table_exists(inspector, "user_node_status") and column_exists(inspector, "user_node_status", "revision"):
        op.drop_column('user_node_status', 'revision')
