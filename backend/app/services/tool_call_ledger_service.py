"""X-09 · Tool Call Ledger Service —— 账本收敛（reconcile）与部分完成证据.

职责（v3/07_tasks/cards/X-09.md 工作项 2/3 + FIX-40 P2-3 残留收编）：

1. **陈旧 in_progress 账本行的确定性收敛**（:meth:`reconcile_stale_in_progress`）：
   进程崩溃后，内部 commit 工具提前落库的 in_progress 行无人 finalize（executor
   两阶段收敛只在**优雅失败路径**可达；kill -9 不可达）——按 started_at 陈旧
   阈值判孤儿，置 ``interrupted``（效果不可核实）。这是 X-05 恢复 sweep 的
   账本侧补充：sweep 兜底 run 行，本服务兜底账本行，两者由
   :meth:`AgentRunService.recover_inflight_runs` 协同编排。

2. **部分完成证据**（:meth:`partial_completion_evidence`）：多步 run 中途失败/
   取消时，已完成步**不静默丢弃**——从账本物化 succeeded/failed/interrupted
   明细 + 补偿提示（AGENT_RUNTIME §6：不假装回滚，显示已完成部分与可补偿
   动作），写入 run.result_ref（API 可见）。

3. **run 维度账本读面**（:meth:`list_tool_calls_for_run`）：审计/用户可见的
   每步执行明细（GET /runs/{run_id}/tool-calls 数据面）。

不重建：agent_tool_calls 表（X-06 迁移 x06_20260919）与 executor 闸门不动；
本服务是读/收敛面，不参与调用授权。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_tool_call import AgentToolCall

__all__ = [
    "ToolCallLedgerService",
    "LedgerReconcileResult",
    "PartialCompletionEvidence",
    "DEFAULT_LEDGER_STALE_AFTER_SECONDS",
    "compute_ledger_stale_after_seconds",
]

#: 陈旧 in_progress 判定缺省（秒）。覆盖 executor 默认 tool timeout（120s）×2
#: + 兼顾 90s LLM 工具的长尾；调用方（admin recover / 恢复 pass）可显式覆盖。
DEFAULT_LEDGER_STALE_AFTER_SECONDS = 300


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def compute_ledger_stale_after_seconds(max_tool_timeout_seconds: float | None = None) -> int:
    """陈旧阈值 = max(缺省, 注册表最长工具超时 × 2 + 60s 余量).

    注册表超时是确定性输入（元数据真源），保证"任何合法长工具都不会被误判
    孤儿"——阈值永远大于最慢合法执行的 2 倍。
    """
    base = int(DEFAULT_LEDGER_STALE_AFTER_SECONDS)
    if max_tool_timeout_seconds is None or max_tool_timeout_seconds <= 0:
        return base
    derived = int(float(max_tool_timeout_seconds) * 2 + 60)
    return max(base, derived)


def _registry_max_timeout_seconds() -> float | None:
    """注册表内最长工具超时（元数据真源；读失败返回 None 用缺省）。"""
    try:
        from app.tools.registry import tool_registry

        timeouts: list[float] = []
        for tool in tool_registry.get_all_tools():
            value = getattr(tool, "timeout_seconds", None)
            if value is None:
                continue
            try:
                timeouts.append(float(value))
            except (TypeError, ValueError):
                continue
        return max(timeouts) if timeouts else None
    except Exception:  # noqa: BLE001 — 阈值推导失败退缺省（sweep 语义不依赖它）
        return None


@dataclass(frozen=True)
class LedgerReconcileResult:
    """一次账本收敛 pass 的结果（确定性摘要；run 层恢复决策的输入）。"""

    reconciled: int = 0
    already_resolved: int = 0  # 扫描时已是 interrupted（前次 pass 已收敛）
    affected_run_ids: list[str] = field(default_factory=list)
    stale_after_seconds: int = DEFAULT_LEDGER_STALE_AFTER_SECONDS


@dataclass(frozen=True)
class PartialCompletionEvidence:
    """run 的部分完成证据（不静默丢弃已完成步；AGENT_RUNTIME §6）.

    - ``succeeded`` / ``failed`` / ``interrupted``：账本明细（tool / key /
      started_at / finished_at / error 归因）；
    - ``compensation_hints``：已完成**写效果**调用的补偿提示（registry 元数据
      ``reversible`` 是唯一真源；不可逆写效果显式标出，供 UI/人工裁决）；
    - ``durable_progress``：是否存在元数据确认的写效果成功步（PARTIAL vs
      FAILED 的判据——纯读成功不构成完成进度）。
    """

    run_id: str
    succeeded: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    interrupted: list[dict[str, Any]] = field(default_factory=list)
    compensation_hints: list[dict[str, Any]] = field(default_factory=list)
    durable_progress: bool = False

    def to_result_ref(self) -> dict[str, Any]:
        """物化为 run.result_ref（API 可见的部分完成语义载体）。"""
        return {
            "scheme": "partial_completion",
            "version": "x09.v1",
            "run_id": self.run_id,
            "succeeded_steps": len(self.succeeded),
            "failed_steps": len(self.failed),
            "interrupted_steps": len(self.interrupted),
            "durable_progress": self.durable_progress,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "interrupted": self.interrupted,
            "compensation_hints": self.compensation_hints,
        }


class ToolCallLedgerService:
    """agent_tool_calls 的收敛/证据/读面（无调用授权职责——那是 executor）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 崩溃残留收敛（kill -9 后 in_progress 孤儿 → interrupted）
    # ------------------------------------------------------------------

    async def reconcile_stale_in_progress(
        self,
        *,
        stale_after_seconds: int | None = None,
        limit: int = 500,
    ) -> LedgerReconcileResult:
        """陈旧 in_progress 账本行 → ``interrupted``（效果不可核实）.

        幂等：已 interrupted 的行不再改写（``already_resolved`` 计数）；行按
        started_at 升序处理（最老的最可能是孤儿）。收敛是**单向**的——
        interrupted 永不回到 in_progress，也永不重执行（duplicate side effect=0）。
        """
        stale_after = int(stale_after_seconds or compute_ledger_stale_after_seconds(_registry_max_timeout_seconds()))
        cutoff = _utcnow() - timedelta(seconds=stale_after)

        stmt = (
            select(AgentToolCall)
            .where(
                AgentToolCall.status.in_(("in_progress", "interrupted")),
                AgentToolCall.started_at.is_not(None),
                AgentToolCall.started_at < cutoff,
            )
            .order_by(AgentToolCall.started_at.asc())
            .limit(max(1, min(int(limit), 2000)))
        )
        rows = list((await self.db.execute(stmt)).scalars().all())

        reconciled = 0
        already = 0
        affected: list[str] = []
        for row in rows:
            if row.status == "interrupted":
                already += 1
            else:
                row.status = "interrupted"
                row.error_type = (row.error_type or "InterruptedAtRecovery")[:100]
                row.error_message = (
                    row.error_message
                    or "execution interrupted (process restart); side-effect outcome could not be verified"
                )
                row.finished_at = row.finished_at or _utcnow()
                self.db.add(row)
                reconciled += 1
                logger.warning(
                    "ledger row reconciled to interrupted: ledger_id={} tool={} key={} run_id={}",
                    row.id,
                    row.tool_name,
                    row.idempotency_key,
                    row.run_id,
                )
            if row.run_id is not None and str(row.run_id) not in affected:
                affected.append(str(row.run_id))

        if reconciled:
            await self.db.commit()

        return LedgerReconcileResult(
            reconciled=reconciled,
            already_resolved=already,
            affected_run_ids=affected,
            stale_after_seconds=stale_after,
        )

    # ------------------------------------------------------------------
    # 2. 部分完成证据（多步执行中途失败的已完成步处置）
    # ------------------------------------------------------------------

    async def partial_completion_evidence(self, run_id: UUID | str) -> PartialCompletionEvidence:
        """从账本物化 run 的部分完成证据 + 补偿提示（AGENT_RUNTIME §6）."""
        run_uuid = UUID(str(run_id))
        stmt = (
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run_uuid)
            .order_by(AgentToolCall.started_at.asc(), AgentToolCall.created_at.asc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return self.build_evidence(run_uuid, rows)

    @staticmethod
    def build_evidence(run_uuid: UUID, rows: list[AgentToolCall]) -> PartialCompletionEvidence:
        """纯物化（无 IO；确定性：同账本行集恒同证据）——测试可直接喂行集."""
        from app.tools.registry import tool_registry

        succeeded: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        interrupted: list[dict[str, Any]] = []
        hints: list[dict[str, Any]] = []
        durable = False

        for row in rows:
            entry = {
                "tool": row.tool_name,
                "idempotency_key": row.idempotency_key,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "error_type": row.error_type,
            }
            if row.status == "succeeded":
                succeeded.append(entry)
                metadata = tool_registry.get_tool_metadata(row.tool_name)
                if metadata is not None and metadata.is_side_effect:
                    # 写效果已确认发生：完成进度成立 + 补偿提示（含不可逆警示）。
                    durable = True
                    hints.append(
                        {
                            "tool": row.tool_name,
                            "idempotency_key": row.idempotency_key,
                            "reversible": metadata.reversible,
                            "hint": (
                                "effect confirmed; compensation path available"
                                if metadata.reversible
                                else "effect confirmed and NOT reversible; manual review required"
                            ),
                        }
                    )
            elif row.status == "interrupted":
                interrupted.append({**entry, "outcome": "unknown"})
            else:
                failed.append(entry)

        return PartialCompletionEvidence(
            run_id=str(run_uuid),
            succeeded=succeeded,
            failed=failed,
            interrupted=interrupted,
            compensation_hints=hints,
            durable_progress=durable,
        )

    # ------------------------------------------------------------------
    # 3. run 维度账本读面（GET /runs/{run_id}/tool-calls 数据面）
    # ------------------------------------------------------------------

    async def list_tool_calls_for_run(
        self,
        run_id: UUID | str,
        *,
        limit: int = 200,
    ) -> list[AgentToolCall]:
        stmt = (
            select(AgentToolCall)
            .where(AgentToolCall.run_id == UUID(str(run_id)))
            .order_by(AgentToolCall.started_at.asc(), AgentToolCall.created_at.asc())
            .limit(max(1, min(int(limit), 500)))
        )
        return list((await self.db.execute(stmt)).scalars().all())
