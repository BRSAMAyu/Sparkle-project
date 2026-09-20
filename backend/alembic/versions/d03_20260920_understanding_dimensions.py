"""understanding_dimension_daily + understanding_calibration_runs：D-03 五维内部度量

Revision ID: d03_20260920
Revises: x06_20260919
Create Date: 2026-09-20

背景（v3 D-03「Understanding 五维内部度量与校准」）：替代神秘 understanding_depth
百分比，形成可诊断的五维内部指标（coverage / correctness / scope_precision /
freshness / utility，公式与缺失语义冻结于 app/core/understanding_dimensions.py）。
本迁移新增两张离线聚合表：

- understanding_dimension_daily：每用户每日一行五维值 + 同窗行为锚点
  （(user_id, metric_date) 唯一，幂等 upsert）。
- understanding_calibration_runs：离线校准运行记录（coverage 重标定 map、
  校准前后 MAE、各维漂移状态快照），审计与误差量化证据面。

零新真源：数据全部来自既有生产表（aurora_judgment_records / memory_corrections /
unresolved_conflicts / context_pack_runs / chat_messages）。

验证：单迁移在本地 sqlite 基座隔离重放（tests/unit/test_d03_understanding_migration_sqlite.py）；
主库只读纪律 —— 本迁移**不得**对主仓 PostgreSQL 直接 apply，随常规发布走
make sync-db / alembic upgrade head。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('understanding_dimension_daily','understanding_calibration_runs');"
#   backfill_plan: "n/a（历史日期可由 celery 任务带 day 参数重算补齐，数据源表保留原值）"
#   owner: "backend"
#   ticket: "v3 D-03 Understanding 五维内部度量与校准"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d03_20260920"
down_revision: str | None = "x03b_20260920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_variant() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "understanding_dimension_daily",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("dimensions", _jsonb_variant(), nullable=False),
        sa.Column("anchors", _jsonb_variant(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "metric_date", name="uq_understanding_dimension_daily_user_date"),
    )
    op.create_index(
        "idx_understanding_dimension_daily_user_id",
        "understanding_dimension_daily",
        ["user_id"],
    )
    op.create_index(
        "idx_understanding_dimension_daily_date",
        "understanding_dimension_daily",
        ["metric_date"],
    )

    op.create_table(
        "understanding_calibration_runs",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("ran_at", sa.DateTime(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("coverage_map", _jsonb_variant(), nullable=False),
        sa.Column("drift_report", _jsonb_variant(), nullable=False),
        sa.Column("overall_status", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_understanding_calibration_runs_user_ran_at",
        "understanding_calibration_runs",
        ["user_id", "ran_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_understanding_calibration_runs_user_ran_at",
        table_name="understanding_calibration_runs",
    )
    op.drop_table("understanding_calibration_runs")
    op.drop_index("idx_understanding_dimension_daily_date", table_name="understanding_dimension_daily")
    op.drop_index("idx_understanding_dimension_daily_user_id", table_name="understanding_dimension_daily")
    op.drop_table("understanding_dimension_daily")
