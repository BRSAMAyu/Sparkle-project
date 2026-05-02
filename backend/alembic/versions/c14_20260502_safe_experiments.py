"""add safe experiment production tables

Revision ID: c14_20260502
Revises: c12_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base


revision: str = "c14_20260502"
down_revision: Union[str, None] = "c12_20260502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "safe_experiments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("experiment_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("eligible_context", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("excluded_context", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("policies", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("assignment_mode", sa.String(length=32), nullable=False, server_default="shadow"),
        sa.Column("reward_model", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("guardrails", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("min_episodes", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("min_distinct_users", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("evidence_grade_required", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("current_episodes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_users", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("outcome_history", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rollback_version", sa.String(length=80), nullable=True),
        sa.Column("previous_versions", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("kill_switch_key", sa.String(length=120), nullable=False),
        sa.Column("incident_trace", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("promotion_candidate", json_type, nullable=True),
        sa.Column("created_by", app.models.base.GUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        sa.Column("concluded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_key"),
    )
    op.create_index("ix_safe_experiments_experiment_key", "safe_experiments", ["experiment_key"], unique=True)
    op.create_index("ix_safe_experiments_status", "safe_experiments", ["status"], unique=False)
    op.create_index("ix_safe_experiments_domain", "safe_experiments", ["domain"], unique=False)
    op.create_index("ix_safe_experiments_kill_switch_key", "safe_experiments", ["kill_switch_key"], unique=False)
    op.create_index("ix_safe_experiments_created_by", "safe_experiments", ["created_by"], unique=False)
    op.create_index("idx_safe_experiments_status_domain", "safe_experiments", ["status", "domain"], unique=False)

    op.create_table(
        "safe_experiment_episodes",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("experiment_id", app.models.base.GUID(), nullable=False),
        sa.Column("experiment_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=True),
        sa.Column("context_signature", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("candidate_actions", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("selected_action", sa.String(length=160), nullable=False),
        sa.Column("selection_reason", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("assignment_mode", sa.String(length=32), nullable=False, server_default="shadow"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="low"),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("outcome_vector", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("guardrail_result", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("incident_trace", json_type, nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["safe_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safe_experiment_episodes_experiment_id", "safe_experiment_episodes", ["experiment_id"])
    op.create_index("ix_safe_experiment_episodes_experiment_key", "safe_experiment_episodes", ["experiment_key"])
    op.create_index("ix_safe_experiment_episodes_user_id", "safe_experiment_episodes", ["user_id"])
    op.create_index(
        "idx_safe_experiment_episodes_exp_created",
        "safe_experiment_episodes",
        ["experiment_id", "created_at"],
    )

    op.add_column(
        "user_settings",
        sa.Column("safe_experiments_opt_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "safe_experiments_opt_out")
    op.drop_index("idx_safe_experiment_episodes_exp_created", table_name="safe_experiment_episodes")
    op.drop_index("ix_safe_experiment_episodes_user_id", table_name="safe_experiment_episodes")
    op.drop_index("ix_safe_experiment_episodes_experiment_key", table_name="safe_experiment_episodes")
    op.drop_index("ix_safe_experiment_episodes_experiment_id", table_name="safe_experiment_episodes")
    op.drop_table("safe_experiment_episodes")
    op.drop_index("idx_safe_experiments_status_domain", table_name="safe_experiments")
    op.drop_index("ix_safe_experiments_created_by", table_name="safe_experiments")
    op.drop_index("ix_safe_experiments_kill_switch_key", table_name="safe_experiments")
    op.drop_index("ix_safe_experiments_domain", table_name="safe_experiments")
    op.drop_index("ix_safe_experiments_status", table_name="safe_experiments")
    op.drop_index("ix_safe_experiments_experiment_key", table_name="safe_experiments")
    op.drop_table("safe_experiments")
