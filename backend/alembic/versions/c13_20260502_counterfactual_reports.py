"""add counterfactual evaluation reports

Revision ID: c13_20260502
Revises: c12_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c13_20260502"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "counterfactual_evaluation_reports",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("context_signature", json_type, nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("policy_a", sa.String(length=128), nullable=False),
        sa.Column("policy_b", sa.String(length=128), nullable=False),
        sa.Column("estimate", json_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_grade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("replaced_by_id", app.models.base.GUID(), nullable=True),
        sa.Column("promotion_candidate", json_type, nullable=False),
        sa.Column("promotion_status", sa.String(length=32), nullable=False, server_default="not_ready"),
        sa.Column("iron_law_compliance", json_type, nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["counterfactual_evaluation_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    table = "counterfactual_evaluation_reports"
    op.create_index(op.f("ix_counterfactual_evaluation_reports_deleted_at"), table, ["deleted_at"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_user_id"), table, ["user_id"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_context_hash"), table, ["context_hash"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_policy_a"), table, ["policy_a"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_policy_b"), table, ["policy_b"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_evidence_grade"), table, ["evidence_grade"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_generated_at"), table, ["generated_at"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_replaced_by_id"), table, ["replaced_by_id"])
    op.create_index(op.f("ix_counterfactual_evaluation_reports_promotion_status"), table, ["promotion_status"])
    op.create_index(
        "idx_counterfactual_report_user_context_policies",
        "counterfactual_evaluation_reports",
        ["user_id", "context_hash", "policy_a", "policy_b", "generated_at"],
    )
    op.create_index(
        "idx_counterfactual_report_pending",
        "counterfactual_evaluation_reports",
        ["promotion_status", "generated_at"],
    )


def downgrade() -> None:
    table = "counterfactual_evaluation_reports"
    op.drop_index("idx_counterfactual_report_pending", table_name=table)
    op.drop_index("idx_counterfactual_report_user_context_policies", table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_promotion_status"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_replaced_by_id"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_generated_at"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_evidence_grade"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_policy_b"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_policy_a"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_context_hash"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_user_id"), table_name=table)
    op.drop_index(op.f("ix_counterfactual_evaluation_reports_deleted_at"), table_name=table)
    op.drop_table(table)
