"""merge multiple heads

Revision ID: 2b9590b2b29d
Revises: aa12bb34cc56, add_subtasks, f9d4e5f6a7b8
Create Date: 2026-01-23 23:12:49.091264

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
revision: str = '2b9590b2b29d'
down_revision: Union[str, None] = ('aa12bb34cc56', 'add_subtasks', 'f9d4e5f6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
