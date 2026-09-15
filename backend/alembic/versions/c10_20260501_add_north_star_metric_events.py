"""add north star metric events

Revision ID: c10_20260501
Revises: b8b01feae32f
Create Date: 2026-05-01 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c10_20260501"
down_revision: str | None = "b8b01feae32f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "north_star_metric_events",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("plan_id", app.models.base.GUID(), nullable=True),
        sa.Column("task_id", app.models.base.GUID(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("numerator", sa.Integer(), nullable=True),
        sa.Column("denominator", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("payload", _json_type(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_north_star_metric_events_event_key"),
    )
    op.create_index(op.f("ix_north_star_metric_events_deleted_at"), "north_star_metric_events", ["deleted_at"])
    op.create_index(op.f("ix_north_star_metric_events_event_key"), "north_star_metric_events", ["event_key"], unique=True)
    op.create_index(op.f("ix_north_star_metric_events_event_type"), "north_star_metric_events", ["event_type"])
    op.create_index(op.f("ix_north_star_metric_events_metric_date"), "north_star_metric_events", ["metric_date"])
    op.create_index(op.f("ix_north_star_metric_events_occurred_at"), "north_star_metric_events", ["occurred_at"])
    op.create_index(op.f("ix_north_star_metric_events_plan_id"), "north_star_metric_events", ["plan_id"])
    op.create_index(op.f("ix_north_star_metric_events_source"), "north_star_metric_events", ["source"])
    op.create_index(op.f("ix_north_star_metric_events_task_id"), "north_star_metric_events", ["task_id"])
    op.create_index(op.f("ix_north_star_metric_events_user_id"), "north_star_metric_events", ["user_id"])
    op.create_index("idx_north_star_metric_events_plan_type", "north_star_metric_events", ["plan_id", "event_type"])
    op.create_index("idx_north_star_metric_events_type_date", "north_star_metric_events", ["event_type", "metric_date"])
    op.create_index("idx_north_star_metric_events_user_date", "north_star_metric_events", ["user_id", "metric_date"])


def downgrade() -> None:
    op.drop_index("idx_north_star_metric_events_user_date", table_name="north_star_metric_events")
    op.drop_index("idx_north_star_metric_events_type_date", table_name="north_star_metric_events")
    op.drop_index("idx_north_star_metric_events_plan_type", table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_user_id"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_task_id"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_source"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_plan_id"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_occurred_at"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_metric_date"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_event_type"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_event_key"), table_name="north_star_metric_events")
    op.drop_index(op.f("ix_north_star_metric_events_deleted_at"), table_name="north_star_metric_events")
    op.drop_table("north_star_metric_events")
