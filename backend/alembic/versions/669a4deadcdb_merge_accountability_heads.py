"""merge_accountability_heads

Revision ID: 669a4deadcdb
Revises: c66d70d3967a, c8e4f2a3b1d6
Create Date: 2026-03-17 23:44:51.190549

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
revision: str = '669a4deadcdb'
down_revision: Union[str, None] = ('c66d70d3967a', 'c8e4f2a3b1d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
