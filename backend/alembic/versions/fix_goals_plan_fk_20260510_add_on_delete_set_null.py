"""fix circular FK between goals and plans

Revision ID: fix_goals_plan_fk_20260510
Revises: comp_idx_20260510
Create Date: 2026-05-10
"""

from alembic import op

revision = 'fix_goals_plan_fk_20260510'
down_revision = 'comp_idx_20260510'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # goals.plan_id REFERENCES plans(id) has no ON DELETE clause.
    # plans.goal_id REFERENCES goals(id) ON DELETE SET NULL.
    # This creates a circular FK where a plan referencing a goal referencing that
    # same plan cannot be deleted. Fix: add ON DELETE SET NULL to goals.plan_id_fkey.
    op.execute("""
        ALTER TABLE goals
        DROP CONSTRAINT IF EXISTS goals_plan_id_fkey,
        ADD CONSTRAINT goals_plan_id_fkey
        FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE goals
        DROP CONSTRAINT IF EXISTS goals_plan_id_fkey,
        ADD CONSTRAINT goals_plan_id_fkey
        FOREIGN KEY (plan_id) REFERENCES plans(id);
    """)
