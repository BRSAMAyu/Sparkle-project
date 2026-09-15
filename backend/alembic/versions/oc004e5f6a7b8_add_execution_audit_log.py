"""add execution audit log

Revision ID: oc004e5f6a7b8
Revises: tp1e2f3a4b5c6
Create Date: 2026-04-02 16:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.base

# revision identifiers, used by Alembic.
revision: str = "oc004e5f6a7b8"
down_revision: Union[str, None] = "tp1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_audit_log",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("intent_id", app.models.base.GUID(), sa.ForeignKey("execution_intents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_audit_log_action", "execution_audit_log", ["action"], unique=False)
    op.create_index("ix_execution_audit_log_actor", "execution_audit_log", ["actor"], unique=False)
    op.create_index("ix_execution_audit_log_intent_id", "execution_audit_log", ["intent_id"], unique=False)
    op.create_index("ix_execution_audit_log_occurred_at", "execution_audit_log", ["occurred_at"], unique=False)
    op.create_index("ix_execution_audit_log_user_id", "execution_audit_log", ["user_id"], unique=False)
    op.create_index(
        "idx_execution_audit_intent_occurred",
        "execution_audit_log",
        ["intent_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "idx_execution_audit_user_action",
        "execution_audit_log",
        ["user_id", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_execution_audit_user_action", table_name="execution_audit_log")
    op.drop_index("idx_execution_audit_intent_occurred", table_name="execution_audit_log")
    op.drop_index("ix_execution_audit_log_user_id", table_name="execution_audit_log")
    op.drop_index("ix_execution_audit_log_occurred_at", table_name="execution_audit_log")
    op.drop_index("ix_execution_audit_log_intent_id", table_name="execution_audit_log")
    op.drop_index("ix_execution_audit_log_actor", table_name="execution_audit_log")
    op.drop_index("ix_execution_audit_log_action", table_name="execution_audit_log")
    op.drop_table("execution_audit_log")
