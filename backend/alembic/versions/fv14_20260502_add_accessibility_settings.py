"""add accessibility settings to user settings

Revision ID: fv14_20260502
Revises: c14_20260502
Create Date: 2026-05-02 14:40:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fv14_20260502"
down_revision: str | None = "c14_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_default():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("'{}'")
    return sa.text("'{}'::jsonb")


def upgrade() -> None:
    if not _has_column("user_settings", "accessibility_settings"):
        op.add_column(
            "user_settings",
            sa.Column(
                "accessibility_settings",
                _json_type(),
                nullable=False,
                server_default=_json_default(),
            ),
        )


def downgrade() -> None:
    if _has_column("user_settings", "accessibility_settings"):
        op.drop_column("user_settings", "accessibility_settings")
