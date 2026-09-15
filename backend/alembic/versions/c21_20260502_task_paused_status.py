"""add paused task status

Revision ID: c21_20260502
Revises: wp18_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c21_20260502"
down_revision: str | None = "wp18_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'PAUSED'")


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("UPDATE tasks SET status = 'IN_PROGRESS' WHERE status = 'PAUSED'"))
    if bind.dialect.name == "postgresql":
        # PostgreSQL enum labels cannot be dropped safely without rebuilding the type.
        return
