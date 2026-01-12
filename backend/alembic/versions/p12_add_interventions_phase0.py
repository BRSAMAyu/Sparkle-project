"""add interventions phase0 tables

Revision ID: p12_add_interventions_phase0
Revises: p11_add_expansion_feedback
Create Date: 2026-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.base import GUID


revision = "p12_add_interventions_phase0"
down_revision = "p11_add_expansion_feedback"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    json_type = postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()

    op.create_table(
        "user_intervention_settings",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("interrupt_threshold", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("daily_interrupt_budget", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("quiet_hours", json_type, nullable=True),
        sa.Column("topic_allowlist", json_type, nullable=True),
        sa.Column("topic_blocklist", json_type, nullable=True),
        sa.Column("do_not_disturb", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id")
    )
    op.create_index(
        "idx_intervention_settings_user",
        "user_intervention_settings",
        ["user_id"],
        unique=True
    )

    op.create_table(
        "intervention_requests",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=True),
        sa.Column("topic", sa.String(length=120), nullable=True),
        sa.Column("requested_level", sa.String(length=40), nullable=False),
        sa.Column("final_level", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reason", json_type, nullable=True),
        sa.Column("content", json_type, nullable=True),
        sa.Column("cooldown_policy", json_type, nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_retractable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supersedes_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("idx_intervention_requests_user", "intervention_requests", ["user_id"], unique=False)
    op.create_index("idx_intervention_requests_topic", "intervention_requests", ["topic"], unique=False)
    op.create_index("idx_intervention_requests_status", "intervention_requests", ["status"], unique=False)
    op.create_index("idx_intervention_requests_dedupe", "intervention_requests", ["dedupe_key"], unique=False)

    op.create_table(
        "intervention_audit_logs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("request_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("guardrail_result", json_type, nullable=True),
        sa.Column("decision_trace", json_type, nullable=True),
        sa.Column("evidence_refs", json_type, nullable=True),
        sa.Column("requested_level", sa.String(length=40), nullable=False),
        sa.Column("final_level", sa.String(length=40), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["intervention_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("idx_intervention_audit_request", "intervention_audit_logs", ["request_id"], unique=False)
    op.create_index("idx_intervention_audit_user", "intervention_audit_logs", ["user_id"], unique=False)
    op.create_index("idx_intervention_audit_action", "intervention_audit_logs", ["action"], unique=False)
    op.create_index("idx_intervention_audit_occurred", "intervention_audit_logs", ["occurred_at"], unique=False)

    op.create_table(
        "intervention_feedback",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("request_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("feedback_type", sa.String(length=40), nullable=False),
        sa.Column("extra_data", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["intervention_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("idx_intervention_feedback_request", "intervention_feedback", ["request_id"], unique=False)
    op.create_index("idx_intervention_feedback_user", "intervention_feedback", ["user_id"], unique=False)
    op.create_index("idx_intervention_feedback_type", "intervention_feedback", ["feedback_type"], unique=False)


def downgrade():
    op.drop_index("idx_intervention_feedback_type", table_name="intervention_feedback")
    op.drop_index("idx_intervention_feedback_user", table_name="intervention_feedback")
    op.drop_index("idx_intervention_feedback_request", table_name="intervention_feedback")
    op.drop_table("intervention_feedback")

    op.drop_index("idx_intervention_audit_occurred", table_name="intervention_audit_logs")
    op.drop_index("idx_intervention_audit_action", table_name="intervention_audit_logs")
    op.drop_index("idx_intervention_audit_user", table_name="intervention_audit_logs")
    op.drop_index("idx_intervention_audit_request", table_name="intervention_audit_logs")
    op.drop_table("intervention_audit_logs")

    op.drop_index("idx_intervention_requests_dedupe", table_name="intervention_requests")
    op.drop_index("idx_intervention_requests_status", table_name="intervention_requests")
    op.drop_index("idx_intervention_requests_topic", table_name="intervention_requests")
    op.drop_index("idx_intervention_requests_user", table_name="intervention_requests")
    op.drop_table("intervention_requests")

    op.drop_index("idx_intervention_settings_user", table_name="user_intervention_settings")
    op.drop_table("user_intervention_settings")
