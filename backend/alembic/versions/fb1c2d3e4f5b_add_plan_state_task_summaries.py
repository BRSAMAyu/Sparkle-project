"""add_plan_state_task_summaries

Revision ID: fb1c2d3e4f5b
Revises: fb1c2d3e4f5a
Create Date: 2026-01-24 18:00:00.000000

Adds lightweight task summaries cache to plan_states.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT task_summaries FROM plan_states LIMIT 1;"
#   backfill_plan: "initialize as empty array"
#   owner: "sparkle-team"
#   ticket: "plan-state-layer"

revision: str = "fb1c2d3e4f5b"
down_revision: Union[str, None] = "fb1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "plan_states",
        sa.Column(
            "task_summaries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("plan_states", "task_summaries")
