"""add_user_devices_table

Revision ID: 1b26570b5c19
Revises: ef2183fa19af
Create Date: 2026-01-24 02:26:18.268932

用户设备令牌表 - 用于推送通知和离线消息推送
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM user_devices;"
#   backfill_plan: "n/a (new table)"
#   owner: "sparkle-team"
#   ticket: "websocket-push"

# revision identifiers, used by Alembic.
revision: str = '1b26570b5c19'
down_revision: Union[str, None] = 'ef2183fa19af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建用户设备表
    op.create_table(
        "user_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("push_token", sa.String(500), nullable=False),
        sa.Column("token_type", sa.String(50), nullable=False),
        sa.Column("device_name", sa.String(100), nullable=True),
        sa.Column("app_version", sa.String(50), nullable=True),
        sa.Column("os_version", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_user_devices"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        comment="用户设备令牌表 - 用于推送通知和离线消息推送"
    )

    # 创建索引
    op.create_index(
        "ix_user_devices_user_id",
        "user_devices",
        ["user_id"]
    )
    op.create_index(
        "ix_user_devices_device_id",
        "user_devices",
        ["device_id"]
    )
    op.create_index(
        "ix_user_devices_push_token",
        "user_devices",
        ["push_token"]
    )
    op.create_index(
        "ix_user_devices_user_device",
        "user_devices",
        ["user_id", "device_id"],
        unique=True
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_user_devices_user_device", table_name="user_devices")
    op.drop_index("ix_user_devices_push_token", table_name="user_devices")
    op.drop_index("ix_user_devices_device_id", table_name="user_devices")
    op.drop_index("ix_user_devices_user_id", table_name="user_devices")

    # 删除表
    op.drop_table("user_devices")
