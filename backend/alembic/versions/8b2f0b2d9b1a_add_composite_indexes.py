"""add_composite_indexes

Revision ID: 8b2f0b2d9b1a
Revises: e7e90c21943d
Create Date: 2026-02-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1"
#   backfill_plan: "n/a"
#   owner: "team-sparkle"
#   ticket: "PERF-P2-INDEX"

# revision identifiers, used by Alembic.
revision: str = '8b2f0b2d9b1a'
down_revision: Union[str, None] = 'e7e90c21943d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_chat_user_session_created_at '
        'ON chat_messages (user_id, session_id, created_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_tasks_user_status_created_at '
        'ON tasks (user_id, status, created_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_tasks_user_created_at '
        'ON tasks (user_id, created_at)'
    )


def downgrade() -> None:
    op.drop_index('idx_tasks_user_created_at', table_name='tasks')
    op.drop_index('idx_tasks_user_status_created_at', table_name='tasks')
    op.drop_index('idx_chat_user_session_created_at', table_name='chat_messages')
