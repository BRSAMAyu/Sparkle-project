"""merge_pii_and_goal_id_heads

Revision ID: ac07dc579128
Revises: 02a063d173ec, p001_20260507
Create Date: 2026-05-08 00:48:11.627996

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
revision: str = 'ac07dc579128'
down_revision: Union[str, None] = ('02a063d173ec', 'p001_20260507')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
