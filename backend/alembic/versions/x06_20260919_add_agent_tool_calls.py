"""X-06 · Tool Registry Safety（agent_tool_calls + 活跃唯一索引扩 BUDGET_EXCEEDED）

Revision ID: x06_20260919
Revises: d05_20260919
Create Date: 2026-09-19

契约真源：backend/app/tools/metadata.py（工具能力元数据封闭词表）+
backend/app/core/run_state_machine.py（agent_run.v2：终态词表 + BUDGET_EXCEEDED
+ terminal_reason "budget_exceeded"）。

Schema 变更（X-06 唯一 DB schema 入口）：

1. 新表 ``agent_tool_calls`` —— 工具调用执行账本（AGENT_RUNTIME.md §4 Tool
   Call 契约持久化）：call/run 关联、args_hash、permission_decision 留痕、
   status(in_progress/succeeded/failed)、result dump、时间戳。
   - ``uq_agent_tool_calls_idem``：部分唯一索引 (user_id, tool_name,
     idempotency_key) WHERE idempotency_key IS NOT NULL —— side-effect 幂等
     强制的 DB 兜底（同 key 恰一次）。
2. 重建 ``uq_agent_runs_intent_active`` —— WHERE 的终态集扩入
   ``BUDGET_EXCEEDED``（BUDGET_EXCEEDED 是终态：同 intent 的 retry 应可开新
   attempt 行，不受旧索引误拦）。仅 PostgreSQL 侧存在该部分索引；SQLite 测试
   库（Base.metadata.create_all）由模型自动建对，无需处理。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models.base import GUID

revision: str = "x06_20260919"
down_revision: str | None = "m08_20260920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# agent_run.v2 终态集（x05 迁移的 6 值 + BUDGET_EXCEEDED；硬编码冻结，不 import
# 运行时常量——历史迁移行为不可随后续词表演进漂移）。
_TERMINAL_VALUES_V2 = (
    "BUDGET_EXCEEDED",
    "CANCELLED",
    "FAILED",
    "PARTIAL",
    "SUCCEEDED",
    "TIMED_OUT",
    "UNKNOWN_OUTCOME",
)
_NOT_TERMINAL_SQL_V2 = "status NOT IN ({})".format(", ".join(f"'{v}'" for v in _TERMINAL_VALUES_V2))
_NOT_TERMINAL_SQL_V1 = "status NOT IN ('CANCELLED', 'FAILED', 'PARTIAL', 'SUCCEEDED', 'TIMED_OUT', 'UNKNOWN_OUTCOME')"

_IDEMPOTENT_WHERE = "idempotency_key IS NOT NULL"


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "agent_tool_calls",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("run_id", GUID(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("args_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("permission_decision", _jsonb_type(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="in_progress"),
        sa.Column("result", _jsonb_type(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_agent_tool_calls_user_id", "agent_tool_calls", ["user_id"])
    op.create_index("ix_agent_tool_calls_run_id", "agent_tool_calls", ["run_id"])
    op.create_index("idx_agent_tool_calls_user_created", "agent_tool_calls", ["user_id", "created_at"])
    op.create_index(
        "uq_agent_tool_calls_idem",
        "agent_tool_calls",
        ["user_id", "tool_name", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(_IDEMPOTENT_WHERE),
        sqlite_where=sa.text(_IDEMPOTENT_WHERE),
    )

    # 活跃唯一索引扩终态集（BUDGET_EXCEEDED 行退出活跃唯一约束）。
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_agent_runs_intent_active", table_name="agent_runs")
        op.create_index(
            "uq_agent_runs_intent_active",
            "agent_runs",
            ["intent_id"],
            unique=True,
            postgresql_where=sa.text(_NOT_TERMINAL_SQL_V2),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_agent_runs_intent_active", table_name="agent_runs")
        op.create_index(
            "uq_agent_runs_intent_active",
            "agent_runs",
            ["intent_id"],
            unique=True,
            postgresql_where=sa.text(_NOT_TERMINAL_SQL_V1),
        )
    op.drop_index("uq_agent_tool_calls_idem", table_name="agent_tool_calls")
    op.drop_index("idx_agent_tool_calls_user_created", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_run_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_user_id", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")
