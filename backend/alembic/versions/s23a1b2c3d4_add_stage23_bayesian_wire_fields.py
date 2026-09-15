"""add stage23 bayesian wire fields

Revision ID: s23a1b2c3d4
Revises: s21a1b2c3d4
Create Date: 2026-04-21 23:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "s23a1b2c3d4"
down_revision = "s21a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("routing_decision_log", sa.Column("source_state_v2", sa.JSON(), nullable=True))
    op.add_column("routing_decision_log", sa.Column("source_state_v2_key", sa.String(length=255), nullable=True))
    op.add_column("routing_decision_log", sa.Column("outcome", sa.String(length=32), nullable=True))
    op.add_column("routing_decision_log", sa.Column("outcome_timestamp", sa.DateTime(), nullable=True))
    op.create_index(
        "idx_routing_decision_log_source_state_v2_key",
        "routing_decision_log",
        ["source_state_v2_key"],
        unique=False,
    )
    op.create_index(
        "idx_routing_decision_log_user_outcome_v2",
        "routing_decision_log",
        ["user_id", "outcome_timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_routing_decision_log_user_outcome_v2", table_name="routing_decision_log")
    op.drop_index("idx_routing_decision_log_source_state_v2_key", table_name="routing_decision_log")
    op.drop_column("routing_decision_log", "outcome_timestamp")
    op.drop_column("routing_decision_log", "outcome")
    op.drop_column("routing_decision_log", "source_state_v2_key")
    op.drop_column("routing_decision_log", "source_state_v2")
