"""add disabled notification type preferences

Revision ID: lane_k_disabled_notification_types
Revises: c18a1b2c3d4, stage_c5_aurora_decision_telemetry
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "lane_k_disabled_notification_types"
down_revision: str | tuple[str, str] | None = (
    "c18a1b2c3d4",
    "stage_c5_aurora_decision_telemetry",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_empty_array_default():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("'[]'")
    return sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "disabled_types",
            _json_type(),
            nullable=False,
            server_default=_json_empty_array_default(),
        ),
    )
    op.alter_column("notification_preferences", "disabled_types", server_default=None)


def downgrade() -> None:
    op.drop_column("notification_preferences", "disabled_types")
