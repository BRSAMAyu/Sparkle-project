"""create_user_tool_history_table

Revision ID: 4f6c3b8e1d2a
Revises: cc9383c4c29f
Create Date: 2026-01-30 06:26:08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.base
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4f6c3b8e1d2a"
down_revision: Union[str, None] = "cc9383c4c29f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_tool_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("tool_category", sa.String(length=50), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column(
            "context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "input_args",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("user_satisfaction", sa.Integer(), nullable=True),
        sa.Column("was_helpful", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("user_tool_history", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_tool_history_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_user_tool_history_tool_name"), ["tool_name"], unique=False)
        batch_op.create_index(batch_op.f("ix_user_tool_history_user_created"), ["user_id", "created_at"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_user_tool_history_user_id"),
            ["user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_user_tool_history_success"),
            ["user_id", "tool_name", "success"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_user_tool_history_metrics"),
            ["user_id", "tool_name", "success", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("user_tool_history")
