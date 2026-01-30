"""task_feedback_system

Revision ID: fa0b1c2d3e4f
Revises: f9d4e5f6a7b8
Create Date: 2026-01-24 12:00:00.000000

Task Feedback System - 任务反馈系统
支持任务完成后的反馈收集、用户偏好推断
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM task_feedbacks;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "task-feedback-system"

revision: str = "fa0b1c2d3e4f"
down_revision: Union[str, None] = "f9d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create task_feedbacks table
    op.create_table(
        "task_feedbacks",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("task_id", app.models.base.GUID(), nullable=False),
        sa.Column("completion_quality", sa.Integer(), nullable=True),  # 1-5 stars
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("inferred_depth_delta", sa.Float(), nullable=True),
        sa.Column("inferred_difficulty_delta", sa.Float(), nullable=True),
        sa.Column("task_difficulty_snapshot", sa.Integer(), nullable=True),
        sa.Column("task_type_snapshot", sa.String(length=50), nullable=True),
        sa.Column("actual_minutes_snapshot", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_task_feedbacks_user_id", "task_feedbacks", ["user_id"], unique=False)
    op.create_index("ix_task_feedbacks_task_id", "task_feedbacks", ["task_id"], unique=False)
    op.create_index("ix_task_feedbacks_completion_quality", "task_feedbacks", ["completion_quality"], unique=False)
    op.create_index("ix_task_feedbacks_user_created", "task_feedbacks", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_task_feedbacks_user_created", "task_feedbacks")
    op.drop_index("ix_task_feedbacks_completion_quality", "task_feedbacks")
    op.drop_index("ix_task_feedbacks_task_id", "task_feedbacks")
    op.drop_index("ix_task_feedbacks_user_id", "task_feedbacks")

    # Drop table
    op.drop_table("task_feedbacks")
