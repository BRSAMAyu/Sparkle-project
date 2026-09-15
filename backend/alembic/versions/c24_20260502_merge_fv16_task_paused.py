"""merge_fv_16_task_paused

Revision ID: c24_20260502
Revises: c23_20260502, c21_20260502
Create Date: 2026-05-02 15:07:45.222514

Architect closeout: merges FV-16 paused-task migration (c21) into the
consolidated chain after merging the FV-16 branch.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1 reverts to multi-head state"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "architect-closeout-2026-05-02"
#   ticket: "FV-CLOSEOUT-PHASE1"

# revision identifiers, used by Alembic.
revision: str = 'c24_20260502'
down_revision: Union[str, None] = ('c23_20260502', 'c21_20260502')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
