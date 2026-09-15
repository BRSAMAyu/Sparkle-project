"""add_estimated_minutes_and_guide_content_to_subtasks

Revision ID: a1b2c3d4e5f6
Revises: 43ff976a8b29
Create Date: 2026-03-15 15:00:00.000000

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
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "43ff976a8b29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subtasks", sa.Column("estimated_minutes", sa.Integer(), nullable=True, server_default="25"))
    op.add_column("subtasks", sa.Column("guide_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("subtasks", "guide_content")
    op.drop_column("subtasks", "estimated_minutes")
