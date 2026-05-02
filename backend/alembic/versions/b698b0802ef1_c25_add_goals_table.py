"""c25_add_goals_table

Revision ID: b698b0802ef1
Revises: c24_20260502
Create Date: 2026-05-02 16:29:15.121764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1 FROM goals LIMIT 1;"
#   backfill_plan: "n/a"
#   owner: "architect"
#   ticket: "P0-7"

revision: str = 'b698b0802ef1'
down_revision: Union[str, None] = 'c24_20260502'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("goal_type", sa.String(64), nullable=False, server_default="general"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("mastery", sa.Float(), server_default="0.0"),
        sa.Column("progress", sa.Float(), server_default="0.0"),
        sa.Column("priority", sa.String(16), server_default="normal"),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("minimum_acceptance_criteria", JSONB(), nullable=True),
        sa.Column("domain_pack_id", sa.String(64), nullable=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=True),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("source_metadata", JSONB(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_goals_user_status", "goals", ["user_id", "status"])
    op.create_index("idx_goals_user_type_status", "goals", ["user_id", "goal_type", "status"])
    op.create_index("idx_goals_user_primary", "goals", ["user_id", "is_primary"])
    op.create_index("idx_goals_target_date", "goals", ["target_date"])


def downgrade() -> None:
    op.drop_index("idx_goals_target_date")
    op.drop_index("idx_goals_user_primary")
    op.drop_index("idx_goals_user_type_status")
    op.drop_index("idx_goals_user_status")
    op.drop_table("goals")
