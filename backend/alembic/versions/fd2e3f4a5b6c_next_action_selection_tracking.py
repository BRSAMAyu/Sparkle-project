"""next_action_selection_tracking

Revision ID: fd2e3f4a5b6c
Revises: fc1c2d3e4f5a
Create Date: 2026-01-24 18:00:00.000000

Next Action Selection Tracking - 下一步操作选择追踪
支持追踪用户对next_action的点击/跳过行为，用于个性化推荐
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM next_action_selections;"
#   backfill_plan: "n/a - new table"
#   owner: "sparkle-team"
#   ticket: "task-feedback-loop"

revision: str = "fd2e3f4a5b6c"
down_revision: Union[str, None] = "fc1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create next_action_selections table
    op.create_table(
        "next_action_selections",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("task_id", app.models.base.GUID(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("action_title", sa.String(length=255), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False, default=False),
        sa.Column("skipped", sa.Boolean(), nullable=False, default=False),
        sa.Column("display_position", sa.Integer(), nullable=True),
        sa.Column("displayed_actions_count", sa.Integer(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )

    # Create indexes for efficient queries
    op.create_index("ix_next_action_selections_user_id", "next_action_selections", ["user_id"], unique=False)
    op.create_index("ix_next_action_selections_task_id", "next_action_selections", ["task_id"], unique=False)
    op.create_index("ix_next_action_selections_action_type", "next_action_selections", ["action_type"], unique=False)
    op.create_index("ix_next_action_selections_user_created", "next_action_selections", ["user_id", "created_at"], unique=False)

    # Create composite index for selection rate calculation
    op.create_index("ix_next_action_selections_user_type_selected", "next_action_selections",
                    ["user_id", "action_type", "selected"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_next_action_selections_user_type_selected", "next_action_selections")
    op.drop_index("ix_next_action_selections_user_created", "next_action_selections")
    op.drop_index("ix_next_action_selections_action_type", "next_action_selections")
    op.drop_index("ix_next_action_selections_task_id", "next_action_selections")
    op.drop_index("ix_next_action_selections_user_id", "next_action_selections")

    # Drop table
    op.drop_table("next_action_selections")
