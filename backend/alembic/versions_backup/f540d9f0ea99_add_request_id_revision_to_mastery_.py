"""add_request_id_revision_to_mastery_audit_log

Revision ID: f540d9f0ea99
Revises: p24_add_equipped_fields
Create Date: 2026-01-29 00:07:48.101644

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
revision: str = 'f540d9f0ea99'
down_revision: Union[str, None] = 'p24_add_equipped_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mastery_audit_log", sa.Column("request_id", sa.String(length=100), nullable=True))
    op.add_column("mastery_audit_log", sa.Column("revision", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("mastery_audit_log", "revision")
    op.drop_column("mastery_audit_log", "request_id")
