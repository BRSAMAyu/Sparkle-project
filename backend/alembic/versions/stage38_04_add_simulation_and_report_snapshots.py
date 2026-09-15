"""stage38 add simulation runs and report snapshots

Revision ID: stage38_04_add_simulation_and_report_snapshots
Revises: stage38_01_add_event_bus_dlq
Create Date: 2026-04-23 01:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "stage38_04_add_simulation_and_report_snapshots"
down_revision = "stage38_01_add_event_bus_dlq"
branch_labels = None
depends_on = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "simulation_runs",
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_key", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("insight_summary", sa.Text(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_runs_deleted_at", "simulation_runs", ["deleted_at"], unique=False)
    op.create_index("ix_simulation_runs_state", "simulation_runs", ["state"], unique=False)
    op.create_index("ix_simulation_runs_user_id", "simulation_runs", ["user_id"], unique=False)
    op.create_index("ix_simulation_runs_last_active_at", "simulation_runs", ["last_active_at"], unique=False)
    op.create_index("ix_simulation_runs_scenario_key", "simulation_runs", ["scenario_key"], unique=False)
    op.create_index("ix_simulation_runs_session_id", "simulation_runs", ["session_id"], unique=True)
    op.create_index(
        "ix_simulation_runs_user_last_active",
        "simulation_runs",
        ["user_id", "last_active_at"],
        unique=False,
    )

    op.create_table(
        "report_snapshots",
        sa.Column("report_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_type", sa.String(length=64), nullable=False),
        sa.Column("cache_version", sa.String(length=128), nullable=True),
        sa.Column("delivery_mode", sa.String(length=64), nullable=True),
        sa.Column("quality_mode", sa.String(length=64), nullable=True),
        sa.Column("trigger_source", sa.Text(), nullable=True),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_snapshots_deleted_at", "report_snapshots", ["deleted_at"], unique=False)
    op.create_index("ix_report_snapshots_user_id", "report_snapshots", ["user_id"], unique=False)
    op.create_index("ix_report_snapshots_snapshot_type", "report_snapshots", ["snapshot_type"], unique=False)
    op.create_index("ix_report_snapshots_cache_version", "report_snapshots", ["cache_version"], unique=False)
    op.create_index("ix_report_snapshots_delivery_mode", "report_snapshots", ["delivery_mode"], unique=False)
    op.create_index("ix_report_snapshots_report_id", "report_snapshots", ["report_id"], unique=True)
    op.create_index(
        "ix_report_snapshots_user_cache",
        "report_snapshots",
        ["user_id", "cache_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_snapshots_user_cache", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_report_id", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_delivery_mode", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_cache_version", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_snapshot_type", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_user_id", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_deleted_at", table_name="report_snapshots")
    op.drop_table("report_snapshots")

    op.drop_index("ix_simulation_runs_user_last_active", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_session_id", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_scenario_key", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_last_active_at", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_user_id", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_state", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_deleted_at", table_name="simulation_runs")
    op.drop_table("simulation_runs")
