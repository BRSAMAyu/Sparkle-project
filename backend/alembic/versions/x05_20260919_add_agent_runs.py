"""X-05 · Unified Agent Run 持久化状态机（agent_runs + agent_run_transitions）

Revision ID: x05_20260919
Revises: x01_20260919
Create Date: 2026-09-19

契约真源：backend/app/core/run_state_machine.py（RUN_STATE_MACHINE_VERSION =
"agent_run.v1"，封闭状态词表 + 迁移图，测试 sha256 双冻结）。

两张新表（X-05 唯一 schema 变更，全部新建、零列变更既有表）：

1. ``agent_runs`` —— 用户可见长任务 run 的唯一持久真源（AGENT_RUNTIME.md §3
   Run contract 全字段：objective/context_refs/allowed_tools/permissions/
   budget/completion_condition/risk_class/status/时间戳 + 活性 heartbeat_at +
   幂等创建 idempotency_key + intent/task/session/trace 关联 + attempt 计数）。
   run_id = 主键 GUID，全链一致；OpenClaw 自分配 id 留在
   execution_intents.external_run_id（关联引用，非身份）。
2. ``agent_run_transitions`` —— append-only 迁移审计（from/to/event_name/actor/
   idempotency_key/reason/details/occurred_at），每次有效迁移一行，与状态变更、
   event_outbox 事件同事务（M-07 同构）。

索引要点：
- ``uq_agent_runs_intent_active``：部分唯一索引（intent_id 非终态唯一）——同
  intent 至多一个活跃 run，retry（intent 终态→ready 重置）开新 attempt 行，
  终态封闭不被打破。PostgreSQL/SQLite 均支持部分索引。
- ``uq_agent_runs_idem``：(user_id, idempotency_key) 唯一——重复 run.created
  恰一次（X-05 并发幂等要求）。
- ``uq_agent_run_transitions_idem``：(run_id, idempotency_key) 唯一——重复
  resume 等幂等操作恰一次。

枚举列不带 DB CHECK（沿用 execution_intent.py create_constraint=False 模式，
封闭词表由应用层契约强制；X-01 同款）。JSONB 列 sqlite 侧退化为 JSON（测试）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models.base import GUID

revision: str = "x05_20260919"
down_revision: str | None = "x01_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TERMINAL_VALUES = ("CANCELLED", "FAILED", "PARTIAL", "SUCCEEDED", "TIMED_OUT", "UNKNOWN_OUTCOME")
_NOT_TERMINAL_SQL = "status NOT IN ({})".format(", ".join(f"'{v}'" for v in _TERMINAL_VALUES))


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    jsonb = _jsonb_type()

    op.create_table(
        "agent_runs",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("context_refs", jsonb, nullable=False),
        sa.Column("allowed_tools", jsonb, nullable=False),
        sa.Column("permissions", jsonb, nullable=False),
        sa.Column("budget", jsonb, nullable=False),
        sa.Column("completion_condition", jsonb, nullable=False),
        sa.Column("risk_class", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("wait_kind", sa.String(length=16), nullable=True),
        sa.Column("wait_expires_at", sa.DateTime(), nullable=True),
        sa.Column("task_id", GUID(), nullable=True),
        sa.Column("intent_id", GUID(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=True),
        sa.Column("steps_done", sa.Integer(), nullable=False),
        sa.Column("steps_total", sa.Integer(), nullable=True),
        sa.Column("terminal_reason", sa.String(length=32), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_ref", jsonb, nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["intent_id"], ["execution_intents.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("idx_agent_runs_task_id", "agent_runs", ["task_id"])
    op.create_index("idx_agent_runs_intent_id", "agent_runs", ["intent_id"])
    op.create_index("idx_agent_runs_session_id", "agent_runs", ["session_id"])
    op.create_index("idx_agent_runs_trace_id", "agent_runs", ["trace_id"])
    op.create_index("idx_agent_runs_heartbeat", "agent_runs", ["heartbeat_at"])
    op.create_index(
        "uq_agent_runs_intent_active",
        "agent_runs",
        ["intent_id"],
        unique=True,
        postgresql_where=sa.text(_NOT_TERMINAL_SQL),
        sqlite_where=sa.text(_NOT_TERMINAL_SQL),
    )
    op.create_index("idx_agent_runs_user_status", "agent_runs", ["user_id", "status"])
    op.create_index("uq_agent_runs_idem", "agent_runs", ["user_id", "idempotency_key"], unique=True)

    op.create_table(
        "agent_run_transitions",
        sa.Column("run_id", GUID(), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("details", jsonb, nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_agent_run_transitions_run_id", "agent_run_transitions", ["run_id"])
    op.create_index(
        "uq_agent_run_transitions_idem",
        "agent_run_transitions",
        ["run_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "idx_agent_run_transitions_run_occurred",
        "agent_run_transitions",
        ["run_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_agent_run_transitions_run_occurred", table_name="agent_run_transitions")
    op.drop_index("uq_agent_run_transitions_idem", table_name="agent_run_transitions")
    op.drop_index("idx_agent_run_transitions_run_id", table_name="agent_run_transitions")
    op.drop_table("agent_run_transitions")
    op.drop_index("uq_agent_runs_idem", table_name="agent_runs")
    op.drop_index("idx_agent_runs_user_status", table_name="agent_runs")
    op.drop_index("uq_agent_runs_intent_active", table_name="agent_runs")
    op.drop_index("idx_agent_runs_heartbeat", table_name="agent_runs")
    op.drop_index("idx_agent_runs_trace_id", table_name="agent_runs")
    op.drop_index("idx_agent_runs_session_id", table_name="agent_runs")
    op.drop_index("idx_agent_runs_intent_id", table_name="agent_runs")
    op.drop_index("idx_agent_runs_task_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("idx_agent_runs_user_id", table_name="agent_runs")
    op.drop_table("agent_runs")
