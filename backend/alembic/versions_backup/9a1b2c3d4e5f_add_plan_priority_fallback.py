"""add_plan_priority_and_is_primary_fallback

Revision ID: 9a1b2c3d4e5f
Revises: 806694d6553f
Create Date: 2026-01-29 00:00:00.000000

Fallback migration to add plan priority/is_primary when earlier branch
was not applied to the current database.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, None] = "806694d6553f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type if missing
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'planpriority') THEN
            CREATE TYPE planpriority AS ENUM ('critical', 'high', 'normal', 'low');
        END IF;
    END $$;
    """)

    # Add columns if missing
    op.execute("ALTER TABLE plans ADD COLUMN IF NOT EXISTS priority planpriority NOT NULL DEFAULT 'normal';")
    op.execute("ALTER TABLE plans ADD COLUMN IF NOT EXISTS is_primary boolean NOT NULL DEFAULT false;")

    # Indexes (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS idx_plans_priority ON plans (priority);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plans_is_primary ON plans (is_primary);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_plans_user_active ON plans (user_id, is_active);")

    # Backfill primary plan per user if none marked
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
    op.execute("DROP INDEX IF EXISTS idx_plans_user_active;")
    op.execute("DROP INDEX IF EXISTS idx_plans_is_primary;")
    op.execute("DROP INDEX IF EXISTS idx_plans_priority;")

    op.execute("ALTER TABLE plans DROP COLUMN IF EXISTS is_primary;")
    op.execute("ALTER TABLE plans DROP COLUMN IF EXISTS priority;")

    op.execute("DO $$ BEGIN DROP TYPE IF EXISTS planpriority; END $$;")
