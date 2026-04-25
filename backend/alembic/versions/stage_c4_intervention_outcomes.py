"""create intervention outcomes table

Revision ID: stage_c4_intervention_outcomes
Revises: s40b1c2d3e4
Create Date: 2026-04-25 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

import app.models.base
from alembic import op

revision: str = "stage_c4_intervention_outcomes"
down_revision: str | None = "s40b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intervention_outcomes",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("plan_id", app.models.base.GUID(), nullable=True),
        sa.Column("task_id", app.models.base.GUID(), nullable=True),
        sa.Column("intervention_type", sa.String(length=64), nullable=True),
        sa.Column("trigger_reason", sa.String(length=128), nullable=True),
        sa.Column("target_concept", sa.String(length=256), nullable=True),
        sa.Column("target_node_id", app.models.base.GUID(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_checked_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_status", sa.String(length=32), nullable=True),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("effective", sa.Boolean(), nullable=True),
        sa.Column("user_adopted", sa.Boolean(), nullable=True),
        sa.Column("adopted_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_intervention_outcomes_deleted_at"), "intervention_outcomes", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_intervention_outcomes_user_id"), "intervention_outcomes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_intervention_outcomes_user_id"), table_name="intervention_outcomes")
    op.drop_index(op.f("ix_intervention_outcomes_deleted_at"), table_name="intervention_outcomes")
    op.drop_table("intervention_outcomes")
