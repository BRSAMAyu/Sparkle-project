"""add_task_reminder_settings

Revision ID: 1228e59a6a83
Revises: p24_add_equipped_fields
Create Date: 2026-01-28 12:14:26.286570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible|forward_only|destructive
#   rollback_plan: "alembic downgrade -1" | "forward_fix_only"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = '1228e59a6a83'
down_revision: Union[str, None] = 'p24_add_equipped_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add task_reminders_enabled column
    op.add_column('user_settings', sa.Column('task_reminders_enabled', sa.Boolean(), nullable=False, server_default='true'))

    # Add task_reminder_times column (JSON field for storing list of reminder times in minutes)
    op.add_column('user_settings', sa.Column('task_reminder_times', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove task_reminder_times column
    op.drop_column('user_settings', 'task_reminder_times')

    # Remove task_reminders_enabled column
    op.drop_column('user_settings', 'task_reminders_enabled')
