"""response_feedback

Revision ID: 8b3f2f5a9c1b
Revises: 732657da3d7b
Create Date: 2026-03-01 10:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

revision: str = "8b3f2f5a9c1b"
down_revision: Union[str, None] = "732657da3d7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "response_feedback",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("response_id", app.models.base.GUID(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("feedback_type", sa.SmallInteger(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("free_text", sa.String(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "response_id", name="uq_response_feedback_user_response"),
    )
    with op.batch_alter_table("response_feedback", schema=None) as batch_op:
        batch_op.create_index(
            "ix_response_feedback_workflow_prompt_created",
            ["workflow_id", "prompt_version", "created_at"],
            unique=False,
        )
        batch_op.create_index("ix_response_feedback_created_at", ["created_at"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_response_feedback_deleted_at"),
            ["deleted_at"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_response_feedback_response_id"), ["response_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_response_feedback_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("response_feedback", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_response_feedback_user_id"))
        batch_op.drop_index(batch_op.f("ix_response_feedback_response_id"))
        batch_op.drop_index(batch_op.f("ix_response_feedback_deleted_at"))
        batch_op.drop_index("ix_response_feedback_created_at")
        batch_op.drop_index("ix_response_feedback_workflow_prompt_created")

    op.drop_table("response_feedback")
