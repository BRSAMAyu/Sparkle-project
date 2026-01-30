"""add_deleted_at_to_subtasks

Revision ID: 54475b98101e
Revises: f540d9f0ea99
Create Date: 2026-01-29 00:10:30.310805

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
revision: str = '54475b98101e'
down_revision: Union[str, None] = 'f540d9f0ea99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subtasks", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("idx_subtasks_deleted_at", "subtasks", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_subtasks_deleted_at", table_name="subtasks")
    op.drop_column("subtasks", "deleted_at")
