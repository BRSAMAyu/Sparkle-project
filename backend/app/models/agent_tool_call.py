"""X-06 · Agent Tool Call Ledger —— 工具调用执行账本（幂等强制 + 审计）.

对应 AGENT_RUNTIME.md §4 Tool Call 契约的持久化落点（call_id / run_id / tool
name / normalized args hash / idempotency_key for side effect / permission
decision / start/end / result / error class），一张新表（Alembic
``x06_20260919``，唯一 DB schema 入口）：

- **side-effect 幂等强制**：``(user_id, tool_name, idempotency_key)`` 部分唯一
  索引（idempotency_key 非空行参与）——同 key 第二次插入撞唯一键，executor
  走重放路径（返回已记录结果，**不重复执行 side effect**）。账本行与工具自身
  的 DB 写入同事务：提交即「已发生且已记账」，回滚即「都未发生」——重试安全。
- **权限判定留痕**：每次过闸调用记录 permission decision（允许/否决归因），
  审计可回答「谁在何时以什么授权调了什么工具」。
- **budget 数据面**：run 维度 usage 计数（tool_calls/cost）由
  AgentRunService.record_run_usage 维护（agent_runs.budget.usage 为计数真源，
  本表是可审计账本，非计数器）。

不重建：UserToolHistory（user_tool_history 表）保持既有观测/偏好学习定位；
本表是**执行安全账本**（幂等/权限/budget），两者数据面不同域。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")

#: 账本状态封闭词表（应用层契约强制，create_constraint=False 先例）。
#: - in_progress：闸门已过、已开始执行（提交后的 in_progress = 进程崩溃残留，
#:   重放该 key 会被拒绝——fail-closed，不盲目重执行 side effect）；
#: - succeeded / failed：执行已收敛，同 key 重放返回记录结果，不再执行；
#: - interrupted（X-09 增补）：执行中断且效果不可核实——工具内部 commit 提前
#:   落库的 in_progress 行在超时/异常/崩溃后经两阶段收敛到此态（executor
#:   失败路径 resolve / 恢复路径 reconcile）。同 key 重放仍拒绝（duplicate
#:   side effect=0）；重试必须换新幂等键（显式决策，非自动）。
TOOL_CALL_STATUSES = ("in_progress", "succeeded", "failed", "interrupted")

_IDEMPOTENT_WHERE = text("idempotency_key IS NOT NULL")


class AgentToolCall(BaseModel):
    """一次通过安全闸门的工具调用（append-ish 账本行）。"""

    __tablename__ = "agent_tool_calls"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    # --- AGENT_RUNTIME.md §4 Tool Call 契约 ---
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_call_id: Mapped[str] = mapped_column(String(128), nullable=True)  # LLM/plan 侧调用 id（追踪用）
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=True)  # side-effect 工具必填（executor 强制）
    args_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # canonical args sha256
    permission_decision: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # decide_tool_permission 结果留痕
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    result: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # ToolResult dump（重放返回体）
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="agent_tool_calls", foreign_keys=[user_id])
    run = relationship("AgentRun", backref="tool_calls", foreign_keys=[run_id])

    __table_args__ = (
        # side-effect 幂等强制：同 (user, tool, key) 恰一行（部分唯一索引，
        # PostgreSQL/SQLite 均支持带 WHERE 的部分索引；X-05 同款）。
        Index(
            "uq_agent_tool_calls_idem",
            "user_id",
            "tool_name",
            "idempotency_key",
            unique=True,
            postgresql_where=_IDEMPOTENT_WHERE,
            sqlite_where=_IDEMPOTENT_WHERE,
        ),
        Index("idx_agent_tool_calls_user_created", "user_id", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "run_id": str(self.run_id) if self.run_id else None,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "idempotency_key": self.idempotency_key,
            "args_hash": self.args_hash,
            "permission_decision": self.permission_decision,
            "status": self.status,
            "result": self.result,
            "execution_time_ms": self.execution_time_ms,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<AgentToolCall(id={self.id}, tool={self.tool_name}, "
            f"status={self.status}, key={self.idempotency_key})>"
        )
