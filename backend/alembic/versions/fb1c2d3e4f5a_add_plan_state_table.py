"""add_plan_state_table

Revision ID: fb1c2d3e4f5a
Revises: fa0b1c2d3e4f
Create Date: 2026-01-24 16:00:00.000000

PlanState - 计划级状态存储
Stores plan-specific context for tracking execution state.

See: docs/state/plan_state_spec.md for design details.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM plan_states;"
#   backfill_plan: "n/a - new table"
#   owner: "sparkle-team"
#   ticket: "plan-state-layer"

revision: str = "fb1c2d3e4f5a"
down_revision: Union[str, None] = "fa0b1c2d3e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create plan_states table
    op.create_table(
        "plan_states",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column(
            "plan_id",
            app.models.base.GUID(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            app.models.base.GUID(),
            nullable=False,
        ),
        # State fields (JSONB)
        sa.Column(
            "facts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "milestones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "task_index",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "feedback_log",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        # Version control
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        # Status management
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        # Timestamps and soft delete
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="chk_plan_states_status",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_plan_states_plan_id",
        "plan_states",
        ["plan_id"],
        unique=True,
    )
    op.create_index(
        "ix_plan_states_user_id",
        "plan_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_plan_states_status",
        "plan_states",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_plan_states_user_status",
        "plan_states",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_plan_states_updated_at",
        "plan_states",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_plan_states_deleted_at",
        "plan_states",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_plan_states_deleted_at", "plan_states")
    op.drop_index("ix_plan_states_updated_at", "plan_states")
    op.drop_index("ix_plan_states_user_status", "plan_states")
    op.drop_index("ix_plan_states_status", "plan_states")
    op.drop_index("ix_plan_states_user_id", "plan_states")
    op.drop_index("ix_plan_states_plan_id", "plan_states")

    # Drop table
    op.drop_table("plan_states")
