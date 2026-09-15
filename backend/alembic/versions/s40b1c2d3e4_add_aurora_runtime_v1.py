"""add aurora runtime v1 tables

Revision ID: s40b1c2d3e4
Revises: s40a1b2c3d4
Create Date: 2026-04-24 23:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base


revision: str = "s40b1c2d3e4"
down_revision: Union[str, None] = "s40a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "aurora_state_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=False),
        sa.Column("runtime_session_id", sa.String(length=128), nullable=True),
        sa.Column("snapshot_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("user_model_snapshot", json_type, nullable=False),
        sa.Column("informational_tensions", json_type, nullable=False),
        sa.Column("current_intent", json_type, nullable=True),
        sa.Column("latent_threads", json_type, nullable=False),
        sa.Column("activity_profile", json_type, nullable=False),
        sa.Column("last_decision_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aurora_state_snapshots_user_id", "aurora_state_snapshots", ["user_id"], unique=False)
    op.create_index(
        "idx_aurora_snapshot_scope",
        "aurora_state_snapshots",
        ["user_id", "surface", "conversation_id", "snapshot_at"],
        unique=False,
    )

    op.create_table(
        "aurora_scheduled_wakes",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("wake_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", app.models.base.GUID(), nullable=True),
        sa.Column("runtime_session_id", sa.String(length=128), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("planned_action", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("urgency_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("suppression_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aurora_scheduled_wakes_wake_id", "aurora_scheduled_wakes", ["wake_id"], unique=False)
    op.create_index("ix_aurora_scheduled_wakes_user_id", "aurora_scheduled_wakes", ["user_id"], unique=False)
    op.create_index(
        "idx_aurora_wake_due",
        "aurora_scheduled_wakes",
        ["status", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "idx_aurora_wake_scope",
        "aurora_scheduled_wakes",
        ["user_id", "surface", "conversation_id"],
        unique=False,
    )
    op.create_index("idx_aurora_wake_id", "aurora_scheduled_wakes", ["wake_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_aurora_wake_id", table_name="aurora_scheduled_wakes")
    op.drop_index("idx_aurora_wake_scope", table_name="aurora_scheduled_wakes")
    op.drop_index("idx_aurora_wake_due", table_name="aurora_scheduled_wakes")
    op.drop_index("ix_aurora_scheduled_wakes_user_id", table_name="aurora_scheduled_wakes")
    op.drop_index("ix_aurora_scheduled_wakes_wake_id", table_name="aurora_scheduled_wakes")
    op.drop_table("aurora_scheduled_wakes")

    op.drop_index("idx_aurora_snapshot_scope", table_name="aurora_state_snapshots")
    op.drop_index("ix_aurora_state_snapshots_user_id", table_name="aurora_state_snapshots")
    op.drop_table("aurora_state_snapshots")
