"""add privacy-preserving community aggregate tables

Revision ID: c16_20260502
Revises: c12_20260502
Create Date: 2026-05-02 15:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c16_20260502"
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
        "community_aggregate_signals",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("signal_id", sa.String(length=128), nullable=False),
        sa.Column("cohort_id", sa.String(length=128), nullable=False),
        sa.Column("cohort_key", sa.String(length=256), nullable=False),
        sa.Column("cohort_criteria", json_type, nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("stat_name", sa.String(length=128), nullable=False),
        sa.Column("cohort_size", sa.Integer(), nullable=False),
        sa.Column("min_cohort_size", sa.Integer(), nullable=False),
        sa.Column("privacy_tier", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("noise_std", sa.Float(), nullable=False),
        sa.Column("confidence_interval", json_type, nullable=False),
        sa.Column("pattern", json_type, nullable=False),
        sa.Column("observation", json_type, nullable=False),
        sa.Column("privacy_cost", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id", name="uq_community_aggregate_signal_id"),
    )
    for col in (
        "deleted_at",
        "signal_id",
        "cohort_id",
        "cohort_key",
        "signal_type",
        "stat_name",
        "privacy_tier",
        "status",
        "generated_at",
        "expires_at",
    ):
        op.create_index(op.f(f"ix_community_aggregate_signals_{col}"), "community_aggregate_signals", [col])
    op.create_index(
        "idx_community_aggregate_cohort_stat",
        "community_aggregate_signals",
        ["cohort_key", "stat_name", "generated_at"],
    )
    op.create_index(
        "idx_community_aggregate_status_generated",
        "community_aggregate_signals",
        ["status", "generated_at"],
    )

    op.create_table(
        "privacy_budget_ledger",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("query_type", sa.String(length=64), nullable=False),
        sa.Column("epsilon_spent", sa.Float(), nullable=False),
        sa.Column("max_epsilon", sa.Float(), nullable=False),
        sa.Column("remaining_epsilon", sa.Float(), nullable=False),
        sa.Column("window_key", sa.String(length=64), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("denial_reason", sa.String(length=128), nullable=False),
        sa.Column("spent_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("deleted_at", "subject_id", "subject_type", "query_type", "window_key", "allowed", "spent_at"):
        op.create_index(op.f(f"ix_privacy_budget_ledger_{col}"), "privacy_budget_ledger", [col])
    op.create_index(
        "idx_privacy_budget_subject_window",
        "privacy_budget_ledger",
        ["subject_id", "window_key", "query_type"],
    )
    op.create_index(
        "idx_privacy_budget_allowed_spent",
        "privacy_budget_ledger",
        ["allowed", "spent_at"],
    )

    op.add_column(
        "user_settings",
        sa.Column("community_intelligence_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "community_intelligence_enabled")

    op.drop_index("idx_privacy_budget_allowed_spent", table_name="privacy_budget_ledger")
    op.drop_index("idx_privacy_budget_subject_window", table_name="privacy_budget_ledger")
    for col in ("spent_at", "allowed", "window_key", "query_type", "subject_type", "subject_id", "deleted_at"):
        op.drop_index(op.f(f"ix_privacy_budget_ledger_{col}"), table_name="privacy_budget_ledger")
    op.drop_table("privacy_budget_ledger")

    op.drop_index("idx_community_aggregate_status_generated", table_name="community_aggregate_signals")
    op.drop_index("idx_community_aggregate_cohort_stat", table_name="community_aggregate_signals")
    for col in (
        "expires_at",
        "generated_at",
        "status",
        "privacy_tier",
        "stat_name",
        "signal_type",
        "cohort_key",
        "cohort_id",
        "signal_id",
        "deleted_at",
    ):
        op.drop_index(op.f(f"ix_community_aggregate_signals_{col}"), table_name="community_aggregate_signals")
    op.drop_table("community_aggregate_signals")
