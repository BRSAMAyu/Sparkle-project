"""understanding_depth_daily：理解深度每日基线表（数据飞轮 MVP）

Revision ID: ud01_20260919
Revises: gfix03_20260918
Create Date: 2026-09-19

背景：understanding_depth 运行时等级（self_evolution_service.UnderstandingDepthService，
L0-L5）为纯 Redis 态、每次请求现算，无历史留痕 → "越用越懂用户"没有可回归的量化
基线。本迁移新增 understanding_depth_daily（user_id, metric_date 唯一），每日离线
聚合落一行 0-1 合成分 + components JSONB（各维度分量与原始样本量）。

验证：单迁移在本地 sqlite 基座隔离重放
（tests/unit/test_understanding_depth_migration_sqlite.py）；
主库只读纪律 —— 本迁移**不得**对主仓 PostgreSQL 直接 apply，随常规发布走
make sync-db / alembic upgrade head。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'understanding_depth_daily';"
#   backfill_plan: "n/a（历史日期可由 celery 任务带 day 参数重算补齐，数据源表保留原值）"
#   owner: "backend"
#   ticket: "数据飞轮专项之四（理解深度基线）"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ud01_20260919"
down_revision: str | None = "gfix03_20260918"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_variant() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "understanding_depth_daily",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("components", _jsonb_variant(), nullable=False),
        sa.Column("context_pack_runs", sa.Integer(), nullable=False),
        sa.Column("chat_turns", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "metric_date", name="uq_understanding_depth_daily_user_date"),
    )
    op.create_index(
        "ix_understanding_depth_daily_deleted_at", "understanding_depth_daily", ["deleted_at"], unique=False
    )
    op.create_index("idx_understanding_depth_daily_user_id", "understanding_depth_daily", ["user_id"], unique=False)
    op.create_index("idx_understanding_depth_daily_date", "understanding_depth_daily", ["metric_date"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_understanding_depth_daily_date", table_name="understanding_depth_daily")
    op.drop_index("idx_understanding_depth_daily_user_id", table_name="understanding_depth_daily")
    op.drop_index("ix_understanding_depth_daily_deleted_at", table_name="understanding_depth_daily")
    op.drop_table("understanding_depth_daily")
