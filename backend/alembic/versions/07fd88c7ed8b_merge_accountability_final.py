"""merge_accountability_final

Revision ID: 07fd88c7ed8b
Revises: 41f17d0a3c2b, d1e2f3a4b5c6
Create Date: 2026-03-18 17:45:15.323181

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
revision: str = '07fd88c7ed8b'
down_revision: Union[str, None] = ('41f17d0a3c2b', 'd1e2f3a4b5c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
