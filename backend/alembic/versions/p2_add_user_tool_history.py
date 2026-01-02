"""Add user_tool_history table for tracking tool execution metrics.

Revision ID: p2_add_user_tool_history
Revises: p1_add_post_visibility
Create Date: 2025-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'p2_add_user_tool_history'
down_revision = 'p1_post_visibility'
branch_labels = None
depends_on = None


def upgrade():
    """Create user_tool_history table with indexes for tracking tool execution."""
    # Create table
    op.create_table(
        'user_tool_history',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('context_snapshot', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create indexes for efficient querying
    op.create_index(
        'idx_user_tool_history_user_id',
        'user_tool_history',
        ['user_id']
    )

    op.create_index(
        'idx_user_tool_history_tool_name',
        'user_tool_history',
        ['tool_name']
    )

    op.create_index(
        'idx_user_tool_history_success',
        'user_tool_history',
        ['user_id', 'tool_name', 'success']
    )

    op.create_index(
        'idx_user_tool_history_created_at',
        'user_tool_history',
        ['created_at']
    )

    op.create_index(
        'idx_user_tool_history_user_created',
        'user_tool_history',
        ['user_id', 'created_at']
    )

    # Create composite index for success rate calculation
    op.create_index(
        'idx_user_tool_history_metrics',
        'user_tool_history',
        ['user_id', 'tool_name', 'success', 'created_at']
    )


def downgrade():
    """Drop user_tool_history table and related indexes."""
    op.drop_index('idx_user_tool_history_metrics')
    op.drop_index('idx_user_tool_history_user_created')
    op.drop_index('idx_user_tool_history_created_at')
    op.drop_index('idx_user_tool_history_success')
    op.drop_index('idx_user_tool_history_tool_name')
    op.drop_index('idx_user_tool_history_user_id')
    op.drop_table('user_tool_history')
