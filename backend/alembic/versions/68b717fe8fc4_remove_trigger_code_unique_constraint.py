"""remove_trigger_code_unique_constraint

Revision ID: 68b717fe8fc4
Revises: a1b2c3d4e5f6
Create Date: 2026-01-23 23:38:33.872432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "achievement-system"

# revision identifiers, used by Alembic.
revision: str = '68b717fe8fc4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique constraint on trigger_code since multiple achievements
    # can legitimately have the same trigger with different configurations
    # (e.g., STREAK_DAYS for different streak lengths)
    op.drop_index('ix_achievements_trigger_code', table_name='achievements')


def downgrade() -> None:
    # Recreate the unique constraint if rolling back
    op.create_index('ix_achievements_trigger_code', 'achievements', ['trigger_code'], unique=True)
