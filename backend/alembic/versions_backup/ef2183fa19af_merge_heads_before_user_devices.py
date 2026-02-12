"""merge_heads_before_user_devices

Revision ID: ef2183fa19af
Revises: 68b717fe8fc4, b2c3d4e5f6a7
Create Date: 2026-01-24 02:26:11.451077

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
revision: str = 'ef2183fa19af'
down_revision: Union[str, None] = ('68b717fe8fc4', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
