"""add execution intent and execution record tables

Revision ID: oc001a2b3c4d5
Revises: e8f1a2b3c4d5
Create Date: 2026-03-27 12:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

# revision identifiers, used by Alembic.
revision: str = "oc001a2b3c4d5"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type(bind) -> sa.JSON:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)

    op.create_table(
        "execution_intents",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("plan_id", app.models.base.GUID(), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", app.models.base.GUID(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_mode", sa.String(length=20), nullable=False, server_default="human"),
        sa.Column("executor", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("instructions", json_type, nullable=False, server_default=sa.text("'[]'::jsonb") if bind.dialect.name == "postgresql" else "[]"),
        sa.Column("target_env", sa.String(length=20), nullable=True),
        sa.Column("policy", json_type, nullable=False, server_default=sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else "{}"),
        sa.Column("success_criteria", json_type, nullable=False, server_default=sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else "{}"),
        sa.Column("result_contract", json_type, nullable=False, server_default=sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else "{}"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("trust_level", sa.String(length=20), nullable=False, server_default="raw"),
        sa.Column("external_run_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("idx_exec_intent_user_status", "execution_intents", ["user_id", "status"], unique=False)
    op.create_index("idx_exec_intent_task", "execution_intents", ["task_id"], unique=False)
    op.create_index("idx_exec_intent_created", "execution_intents", ["created_at"], unique=False)
    op.create_index("idx_exec_intent_external_run", "execution_intents", ["external_run_id"], unique=False)
    op.create_index("idx_exec_intent_plan", "execution_intents", ["plan_id"], unique=False)

    op.create_table(
        "execution_records",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "execution_intent_id",
            app.models.base.GUID(),
            sa.ForeignKey("execution_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", app.models.base.GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", app.models.base.GUID(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("executor_type", sa.String(length=50), nullable=False, server_default="openclaw"),
        sa.Column("external_run_id", sa.String(length=255), nullable=True),
        sa.Column("raw_response", json_type, nullable=False, server_default=sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else "{}"),
        sa.Column("parsed_output", json_type, nullable=True),
        sa.Column("artifacts", json_type, nullable=False, server_default=sa.text("'[]'::jsonb") if bind.dialect.name == "postgresql" else "[]"),
        sa.Column("trust_level", sa.String(length=20), nullable=False, server_default="raw"),
        sa.Column("validation_passed", sa.Integer(), nullable=True),
        sa.Column("validation_total", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", json_type, nullable=True),
        sa.Column("tool_calls_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("approval_requested", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_started_at", sa.DateTime(), nullable=True),
        sa.Column("execution_completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_intent_id"),
    )
    op.create_index("idx_exec_record_user", "execution_records", ["user_id"], unique=False)
    op.create_index("idx_exec_record_intent", "execution_records", ["execution_intent_id"], unique=False)
    op.create_index("idx_exec_record_trust", "execution_records", ["trust_level"], unique=False)
    op.create_index("idx_exec_record_created", "execution_records", ["created_at"], unique=False)

    op.add_column("tasks", sa.Column("execution_mode", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "execution_mode")

    op.drop_index("idx_exec_record_created", table_name="execution_records")
    op.drop_index("idx_exec_record_trust", table_name="execution_records")
    op.drop_index("idx_exec_record_intent", table_name="execution_records")
    op.drop_index("idx_exec_record_user", table_name="execution_records")
    op.drop_table("execution_records")

    op.drop_index("idx_exec_intent_plan", table_name="execution_intents")
    op.drop_index("idx_exec_intent_external_run", table_name="execution_intents")
    op.drop_index("idx_exec_intent_created", table_name="execution_intents")
    op.drop_index("idx_exec_intent_task", table_name="execution_intents")
    op.drop_index("idx_exec_intent_user_status", table_name="execution_intents")
    op.drop_table("execution_intents")
