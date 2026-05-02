"""add privacy preserving community aggregates

Revision ID: c16_20260502
Revises: c12_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
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
        sa.Column("cohort_key", sa.String(length=160), nullable=False),
        sa.Column("cohort_type", sa.String(length=64), nullable=False),
        sa.Column("cohort_criteria", json_type, nullable=False),
        sa.Column("stat_name", sa.String(length=96), nullable=False),
        sa.Column("privacy_tier", sa.String(length=32), nullable=False),
        sa.Column("cohort_size", sa.Integer(), nullable=False),
        sa.Column("min_cohort_size", sa.Integer(), nullable=False),
        sa.Column("noised_value", sa.Float(), nullable=True),
        sa.Column("noise_std", sa.Float(), nullable=False),
        sa.Column("confidence_interval", json_type, nullable=False),
        sa.Column("pattern", json_type, nullable=False),
        sa.Column("directive_payload", json_type, nullable=False),
        sa.Column("source_window_start", sa.DateTime(), nullable=True),
        sa.Column("source_window_end", sa.DateTime(), nullable=True),
        sa.Column("epsilon_spent", sa.Float(), nullable=False),
        sa.Column("generated_by", sa.String(length=64), nullable=False),
        sa.Column("policy_bias_only", sa.Boolean(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_aggregate_signals_deleted_at"), "community_aggregate_signals", ["deleted_at"])
    op.create_index(op.f("ix_community_aggregate_signals_cohort_key"), "community_aggregate_signals", ["cohort_key"])
    op.create_index(op.f("ix_community_aggregate_signals_cohort_type"), "community_aggregate_signals", ["cohort_type"])
    op.create_index(op.f("ix_community_aggregate_signals_stat_name"), "community_aggregate_signals", ["stat_name"])
    op.create_index(op.f("ix_community_aggregate_signals_privacy_tier"), "community_aggregate_signals", ["privacy_tier"])
    op.create_index(op.f("ix_community_aggregate_signals_generated_at"), "community_aggregate_signals", ["generated_at"])
    op.create_index(
        "idx_community_aggregate_latest",
        "community_aggregate_signals",
        ["cohort_type", "stat_name", "generated_at"],
    )

    op.create_table(
        "privacy_budget_ledger",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("requester_user_id", sa.String(length=128), nullable=True),
        sa.Column("budget_subject", sa.String(length=160), nullable=False),
        sa.Column("query_type", sa.String(length=64), nullable=False),
        sa.Column("epsilon_spent", sa.Float(), nullable=False),
        sa.Column("epsilon_remaining", sa.Float(), nullable=False),
        sa.Column("max_epsilon", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("denial_reason", sa.String(length=160), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_privacy_budget_ledger_deleted_at"), "privacy_budget_ledger", ["deleted_at"])
    op.create_index(op.f("ix_privacy_budget_ledger_requester_user_id"), "privacy_budget_ledger", ["requester_user_id"])
    op.create_index(op.f("ix_privacy_budget_ledger_budget_subject"), "privacy_budget_ledger", ["budget_subject"])
    op.create_index(op.f("ix_privacy_budget_ledger_query_type"), "privacy_budget_ledger", ["query_type"])
    op.create_index(op.f("ix_privacy_budget_ledger_status"), "privacy_budget_ledger", ["status"])
    op.create_index(
        "idx_privacy_budget_subject_status",
        "privacy_budget_ledger",
        ["budget_subject", "status", "created_at"],
    )

    op.add_column(
        "user_settings",
        sa.Column("community_intelligence_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "community_intelligence_enabled")
    op.drop_index("idx_privacy_budget_subject_status", table_name="privacy_budget_ledger")
    op.drop_index(op.f("ix_privacy_budget_ledger_status"), table_name="privacy_budget_ledger")
    op.drop_index(op.f("ix_privacy_budget_ledger_query_type"), table_name="privacy_budget_ledger")
    op.drop_index(op.f("ix_privacy_budget_ledger_budget_subject"), table_name="privacy_budget_ledger")
    op.drop_index(op.f("ix_privacy_budget_ledger_requester_user_id"), table_name="privacy_budget_ledger")
    op.drop_index(op.f("ix_privacy_budget_ledger_deleted_at"), table_name="privacy_budget_ledger")
    op.drop_table("privacy_budget_ledger")

    op.drop_index("idx_community_aggregate_latest", table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_generated_at"), table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_privacy_tier"), table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_stat_name"), table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_cohort_type"), table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_cohort_key"), table_name="community_aggregate_signals")
    op.drop_index(op.f("ix_community_aggregate_signals_deleted_at"), table_name="community_aggregate_signals")
    op.drop_table("community_aggregate_signals")
