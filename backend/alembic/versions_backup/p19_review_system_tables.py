"""add review system tables

Revision ID: p19_review_system_tables
Revises: p18_event_sequence_counters
Create Date: 2026-01-26 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision: str = "p19_review_system_tables"
down_revision: Union[str, None] = "p18_event_sequence_counters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()

    if not table_exists(inspector, "review_history"):
        op.create_table(
            "review_history",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("review_id", sa.String(length=64), nullable=False),
            sa.Column("target_id", sa.String(length=128), nullable=False),
            sa.Column("target_type", sa.String(length=50), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("session_id", sa.String(length=128), nullable=True),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("issues_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reflection_round", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reflection_outcome", sa.String(length=64), nullable=True),
            sa.Column("score_delta", sa.Float(), nullable=False, server_default="0"),
            sa.Column("user_feedback", sa.String(length=64), nullable=True),
            sa.Column("user_satisfied", sa.Boolean(), nullable=True),
            sa.Column("feedback_timestamp", sa.DateTime(), nullable=True),
            sa.Column("reviewer_model", sa.String(length=100), nullable=True),
            sa.Column("review_duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("requires_reflection", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("user_query", sa.Text(), nullable=True),
            sa.Column("content_snapshot", sa.Text(), nullable=True),
        )
        op.create_index("ix_review_history_review_id", "review_history", ["review_id"], unique=True)
        op.create_index("ix_review_history_target_id", "review_history", ["target_id"])
        op.create_index("ix_review_history_target_type", "review_history", ["target_type"])
        op.create_index("ix_review_history_user_id", "review_history", ["user_id"])
        op.create_index("ix_review_history_session_id", "review_history", ["session_id"])
        op.create_index("ix_review_history_decision", "review_history", ["decision"])

    if not table_exists(inspector, "review_feedback"):
        op.create_table(
            "review_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("feedback_id", sa.String(length=64), nullable=False),
            sa.Column("review_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("feedback_type", sa.String(length=32), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("issues_reported", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("original_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("original_decision", sa.String(length=32), nullable=True),
            sa.Column("was_reflected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("was_helpful", sa.Boolean(), nullable=True),
            sa.Column("was_accurate", sa.Boolean(), nullable=True),
            sa.Column("inaccurate_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("specificity_level", sa.String(length=32), nullable=True),
            sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        op.create_index("ix_review_feedback_feedback_id", "review_feedback", ["feedback_id"], unique=True)
        op.create_index("ix_review_feedback_review_id", "review_feedback", ["review_id"])
        op.create_index("ix_review_feedback_user_id", "review_feedback", ["user_id"])
        op.create_index("ix_review_feedback_type", "review_feedback", ["feedback_type"])

    if not table_exists(inspector, "review_overrides"):
        op.create_table(
            "review_overrides",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("override_id", sa.String(length=64), nullable=False),
            sa.Column("review_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("original_decision", sa.String(length=32), nullable=False),
            sa.Column("new_decision", sa.String(length=32), nullable=False),
            sa.Column("override_type", sa.String(length=64), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("was_correct", sa.Boolean(), nullable=True),
            sa.Column("admin_reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        op.create_index("ix_review_overrides_override_id", "review_overrides", ["override_id"], unique=True)
        op.create_index("ix_review_overrides_review_id", "review_overrides", ["review_id"])
        op.create_index("ix_review_overrides_user_id", "review_overrides", ["user_id"])

    if not table_exists(inspector, "appeals"):
        op.create_table(
            "appeals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("appeal_id", sa.String(length=64), nullable=False),
            sa.Column("review_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("appeal_reason", sa.Text(), nullable=False),
            sa.Column("issues_with_review", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("assigned_to", sa.String(length=64), nullable=True),
            sa.Column("secondary_review_id", sa.String(length=64), nullable=True),
            sa.Column("secondary_decision", sa.String(length=32), nullable=True),
            sa.Column("secondary_score", sa.Float(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("resolved_by", sa.String(length=64), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_appeals_appeal_id", "appeals", ["appeal_id"], unique=True)
        op.create_index("ix_appeals_review_id", "appeals", ["review_id"])
        op.create_index("ix_appeals_user_id", "appeals", ["user_id"])
        op.create_index("ix_appeals_status", "appeals", ["status"])

    if not table_exists(inspector, "arbitration_cases"):
        op.create_table(
            "arbitration_cases",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("case_id", sa.String(length=64), nullable=False),
            sa.Column("appeal_id", sa.String(length=64), nullable=False),
            sa.Column("review_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("escalation_reason", sa.String(length=64), nullable=False),
            sa.Column("priority", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("assigned_to", sa.String(length=64), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.Column("original_review_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("secondary_review_score", sa.Float(), nullable=True),
            sa.Column("score_discrepancy", sa.Float(), nullable=False, server_default="0"),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("final_decision", sa.String(length=32), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.String(length=64), nullable=True),
            sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        op.create_index("ix_arbitration_cases_case_id", "arbitration_cases", ["case_id"], unique=True)
        op.create_index("ix_arbitration_cases_appeal_id", "arbitration_cases", ["appeal_id"])
        op.create_index("ix_arbitration_cases_review_id", "arbitration_cases", ["review_id"])
        op.create_index("ix_arbitration_cases_user_id", "arbitration_cases", ["user_id"])
        op.create_index("ix_arbitration_cases_priority", "arbitration_cases", ["priority"])
        op.create_index("ix_arbitration_cases_status", "arbitration_cases", ["status"])
        op.create_index("ix_arbitration_cases_reason", "arbitration_cases", ["escalation_reason"])

    if not table_exists(inspector, "arbitration_decisions"):
        op.create_table(
            "arbitration_decisions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("case_id", sa.String(length=64), nullable=False),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("arbitrator_id", sa.String(length=64), nullable=False),
            sa.Column("arbitrator_role", sa.String(length=32), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
            sa.Column("feedback_for_model", sa.Text(), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_arbitration_decisions_case_id", "arbitration_decisions", ["case_id"])


def downgrade() -> None:
    op.drop_table("arbitration_decisions")
    op.drop_table("arbitration_cases")
    op.drop_table("appeals")
    op.drop_table("review_overrides")
    op.drop_table("review_feedback")
    op.drop_table("review_history")
