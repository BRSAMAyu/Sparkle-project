"""stage38 add event bus dlq

Revision ID: stage38_01_add_event_bus_dlq
Revises: s31a1b2c3d4
Create Date: 2026-04-23 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "stage38_01_add_event_bus_dlq"
down_revision = "s31a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_bus_dlq",
        sa.Column("stream", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_name", sa.String(length=255), nullable=False),
        sa.Column("consumer_name", sa.String(length=255), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_stage", sa.String(length=64), nullable=False, server_default="consume"),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_bus_dlq_created_at"), "event_bus_dlq", ["created_at"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_deleted_at"), "event_bus_dlq", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_event_type"), "event_bus_dlq", ["event_type"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_failure_stage"), "event_bus_dlq", ["failure_stage"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_group_name"), "event_bus_dlq", ["group_name"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_message_id"), "event_bus_dlq", ["message_id"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_stream"), "event_bus_dlq", ["stream"], unique=False)
    op.create_index(op.f("ix_event_bus_dlq_user_id"), "event_bus_dlq", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_event_bus_dlq_user_id"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_stream"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_message_id"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_group_name"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_failure_stage"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_event_type"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_deleted_at"), table_name="event_bus_dlq")
    op.drop_index(op.f("ix_event_bus_dlq_created_at"), table_name="event_bus_dlq")
    op.drop_table("event_bus_dlq")
