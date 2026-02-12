"""final_master_branch_merge

Revision ID: ef23a457487c
Revises: 1b26570b5c19, 9a1b2c3d4e5f
Create Date: 2026-01-30 06:17:57.262761

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
revision: str = 'ef23a457487c'
down_revision: Union[str, None] = ('1b26570b5c19', '9a1b2c3d4e5f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
