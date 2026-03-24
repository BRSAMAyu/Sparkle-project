"""add_accountability_slot_type

Revision ID: c1f4e7a9b2d6
Revises: b8f1c2d3e4f5
Create Date: 2026-03-21 09:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "c1f4e7a9b2d6"
down_revision: Union[str, None] = "b8f1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    slot_enum = sa.Enum("core", name="accountabilityslottype")
    if bind.dialect.name == "postgresql":
        slot_enum.create(bind, checkfirst=True)

    if inspector.has_table("accountability_partnership") and not _has_column(
        inspector,
        "accountability_partnership",
        "slot_type",
    ):
        with op.batch_alter_table("accountability_partnership", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "slot_type",
                    slot_enum,
                    nullable=False,
                    server_default="core",
                )
            )

    inspector = inspect(bind)
    if inspector.has_table("accountability_partnership") and not _has_index(
        inspector,
        "accountability_partnership",
        "idx_accountability_slot_status",
    ):
        op.create_index(
            "idx_accountability_slot_status",
            "accountability_partnership",
            ["slot_type", "status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("accountability_partnership") and _has_index(
        inspector,
        "accountability_partnership",
        "idx_accountability_slot_status",
    ):
        op.drop_index("idx_accountability_slot_status", table_name="accountability_partnership")

    inspector = inspect(bind)
    if inspector.has_table("accountability_partnership") and _has_column(
        inspector,
        "accountability_partnership",
        "slot_type",
    ):
        with op.batch_alter_table("accountability_partnership", schema=None) as batch_op:
            batch_op.drop_column("slot_type")

    slot_enum = sa.Enum("core", name="accountabilityslottype")
    if bind.dialect.name == "postgresql":
        slot_enum.drop(bind, checkfirst=True)
