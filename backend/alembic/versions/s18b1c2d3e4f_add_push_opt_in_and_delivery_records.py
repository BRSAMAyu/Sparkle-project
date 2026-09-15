"""add stage18 push opt-in and delivery records

Revision ID: s18b1c2d3e4f
Revises: s17a1b2c3d4
Create Date: 2026-04-21 01:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "s18b1c2d3e4f"
down_revision = "s17a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_push_opt_in",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_commitment_follow_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_engagement_recovery", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=False, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=False, server_default="08:00"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Shanghai"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_user_push_opt_in_user", "user_push_opt_in", ["user_id"], unique=True)

    op.create_table(
        "push_delivery_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("message_template_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("evidence_token", sa.String(length=255), nullable=False),
        sa.Column("delivery_channel", sa.String(length=32), nullable=False, server_default="websocket"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="sent"),
        sa.Column("scheduled_send_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("acted_at", sa.DateTime(), nullable=True),
        sa.Column("retracted_at", sa.DateTime(), nullable=True),
        sa.Column("retractable_until", sa.DateTime(), nullable=True),
        sa.Column("category_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_push_delivery_user_sent", "push_delivery_records", ["user_id", "sent_at"], unique=False)
    op.create_index(
        "idx_push_delivery_user_category",
        "push_delivery_records",
        ["user_id", "category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_push_delivery_user_category", table_name="push_delivery_records")
    op.drop_index("idx_push_delivery_user_sent", table_name="push_delivery_records")
    op.drop_table("push_delivery_records")
    op.drop_index("idx_user_push_opt_in_user", table_name="user_push_opt_in")
    op.drop_table("user_push_opt_in")
