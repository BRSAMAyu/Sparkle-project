"""add card protocol tables (cards, card_edges, task_occurrences, planning_artifacts, intervention_records)

Revision ID: cp001a2b3c4d5
Revises: oc005a6b7c8d9
Create Date: 2026-04-02 22:00:00.000000

Card Protocol Phase 1: Core data layer.
Tables: cards, card_edges, task_occurrences, planning_artifacts, intervention_records
CardSnapshots deferred to Phase 5 (sharing/adoption).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "cp001a2b3c4d5"
down_revision = "oc005a6b7c8d9"
branch_labels = None
depends_on = None


def _jsonb():
    """Return JSONB on PostgreSQL, JSON on SQLite."""
    if op.get_bind().dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    jsonb = _jsonb()
    uuid_type = postgresql.UUID(as_uuid=True)
    if op.get_bind().dialect.name == "sqlite":
        uuid_type = sa.String(36)

    # ------------------------------------------------------------------
    # 1. cards — canonical semantic entity
    # ------------------------------------------------------------------
    op.create_table(
        "cards",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("card_type", sa.String(32), nullable=False),
        sa.Column("owner_id", uuid_type, nullable=False),
        sa.Column("holder_id", uuid_type, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("schema_version", sa.String(16), nullable=False, server_default="'3.0'"),
        sa.Column("lifecycle_status", sa.String(24), nullable=False, server_default="'DRAFT'"),
        sa.Column("visibility", sa.String(24), nullable=False, server_default="'PRIVATE'"),
        sa.Column("tags", jsonb, nullable=False, server_default="'[]'"),
        sa.Column("metadata", jsonb, nullable=False, server_default="'{}'"),
        sa.Column("source_type", sa.String(24), nullable=False, server_default="'ORIGINAL'"),
        sa.Column("origin_card_id", uuid_type, nullable=True),
        sa.Column("origin_snapshot_id", uuid_type, nullable=True),
        sa.Column("created_by", sa.String(16), nullable=False, server_default="'AI'"),
        sa.Column("updated_by", sa.String(16), nullable=False, server_default="'AI'"),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holder_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_card_id"], ["cards.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_cards_deleted_at", "cards", ["deleted_at"], unique=False)
    op.create_index("ix_cards_card_type", "cards", ["card_type"], unique=False)
    op.create_index("ix_cards_owner_id", "cards", ["owner_id"], unique=False)
    op.create_index("ix_cards_holder_id", "cards", ["holder_id"], unique=False)
    op.create_index("ix_cards_lifecycle_status", "cards", ["lifecycle_status"], unique=False)
    op.create_index("ix_cards_owner_type", "cards", ["owner_id", "card_type"], unique=False)
    op.create_index("ix_cards_holder_status", "cards", ["holder_id", "lifecycle_status"], unique=False)
    op.create_index("ix_cards_type_status", "cards", ["card_type", "lifecycle_status"], unique=False)

    # ------------------------------------------------------------------
    # 2. card_edges — graph relationships (card-to-card only)
    # ------------------------------------------------------------------
    op.create_table(
        "card_edges",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("from_card_id", uuid_type, nullable=False),
        sa.Column("to_card_id", uuid_type, nullable=False),
        sa.Column("edge_type", sa.String(32), nullable=False),
        sa.Column("binding_mode", sa.String(24), nullable=False, server_default="'OWNED'"),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("temporal_window", jsonb, nullable=True),
        sa.Column("metadata", jsonb, nullable=False, server_default="'{}'"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["from_card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("from_card_id", "to_card_id", "edge_type", name="uq_card_edge_unique"),
    )
    op.create_index("ix_card_edges_deleted_at", "card_edges", ["deleted_at"], unique=False)
    op.create_index("ix_card_edges_from_card_id", "card_edges", ["from_card_id"], unique=False)
    op.create_index("ix_card_edges_to_card_id", "card_edges", ["to_card_id"], unique=False)
    op.create_index("ix_card_edges_edge_type", "card_edges", ["edge_type"], unique=False)
    op.create_index("ix_card_edges_active", "card_edges", ["active"], unique=False)
    op.create_index("ix_card_edges_from_type", "card_edges", ["from_card_id", "edge_type"], unique=False)
    op.create_index("ix_card_edges_to_type", "card_edges", ["to_card_id", "edge_type"], unique=False)
    op.create_index("ix_card_edges_active_type", "card_edges", ["active", "edge_type"], unique=False)

    # ------------------------------------------------------------------
    # 3. task_occurrences — execution instances (NOT cards, NOT in card_edges)
    # ------------------------------------------------------------------
    op.create_table(
        "task_occurrences",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("series_card_id", uuid_type, nullable=False),
        sa.Column("plan_card_id", uuid_type, nullable=True),
        sa.Column("phase_card_id", uuid_type, nullable=True),
        sa.Column("scheduled_for", sa.Date(), nullable=True),
        sa.Column("window_start", sa.DateTime(), nullable=True),
        sa.Column("window_end", sa.DateTime(), nullable=True),
        sa.Column("occurrence_status", sa.String(24), nullable=False, server_default="'PLANNED'"),
        sa.Column("actual_minutes", sa.Integer(), nullable=True),
        sa.Column("completion_quality", sa.Integer(), nullable=True),
        sa.Column("deferral_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("generated_by_rule_hash", sa.String(128), nullable=False, server_default="''"),
        sa.Column("feedback_payload", jsonb, nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["series_card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["phase_card_id"], ["cards.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_occurrences_deleted_at", "task_occurrences", ["deleted_at"], unique=False)
    op.create_index("ix_occurrences_series_card_id", "task_occurrences", ["series_card_id"], unique=False)
    op.create_index("ix_occurrences_plan_card_id", "task_occurrences", ["plan_card_id"], unique=False)
    op.create_index("ix_occurrences_scheduled_for", "task_occurrences", ["scheduled_for"], unique=False)
    op.create_index("ix_occurrences_status", "task_occurrences", ["occurrence_status"], unique=False)
    op.create_index("ix_occurrences_series_status", "task_occurrences", ["series_card_id", "occurrence_status"], unique=False)
    op.create_index("ix_occurrences_scheduled_date", "task_occurrences", ["scheduled_for", "occurrence_status"], unique=False)
    op.create_index("ix_occurrences_plan_date", "task_occurrences", ["plan_card_id", "scheduled_for"], unique=False)

    # ------------------------------------------------------------------
    # 4. planning_artifacts — versioned AI governance records
    # ------------------------------------------------------------------
    op.create_table(
        "planning_artifacts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("plan_card_id", uuid_type, nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(24), nullable=False, server_default="'DRAFT'"),
        sa.Column("payload", jsonb, nullable=False, server_default="'{}'"),
        sa.Column("based_on_versions", jsonb, nullable=False, server_default="'{}'"),
        sa.Column("created_by_agent", sa.String(64), nullable=True),
        sa.Column("approved_by_user_id", uuid_type, nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["plan_card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("plan_card_id", "artifact_type", "version", name="uq_artifact_version"),
    )
    op.create_index("ix_artifacts_deleted_at", "planning_artifacts", ["deleted_at"], unique=False)
    op.create_index("ix_artifacts_plan_card_id", "planning_artifacts", ["plan_card_id"], unique=False)
    op.create_index("ix_artifacts_artifact_type", "planning_artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_artifacts_status", "planning_artifacts", ["status"], unique=False)
    op.create_index("ix_artifacts_plan_type", "planning_artifacts", ["plan_card_id", "artifact_type"], unique=False)
    op.create_index("ix_artifacts_type_status", "planning_artifacts", ["artifact_type", "status"], unique=False)

    # ------------------------------------------------------------------
    # 5. intervention_records — tracked intervention lifecycle
    # ------------------------------------------------------------------
    op.create_table(
        "intervention_records",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("plan_card_id", uuid_type, nullable=True),
        sa.Column("phase_card_id", uuid_type, nullable=True),
        sa.Column("task_occurrence_id", uuid_type, nullable=True),
        sa.Column("knowledge_card_id", uuid_type, nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_source_ref", sa.String(128), nullable=True),
        sa.Column("diagnosis_payload", jsonb, nullable=False, server_default="'{}'"),
        sa.Column("delivery_strategy", sa.String(24), nullable=False),
        sa.Column("delivery_channel", sa.String(24), nullable=False),
        sa.Column("content_version", sa.String(64), nullable=False, server_default="'1'"),
        sa.Column("acceptance_status", sa.String(24), nullable=False, server_default="'CREATED'"),
        sa.Column("action_payload", jsonb, nullable=True),
        sa.Column("outcome_window_days", sa.Integer(), nullable=False, server_default=sa.text("7")),
        sa.Column("outcome_status", sa.String(24), nullable=False, server_default="'PENDING'"),
        sa.Column("evidence_payload", jsonb, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["phase_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_occurrence_id"], ["task_occurrences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["knowledge_card_id"], ["cards.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_intervention_deleted_at", "intervention_records", ["deleted_at"], unique=False)
    op.create_index("ix_intervention_user_id", "intervention_records", ["user_id"], unique=False)
    op.create_index("ix_intervention_plan_card_id", "intervention_records", ["plan_card_id"], unique=False)
    op.create_index("ix_intervention_trigger_type", "intervention_records", ["trigger_type"], unique=False)
    op.create_index("ix_intervention_acceptance_status", "intervention_records", ["acceptance_status"], unique=False)
    op.create_index("ix_intervention_user_status", "intervention_records", ["user_id", "acceptance_status"], unique=False)
    op.create_index("ix_intervention_trigger_channel", "intervention_records", ["trigger_type", "delivery_channel"], unique=False)
    op.create_index("ix_intervention_outcome", "intervention_records", ["outcome_status", "outcome_window_days"], unique=False)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("intervention_records")
    op.drop_table("planning_artifacts")
    op.drop_table("task_occurrences")
    op.drop_table("card_edges")
    op.drop_table("cards")
