"""add achievement context snapshot

Revision ID: c17a1b2c3d4
Revises: stage_c4_intervention_outcomes
Create Date: 2026-04-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c17a1b2c3d4"
down_revision: str | None = "stage_c4_intervention_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    op.add_column(
        "user_achievements",
        sa.Column("context_snapshot", _json_type(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_achievements", "context_snapshot")
