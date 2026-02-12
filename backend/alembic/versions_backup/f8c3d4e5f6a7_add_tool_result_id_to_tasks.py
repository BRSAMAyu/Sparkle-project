"""add tool_result_id to tasks

Revision ID: f8c3d4e5f6a7
Revises: f7b2c3d4e5f6
Create Date: 2026-01-21 03:29:00.000000

This migration adds the tool_result_id column to the tasks table,
which is used to track which tool result created this task.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f8c3d4e5f6a7'
down_revision = 'f7b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column exists before adding (for safety)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tasks')]

    if 'tool_result_id' not in columns:
        op.add_column(
            'tasks',
            sa.Column('tool_result_id', sa.String(length=50), nullable=True),
        )
        # Create index for querying tasks by tool result
        op.create_index(
            'ix_tasks_tool_result_id',
            'tasks',
            ['tool_result_id'],
        )


def downgrade() -> None:
    op.drop_index('ix_tasks_tool_result_id', 'tasks')
    op.drop_column('tasks', 'tool_result_id')
