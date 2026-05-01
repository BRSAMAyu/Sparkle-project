"""add aurora decision telemetry table

Revision ID: stage_c5_aurora_decision_telemetry
Revises: stage_c4_intervention_outcomes
Create Date: 2026-04-25 11:30:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base
from alembic import op

revision: str = "stage_c5_aurora_decision_telemetry"
down_revision: str | None = "stage_c4_intervention_outcomes"
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
        "aurora_decision_telemetry",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("wake_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("energy_level", sa.String(length=16), nullable=False, server_default="light"),
        sa.Column("strategy_payload", json_type, nullable=False),
        sa.Column("expression_payload", json_type, nullable=False),
        sa.Column("context_mask", json_type, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("chat_directive_core", json_type, nullable=False),
        sa.Column("standard_layer_contract", json_type, nullable=False),
        sa.Column("strategy_confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("outcome_filled_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_aurora_decision_telemetry_deleted_at"), "aurora_decision_telemetry", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_decision_id"), "aurora_decision_telemetry", ["decision_id"], unique=True)
    op.create_index(op.f("ix_aurora_decision_telemetry_user_id"), "aurora_decision_telemetry", ["user_id"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_surface"), "aurora_decision_telemetry", ["surface"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_conversation_id"), "aurora_decision_telemetry", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_request_id"), "aurora_decision_telemetry", ["request_id"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_decided_at"), "aurora_decision_telemetry", ["decided_at"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_energy_level"), "aurora_decision_telemetry", ["energy_level"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_action"), "aurora_decision_telemetry", ["action"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_outcome"), "aurora_decision_telemetry", ["outcome"], unique=False)
    op.create_index(op.f("ix_aurora_decision_telemetry_outcome_filled_at"), "aurora_decision_telemetry", ["outcome_filled_at"], unique=False)
    op.create_index(
        "idx_aurora_decision_telemetry_scope_ts",
        "aurora_decision_telemetry",
        ["user_id", "conversation_id", "decided_at"],
        unique=False,
    )
    op.create_index(
        "idx_aurora_decision_telemetry_surface_ts",
        "aurora_decision_telemetry",
        ["surface", "decided_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_aurora_decision_telemetry_surface_ts", table_name="aurora_decision_telemetry")
    op.drop_index("idx_aurora_decision_telemetry_scope_ts", table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_outcome_filled_at"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_outcome"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_action"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_energy_level"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_decided_at"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_request_id"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_conversation_id"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_surface"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_user_id"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_decision_id"), table_name="aurora_decision_telemetry")
    op.drop_index(op.f("ix_aurora_decision_telemetry_deleted_at"), table_name="aurora_decision_telemetry")
    op.drop_table("aurora_decision_telemetry")
