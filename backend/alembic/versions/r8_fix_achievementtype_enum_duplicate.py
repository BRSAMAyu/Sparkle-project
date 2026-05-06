"""fix achievementtype ENUM duplicate PLANNING/planning values

Revision ID: r8_fix_achievementtype_enum_duplicate
Revises: r8_merge_c1b2c3d4e5f6_de30c736266b
Create Date: 2026-05-06 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT unnest(enum_range(NULL::achievementtype));"
#   backfill_plan: "UPDATE achievements SET type = 'planning' WHERE type = 'PLANNING'"
#   owner: "qa-round8"
#   ticket: "QA-R8-BUG-13"

revision: str = 'r8_fix_achievementtype_enum_duplicate'
down_revision: Union[str, None] = 'r8_merge_c1b2c3d4e5f6_de30c736266b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalize uppercase PLANNING rows → lowercase planning before removing the duplicate
    op.execute("UPDATE achievements SET type = 'planning' WHERE type = 'PLANNING'")

    # PostgreSQL does not support DROP VALUE from an ENUM directly.
    # Strategy: rename old type → create new type without duplicate → cast → drop old.
    op.execute("ALTER TYPE achievementtype RENAME TO achievementtype_old")
    op.execute("""
        CREATE TYPE achievementtype AS ENUM (
            'MILESTONE',
            'STREAK',
            'MASTERY',
            'TASK_COMPLETE',
            'HIDDEN',
            'SOCIAL',
            'CONTRACT',
            'STUDY_TIME',
            'NODE_EXPLORE',
            'SPRINT',
            'planning'
        )
    """)
    op.execute("""
        ALTER TABLE achievements
            ALTER COLUMN type TYPE achievementtype
            USING type::text::achievementtype
    """)
    op.execute("DROP TYPE achievementtype_old")


def downgrade() -> None:
    # Re-add the PLANNING uppercase variant (no data loss since we only removed it)
    op.execute("ALTER TYPE achievementtype ADD VALUE IF NOT EXISTS 'PLANNING'")
