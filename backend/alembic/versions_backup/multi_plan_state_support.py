"""multi plan state support

Add multi-plan fields to plan_states table for parallel plan management.

Revision ID: multi_plan_state_support
Revises: 1b26570b5c19
Create Date: 2026-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'multi_plan_state_support'
down_revision = 'fd2e3f4a5b6c'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_focus column to track currently focused plan
    op.add_column(
        'plan_states',
        sa.Column('is_focus', sa.Boolean(), nullable=False, server_default='FALSE')
    )

    # Add last_focus_time to track when plan was last focused
    op.add_column(
        'plan_states',
        sa.Column('last_focus_time', sa.DateTime(timezone=True), nullable=True)
    )

    # Add parallel_priority for sorting active plans
    op.add_column(
        'plan_states',
        sa.Column('parallel_priority', sa.Integer(), nullable=False, server_default='0')
    )

    # Create composite index for user+focus queries (critical for multi-plan)
    op.create_index(
        'idx_plan_states_user_focus',
        'plan_states',
        ['user_id', 'is_focus']
    )

    # Create index for parallel priority ordering
    op.create_index(
        'idx_plan_states_parallel_priority',
        'plan_states',
        ['parallel_priority']
    )

    # Create composite index for focus time queries
    op.create_index(
        'idx_plan_states_focus_time',
        'plan_states',
        ['last_focus_time']
    )


def downgrade():
    # Drop indexes
    op.drop_index('idx_plan_states_focus_time', table_name='plan_states')
    op.drop_index('idx_plan_states_parallel_priority', table_name='plan_states')
    op.drop_index('idx_plan_states_user_focus', table_name='plan_states')

    # Drop columns
    op.drop_column('plan_states', 'parallel_priority')
    op.drop_column('plan_states', 'last_focus_time')
    op.drop_column('plan_states', 'is_focus')
