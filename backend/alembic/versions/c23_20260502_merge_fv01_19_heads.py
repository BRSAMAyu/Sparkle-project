"""merge_fv01_19_heads

Revision ID: c23_20260502
Revises: c15_20260502, c16_20260502, c17_20260502, c18_20260502, c19_20260502, c20_20260502, c22_20260502, fv14_20260502, fv15_20260502, fv17_20260502
Create Date: 2026-05-02 14:55:27.817471

Architect closeout merge: consolidates 10 parallel FV migration heads into a
single chain. Pure reconciliation, no schema changes. The 10 parent
migrations remain individually reversible.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1 reverts to original 10 heads (multi-head state)"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "architect-closeout-2026-05-02"
#   ticket: "FV-CLOSEOUT-PHASE1"

# revision identifiers, used by Alembic.
revision: str = 'c23_20260502'
down_revision: Union[str, None] = ('c15_20260502', 'c16_20260502', 'c17_20260502', 'c18_20260502', 'c19_20260502', 'c20_20260502', 'c22_20260502', 'fv14_20260502', 'fv15_20260502', 'fv17_20260502')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
