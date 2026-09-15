"""add_paused_at_reason_to_tasks

Revision ID: de30c736266b
Revises: c28_20260504
Create Date: 2026-05-03 15:00:48.286509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT paused_at, paused_reason FROM tasks LIMIT 0;"
#   backfill_plan: "n/a — new nullable columns, no existing rows need backfill"
#   owner: "acceptance-fixer"
#   ticket: "ISSUE-20260503-2101-I2"

revision: str = 'de30c736266b'
down_revision: Union[str, None] = 'c28_20260504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("paused_at", sa.DateTime(), nullable=True))
    op.add_column("tasks", sa.Column("paused_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "paused_reason")
    op.drop_column("tasks", "paused_at")
