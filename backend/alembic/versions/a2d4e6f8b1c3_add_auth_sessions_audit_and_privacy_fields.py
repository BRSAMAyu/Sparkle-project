"""add auth sessions, auth audit, and privacy fields

Revision ID: a2d4e6f8b1c3
Revises: c9f3b2a7e1d4
Create Date: 2026-03-15 18:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2d4e6f8b1c3"
down_revision: Union[str, None] = "c9f3b2a7e1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("password_login_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("agreed_to_tos_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("agreed_to_privacy_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("tos_version", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("privacy_version", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("agreed_locale", sa.String(length=20), nullable=True))

    op.execute(
        sa.text(
            "UPDATE users SET password_login_enabled = FALSE "
            "WHERE registration_source IN ('google', 'apple', 'wechat', 'guest')"
        )
    )

    op.create_table(
        "user_sessions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("refresh_token_jti", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_session_id", "user_sessions", ["session_id"], unique=False)
    op.create_index("ix_user_sessions_device_id", "user_sessions", ["device_id"], unique=False)
    op.create_index("ix_user_sessions_device_type", "user_sessions", ["device_type"], unique=False)
    op.create_index("ix_user_sessions_refresh_token_jti", "user_sessions", ["refresh_token_jti"], unique=False)
    op.create_index("ix_user_sessions_is_active", "user_sessions", ["is_active"], unique=False)
    op.create_index("ix_user_sessions_last_active_at", "user_sessions", ["last_active_at"], unique=False)
    op.create_index("ix_user_sessions_deleted_at", "user_sessions", ["deleted_at"], unique=False)
    op.create_index("idx_user_sessions_user_active", "user_sessions", ["user_id", "is_active"], unique=False)

    op.create_table(
        "auth_audit_log",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_audit_log_user_id", "auth_audit_log", ["user_id"], unique=False)
    op.create_index("ix_auth_audit_log_action", "auth_audit_log", ["action"], unique=False)
    op.create_index("ix_auth_audit_log_occurred_at", "auth_audit_log", ["occurred_at"], unique=False)
    op.create_index("idx_auth_audit_user_occurred", "auth_audit_log", ["user_id", "occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_auth_audit_user_occurred", table_name="auth_audit_log")
    op.drop_index("ix_auth_audit_log_occurred_at", table_name="auth_audit_log")
    op.drop_index("ix_auth_audit_log_action", table_name="auth_audit_log")
    op.drop_index("ix_auth_audit_log_user_id", table_name="auth_audit_log")
    op.drop_table("auth_audit_log")

    op.drop_index("idx_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_deleted_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_last_active_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_is_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_jti", table_name="user_sessions")
    op.drop_index("ix_user_sessions_device_type", table_name="user_sessions")
    op.drop_index("ix_user_sessions_device_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_session_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("agreed_locale")
        batch_op.drop_column("privacy_version")
        batch_op.drop_column("tos_version")
        batch_op.drop_column("agreed_to_privacy_at")
        batch_op.drop_column("agreed_to_tos_at")
        batch_op.drop_column("password_login_enabled")
