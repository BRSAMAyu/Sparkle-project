"""merge_c1b2c3d4_de30c736266b_20260516

Revision ID: a9af85273edc
Revises: c1b2c3d4e5f6, de30c736266b
Create Date: 2026-05-16 17:14:53.236363

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
revision: str = 'a9af85273edc'
down_revision: Union[str, None] = ('c1b2c3d4e5f6', 'de30c736266b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
