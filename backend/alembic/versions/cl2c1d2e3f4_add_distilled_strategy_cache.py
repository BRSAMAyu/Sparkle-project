"""add distilled strategy cache

Revision ID: cl2c1d2e3f4
Revises: a8b7c6d5e4f3
Create Date: 2026-04-20 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cl2c1d2e3f4"
down_revision = "a8b7c6d5e4f3"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON() if op.get_bind().dialect.name == "sqlite" else postgresql.JSONB(astext_type=sa.Text())


def _uuid_type() -> sa.types.TypeEngine:
    return sa.String(length=36) if op.get_bind().dialect.name == "sqlite" else postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    json_type = _json_type()
    uuid_type = _uuid_type()

    op.create_table(
        "distilled_strategy_cache",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("applicability_scope", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("shareability", sa.String(length=64), nullable=False),
        sa.Column("source_trajectory_type", sa.String(length=128), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_distilled_strategy_cache_status", "distilled_strategy_cache", ["status"], unique=False)
    op.create_index("ix_distilled_strategy_cache_shareability", "distilled_strategy_cache", ["shareability"], unique=False)
    op.create_index(
        "ix_distilled_strategy_cache_source_trajectory_type",
        "distilled_strategy_cache",
        ["source_trajectory_type"],
        unique=False,
    )
    op.create_index("ix_distilled_strategy_cache_updated_at", "distilled_strategy_cache", ["updated_at"], unique=False)
    op.create_index(
        "ix_distilled_strategy_cache_status_source",
        "distilled_strategy_cache",
        ["status", "source_trajectory_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_distilled_strategy_cache_status_source", table_name="distilled_strategy_cache")
    op.drop_index("ix_distilled_strategy_cache_updated_at", table_name="distilled_strategy_cache")
    op.drop_index("ix_distilled_strategy_cache_source_trajectory_type", table_name="distilled_strategy_cache")
    op.drop_index("ix_distilled_strategy_cache_shareability", table_name="distilled_strategy_cache")
    op.drop_index("ix_distilled_strategy_cache_status", table_name="distilled_strategy_cache")
    op.drop_table("distilled_strategy_cache")
