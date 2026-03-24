"""merge heads

Revision ID: 0896bb7f89b3
Revises: a2d4e6f8b1c3, a6e9c1f4d2b3
Create Date: 2026-03-15 13:54:46.034433

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
revision: str = '0896bb7f89b3'
down_revision: Union[str, None] = ('a2d4e6f8b1c3', 'a6e9c1f4d2b3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
