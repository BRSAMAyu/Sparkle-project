"""merge_final_heads_20260516

Revision ID: 0150e391736a
Revises: a9af85273edc, fix_goals_plan_fk_20260510
Create Date: 2026-05-16 17:15:16.007129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible|forward_only|destructive
#   rollback_plan: "alembic downgrade -1" | "forward_fix_only"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = '0150e391736a'
down_revision: Union[str, None] = ('a9af85273edc', 'fix_goals_plan_fk_20260510')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
