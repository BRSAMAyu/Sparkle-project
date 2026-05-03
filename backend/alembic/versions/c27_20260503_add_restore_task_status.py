"""add restore task status

Revision ID: c27_20260503
Revises: c26_20260502
Create Date: 2026-05-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c27_20260503"
down_revision: str | None = "c26_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'RESTORE'")


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("UPDATE tasks SET status = 'IN_PROGRESS' WHERE status = 'RESTORE'"))
    if bind.dialect.name == "postgresql":
        # PostgreSQL enum labels cannot be dropped safely without rebuilding the type.
        return
