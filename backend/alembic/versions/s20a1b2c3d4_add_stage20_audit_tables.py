"""add stage20 audit tables

Revision ID: s20a1b2c3d4
Revises: s18b1c2d3e4f
Create Date: 2026-04-21 18:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "s20a1b2c3d4"
down_revision = "s18b1c2d3e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aurora_judgment_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("task_sufficiency_score", sa.Float(), nullable=False),
        sa.Column("task_missing_dimensions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("context_sufficiency_score", sa.Float(), nullable=False),
        sa.Column("context_missing_dimensions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("judge_version", sa.String(length=16), nullable=False, server_default="v1"),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_aurora_judgment_records_user_computed",
        "aurora_judgment_records",
        ["user_id", "computed_at"],
        unique=False,
    )

    op.create_table(
        "conflict_resolution_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("loser_record_id", sa.String(length=36), nullable=True),
        sa.Column("winner_record_id", sa.String(length=36), nullable=True),
        sa.Column("loser_lane", sa.String(length=40), nullable=True),
        sa.Column("winner_lane", sa.String(length=40), nullable=True),
        sa.Column("resolution_action", sa.String(length=32), nullable=False),
        sa.Column("resolution_reason", sa.String(length=128), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=False),
        sa.Column("conflict_key", sa.String(length=64), nullable=True),
        sa.Column("evidence_tokens", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_conflict_resolution_records_user_resolved",
        "conflict_resolution_records",
        ["user_id", "resolved_at"],
        unique=False,
    )
    op.create_index(
        "idx_conflict_resolution_records_user_conflict_key",
        "conflict_resolution_records",
        ["user_id", "conflict_key"],
        unique=False,
    )

    op.create_table(
        "unresolved_conflicts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conflict_key", sa.String(length=64), nullable=False),
        sa.Column("left_record_id", sa.String(length=36), nullable=True),
        sa.Column("right_record_id", sa.String(length=36), nullable=True),
        sa.Column("left_summary", sa.String(length=2000), nullable=False),
        sa.Column("right_summary", sa.String(length=2000), nullable=False),
        sa.Column("left_lane", sa.String(length=40), nullable=False),
        sa.Column("right_lane", sa.String(length=40), nullable=False),
        sa.Column("left_evidence_token", sa.String(length=128), nullable=True),
        sa.Column("right_evidence_token", sa.String(length=128), nullable=True),
        sa.Column("left_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("right_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_user"),
        sa.Column("surfaced_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_reason", sa.String(length=128), nullable=True),
        sa.Column("selected_side", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_unresolved_conflicts_user_status",
        "unresolved_conflicts",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_unresolved_conflicts_user_conflict_key",
        "unresolved_conflicts",
        ["user_id", "conflict_key"],
        unique=False,
    )

    op.create_table(
        "routing_decision_log",
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("input_aggregator_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("sufficiency_judgment_id", sa.String(length=36), nullable=True),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("decision_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("outcome_signal_id", sa.String(length=128), nullable=True),
        sa.Column("outcome_type", sa.String(length=32), nullable=True),
        sa.Column("outcome_collected_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index(
        "idx_routing_decision_log_user_decided",
        "routing_decision_log",
        ["user_id", "decided_at"],
        unique=False,
    )
    op.create_index(
        "idx_routing_decision_log_user_outcome",
        "routing_decision_log",
        ["user_id", "outcome_collected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_routing_decision_log_user_outcome", table_name="routing_decision_log")
    op.drop_index("idx_routing_decision_log_user_decided", table_name="routing_decision_log")
    op.drop_table("routing_decision_log")
    op.drop_index("idx_unresolved_conflicts_user_conflict_key", table_name="unresolved_conflicts")
    op.drop_index("idx_unresolved_conflicts_user_status", table_name="unresolved_conflicts")
    op.drop_table("unresolved_conflicts")
    op.drop_index("idx_conflict_resolution_records_user_conflict_key", table_name="conflict_resolution_records")
    op.drop_index("idx_conflict_resolution_records_user_resolved", table_name="conflict_resolution_records")
    op.drop_table("conflict_resolution_records")
    op.drop_index("idx_aurora_judgment_records_user_computed", table_name="aurora_judgment_records")
    op.drop_table("aurora_judgment_records")
