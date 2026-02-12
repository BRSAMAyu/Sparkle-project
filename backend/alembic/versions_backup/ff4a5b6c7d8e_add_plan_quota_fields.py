"""add_plan_priority_and_is_primary

Revision ID: ff4a5b6c7d8e
Revises: fe3f4a5b6c7d
Create Date: 2026-01-25 10:00:00.000000

P0: Add priority and is_primary fields to plans table.
Supports parallel plan limit system with priority-based selection.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT priority, is_primary FROM plans LIMIT 1;"
#   backfill_plan: "Existing plans get priority='normal', is_primary=false"
#   owner: "sparkle-team"
#   ticket: "p0-plan-quota-system"

revision: str = "ff4a5b6c7d8e"
down_revision: Union[str, None] = "fe3f4a5b6c7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type for PlanPriority
    plan_priority_enum = sa.Enum(
        'critical', 'high', 'normal', 'low',
        name='planpriority',
        create_type=False
    )

    # Create enum type in PostgreSQL
    op.execute("CREATE TYPE planpriority AS ENUM ('critical', 'high', 'normal', 'low')")

    # Add priority column with default 'normal'
    op.add_column(
        "plans",
        sa.Column(
            "priority",
            plan_priority_enum,
            nullable=False,
            server_default="normal",
        ),
    )

    # Add is_primary column with default false
    op.add_column(
        "plans",
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Create indexes for efficient querying
    op.create_index("idx_plans_priority", "plans", ["priority"])
    op.create_index("idx_plans_is_primary", "plans", ["is_primary"])
    op.create_index("idx_plans_user_active", "plans", ["user_id", "is_active"])

    # Set the first active plan for each user as primary (backfill)
    # This is a one-time migration to set primary plans for existing users
    op.execute("""
        WITH ranked_plans AS (
            SELECT id, user_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
            FROM plans
            WHERE is_active = true
        )
        UPDATE plans
        SET is_primary = true
        FROM ranked_plans
        WHERE plans.id = ranked_plans.id AND ranked_plans.rn = 1
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_plans_user_active", table_name="plans")
    op.drop_index("idx_plans_is_primary", table_name="plans")
    op.drop_index("idx_plans_priority", table_name="plans")

    # Drop columns
    op.drop_column("plans", "is_primary")
    op.drop_column("plans", "priority")

    # Drop enum type
    op.execute("DROP TYPE planpriority")
