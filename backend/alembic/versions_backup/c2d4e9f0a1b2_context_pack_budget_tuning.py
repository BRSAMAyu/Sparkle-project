"""context_pack_budget_tuning

Revision ID: c2d4e9f0a1b2
Revises: b7c1d8e5f3a7
Create Date: 2026-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "c2d4e9f0a1b2"
down_revision: Union[str, None] = "b7c1d8e5f3a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "context_pack_runs",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("intent", sa.String(length=30), nullable=False),
        sa.Column("budgets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("memory_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_score_avg", sa.Float(), nullable=True),
        sa.Column("response_id", app.models.base.GUID(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("trace_id", sa.String(length=100), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_context_pack_runs_user_created",
        "context_pack_runs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_context_pack_runs_intent",
        "context_pack_runs",
        ["intent"],
        unique=False,
    )
    op.create_index(
        "ix_context_pack_runs_deleted_at",
        "context_pack_runs",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "context_budget_profiles",
        sa.Column("intent", sa.String(length=30), nullable=False),
        sa.Column("bucket", sa.String(length=30), nullable=False),
        sa.Column("multiplier", sa.Float(), nullable=False),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent", "bucket", name="uq_context_budget_profiles_intent_bucket"),
    )
    op.create_index(
        "idx_context_budget_profiles_intent",
        "context_budget_profiles",
        ["intent"],
        unique=False,
    )
    op.create_index(
        "ix_context_budget_profiles_deleted_at",
        "context_budget_profiles",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "context_pack_feedback",
        sa.Column("pack_run_id", app.models.base.GUID(), nullable=False),
        sa.Column("feedback_type", sa.String(length=20), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_context_pack_feedback_pack_run_id",
        "context_pack_feedback",
        ["pack_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_context_pack_feedback_deleted_at",
        "context_pack_feedback",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_context_pack_feedback_deleted_at", table_name="context_pack_feedback")
    op.drop_index("ix_context_pack_feedback_pack_run_id", table_name="context_pack_feedback")
    op.drop_table("context_pack_feedback")

    op.drop_index("ix_context_budget_profiles_deleted_at", table_name="context_budget_profiles")
    op.drop_index("idx_context_budget_profiles_intent", table_name="context_budget_profiles")
    op.drop_table("context_budget_profiles")

    op.drop_index("ix_context_pack_runs_deleted_at", table_name="context_pack_runs")
    op.drop_index("idx_context_pack_runs_intent", table_name="context_pack_runs")
    op.drop_index("idx_context_pack_runs_user_created", table_name="context_pack_runs")
    op.drop_table("context_pack_runs")
