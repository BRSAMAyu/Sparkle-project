"""merge_all_heads

Revision ID: c66d70d3967a
Revises: a3c5d7e9f1b2, b2c3d4e5f6g7, d1f2a3b4c5e6
Create Date: 2026-03-16 19:50:15.731707

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
revision: str = 'c66d70d3967a'
down_revision: Union[str, None] = ('a3c5d7e9f1b2', 'b2c3d4e5f6g7', 'd1f2a3b4c5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
