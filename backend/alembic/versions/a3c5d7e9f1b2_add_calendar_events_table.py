"""add calendar_events table

Revision ID: a3c5d7e9f1b2
Revises: f2b3c4d5e6f7
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a3c5d7e9f1b2"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.GUID(), nullable=False),
        sa.Column("user_id", sa.GUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_all_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("color", sa.String(32), nullable=True),
        sa.Column("recurrence_rule", sa.String(512), nullable=True),
        sa.Column("recurrence_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_minutes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(32), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("task_id", sa.GUID(), nullable=True),
        sa.Column("plan_id", sa.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建索引
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])
    op.create_index("ix_calendar_events_user_time", "calendar_events", ["user_id", "start_time"])
    op.create_index("ix_calendar_events_user_deleted", "calendar_events", ["user_id", "deleted_at"])
    op.create_index("ix_calendar_events_task_id", "calendar_events", ["task_id"])
    op.create_index("ix_calendar_events_plan_id", "calendar_events", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_calendar_events_plan_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_task_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_deleted", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_time", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_id", table_name="calendar_events")
    op.drop_table("calendar_events")
