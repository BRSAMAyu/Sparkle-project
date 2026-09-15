"""merge_galaxy_doc_community

Revision ID: c50dce18e33a
Revises: cs001, merge_galaxy_doc_20260426
Create Date: 2026-04-26 21:37:58.217748

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
revision: str = 'c50dce18e33a'
down_revision: Union[str, None] = ('cs001', 'merge_galaxy_doc_20260426')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
