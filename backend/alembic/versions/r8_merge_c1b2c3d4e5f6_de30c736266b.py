"""merge unmerged heads: c1b2c3d4e5f6 and de30c736266b

Revision ID: r8_merge_c1b2c3d4e5f6_de30c736266b
Revises: c1b2c3d4e5f6, de30c736266b
Create Date: 2026-05-06 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a — merge only, no schema changes"
#   owner: "qa-round8"
#   ticket: "QA-R8-BUG-11"

revision: str = 'r8_merge_c1b2c3d4e5f6_de30c736266b'
down_revision: Union[str, None] = ('c1b2c3d4e5f6', 'de30c736266b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
