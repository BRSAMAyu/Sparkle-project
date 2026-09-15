"""add stage16 memory write lane fields

Revision ID: f9c16a4b2d3e
Revises: z1a2b3c4d5e6
Create Date: 2026-04-20 12:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c16a4b2d3e"
down_revision: Union[str, None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    episodic_columns = (
        ("source_lane", sa.String(length=40), {"nullable": False, "server_default": "direct_capture"}),
        ("confidence", sa.Float(), {"nullable": True}),
        ("evidence_token", sa.String(length=128), {"nullable": True}),
        ("decay_policy", sa.String(length=32), {"nullable": True}),
        ("semantic_key", sa.String(length=64), {"nullable": True}),
        ("revoked_at", sa.DateTime(), {"nullable": True}),
    )
    for name, type_, kwargs in episodic_columns:
        if not _column_exists(inspector, "episodic_memories", name):
            op.add_column("episodic_memories", sa.Column(name, type_, **kwargs))

    if not _column_exists(inspector, "user_memory_settings", "allow_inferred_episodic"):
        op.add_column(
            "user_memory_settings",
            sa.Column("allow_inferred_episodic", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if not _index_exists(inspector, "episodic_memories", "idx_episodic_memories_source_lane"):
        op.create_index("idx_episodic_memories_source_lane", "episodic_memories", ["user_id", "source_lane"], unique=False)
    if not _index_exists(inspector, "episodic_memories", "idx_episodic_memories_evidence_token"):
        op.create_index("idx_episodic_memories_evidence_token", "episodic_memories", ["user_id", "evidence_token"], unique=False)
    if not _index_exists(inspector, "episodic_memories", "idx_episodic_memories_semantic_key"):
        op.create_index("idx_episodic_memories_semantic_key", "episodic_memories", ["user_id", "semantic_key"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name in (
        "idx_episodic_memories_semantic_key",
        "idx_episodic_memories_evidence_token",
        "idx_episodic_memories_source_lane",
    ):
        if _index_exists(inspector, "episodic_memories", index_name):
            op.drop_index(index_name, table_name="episodic_memories")

    if _column_exists(inspector, "user_memory_settings", "allow_inferred_episodic"):
        op.drop_column("user_memory_settings", "allow_inferred_episodic")

    for column_name in (
        "revoked_at",
        "semantic_key",
        "decay_policy",
        "evidence_token",
        "confidence",
        "source_lane",
    ):
        if _column_exists(inspector, "episodic_memories", column_name):
            op.drop_column("episodic_memories", column_name)
