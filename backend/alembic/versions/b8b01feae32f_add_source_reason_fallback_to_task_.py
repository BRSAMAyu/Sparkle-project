"""add_source_reason_fallback_to_task_documents

Revision ID: b8b01feae32f
Revises: c50dce18e33a
Create Date: 2026-04-26 21:46:49.137782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT column_name FROM information_schema.columns WHERE table_name='task_documents' AND column_name='source_reason';"
#   backfill_plan: "n/a"
#   owner: "knowledge-loop"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = 'b8b01feae32f'
down_revision: Union[str, None] = 'c50dce18e33a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("task_documents", sa.Column("source_reason", sa.String(500), nullable=True))
    op.add_column("task_documents", sa.Column("fallback_action", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("task_documents", "fallback_action")
    op.drop_column("task_documents", "source_reason")
