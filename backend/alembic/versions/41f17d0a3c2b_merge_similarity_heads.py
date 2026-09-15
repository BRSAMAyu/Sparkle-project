"""merge similarity heads

Revision ID: 41f17d0a3c2b
Revises: 669a4deadcdb, z1a2b3c4d5e6
Create Date: 2026-03-18 02:44:31.591535

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
revision: str = '41f17d0a3c2b'
down_revision: Union[str, None] = ('669a4deadcdb', 'z1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
