"""X-05 · Unified Agent Run Service —— run 状态机唯一写入权威.

每次**有效**状态迁移在一个数据库事务内原子完成（M-07 同构）：

1. ``agent_runs.status`` 变更（含 wait/终态归因/进度/心跳字段）；
2. ``agent_run_transitions`` append-only 审计行；
3. ``event_outbox`` 事件（D-01 封闭词表，``build_event_metadata`` 信封，
   ``event_sequence_counters`` 单调序列）。

幂等/并发契约（卡面：「重复 run.created / 重复 user_resumed 恰一次」）：
- **create**：``(user_id, idempotency_key)`` 唯一索引兜底；同 key 重复调用返回
  既有 run（``created=False``），run.created 事件恰一条（并发撞唯一键 → 复查
  收敛，M-07 懒建同法）。
- **transition**：``SELECT ... FOR UPDATE`` 锁 run 行 + 复查当前状态——第二个
  调用方（被行锁阻塞，或纯重试）看到已迁移状态即返回 no-op（``applied=False``），
  不写第二行审计、不发第二个事件。携带 ``idempotency_key`` 的重放按
  ``(run_id, idempotency_key)`` 唯一索引二次兜底。
- **非法迁移**：封闭迁移图（``app/core/run_state_machine.py``）拒绝，
  ``IllegalRunTransitionError``（ValueError 子类 → API 409，tasks.py:999 先例）；
  终态无出边（终态封闭）。

Worker restart 恢复（AGENT_RUNTIME.md §5「明确 terminal」）：
- :meth:`AgentRunService.recover_stale_runs` —— QUEUED 陈旧→CANCELLED；
  AWAITING_* 等待过期→TIMED_OUT；RUNNING/EXECUTING 心跳陈旧→UNKNOWN_OUTCOME
  （已发生 side effect 不假装知道结果）；intent 终态漂移→投影修复（QUEUED
  分支同样先漂移后推测，R2 F3）。
- :meth:`AgentRunService.project_intent_status` —— ExecutionIntent 状态漏斗
  （event_bus EXECUTION_STATUS_CHANGED）→ run 投影；终态事件重投恒等幂等
  （幻影守卫，R2 F1），用户取消不复活（R2 F2），QUEUED 迟到终态两步收敛
  （R2 F3）。

不重建（见 v3-output/X-05/RUNTIME_MAP.md）：ExecutionIntent 协议状态机零改动；
RunLedgerStore 保持 chat 观测定位。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Iterable
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_registry import CorrelationIds, EventSource, build_event_metadata
from app.core.run_state_machine import (
    ACTIVE_RUN_STATUSES,
    INTENT_STATUS_TO_RUN_STATUS,
    RESUMABLE_RUN_STATUSES,
    RUN_STATE_MACHINE_VERSION,
    InvalidResumeTargetError,
    RunStatus,
    RunWaitKind,
    event_name_for_transition,
    is_terminal_run_status,
    run_status_for_intent_status,
    terminal_reason_vocabulary,
)
from app.models.agent_run import AgentRun, AgentRunKind, AgentRunTransition
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus

AGENT_RUN_PAYLOAD_SCHEMA = RUN_STATE_MACHINE_VERSION  # "agent_run.v1"
AGENT_RUN_AGGREGATE_TYPE = "agent_run"
AGENT_RUN_SERVICE_NAME = "agent_run_service"

#: 恢复 sweep 的默认陈旧阈值（无新心跳多久判孤儿）。execution 轨道的 intent
#: 默认 timeout 300s、状态漏斗只在变更时触达，取 6h 为保守默认；调用方可显式
#: 覆盖（admin recover 端点透传）。
DEFAULT_STALE_AFTER_SECONDS = 6 * 3600

#: 这些终态归因下的 CANCELLED run 永不在**同一 intent** 下复活（R2 F1/F2）：
#: - ``user_cancelled``：用户显式取消——即使 intent 行因传播部分失败仍非终态，
#:   后到的执行状态事件也不得把取消"视觉撤销"（真重试走 retry_intent，开的是
#:   **新 intent**，天然不受此守卫影响）；
#: - ``handed_back``：任务交还用户执行，同属用户意图的取消语义。
#: （``queue_stale`` 不在其中：那是 sweep 对"从未启动"的推测，迟到的事件证明
#:   执行确实启动时，允许开新 attempt 如实记录。）
NON_RESURRECTABLE_CANCEL_REASONS: frozenset[str] = frozenset({"user_cancelled", "handed_back"})


#: ExecutionIntent 协议的终态集（执行器侧真源；投影守卫/漂移修复共用）。
_INTENT_TERMINAL_STATUSES: frozenset[ExecutionIntentStatus] = frozenset(
    {
        ExecutionIntentStatus.SUCCEEDED,
        ExecutionIntentStatus.PARTIAL,
        ExecutionIntentStatus.FAILED,
        ExecutionIntentStatus.CANCELED,
        ExecutionIntentStatus.TIMED_OUT,
        ExecutionIntentStatus.HANDED_BACK,
    }
)


#: intent 投影创建 run 的确定性幂等键（同 intent 同 attempt 恰一次 run.created）。
def intent_attempt_key(intent_id: UUID | str, attempt: int) -> str:
    return f"intent:{str(intent_id)}:attempt:{int(attempt)}"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RunNotFoundError(ValueError):
    """run 不存在或不属于该用户（API 层 404；与 _get_user_intent 同形）。"""


class TransitionActor(StrEnum):
    USER = "user"
    WORKER = "worker"
    SYSTEM = "system"
    RECOVERY = "recovery"
    PROJECTION = "projection"


@dataclass(frozen=True)
class RunMutationResult:
    """一次 create/transition/resume/cancel 的结果（applied=False 即幂等 no-op）。"""

    run: AgentRun
    applied: bool
    created: bool = False
    event_name: str | None = None
    event_written: bool = False


class AgentRunService:
    """run 状态机唯一写入权威（读写均经本服务；API/消费者不直改 run 行）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 读（单一权威端点的数据面）
    # ------------------------------------------------------------------

    async def get_run(self, run_id: UUID | str, *, user_id: UUID | str | None = None) -> AgentRun:
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None))
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        return run

    async def list_runs(
        self,
        *,
        user_id: UUID | str,
        task_id: UUID | str | None = None,
        intent_id: UUID | str | None = None,
        session_id: str | None = None,
        active_only: bool = False,
        limit: int = 50,
    ) -> list[AgentRun]:
        stmt = select(AgentRun).where(
            AgentRun.user_id == UUID(str(user_id)),
            AgentRun.deleted_at.is_(None),
        )
        if task_id is not None:
            stmt = stmt.where(AgentRun.task_id == UUID(str(task_id)))
        if intent_id is not None:
            stmt = stmt.where(AgentRun.intent_id == UUID(str(intent_id)))
        if session_id is not None:
            stmt = stmt.where(AgentRun.session_id == session_id)
        if active_only:
            stmt = stmt.where(AgentRun.status.in_([s.value for s in ACTIVE_RUN_STATUSES]))
        stmt = stmt.order_by(AgentRun.updated_at.desc()).limit(max(1, min(int(limit), 200)))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_transitions(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str | None = None,
        limit: int = 100,
    ) -> list[AgentRunTransition]:
        await self.get_run(run_id, user_id=user_id)
        stmt = (
            select(AgentRunTransition)
            .where(AgentRunTransition.run_id == UUID(str(run_id)))
            .order_by(AgentRunTransition.occurred_at.asc(), AgentRunTransition.created_at.asc())
            .limit(max(1, min(int(limit), 500)))
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # create（幂等：重复 run.created 恰一次）
    # ------------------------------------------------------------------

    async def create_run(
        self,
        *,
        user_id: UUID | str,
        objective: str,
        kind: AgentRunKind | str = AgentRunKind.EXECUTION,
        idempotency_key: str | None = None,
        task_id: UUID | str | None = None,
        intent_id: UUID | str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
        attempt: int = 1,
        context_refs: Iterable[str] | None = None,
        allowed_tools: Iterable[str] | None = None,
        permissions: dict[str, Any] | None = None,
        budget: dict[str, Any] | None = None,
        completion_condition: dict[str, Any] | None = None,
        risk_class: str | None = None,
        steps_total: int | None = None,
        initial_status: RunStatus | str = RunStatus.QUEUED,
        terminal_reason: str | None = None,
        actor: str = TransitionActor.USER,
        source: EventSource | str = EventSource.SERVER_SERVICE,
    ) -> RunMutationResult:
        """创建 run（run.created 事件同事务，恰一次）。

        ``initial_status`` 允许终态：仅供**迟到投影 catch-up**（消费者首次见到
        的 intent 状态已是终态时，按终态直接建档，审计行 from=None）。常规创建
        一律 QUEUED。``terminal_reason`` 仅在 ``initial_status`` 为终态时生效
        （封闭词表校验），保证 catch-up 建档与正常迁移的终态归因一致（R2 F7）。
        """
        user_uuid = UUID(str(user_id))
        key = (str(idempotency_key).strip() if idempotency_key else None) or None
        initial = RunStatus(initial_status)
        if terminal_reason is not None:
            terminal_reason = str(terminal_reason)
            if not is_terminal_run_status(initial):
                raise ValueError("terminal_reason is only valid with a terminal initial_status")
            if terminal_reason not in terminal_reason_vocabulary:
                raise ValueError(f"unknown terminal reason {terminal_reason!r} (closed vocabulary)")

        if key is not None:
            existing = await self._find_by_idempotency_key(user_uuid, key)
            if existing is not None:
                return RunMutationResult(
                    run=existing, applied=True, created=False, event_name="run.created", event_written=False
                )

        now = _utcnow()
        run_id = uuid4()
        run = AgentRun(
            id=run_id,
            user_id=user_uuid,
            kind=AgentRunKind(kind) if not isinstance(kind, AgentRunKind) else kind,
            objective=str(objective or "").strip() or "(untitled run)",
            context_refs=list(context_refs or []),
            allowed_tools=list(allowed_tools or []),
            permissions=dict(permissions or {}),
            budget=dict(budget or {}),
            completion_condition=dict(completion_condition or {}),
            risk_class=risk_class,
            status=initial,
            wait_kind=None,
            wait_expires_at=None,
            task_id=UUID(str(task_id)) if task_id else None,
            intent_id=UUID(str(intent_id)) if intent_id else None,
            session_id=str(session_id)[:64] if session_id else None,
            trace_id=str(trace_id)[:64] if trace_id else None,
            attempt=int(attempt) or 1,
            steps_total=int(steps_total) if steps_total else None,
            heartbeat_at=now,
            idempotency_key=key,
            started_at=now if initial is not RunStatus.QUEUED else None,
            completed_at=now if is_terminal_run_status(initial) else None,
            terminal_reason=terminal_reason if is_terminal_run_status(initial) else None,
        )
        self.db.add(run)
        transition = AgentRunTransition(
            run_id=run_id,
            from_status=None,
            to_status=initial.value,
            event_name="run.created",
            actor=str(actor),
            idempotency_key=key,
            reason=None,
            details={"kind": run.kind.value if run.kind else None, "attempt": run.attempt},
            occurred_at=now,
        )
        self.db.add(transition)
        event_written = await self._write_run_event_in_txn(
            run=run,
            event_name="run.created",
            source=source,
            service=AGENT_RUN_SERVICE_NAME,
            payload={
                "schema_version": AGENT_RUN_PAYLOAD_SCHEMA,
                "run_id": str(run.id),
                "state": initial.value,
                "kind": run.kind.value if run.kind else None,
                "objective": run.objective,
                "task_id": str(run.task_id) if run.task_id else None,
                "attempt": run.attempt,
            },
        )
        try:
            await self.db.commit()
        except IntegrityError:
            # 并发同 key 双创建（或活跃 intent run 撞部分唯一索引）→ 复查收敛。
            await self.db.rollback()
            if key is not None:
                existing = await self._find_by_idempotency_key(user_uuid, key)
                if existing is not None:
                    return RunMutationResult(
                        run=existing, applied=True, created=False, event_name="run.created", event_written=False
                    )
            raise
        await self.db.refresh(run)
        return RunMutationResult(
            run=run, applied=True, created=True, event_name="run.created", event_written=event_written
        )

    # ------------------------------------------------------------------
    # transition（FOR UPDATE + 复查；非法迁移拒绝；同事务审计+事件）
    # ------------------------------------------------------------------

    async def transition(
        self,
        run_id: UUID | str,
        to_status: RunStatus | str,
        *,
        user_id: UUID | str | None = None,
        actor: str = TransitionActor.WORKER,
        reason: str | None = None,
        idempotency_key: str | None = None,
        wait_kind: RunWaitKind | str | None = None,
        wait_expires_at: datetime | None = None,
        error_category: str | None = None,
        error_message: str | None = None,
        current_stage: str | None = None,
        steps_done: int | None = None,
        steps_total: int | None = None,
        result_ref: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        source: EventSource | str = EventSource.WORKER,
    ) -> RunMutationResult:
        """执行一次状态迁移（核心入口；resume/cancel/恢复均走这里）。"""
        from app.core.run_state_machine import assert_transition_legal  # 局部导入避免环

        target = RunStatus(to_status)
        key = (str(idempotency_key).strip() if idempotency_key else None) or None

        stmt = (
            select(AgentRun)
            .where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None))
            .with_for_update()  # PG 行锁；sqlite 测试下为 no-op，由复查+唯一索引兜底
        )
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")

        current = RunStatus(run.status)
        if current is target:
            # 幂等复查（M-07 同法）：第二个调用方看到已迁移状态 → no-op，
            # 不写第二行审计、不发第二个事件（恰一次）。
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)

        assert_transition_legal(current, target)

        now = _utcnow()
        terminal = is_terminal_run_status(target)
        if terminal and reason is not None:
            reason = str(reason)
            if reason not in terminal_reason_vocabulary:
                raise ValueError(f"unknown terminal reason {reason!r} (closed vocabulary)")

        run.status = target
        run.heartbeat_at = now
        if current is RunStatus.QUEUED and target is not RunStatus.QUEUED and run.started_at is None:
            run.started_at = now
        if terminal:
            run.completed_at = now
            run.terminal_reason = reason
            run.wait_kind = None
            run.wait_expires_at = None
        elif target in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
            run.wait_kind = (
                RunWaitKind(wait_kind).value
                if wait_kind
                else (
                    RunWaitKind.APPROVAL.value if target is RunStatus.AWAITING_APPROVAL else RunWaitKind.USER_STEP.value
                )
            )
            run.wait_expires_at = wait_expires_at
        else:
            run.wait_kind = None
            run.wait_expires_at = None
        if error_category is not None:
            run.error_category = str(error_category)[:100]
        if error_message is not None:
            run.error_message = str(error_message)
        if current_stage is not None:
            run.current_stage = str(current_stage)[:64]
        if steps_done is not None:
            run.steps_done = int(steps_done)
        if steps_total is not None:
            run.steps_total = int(steps_total)
        if result_ref is not None:
            run.result_ref = dict(result_ref)

        event_name = event_name_for_transition(current, target)
        transition_row = AgentRunTransition(
            run_id=run.id,
            from_status=current.value,
            to_status=target.value,
            event_name=event_name.value,
            actor=str(actor),
            idempotency_key=key,
            reason=reason,
            details=dict(details or {}),
            occurred_at=now,
        )
        self.db.add(transition_row)

        payload: dict[str, Any] = {
            "schema_version": AGENT_RUN_PAYLOAD_SCHEMA,
            "run_id": str(run.id),
            "from": current.value,
            "to": target.value,
        }
        if reason:
            payload["reason"] = reason
        if terminal:
            payload["terminal"] = True
        if target in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
            payload["wait"] = {
                "kind": run.wait_kind,
                "expires_at": run.wait_expires_at.isoformat() if run.wait_expires_at else None,
            }
        event_written = await self._write_run_event_in_txn(
            run=run,
            event_name=event_name.value,
            source=source,
            service=AGENT_RUN_SERVICE_NAME,
            payload=payload,
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            if key is not None:
                replay = await self._find_transition(run.id, key)
                if replay is not None:
                    refreshed = await self.get_run(run_id, user_id=user_id)
                    return RunMutationResult(
                        run=refreshed, applied=False, created=False, event_name=None, event_written=False
                    )
            raise
        await self.db.refresh(run)
        return RunMutationResult(
            run=run, applied=True, created=False, event_name=event_name.value, event_written=event_written
        )

    # ------------------------------------------------------------------
    # 语义操作（API 面）
    # ------------------------------------------------------------------

    async def resume(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str,
        to_status: RunStatus | str = RunStatus.RUNNING,
        idempotency_key: str | None = None,
        current_stage: str | None = None,
    ) -> RunMutationResult:
        """用户恢复等待中的 run（run.user_resumed 事件；重复恢复恰一次）。

        ``to_status`` 服务端白名单（R2 F4）：只允许 :data:`RESUMABLE_RUN_STATUSES`
        （RUNNING/EXECUTING——resume 的两个执行落点）。终态/等待态/未知值一律
        ``InvalidResumeTargetError``（API 层 422）——客户端不得借 resume 注入
        ``AWAITING_USER → SUCCEEDED`` 之类的伪造迁移或自批 approval。
        """
        try:
            target = RunStatus(to_status)
        except ValueError:
            raise InvalidResumeTargetError(
                f"unknown resume target status {to_status!r} (allowed: {sorted(s.value for s in RESUMABLE_RUN_STATUSES)})"
            ) from None
        if target not in RESUMABLE_RUN_STATUSES:
            raise InvalidResumeTargetError(
                f"resume target {target.value} is not a legal resume landing status "
                f"(allowed: {sorted(s.value for s in RESUMABLE_RUN_STATUSES)}); "
                "terminal/waiting statuses cannot be injected via resume"
            )
        return await self.transition(
            run_id,
            target,
            user_id=user_id,
            actor=TransitionActor.USER,
            reason=None,
            idempotency_key=idempotency_key,
            current_stage=current_stage,
            source=EventSource.SERVER_SERVICE,
        )

    async def cancel(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str,
        reason: str = "user_cancelled",
        idempotency_key: str | None = None,
    ) -> RunMutationResult:
        """用户取消（AGENT_RUNTIME.md §6：状态变更 + 下游协作取消）。"""
        run = await self.get_run(run_id, user_id=user_id)
        if RunStatus(run.status) is RunStatus.CANCELLED:
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)
        return await self.transition(
            run_id,
            RunStatus.CANCELLED,
            user_id=user_id,
            actor=TransitionActor.USER,
            reason=reason,
            idempotency_key=idempotency_key,
            source=EventSource.SERVER_SERVICE,
        )

    async def record_step(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str,
        step_id: str,
        ordinal: int,
        label: str | None = None,
        effects: list[str] | None = None,
        steps_total: int | None = None,
        dedup_key: str | None = None,
        source: EventSource | str = EventSource.WORKER,
    ) -> RunMutationResult:
        """记录步进进度（run.step_completed 事件；不改状态；终态拒绝）。

        进度按**绝对序号**上报（UI 语义「正在执行 2/4」天然幂等）：ordinal ≤
        已记录值视为重放 no-op。读取走 ``FOR UPDATE`` 行锁（R2 F5）：单调
        判定与写入同持锁串行化，并发乱序提交（先 4 后 3）不会把 steps_done
        回退——sqlite 测试下 FOR UPDATE 为 no-op，由 PG 行锁保证。
        """
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        if is_terminal_run_status(run.status):
            raise ValueError(f"run {run_id} is terminal ({run.status.value}); step recording rejected")
        ordinal = int(ordinal)
        if ordinal <= int(run.steps_done or 0):
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)

        now = _utcnow()
        run.steps_done = ordinal
        run.heartbeat_at = now
        if steps_total is not None:
            run.steps_total = int(steps_total)
        if label:
            run.current_stage = str(label)[:64]
        payload = {
            "schema_version": AGENT_RUN_PAYLOAD_SCHEMA,
            "run_id": str(run.id),
            "step_id": str(step_id)[:64],
            "ordinal": ordinal,
            "stage": run.current_stage,
            "steps_done": ordinal,
            "steps_total": run.steps_total,
            "effective_change": True,
        }
        if effects:
            payload["effects"] = [str(e)[:128] for e in effects][:16]
        if dedup_key:
            payload["dedup_key"] = str(dedup_key)[:128]
        event_written = await self._write_run_event_in_txn(
            run=run,
            event_name="run.step_completed",
            source=source,
            service=AGENT_RUN_SERVICE_NAME,
            payload=payload,
        )
        await self.db.commit()
        await self.db.refresh(run)
        return RunMutationResult(
            run=run, applied=True, created=False, event_name="run.step_completed", event_written=event_written
        )

    # ------------------------------------------------------------------
    # intent → run 投影（消费 event_bus EXECUTION_STATUS_CHANGED）
    # ------------------------------------------------------------------

    async def project_intent_status(
        self,
        *,
        intent_id: UUID | str,
        user_id: UUID | str,
        new_status: str,
        task_id: UUID | str | None = None,
    ) -> RunMutationResult | None:
        """把 ExecutionIntent 状态漏斗事件投影到 run 脊柱。

        at-least-once 投递下的收敛契约（R2 F1/F2/F3 返修）：

        - **活跃 run 存在**：状态不同则迁移（FOR UPDATE+复查吸收重复投递）。
          QUEUED run 收到 SUCCEEDED/PARTIAL（中间事件丢失的迟到终态）经
          ``QUEUED→RUNNING→终态`` 两步合法收敛——不加禁边、不吞事件、不等
          sweep（封闭迁移图不变）；
        - **无活跃 run 且该 intent 从无 run**：迟到 catch-up 建档（含终态直接
          建档，from=None 审计 + 终态归因，R2 F7）；
        - **无活跃 run 且已有终态 run**：绝不盲目 create——终态事件重投/迟到
          一律 no-op（投影收敛到既有终态记录：同一终态事件投 N 次恒 1 条 run，
          无双终态并存，R2 F1）；非终态事件仅在 intent 行**当前非终态**（真实
          retry 复位 / queue_stale 修正）且既有终态归因非
          :data:`NON_RESURRECTABLE_CANCEL_REASONS`（用户取消不复活，R2 F2）
          时才开新 attempt。
        """
        intent_uuid = UUID(str(intent_id))
        target = run_status_for_intent_status(new_status)

        active_run = await self._find_active_run_for_intent(intent_uuid)
        if active_run is not None:
            current = RunStatus(active_run.status)
            if current is target:
                return None  # 重复投递 no-op
            if current is RunStatus.QUEUED and target in (RunStatus.SUCCEEDED, RunStatus.PARTIAL):
                # QUEUED 无直达成败边（"从未启动不可能成功"是封闭图语义）。
                # 中间 dispatched/running 事件丢失时补一步 RUNNING（如实记录
                # "确实启动过"），再落终态——两步均合法边，图零改动。
                await self.transition(
                    active_run.id,
                    RunStatus.RUNNING,
                    actor=TransitionActor.PROJECTION,
                    source=EventSource.WORKER,
                    details={"intent_status": str(new_status), "catch_up": True},
                )
            reason = self._projection_reason(intent_status=new_status, target=target)
            return await self.transition(
                active_run.id,
                target,
                actor=TransitionActor.PROJECTION,
                reason=reason,
                idempotency_key=None,
                error_category=("intent_terminal_reason" if is_terminal_run_status(target) else None),
                source=EventSource.WORKER,
                details={"intent_status": str(new_status)},
            )

        # 无活跃 run：先过幻影守卫（R2 F1）——只有"允许 create"才继续。
        latest = await self._find_latest_run_for_intent(intent_uuid)
        if latest is not None and is_terminal_run_status(latest.status):
            if is_terminal_run_status(target):
                # 终态事件重投/迟到（含 sweep 已判 UNKNOWN_OUTCOME 后迟到的
                # succeeded）：既有终态记录即结论——不铸第二条终态 run。
                logger.info(
                    "run projection converged to existing terminal: run_id={} status={} reason={} "
                    "(redelivered/late terminal event intent_status={})",
                    latest.id,
                    latest.status.value if latest.status else None,
                    latest.terminal_reason,
                    str(new_status),
                )
                return None
            # 非终态事件 + 既有终态 run：仅真实复位才开新 attempt。
            if latest.terminal_reason in NON_RESURRECTABLE_CANCEL_REASONS:
                # 用户取消/handed_back 在同一 intent 下不可复活（R2 F2）；
                # 即使 intent 行因传播部分失败仍非终态，取消也不被视觉撤销。
                logger.info(
                    "run projection refuses resurrection of cancelled run_id={} reason={} " "(stale intent_status={})",
                    latest.id,
                    latest.terminal_reason,
                    str(new_status),
                )
                return None
            intent_is_terminal = await self._intent_row_is_terminal(intent_uuid)
            if intent_is_terminal is None or intent_is_terminal:
                # intent 行缺失（无权威复位证据）或已终态（乱序迟到的旧非终态
                # 事件）→ no-op：真值已记录；真 retry 走 retry_intent 开新 intent。
                logger.info(
                    "run projection no-op: intent row terminal-or-missing for intent_id={} (stale intent_status={})",
                    intent_uuid,
                    str(new_status),
                )
                return None
            # intent 行非终态 = 真实复位（retry 同 intent 复位 / queue_stale 推测
            # 被迟到的启动证伪）→ 允许开新 attempt，如实记录。

        attempt = (await self._count_runs_for_intent(intent_uuid)) + 1
        objective = await self._resolve_intent_objective(intent_uuid) or f"Execution run (intent {intent_uuid})"
        risk_class = await self._resolve_task_risk_class(task_id)
        terminal_reason = (
            self._projection_reason(intent_status=new_status, target=target) if is_terminal_run_status(target) else None
        )
        return await self.create_run(
            user_id=user_id,
            objective=objective,
            kind=AgentRunKind.EXECUTION,
            idempotency_key=intent_attempt_key(intent_uuid, attempt),
            task_id=task_id,
            intent_id=intent_uuid,
            attempt=attempt,
            risk_class=risk_class,
            initial_status=target,
            terminal_reason=terminal_reason,
            actor=TransitionActor.PROJECTION,
            source=EventSource.WORKER,
        )

    @staticmethod
    def _projection_reason(*, intent_status: str, target: RunStatus) -> str | None:
        if not is_terminal_run_status(target):
            return None
        if target is RunStatus.CANCELLED:
            # handed_back → CANCELLED(handed_back)；intent canceled → user_cancelled。
            return "handed_back" if str(intent_status).strip().lower() == "handed_back" else "user_cancelled"
        return {
            RunStatus.SUCCEEDED: "completed",
            RunStatus.PARTIAL: "completed_partial",
            RunStatus.FAILED: "failed",
            RunStatus.TIMED_OUT: "timeout",
        }.get(target)

    # ------------------------------------------------------------------
    # worker restart 恢复（明确 terminal）
    # ------------------------------------------------------------------

    async def recover_stale_runs(
        self,
        *,
        stale_after_seconds: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """恢复 sweep：孤儿/过期 run 迁移到明确状态（AGENT_RUNTIME.md §5）。

        - QUEUED 心跳陈旧 → CANCELLED(queue_stale)：从未启动，无未知效果；
        - AWAITING_* wait_expires_at 已过 → TIMED_OUT(wait_expired)；
        - AWAITING_*/RUNNING/EXECUTING 心跳陈旧 → UNKNOWN_OUTCOME
          (worker_restart_orphan)：已发生 side effect 不假装知道结果；
        - execution 轨道 intent 已终态但 run 仍活跃 → 投影修复终态
          (projection_drift_repair)。
        """
        stale_after = int(stale_after_seconds or DEFAULT_STALE_AFTER_SECONDS)
        cutoff = _utcnow() - timedelta(seconds=stale_after)
        now = _utcnow()

        actions: list[dict[str, Any]] = []
        stmt = (
            select(AgentRun)
            .where(
                AgentRun.deleted_at.is_(None),
                AgentRun.status.in_([s.value for s in ACTIVE_RUN_STATUSES]),
            )
            .order_by(AgentRun.heartbeat_at.asc())
            .limit(max(1, min(int(limit), 1000)))
        )
        runs = list((await self.db.execute(stmt)).scalars().all())

        for run in runs:
            status = RunStatus(run.status)
            try:
                if status is RunStatus.QUEUED:
                    # intent 漂移修复优先于 queue_stale 推测（R2 F3）：intent 已
                    # 终态即先落真值——实际成功的 run 绝不以 CANCELLED(queue_stale)
                    # 收场。漂移判据与 AWAITING 分支同构（intent 行真源比对）。
                    drift = await self._intent_drift_target(run)
                    if drift is not None:
                        target, reason = drift
                        result = await self._apply_drift_repair(run, target, reason)
                        actions.append(self._action(run, result, "drift_repaired"))
                    elif run.heartbeat_at and run.heartbeat_at < cutoff:
                        result = await self.transition(
                            run.id,
                            RunStatus.CANCELLED,
                            actor=TransitionActor.RECOVERY,
                            reason="queue_stale",
                            source=EventSource.WORKER,
                        )
                        actions.append(self._action(run, result, "queue_stale_cancelled"))
                elif status in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
                    # intent 漂移修复优先：intent 已终态即落终态，不等等待窗口。
                    drift = await self._intent_drift_target(run)
                    if drift is not None:
                        target, reason = drift
                        result = await self.transition(
                            run.id,
                            target,
                            actor=TransitionActor.RECOVERY,
                            reason=reason,
                            source=EventSource.WORKER,
                        )
                        actions.append(self._action(run, result, "drift_repaired"))
                    elif run.wait_expires_at and run.wait_expires_at < now:
                        result = await self.transition(
                            run.id,
                            RunStatus.TIMED_OUT,
                            actor=TransitionActor.RECOVERY,
                            reason="wait_expired",
                            source=EventSource.WORKER,
                        )
                        actions.append(self._action(run, result, "wait_expired_timed_out"))
                    elif run.heartbeat_at and run.heartbeat_at < cutoff:
                        result = await self.transition(
                            run.id,
                            RunStatus.UNKNOWN_OUTCOME,
                            actor=TransitionActor.RECOVERY,
                            reason="worker_restart_orphan",
                            source=EventSource.WORKER,
                        )
                        actions.append(self._action(run, result, "orphan_unknown_outcome"))
                elif status in (RunStatus.RUNNING, RunStatus.EXECUTING):
                    if run.heartbeat_at and run.heartbeat_at < cutoff:
                        # intent 漂移修复优先于孤儿判定：intent 已终态 → 投影终态。
                        drift = await self._intent_drift_target(run)
                        if drift is not None:
                            target, reason = drift
                            result = await self.transition(
                                run.id,
                                target,
                                actor=TransitionActor.RECOVERY,
                                reason=reason,
                                source=EventSource.WORKER,
                            )
                            actions.append(self._action(run, result, "drift_repaired"))
                        else:
                            result = await self.transition(
                                run.id,
                                RunStatus.UNKNOWN_OUTCOME,
                                actor=TransitionActor.RECOVERY,
                                reason="worker_restart_orphan",
                                source=EventSource.WORKER,
                            )
                            actions.append(self._action(run, result, "orphan_unknown_outcome"))
            except ValueError as exc:
                logger.warning(
                    "run recovery skipped run_id={} status={} error={}",
                    run.id,
                    status.value,
                    exc,
                )
                actions.append({"run_id": str(run.id), "status": status.value, "skipped": str(exc)})

        return {
            "stale_after_seconds": stale_after,
            "scanned": len(runs),
            "applied": sum(1 for a in actions if a.get("applied")),
            "actions": actions,
        }

    async def _apply_drift_repair(
        self,
        run: AgentRun,
        target: RunStatus,
        reason: str,
    ) -> RunMutationResult:
        """漂移修复迁移（recovery actor）。

        QUEUED → SUCCEEDED/PARTIAL 是封闭图禁边（"从未启动不可能成功"）；
        但漂移场景的语义是"中间事件丢失、执行其实发生过"——经
        ``QUEUED→RUNNING→终态`` 两步合法边收敛，与投影路径的迟到终态收敛
        同构（R2 F3）。图不加边、终态封闭不变。
        """
        current = RunStatus(run.status)
        if current is RunStatus.QUEUED and target in (RunStatus.SUCCEEDED, RunStatus.PARTIAL):
            await self.transition(
                run.id,
                RunStatus.RUNNING,
                actor=TransitionActor.RECOVERY,
                source=EventSource.WORKER,
                details={"drift_repair_catch_up": True},
            )
        return await self.transition(
            run.id,
            target,
            actor=TransitionActor.RECOVERY,
            reason=reason,
            source=EventSource.WORKER,
        )

    async def _intent_drift_target(self, run: AgentRun) -> tuple[RunStatus, str] | None:
        """execution 轨道 run 的 intent 已终态而 run 仍活跃 → 返回修复目标。"""
        if run.intent_id is None:
            return None
        intent = await self.db.get(ExecutionIntent, run.intent_id)
        if intent is None or intent.status is None:
            return None
        if intent.status not in _INTENT_TERMINAL_STATUSES:
            return None
        target = INTENT_STATUS_TO_RUN_STATUS[intent.status.value]
        if RunStatus(run.status) is target:
            return None
        reason = self._projection_reason(intent_status=intent.status.value, target=target)
        return target, (reason or "projection_drift_repair")

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _action(run: AgentRun, result: RunMutationResult, kind: str) -> dict[str, Any]:
        return {
            "run_id": str(run.id),
            "kind": kind,
            "applied": result.applied,
            "to": result.run.status.value if result.run.status else None,
        }

    async def _find_by_idempotency_key(self, user_uuid: UUID, key: str) -> AgentRun | None:
        stmt = select(AgentRun).where(
            AgentRun.user_id == user_uuid,
            AgentRun.idempotency_key == key,
            AgentRun.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _find_transition(self, run_uuid: UUID, key: str) -> AgentRunTransition | None:
        stmt = select(AgentRunTransition).where(
            AgentRunTransition.run_id == run_uuid,
            AgentRunTransition.idempotency_key == key,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _find_active_run_for_intent(self, intent_uuid: UUID) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(
                AgentRun.intent_id == intent_uuid,
                AgentRun.deleted_at.is_(None),
                AgentRun.status.in_([s.value for s in ACTIVE_RUN_STATUSES]),
            )
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _find_latest_run_for_intent(self, intent_uuid: UUID) -> AgentRun | None:
        """该 intent 的最新一条 run（任意状态；attempt 单调，取最大 attempt）。"""
        stmt = (
            select(AgentRun)
            .where(AgentRun.intent_id == intent_uuid, AgentRun.deleted_at.is_(None))
            .order_by(AgentRun.attempt.desc(), AgentRun.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _intent_row_is_terminal(self, intent_uuid: UUID) -> bool | None:
        """intent 行当前是否终态；行缺失/无状态返回 ``None``（与 False 区分）。

        F1 幻影守卫的真源比对：事件只是触发器，intent 行的协议状态才是复位
        证据——行缺失时"无权威证据"，同样不允许开新 attempt。
        """
        intent = await self.db.get(ExecutionIntent, intent_uuid)
        if intent is None or intent.status is None:
            return None
        return intent.status in _INTENT_TERMINAL_STATUSES

    async def _count_runs_for_intent(self, intent_uuid: UUID) -> int:
        result = await self.db.execute(select(func.count(AgentRun.id)).where(AgentRun.intent_id == intent_uuid))
        return int(result.scalar_one() or 0)

    async def _resolve_intent_objective(self, intent_uuid: UUID) -> str | None:
        intent = await self.db.get(ExecutionIntent, intent_uuid)
        if intent is None or not intent.goal:
            return None
        return str(intent.goal)[:500]

    async def _resolve_task_risk_class(self, task_id: UUID | str | None) -> str | None:
        if task_id is None:
            return None
        try:
            from app.models.task import Task

            task = await self.db.get(Task, UUID(str(task_id)))
            if task is not None and getattr(task, "risk_class", None):
                return str(task.risk_class)
        except Exception:  # noqa: BLE001 — risk_class 是增强字段，缺失不阻塞投影
            return None
        return None

    # ------------------------------------------------------------------
    # event_outbox 同事务写入（M-07 galaxy writer 模式照抄；见模块 docstring）
    # ------------------------------------------------------------------

    async def _write_run_event_in_txn(
        self,
        *,
        run: AgentRun,
        event_name: str,
        source: EventSource | str,
        service: str,
        payload: dict[str, Any],
    ) -> bool:
        if not await self._outbox_tables_exist():
            logger.warning("run event skipped: event_outbox tables unavailable run_id={}", run.id)
            return False

        sequence_number = await self._next_sequence(AGENT_RUN_AGGREGATE_TYPE, run.id)
        correlation: dict[str, str] = {"run_id": str(run.id)}
        if run.task_id:
            correlation["task_id"] = str(run.task_id)
        if run.session_id:
            correlation["session_id"] = str(run.session_id)
        metadata = build_event_metadata(
            user_id=run.user_id,
            source=source,
            service=service,
            event_name=event_name,
            aggregate_type=AGENT_RUN_AGGREGATE_TYPE,
            aggregate_id=run.id,
            sequence_number=sequence_number,
            correlation=CorrelationIds(**correlation),
            extra={
                "run_state_machine_version": RUN_STATE_MACHINE_VERSION,
            },
        )
        await self.db.execute(
            text("""
                INSERT INTO event_outbox
                (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
                """),
            {
                "aggregate_type": AGENT_RUN_AGGREGATE_TYPE,
                "aggregate_id": str(run.id),
                "event_type": event_name,
                "sequence_number": sequence_number,
                "payload": json.dumps(payload, ensure_ascii=False),
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )
        return True

    async def _outbox_tables_exist(self) -> bool:
        connection = await self.db.connection()
        return await connection.run_sync(lambda sync_conn: _has_table(sync_conn, "event_outbox"))

    async def _next_sequence(self, aggregate_type: str, aggregate_id: UUID) -> int:
        """单调 per-aggregate 序列（M-07 `_next_sequence` 同法）。"""
        try:
            result = await self.db.execute(
                text("""
                    INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                    VALUES (:aggregate_type, :aggregate_id, 1)
                    ON CONFLICT (aggregate_type, aggregate_id)
                    DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                    RETURNING next_sequence
                    """),
                {"aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)},
            )
            return int(result.scalar_one())
        except Exception as exc:  # noqa: BLE001 — sqlite 等方言退化读改写
            logger.debug("run event sequence upsert fallback ({})", exc)
            current_result = await self.db.execute(
                text(
                    "SELECT next_sequence FROM event_sequence_counters "
                    "WHERE aggregate_type = :t AND aggregate_id = :a"
                ),
                {"t": aggregate_type, "a": str(aggregate_id)},
            )
            current = current_result.scalar_one_or_none()
            if current is None:
                await self.db.execute(
                    text(
                        "INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence) "
                        "VALUES (:t, :a, 1)"
                    ),
                    {"t": aggregate_type, "a": str(aggregate_id)},
                )
                return 1
            nxt = int(current) + 1
            await self.db.execute(
                text(
                    "UPDATE event_sequence_counters SET next_sequence = :n "
                    "WHERE aggregate_type = :t AND aggregate_id = :a"
                ),
                {"n": nxt, "t": aggregate_type, "a": str(aggregate_id)},
            )
            return nxt


def _has_table(sync_conn, name: str) -> bool:
    from sqlalchemy import inspect

    try:
        return inspect(sync_conn).has_table(name)
    except Exception:  # noqa: BLE001
        return False
