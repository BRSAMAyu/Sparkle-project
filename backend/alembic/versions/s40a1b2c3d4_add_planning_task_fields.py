"""add planning task guide fields

Revision ID: s40a1b2c3d4
Revises: s39c1d2e3f4
Create Date: 2026-04-24 22:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s40a1b2c3d4"
down_revision: Union[str, None] = "s39c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("tasks", sa.Column("guide_json", _jsonb_type(), nullable=True))
    op.add_column("tasks", sa.Column("ai_prompt", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("source_planning_session_id", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("phase_index", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("success_criteria", sa.Text(), nullable=True))
    op.create_index(
        "ix_tasks_source_planning_session_id",
        "tasks",
        ["source_planning_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_source_planning_session_id", table_name="tasks")
    op.drop_column("tasks", "success_criteria")
    op.drop_column("tasks", "phase_index")
    op.drop_column("tasks", "source_planning_session_id")
    op.drop_column("tasks", "ai_prompt")
    op.drop_column("tasks", "guide_json")
