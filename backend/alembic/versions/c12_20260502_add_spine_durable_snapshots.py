"""add spine durable snapshots

Revision ID: c12_20260502
Revises: wp18_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c12_20260502"
down_revision: str | None = "wp18_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "goal_world_graph_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("graph_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("goal_id", sa.String(length=128), nullable=False),
        sa.Column("goal_type", sa.String(length=64), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("last_saved_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goal_world_graph_snapshots_deleted_at"), "goal_world_graph_snapshots", ["deleted_at"])
    op.create_index(op.f("ix_goal_world_graph_snapshots_graph_id"), "goal_world_graph_snapshots", ["graph_id"])
    op.create_index(op.f("ix_goal_world_graph_snapshots_user_id"), "goal_world_graph_snapshots", ["user_id"])
    op.create_index(op.f("ix_goal_world_graph_snapshots_goal_id"), "goal_world_graph_snapshots", ["goal_id"])
    op.create_index(op.f("ix_goal_world_graph_snapshots_goal_type"), "goal_world_graph_snapshots", ["goal_type"])
    op.create_index(op.f("ix_goal_world_graph_snapshots_last_saved_at"), "goal_world_graph_snapshots", ["last_saved_at"])
    op.create_index(
        "idx_goal_world_graph_user_goal",
        "goal_world_graph_snapshots",
        ["user_id", "goal_id"],
        unique=True,
    )
    op.create_index(
        "idx_goal_world_graph_user_type",
        "goal_world_graph_snapshots",
        ["user_id", "goal_type", "last_saved_at"],
    )

    op.create_table(
        "growth_chronicle_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("confirmed_count", sa.Integer(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("last_saved_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_growth_chronicle_snapshots_user_id"),
    )
    op.create_index(op.f("ix_growth_chronicle_snapshots_deleted_at"), "growth_chronicle_snapshots", ["deleted_at"])
    op.create_index(op.f("ix_growth_chronicle_snapshots_user_id"), "growth_chronicle_snapshots", ["user_id"])
    op.create_index(op.f("ix_growth_chronicle_snapshots_last_saved_at"), "growth_chronicle_snapshots", ["last_saved_at"])
    op.create_index(
        "idx_growth_chronicle_user_saved",
        "growth_chronicle_snapshots",
        ["user_id", "last_saved_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_growth_chronicle_user_saved", table_name="growth_chronicle_snapshots")
    op.drop_index(op.f("ix_growth_chronicle_snapshots_last_saved_at"), table_name="growth_chronicle_snapshots")
    op.drop_index(op.f("ix_growth_chronicle_snapshots_user_id"), table_name="growth_chronicle_snapshots")
    op.drop_index(op.f("ix_growth_chronicle_snapshots_deleted_at"), table_name="growth_chronicle_snapshots")
    op.drop_table("growth_chronicle_snapshots")

    op.drop_index("idx_goal_world_graph_user_type", table_name="goal_world_graph_snapshots")
    op.drop_index("idx_goal_world_graph_user_goal", table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_last_saved_at"), table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_goal_type"), table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_goal_id"), table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_user_id"), table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_graph_id"), table_name="goal_world_graph_snapshots")
    op.drop_index(op.f("ix_goal_world_graph_snapshots_deleted_at"), table_name="goal_world_graph_snapshots")
    op.drop_table("goal_world_graph_snapshots")
