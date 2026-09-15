"""add persdyn attractors

Revision ID: s27a1b2c3d4
Revises: s26a1b2c3d4
Create Date: 2026-04-21 20:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s27a1b2c3d4"
down_revision: Union[str, None] = "s26a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "persdyn_attractors"):
        op.create_table(
            "persdyn_attractors",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dim", sa.String(length=40), nullable=False),
            sa.Column("baseline", sa.Float(), nullable=False, server_default="0"),
            sa.Column("variability", sa.Float(), nullable=False, server_default="0"),
            sa.Column("recovery_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "persdyn_attractors", "idx_persdyn_attractors_user_dim"):
        op.create_index(
            "idx_persdyn_attractors_user_dim",
            "persdyn_attractors",
            ["user_id", "dim"],
            unique=True,
        )
    if not _index_exists(inspector, "persdyn_attractors", "idx_persdyn_attractors_user_confidence"):
        op.create_index(
            "idx_persdyn_attractors_user_confidence",
            "persdyn_attractors",
            ["user_id", "confidence"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "persdyn_attractors"):
        for index_name in (
            "idx_persdyn_attractors_user_confidence",
            "idx_persdyn_attractors_user_dim",
        ):
            if _index_exists(inspector, "persdyn_attractors", index_name):
                op.drop_index(index_name, table_name="persdyn_attractors")
        op.drop_table("persdyn_attractors")
