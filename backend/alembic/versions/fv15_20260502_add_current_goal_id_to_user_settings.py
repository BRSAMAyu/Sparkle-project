"""add current goal selection to user settings

Revision ID: fv15_20260502
Revises: wp18_20260502
Create Date: 2026-05-02 14:25:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "fv15_20260502"
down_revision: str | None = "wp18_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if not _has_column("user_settings", "current_goal_id"):
        op.add_column(
            "user_settings",
            sa.Column("current_goal_id", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    if _has_column("user_settings", "current_goal_id"):
        op.drop_column("user_settings", "current_goal_id")
