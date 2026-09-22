"""merge_rd01_intakeidx

Revision ID: 463923b1704e
Revises: rd01_20260922, intakeidx_20260922
Create Date: 2026-09-22 22:27:45.656335

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
revision: str = '463923b1704e'
down_revision: Union[str, None] = ('rd01_20260922', 'intakeidx_20260922')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
