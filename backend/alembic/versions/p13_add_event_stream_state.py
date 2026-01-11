"""add event stream and user state snapshot

Revision ID: p13_add_event_stream_state
Revises: p12_add_interventions_phase0
Create Date: 2026-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID


revision = "p13_add_event_stream_state"
down_revision = "p12_add_interventions_phase0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tracking_events",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("ts_ms", sa.BigInteger(), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id")
    )
    op.create_index("idx_tracking_events_event_id", "tracking_events", ["event_id"], unique=True)
    op.create_index("idx_tracking_events_user", "tracking_events", ["user_id"], unique=False)
    op.create_index("idx_tracking_events_type", "tracking_events", ["event_type"], unique=False)
    op.create_index("idx_tracking_events_ts", "tracking_events", ["ts_ms"], unique=False)

    op.create_table(
        "user_state_snapshots",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("cognitive_load", sa.Float(), nullable=False),
        sa.Column("interruptibility", sa.Float(), nullable=False),
        sa.Column("strain_index", sa.Float(), nullable=False),
        sa.Column("focus_mode", sa.Boolean(), nullable=False),
        sa.Column("sprint_mode", sa.Boolean(), nullable=False),
        sa.Column("knowledge_state", sa.JSON(), nullable=True),
        sa.Column("time_context", sa.JSON(), nullable=True),
        sa.Column("derived_event_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("idx_user_state_user", "user_state_snapshots", ["user_id"], unique=False)
    op.create_index("idx_user_state_snapshot", "user_state_snapshots", ["snapshot_at"], unique=False)


def downgrade():
    op.drop_index("idx_user_state_snapshot", table_name="user_state_snapshots")
    op.drop_index("idx_user_state_user", table_name="user_state_snapshots")
    op.drop_table("user_state_snapshots")

    op.drop_index("idx_tracking_events_ts", table_name="tracking_events")
    op.drop_index("idx_tracking_events_type", table_name="tracking_events")
    op.drop_index("idx_tracking_events_user", table_name="tracking_events")
    op.drop_index("idx_tracking_events_event_id", table_name="tracking_events")
    op.drop_table("tracking_events")
