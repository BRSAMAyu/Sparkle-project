"""p15_add_candidate_action_feedback

Revision ID: p15_feedback
Revises: 52addf3b10af
Create Date: 2026-01-15 12:00:00.000000

PR-15: Feedback Loop + Learning
Creates candidate_action_feedback table for tracking user interactions with
predicted actions. Enables daily learning job to calibrate signal thresholds.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

# revision identifiers, used by Alembic.
revision: str = 'p15_feedback'
down_revision: Union[str, None] = '52addf3b10af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create candidate_action_feedback table"""

    # Create candidate_action_feedback table
    op.create_table(
        'candidate_action_feedback',
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('candidate_id', sa.String(length=64), nullable=False),
        sa.Column('action_type', sa.String(length=32), nullable=False),
        sa.Column('feedback_type', sa.String(length=16), nullable=False),
        sa.Column('executed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completion_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    with op.batch_alter_table('candidate_action_feedback', schema=None) as batch_op:
        # Index for user-specific queries
        batch_op.create_index(
            'idx_candidate_feedback_user_type',
            ['user_id', 'action_type'],
            unique=False
        )

        # Index for time-based queries (daily learning job)
        batch_op.create_index(
            'idx_candidate_feedback_created',
            ['created_at'],
            unique=False
        )

        # Index for feedback type analysis
        batch_op.create_index(
            'idx_candidate_feedback_type',
            ['feedback_type'],
            unique=False
        )

        # Index for action type analysis
        batch_op.create_index(
            'idx_candidate_feedback_action',
            ['action_type'],
            unique=False
        )

        # Soft delete index
        batch_op.create_index(
            batch_op.f('ix_candidate_action_feedback_deleted_at'),
            ['deleted_at'],
            unique=False
        )


def downgrade() -> None:
    """Drop candidate_action_feedback table"""

    # Drop all indexes first
    with op.batch_alter_table('candidate_action_feedback', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_candidate_action_feedback_deleted_at'))
        batch_op.drop_index('idx_candidate_feedback_action')
        batch_op.drop_index('idx_candidate_feedback_type')
        batch_op.drop_index('idx_candidate_feedback_created')
        batch_op.drop_index('idx_candidate_feedback_user_type')

    # Drop table
    op.drop_table('candidate_action_feedback')
