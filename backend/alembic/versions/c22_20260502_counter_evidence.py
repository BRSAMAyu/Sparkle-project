"""add counter evidence to strategy beliefs

Revision ID: c22_20260502
Revises: c12_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base


revision: str = "c22_20260502"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_default(value: str):
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text(f"'{value}'")
    return sa.text(f"'{value}'::jsonb")


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    json_type = _json_type()

    if not _table_exists(inspector, "strategy_belief_snapshots"):
        op.create_table(
            "strategy_belief_snapshots",
            sa.Column("id", app.models.base.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("strategy_key", sa.String(length=128), nullable=False),
            sa.Column("alpha", sa.Float(), nullable=False, server_default="1"),
            sa.Column("beta", sa.Float(), nullable=False, server_default="1"),
            sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_updated", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("counter_evidence", json_type, nullable=False, server_default=_json_default("[]")),
            sa.Column("metadata", json_type, nullable=False, server_default=_json_default("{}")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "strategy_key", name="uq_strategy_belief_snapshots_user_strategy"),
        )
        op.create_index(
            op.f("ix_strategy_belief_snapshots_deleted_at"),
            "strategy_belief_snapshots",
            ["deleted_at"],
        )
        op.create_index(op.f("ix_strategy_belief_snapshots_user_id"), "strategy_belief_snapshots", ["user_id"])
        op.create_index(
            op.f("ix_strategy_belief_snapshots_strategy_key"),
            "strategy_belief_snapshots",
            ["strategy_key"],
        )
        op.create_index(
            "idx_strategy_belief_user_score_inputs",
            "strategy_belief_snapshots",
            ["user_id", "strategy_key", "evidence_count"],
        )
        return

    if not _column_exists(inspector, "strategy_belief_snapshots", "counter_evidence"):
        op.add_column(
            "strategy_belief_snapshots",
            sa.Column("counter_evidence", json_type, nullable=False, server_default=_json_default("[]")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "strategy_belief_snapshots") and _column_exists(
        inspector,
        "strategy_belief_snapshots",
        "counter_evidence",
    ):
        op.drop_column("strategy_belief_snapshots", "counter_evidence")
