"""add_deleted_at_to_task_feedbacks

Revision ID: 806694d6553f
Revises: 54475b98101e
Create Date: 2026-01-29 00:11:21.939776

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
revision: str = '806694d6553f'
down_revision: Union[str, None] = '54475b98101e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("task_feedbacks", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("idx_task_feedbacks_deleted_at", "task_feedbacks", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_task_feedbacks_deleted_at", table_name="task_feedbacks")
    op.drop_column("task_feedbacks", "deleted_at")
