"""merge card protocol and phase3 strategy outcomes

Revision ID: f18222fe1c3e
Revises: cp002b3c4d5e6, ps003_phase3_strategy_outcomes
Create Date: 2026-04-03 10:04:41.964409

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
revision: str = 'f18222fe1c3e'
down_revision: Union[str, None] = ('cp002b3c4d5e6', 'ps003_phase3_strategy_outcomes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
