"""add stage31 idiographic tables

Revision ID: s31a1b2c3d4
Revises: s295a1b2c3d4
Create Date: 2026-04-22 16:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s31a1b2c3d4"
down_revision: Union[str, None] = "s295a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.JSON:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "daily_behavior_vector",
        sa.Column("user_id", _uuid_type(), nullable=False),
        sa.Column("vector_date", sa.Date(), nullable=False),
        sa.Column("dims_payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage30_dim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("silent_window_cut", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_daily_behavior_vector_user_date",
        "daily_behavior_vector",
        ["user_id", "vector_date"],
        unique=True,
    )
    op.create_index(
        "idx_daily_behavior_vector_user_active",
        "daily_behavior_vector",
        ["user_id", "active_event_count"],
        unique=False,
    )

    op.create_table(
        "idiographic_associations",
        sa.Column("user_id", _uuid_type(), nullable=False),
        sa.Column("dim_a", sa.String(length=64), nullable=False),
        sa.Column("dim_b", sa.String(length=64), nullable=False),
        sa.Column("dim_pair", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False, server_default="positive_sync"),
        sa.Column("correlation", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p_value_raw", sa.Float(), nullable=False, server_default="1"),
        sa.Column("p_value_bh", sa.Float(), nullable=False, server_default="1"),
        sa.Column("sample_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank_pair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("density_insufficient", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("path_mode", sa.String(length=16), nullable=False, server_default="B"),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("disclaimer_text", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("rendered_text", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("user_disconfirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_disconfirmed_until", sa.DateTime(), nullable=True),
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_idiographic_associations_user_pair",
        "idiographic_associations",
        ["user_id", "dim_pair"],
        unique=True,
    )
    op.create_index(
        "idx_idiographic_associations_user_visible",
        "idiographic_associations",
        ["user_id", "visible"],
        unique=False,
    )

    op.create_table(
        "idiographic_changepoints",
        sa.Column("user_id", _uuid_type(), nullable=False),
        sa.Column("dim", sa.String(length=64), nullable=False),
        sa.Column("change_date", sa.Date(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("path_mode", sa.String(length=16), nullable=False, server_default="B"),
        sa.Column("rendered_text", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_idiographic_changepoints_user_dim_date",
        "idiographic_changepoints",
        ["user_id", "dim", "change_date"],
        unique=True,
    )

    op.add_column(
        "routing_decision_log",
        sa.Column("idiographic_associations_injected", _json_type(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("routing_decision_log", "idiographic_associations_injected")
    op.drop_index(
        "idx_idiographic_changepoints_user_dim_date",
        table_name="idiographic_changepoints",
    )
    op.drop_table("idiographic_changepoints")
    op.drop_index(
        "idx_idiographic_associations_user_visible",
        table_name="idiographic_associations",
    )
    op.drop_index(
        "idx_idiographic_associations_user_pair",
        table_name="idiographic_associations",
    )
    op.drop_table("idiographic_associations")
    op.drop_index(
        "idx_daily_behavior_vector_user_active",
        table_name="daily_behavior_vector",
    )
    op.drop_index(
        "idx_daily_behavior_vector_user_date",
        table_name="daily_behavior_vector",
    )
    op.drop_table("daily_behavior_vector")
