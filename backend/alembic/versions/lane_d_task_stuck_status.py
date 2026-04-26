"""add stuck task status

Revision ID: lane_d_task_stuck_status
Revises: c18a1b2c3d4, stage_c5_aurora_decision_telemetry
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "lane_d_task_stuck_status"
down_revision: str | tuple[str, str] | None = ("c18a1b2c3d4", "stage_c5_aurora_decision_telemetry")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'STUCK'")


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("UPDATE tasks SET status = 'IN_PROGRESS' WHERE status = 'STUCK'"))
    if bind.dialect.name == "postgresql":
        # PostgreSQL enum labels cannot be dropped safely without rebuilding the type.
        return
