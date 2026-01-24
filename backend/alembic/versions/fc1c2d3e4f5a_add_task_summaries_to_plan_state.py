"""add_task_summaries_to_plan_state

Revision ID: fc1c2d3e4f5a
Revises: fb1c2d3e4f5a
Create Date: 2026-01-24 17:00:00.000000

Add task_summaries JSONB column to plan_states table.
Stores recent task summaries for quick plan context lookup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT task_summaries FROM plan_states LIMIT 1;"
#   backfill_plan: "n/a - new column with default"
#   owner: "sparkle-team"
#   ticket: "plan-scope-wiring"

revision: str = "fc1c2d3e4f5a"
down_revision: Union[str, None] = "fb1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add task_summaries column with default empty array
    op.add_column(
        "plan_states",
        sa.Column(
            "task_summaries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    # Create GIN index for efficient JSONB queries
    op.create_index(
        "ix_plan_states_task_summaries",
        "plan_states",
        ["task_summaries"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_plan_states_task_summaries", "plan_states")

    # Drop column
    op.drop_column("plan_states", "task_summaries")
