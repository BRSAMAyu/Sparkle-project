"""add error record galaxy echo fields

Revision ID: c18a1b2c3d4
Revises: c17a1b2c3d4
Create Date: 2026-04-25 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

import app.models.base
from alembic import op

revision: str = "c18a1b2c3d4"
down_revision: str | None = "c17a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("error_records", sa.Column("affected_node_id", app.models.base.GUID(), nullable=True))
    op.add_column("error_records", sa.Column("mastery_delta", sa.Float(), nullable=True))
    op.create_index("idx_error_records_affected_node", "error_records", ["affected_node_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_error_records_affected_node", table_name="error_records")
    op.drop_column("error_records", "mastery_delta")
    op.drop_column("error_records", "affected_node_id")
