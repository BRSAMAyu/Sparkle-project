"""add durable session recovery snapshots

Revision ID: c11_20260502
Revises: c10_20260501
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c11_20260502"
down_revision: str | None = "c10_20260501"
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
        "aurora_core_session_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=True),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("resume_token_hash", sa.String(length=64), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_aurora_core_session_snapshots_session_id"),
        sa.UniqueConstraint("resume_token_hash", name="uq_aurora_core_session_snapshots_resume_token_hash"),
    )
    op.create_index(op.f("ix_aurora_core_session_snapshots_deleted_at"), "aurora_core_session_snapshots", ["deleted_at"])
    op.create_index(op.f("ix_aurora_core_session_snapshots_session_id"), "aurora_core_session_snapshots", ["session_id"])
    op.create_index(op.f("ix_aurora_core_session_snapshots_user_id"), "aurora_core_session_snapshots", ["user_id"])
    op.create_index(
        op.f("ix_aurora_core_session_snapshots_conversation_id"),
        "aurora_core_session_snapshots",
        ["conversation_id"],
    )
    op.create_index(op.f("ix_aurora_core_session_snapshots_surface"), "aurora_core_session_snapshots", ["surface"])
    op.create_index(op.f("ix_aurora_core_session_snapshots_status"), "aurora_core_session_snapshots", ["status"])
    op.create_index(op.f("ix_aurora_core_session_snapshots_stage"), "aurora_core_session_snapshots", ["stage"])
    op.create_index(
        op.f("ix_aurora_core_session_snapshots_resume_token_hash"),
        "aurora_core_session_snapshots",
        ["resume_token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_aurora_core_session_snapshots_last_activity_at"),
        "aurora_core_session_snapshots",
        ["last_activity_at"],
    )
    op.create_index(op.f("ix_aurora_core_session_snapshots_expires_at"), "aurora_core_session_snapshots", ["expires_at"])
    op.create_index(
        "idx_aurora_core_session_user_status",
        "aurora_core_session_snapshots",
        ["user_id", "status", "last_activity_at"],
    )
    op.create_index(
        "idx_aurora_core_session_conversation",
        "aurora_core_session_snapshots",
        ["user_id", "conversation_id", "last_activity_at"],
    )

    op.create_table(
        "durable_session_state_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("fsm_state", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("recoverable", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_durable_session_state_snapshots_session_id"),
    )
    op.create_index(op.f("ix_durable_session_state_snapshots_deleted_at"), "durable_session_state_snapshots", ["deleted_at"])
    op.create_index(op.f("ix_durable_session_state_snapshots_session_id"), "durable_session_state_snapshots", ["session_id"])
    op.create_index(op.f("ix_durable_session_state_snapshots_user_id"), "durable_session_state_snapshots", ["user_id"])
    op.create_index(op.f("ix_durable_session_state_snapshots_request_id"), "durable_session_state_snapshots", ["request_id"])
    op.create_index(op.f("ix_durable_session_state_snapshots_fsm_state"), "durable_session_state_snapshots", ["fsm_state"])
    op.create_index(op.f("ix_durable_session_state_snapshots_recoverable"), "durable_session_state_snapshots", ["recoverable"])
    op.create_index(op.f("ix_durable_session_state_snapshots_last_seen_at"), "durable_session_state_snapshots", ["last_seen_at"])
    op.create_index(op.f("ix_durable_session_state_snapshots_expires_at"), "durable_session_state_snapshots", ["expires_at"])
    op.create_index(
        "idx_durable_session_state_recovery",
        "durable_session_state_snapshots",
        ["session_id", "recoverable", "expires_at"],
    )
    op.create_index(
        "idx_durable_session_state_user_seen",
        "durable_session_state_snapshots",
        ["user_id", "last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_durable_session_state_user_seen", table_name="durable_session_state_snapshots")
    op.drop_index("idx_durable_session_state_recovery", table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_expires_at"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_last_seen_at"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_recoverable"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_fsm_state"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_request_id"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_user_id"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_session_id"), table_name="durable_session_state_snapshots")
    op.drop_index(op.f("ix_durable_session_state_snapshots_deleted_at"), table_name="durable_session_state_snapshots")
    op.drop_table("durable_session_state_snapshots")

    op.drop_index("idx_aurora_core_session_conversation", table_name="aurora_core_session_snapshots")
    op.drop_index("idx_aurora_core_session_user_status", table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_expires_at"), table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_last_activity_at"), table_name="aurora_core_session_snapshots")
    op.drop_index(
        op.f("ix_aurora_core_session_snapshots_resume_token_hash"),
        table_name="aurora_core_session_snapshots",
    )
    op.drop_index(op.f("ix_aurora_core_session_snapshots_stage"), table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_status"), table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_surface"), table_name="aurora_core_session_snapshots")
    op.drop_index(
        op.f("ix_aurora_core_session_snapshots_conversation_id"),
        table_name="aurora_core_session_snapshots",
    )
    op.drop_index(op.f("ix_aurora_core_session_snapshots_user_id"), table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_session_id"), table_name="aurora_core_session_snapshots")
    op.drop_index(op.f("ix_aurora_core_session_snapshots_deleted_at"), table_name="aurora_core_session_snapshots")
    op.drop_table("aurora_core_session_snapshots")
