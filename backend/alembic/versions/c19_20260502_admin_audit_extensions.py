"""admin audit extensions

Revision ID: c19_20260502
Revises: wp18_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

import app.models.base


revision: str = "c19_20260502"
down_revision: str | None = "wp18_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "admin_audit_log",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("admin_user_id", app.models.base.GUID(), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("trace_id", sa.String(length=100), nullable=True),
        sa.Column("actor_claims", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "retention_until",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP + INTERVAL '90 days')") if _is_postgresql() else None,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_log_action", "admin_audit_log", ["action"], unique=False)
    op.create_index("ix_admin_audit_log_admin_user_id", "admin_audit_log", ["admin_user_id"], unique=False)
    op.create_index("ix_admin_audit_log_category", "admin_audit_log", ["category"], unique=False)
    op.create_index("ix_admin_audit_log_created_at", "admin_audit_log", ["created_at"], unique=False)
    op.create_index("ix_admin_audit_log_id", "admin_audit_log", ["id"], unique=False)
    op.create_index("ix_admin_audit_log_ip_address", "admin_audit_log", ["ip_address"], unique=False)
    op.create_index("ix_admin_audit_log_occurred_at", "admin_audit_log", ["occurred_at"], unique=False)
    op.create_index("ix_admin_audit_log_outcome", "admin_audit_log", ["outcome"], unique=False)
    op.create_index("ix_admin_audit_log_path", "admin_audit_log", ["path"], unique=False)
    op.create_index("ix_admin_audit_log_request_id", "admin_audit_log", ["request_id"], unique=False)
    op.create_index("ix_admin_audit_log_retention_until", "admin_audit_log", ["retention_until"], unique=False)
    op.create_index("ix_admin_audit_log_risk", "admin_audit_log", ["risk"], unique=False)
    op.create_index("ix_admin_audit_log_status_code", "admin_audit_log", ["status_code"], unique=False)
    op.create_index("ix_admin_audit_log_trace_id", "admin_audit_log", ["trace_id"], unique=False)
    op.create_index(
        "idx_admin_audit_category_occurred",
        "admin_audit_log",
        ["category", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "idx_admin_audit_user_occurred",
        "admin_audit_log",
        ["admin_user_id", "occurred_at"],
        unique=False,
    )

    if _is_postgresql():
        op.execute(
            """
            CREATE OR REPLACE FUNCTION admin_audit_log_prevent_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'admin_audit_log is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_admin_audit_log_prevent_mutation
            BEFORE UPDATE OR DELETE ON admin_audit_log
            FOR EACH ROW EXECUTE FUNCTION admin_audit_log_prevent_mutation();
            """
        )
        op.execute("ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;")
        op.execute(
            """
            CREATE POLICY admin_audit_log_insert_only
            ON admin_audit_log
            FOR INSERT
            WITH CHECK (true);
            """
        )
        op.execute(
            """
            CREATE POLICY admin_audit_log_select_only
            ON admin_audit_log
            FOR SELECT
            USING (true);
            """
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute("DROP POLICY IF EXISTS admin_audit_log_select_only ON admin_audit_log;")
        op.execute("DROP POLICY IF EXISTS admin_audit_log_insert_only ON admin_audit_log;")
        op.execute("DROP TRIGGER IF EXISTS trg_admin_audit_log_prevent_mutation ON admin_audit_log;")
        op.execute("DROP FUNCTION IF EXISTS admin_audit_log_prevent_mutation();")

    op.drop_index("idx_admin_audit_user_occurred", table_name="admin_audit_log")
    op.drop_index("idx_admin_audit_category_occurred", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_trace_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_status_code", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_risk", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_retention_until", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_request_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_path", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_outcome", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_occurred_at", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_ip_address", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_created_at", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_category", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_admin_user_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_action", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
