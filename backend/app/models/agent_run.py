"""X-05 · Unified Agent Run —— 持久化 run 脊柱模型.

两张新表（Alembic ``x05_20260919``，唯一 DB schema 入口）：

- ``agent_runs``：用户可见长任务的唯一持久真源（AGENT_RUNTIME.md §3 Run
  contract：objective / context refs / allowed_tools / permissions / budget /
  completion_condition / risk_class / status / timestamps）。run_id 即主键
  GUID，全链（App→网关→引擎→OpenClaw）一致；OpenClaw 自分配 id 留在
  ExecutionIntent.external_run_id（关联引用，非身份）。
- ``agent_run_transitions``：append-only 迁移审计（from/to/event/actor/
  idempotency_key/reason）。每次有效迁移一行，与状态变更、event_outbox
  事件同事务落库（M-07 同构）。

不重建（X-05 Forbidden 边界，见 v3-output/X-05/RUNTIME_MAP.md §4）：
- ExecutionIntent 是执行器协议真源，本模型只引用不复制其协议字段；
- RunLedgerStore（Redis TTL ledger）保持 chat 轨道 observability 定位。

状态词表与迁移图封闭于 ``app/core/run_state_machine.py``（sha256 双冻结）；
本模型枚举列沿用 execution_intent 的 ``create_constraint=False +
native_enum=False`` 模式（封闭词表由应用层契约强制，X-01 同款）。
"""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.run_state_machine import TERMINAL_RUN_STATUSES, RunStatus
from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")

_TERMINAL_VALUES = sorted(s.value for s in TERMINAL_RUN_STATUSES)

#: 活跃 run 唯一索引的 WHERE 条本（非终态行才参与唯一约束；retry 从终态开新 attempt）。
_NOT_TERMINAL_WHERE = text("status NOT IN ({})".format(", ".join(f"'{v}'" for v in _TERMINAL_VALUES)))


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class AgentRunKind(enum.StrEnum):
    """run 轨道类型（封闭词表；X-05 接线 execution 轨道，其余为后续卡预留）。"""

    EXECUTION = "execution"  # OpenClaw 委派（ExecutionIntent 投影）
    CHAT = "chat"  # chat 长任务（后续卡接线；当前 chat 轨道走 RunLedgerStore）
    SYSTEM = "system"  # 系统侧长任务（后续卡）


class AgentRun(BaseModel):
    """用户可见长任务 run 的唯一持久真源。"""

    __tablename__ = "agent_runs"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(
        Enum(AgentRunKind, values_callable=_enum_values, create_constraint=False, native_enum=False),
        nullable=False,
        default=AgentRunKind.EXECUTION,
    )

    # --- AGENT_RUNTIME.md §3 Run contract ---
    objective = Column(Text, nullable=False)
    context_refs = Column(JSONBCompat, nullable=False, default=list)  # ["scheme://id", ...]（C-01 对齐）
    allowed_tools = Column(JSONBCompat, nullable=False, default=list)
    permissions = Column(JSONBCompat, nullable=False, default=dict)
    budget = Column(JSONBCompat, nullable=False, default=dict)  # token/cost/time/tool_calls
    completion_condition = Column(JSONBCompat, nullable=False, default=dict)
    risk_class = Column(String(16), nullable=True)  # 复用 X-01 词表 low|medium|high|critical

    # --- 状态机 ---
    status = Column(
        Enum(RunStatus, values_callable=_enum_values, create_constraint=False, native_enum=False),
        nullable=False,
        default=RunStatus.QUEUED,
        index=True,
    )
    wait_kind = Column(String(16), nullable=True)  # user_step|approval（AWAITING_* 态非空）
    wait_expires_at = Column(DateTime, nullable=True)

    # --- 关联（跨轨 correlation；intent 轨道 1 活跃 run per intent） ---
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    intent_id = Column(GUID(), ForeignKey("execution_intents.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    trace_id = Column(String(64), nullable=True, index=True)
    attempt = Column(Integer, nullable=False, default=1)  # 同 intent 的第 N 次尝试（retry 开新 run）

    # --- 进度（UI 阶段「正在执行 2/4」；App 只读） ---
    current_stage = Column(String(64), nullable=True)
    steps_done = Column(Integer, nullable=False, default=0)
    steps_total = Column(Integer, nullable=True)

    # --- 终态归因（封闭词表 terminal_reason_vocabulary） ---
    terminal_reason = Column(String(32), nullable=True)
    error_category = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    result_ref = Column(JSONBCompat, nullable=True)  # {"scheme": ..., "ref": ...}（结果引用，非结果本体）

    # --- 活性（worker restart 恢复判定） ---
    heartbeat_at = Column(DateTime, nullable=False)  # 创建时置初值；迁移/步进/投影触达时刷新

    # --- 幂等创建（重复 run.created 恰一次） ---
    idempotency_key = Column(String(255), nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="agent_runs", foreign_keys=[user_id])
    transitions = relationship(
        "AgentRunTransition",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentRunTransition.created_at",
    )

    __table_args__ = (
        # 活跃 run 唯一：同一 intent 至多一个非终态 run（retry 从终态开新 attempt）。
        # 部分唯一索引（PostgreSQL/SQLite 均支持带 WHERE 的部分索引）。
        Index(
            "uq_agent_runs_intent_active",
            "intent_id",
            unique=True,
            postgresql_where=_NOT_TERMINAL_WHERE,
            sqlite_where=_NOT_TERMINAL_WHERE,
        ),
        Index("idx_agent_runs_user_status", "user_id", "status"),
        Index("idx_agent_runs_idem", "user_id", "idempotency_key", unique=True),
        Index("idx_agent_runs_heartbeat", "heartbeat_at"),
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_RUN_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.id),
            "user_id": str(self.user_id),
            "kind": self.kind.value if self.kind else None,
            "objective": self.objective,
            "status": self.status.value if self.status else None,
            "is_terminal": self.is_terminal,
            "wait_kind": self.wait_kind,
            "wait_expires_at": self.wait_expires_at.isoformat() if self.wait_expires_at else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "intent_id": str(self.intent_id) if self.intent_id else None,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "attempt": int(self.attempt or 1),
            "context_refs": self.context_refs or [],
            "allowed_tools": self.allowed_tools or [],
            "permissions": self.permissions or {},
            "budget": self.budget or {},
            "completion_condition": self.completion_condition or {},
            "risk_class": self.risk_class,
            "current_stage": self.current_stage,
            "steps_done": int(self.steps_done or 0),
            "steps_total": self.steps_total,
            "terminal_reason": self.terminal_reason,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "result_ref": self.result_ref,
            "heartbeat_at": self.heartbeat_at.isoformat() if self.heartbeat_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AgentRun(id={self.id}, status={self.status}, kind={self.kind})>"


class AgentRunTransition(BaseModel):
    """一次有效 run 状态迁移的 append-only 审计行（与状态变更、事件同事务）。"""

    __tablename__ = "agent_run_transitions"

    run_id = Column(GUID(), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(24), nullable=True)  # None = 创建（QUEUED 落库）
    to_status = Column(String(24), nullable=False)
    event_name = Column(String(64), nullable=False)  # 同事务写入 outbox 的事件名
    actor = Column(String(32), nullable=False)  # user|worker|system|recovery|projection
    idempotency_key = Column(String(255), nullable=True)  # 提供时按 (run_id, key) 唯一
    reason = Column(String(64), nullable=True)
    details = Column(JSONBCompat, nullable=True)
    occurred_at = Column(DateTime, nullable=False)

    run = relationship("AgentRun", back_populates="transitions")

    __table_args__ = (
        Index("uq_agent_run_transitions_idem", "run_id", "idempotency_key", unique=True),
        Index("idx_agent_run_transitions_run_occurred", "run_id", "occurred_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "from_status": self.from_status,
            "to_status": self.to_status,
            "event_name": self.event_name,
            "actor": self.actor,
            "reason": self.reason,
            "details": self.details,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
