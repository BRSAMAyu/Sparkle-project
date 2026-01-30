"""add confirmed_at to tasks

Revision ID: f7b2c3d4e5f6
Revises: f6a1b2c3d4e5
Create Date: 2026-01-21 03:24:00.000000

This migration adds the confirmed_at column to the tasks table,
which is used to track when a task was confirmed by the user.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f7b2c3d4e5f6'
down_revision = 'b1c2d3e4f5a6'  # Merge with the other head branch
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column exists before adding (for safety)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tasks')]

    if 'confirmed_at' not in columns:
        op.add_column(
            'tasks',
            sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        )
        # Create index for querying confirmed tasks efficiently
        op.create_index(
            'ix_tasks_confirmed_at',
            'tasks',
            ['confirmed_at'],
        )


def downgrade() -> None:
    op.drop_index('ix_tasks_confirmed_at', 'tasks')
    op.drop_column('tasks', 'confirmed_at')
