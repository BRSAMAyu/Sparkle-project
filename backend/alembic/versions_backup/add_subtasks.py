"""add subtasks

Revision ID: add_subtasks
Revises: f8c3d4e5f6a7
Create Date: 2024-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_subtasks'
down_revision = 'f8c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Create subtasks table
    op.create_table(
        'subtasks',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('parent_task_id', UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_subtasks_parent_task_id', 'parent_task_id'),
        sa.Index('idx_subtasks_status', 'status'),
        sa.Index('idx_subtasks_order', 'order'),
    )

    # Add columns to tasks table for subtask counters
    op.add_column('tasks', sa.Column('subtasks_total', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('subtasks_completed', sa.Integer(), nullable=False, server_default='0'))

    # Create indexes for the new columns
    op.create_index('idx_tasks_subtasks_total', 'tasks', ['subtasks_total'])
    op.create_index('idx_tasks_subtasks_completed', 'tasks', ['subtasks_completed'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_tasks_subtasks_completed', table_name='tasks')
    op.drop_index('idx_tasks_subtasks_total', table_name='tasks')

    # Drop columns from tasks table
    op.drop_column('tasks', 'subtasks_completed')
    op.drop_column('tasks', 'subtasks_total')

    # Drop subtasks table
    op.drop_table('subtasks')
