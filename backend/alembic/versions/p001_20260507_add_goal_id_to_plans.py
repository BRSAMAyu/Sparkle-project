"""add goal_id column to plans table

Revision ID: p001_20260507
Revises: 7f807dcd4e5f
Create Date: 2026-05-07 14:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p001_20260507"
down_revision: str | None = "7f807dcd4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("goal_id", postgresql.UUID(), nullable=True))
    op.create_index("idx_plans_goal_id", "plans", ["goal_id"])
    op.create_foreign_key(
        "fk_plans_goal_id_goals",
        "plans",
        "goals",
        ["goal_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_plans_goal_id_goals", "plans", type_="foreignkey")
    op.drop_index("idx_plans_goal_id", table_name="plans")
    op.drop_column("plans", "goal_id")
