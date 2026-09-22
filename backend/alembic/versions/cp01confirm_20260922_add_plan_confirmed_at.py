"""CP-01 · plans.confirmed_at 计划人工确认列（exam-sprint 计划草案→确认闭环）

Revision ID: cp01confirm_20260922
Revises: planlink_20260922
Create Date: 2026-09-22

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop plans.confirmed_at 列。
        列为本卡新增、无存量数据依赖，downgrade 后 schema 与升级前一致；
        确认动作本身是可再生的用户事实（重新点击确认即可），不涉及数据回填。"
    verification_query: "SELECT column_name FROM information_schema.columns WHERE table_name='plans' AND column_name='confirmed_at';"
    backfill_plan: "无回填——存量计划一律视为未确认（confirmed_at NULL），由
        用户在端点上逐计划显式确认；不做任何推测性批量盖章。"
    owner: "CP-01"
    ticket: "V3 CP-01 exam-sprint 计划人工确认端点（北极星 LOOP3 实证 404 缺口）"

背景：北极星 LOOP3 实测 `POST /plans/{id}/confirm` 404，静态审计全仓只有
chat action 级 confirm 与 compass 工件 approve——exam-sprint 计划草案→人工
确认无专用端点。落点裁决：plans 表没有 status/draft 列（PlanStatus 枚举无
列引用；PlanStage 是学习旅程阶段 sprint/daily/review/paused；PlanState.status
是执行态存储 active/archived），三者均不承载确认语义，故新增
confirmed_at（nullable DateTime）：NULL=待确认（草稿态），非 NULL=已确认
（生效态）。

方言可移植性：纯 add_column/drop_column，无 JSON 谓词无数据改写；SQLite
基座走 batch_alter_table（sqlite 无 ALTER DROP COLUMN 的老版本兼容），
PostgreSQL 端 batch 模式原样发出 ALTER 语句、不触发表重建。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cp01confirm_20260922"
down_revision: str | None = "planlink_20260922"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("confirmed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("plans") as batch_op:
        batch_op.drop_column("confirmed_at")
