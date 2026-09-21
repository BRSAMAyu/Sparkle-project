"""X-07 · Hybrid Handoff —— agent_runs.steps 步骤计划列

Revision ID: x07_20260921
Revises: d03_20260920
Create Date: 2026-09-21

契约真源：backend/app/core/run_steps.py（RUN_STEPS_CONTRACT_VERSION =
"run_steps.v1"，StepOwner/StepCompletionKind 封闭词表）。

单列变更（X-07 唯一 schema 变更；**零新表、零状态机改动**）：

``agent_runs.steps``（JSONB，NOT NULL，server default '[]'）——run 聚合内的
hybrid 步骤计划持久列（X-05 真源的扩展，**不建平行真源**）：每步含
step_id/ordinal/label/owner(agent|human|hybrid)/completion_condition(kind)/
artifacts([{"scheme","ref"} 引用，不复制本体])/awaiting(轮到用户的提示戳)/
completion(完成戳，含幂等键)。列内容契约由应用层 ``app/core/run_steps.py``
fail-closed 强制（封闭词表 + 归一化，X-01 action_plan 列同款），DB 层不带
CHECK（execution_intent.py create_constraint=False 先例）。

「当前 awaiting step」是推导态（run AWAITING_* + wait_kind=user_step 时第一
个未完成步骤），冷启动/通知重开从本列 + status 推导，不依赖内存；取消
（user_cancelled）/过期（wait_expired→TIMED_OUT）沿用 run 状态机既有词表
与 sweep，零新转换边（X-03/X-04 终态封闭纪律不被触碰）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "x07_20260921"
down_revision: str | None = "d03_20260920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    bind = op.get_bind()
    server_default = "[]" if bind.dialect.name == "sqlite" else sa.text("'[]'::jsonb")
    op.add_column(
        "agent_runs",
        sa.Column("steps", _jsonb_type(), nullable=False, server_default=server_default),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "steps")
