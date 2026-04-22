"""extend idempotency keys for stage39 shop dedupe

Revision ID: s39b1c2d3e4
Revises: s39a1b2c3d4
Create Date: 2026-04-23 11:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s39b1c2d3e4"
down_revision: Union[str, None] = "s39a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.alter_column("key", existing_type=sa.String(length=64), type_=sa.String(length=255))
        batch_op.add_column(sa.Column("endpoint", sa.String(length=128), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("response_hash", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.drop_column("response_hash")
        batch_op.drop_column("endpoint")
        batch_op.alter_column("key", existing_type=sa.String(length=255), type_=sa.String(length=64))
