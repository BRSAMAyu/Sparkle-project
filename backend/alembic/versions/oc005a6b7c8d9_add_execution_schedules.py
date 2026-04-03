"""add execution schedules

Revision ID: oc005a6b7c8d9
Revises: oc004e5f6a7b8
Create Date: 2026-04-02 20:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "oc005a6b7c8d9"
down_revision = "oc004e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text())
    if op.get_bind().dialect.name == "sqlite":
        jsonb_type = sa.JSON()

    op.create_table(
        "execution_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intent_template", jsonb_type, nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_config", jsonb_type, nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_execution_schedules_deleted_at", "execution_schedules", ["deleted_at"], unique=False)
    op.create_index("ix_execution_schedules_is_active", "execution_schedules", ["is_active"], unique=False)
    op.create_index("ix_execution_schedules_next_run_at", "execution_schedules", ["next_run_at"], unique=False)
    op.create_index("ix_execution_schedules_task_id", "execution_schedules", ["task_id"], unique=False)
    op.create_index("ix_execution_schedules_user_id", "execution_schedules", ["user_id"], unique=False)
    op.create_index("idx_execution_schedule_due", "execution_schedules", ["is_active", "next_run_at"], unique=False)
    op.create_index(
        "idx_execution_schedule_user_trigger",
        "execution_schedules",
        ["user_id", "trigger_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_execution_schedule_user_trigger", table_name="execution_schedules")
    op.drop_index("idx_execution_schedule_due", table_name="execution_schedules")
    op.drop_index("ix_execution_schedules_user_id", table_name="execution_schedules")
    op.drop_index("ix_execution_schedules_task_id", table_name="execution_schedules")
    op.drop_index("ix_execution_schedules_next_run_at", table_name="execution_schedules")
    op.drop_index("ix_execution_schedules_is_active", table_name="execution_schedules")
    op.drop_index("ix_execution_schedules_deleted_at", table_name="execution_schedules")
    op.drop_table("execution_schedules")
