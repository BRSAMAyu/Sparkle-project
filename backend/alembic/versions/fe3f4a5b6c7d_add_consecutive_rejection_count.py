"""add_consecutive_rejection_count_to_plan_state

Revision ID: fe3f4a5b6c7d
Revises: fd2e3f4a5b6c
Create Date: 2026-01-24 19:00:00.000000

P0-2: Add consecutive_rejection_count to plan_states table.
Tracks consecutive plan rejections to trigger phase rollback after 2 rejections.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT consecutive_rejection_count FROM plan_states LIMIT 1;"
#   backfill_plan: "n/a - new column with default 0"
#   owner: "sparkle-team"
#   ticket: "p0-rejection-rollback"

revision: str = "fe3f4a5b6c7d"
down_revision: Union[str, None] = "fd2e3f4a5b6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add consecutive_rejection_count column with default 0
    op.add_column(
        "plan_states",
        sa.Column(
            "consecutive_rejection_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    # Drop column
    op.drop_column("plan_states", "consecutive_rejection_count")
