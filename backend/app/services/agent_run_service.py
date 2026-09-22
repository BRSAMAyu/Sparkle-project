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
    RunStateError,
    RunStatus,
    RunWaitKind,
    event_name_for_transition,
    is_terminal_run_status,
    run_status_for_intent_status,
    terminal_reason_vocabulary,
)
from app.core.run_steps import (
    RUN_STEPS_CONTRACT_VERSION,
    find_step,
    first_incomplete_step,
    normalize_artifact_refs,
    normalize_run_steps,
    reconcile_step_counters,
    step_completion_stamped,
)
from app.models.agent_run import AgentRun, AgentRunKind, AgentRunTransition
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus

AGENT_RUN_PAYLOAD_SCHEMA = RUN_STATE_MACHINE_VERSION  # "agent_run.v2"
AGENT_RUN_AGGREGATE_TYPE = "agent_run"
AGENT_RUN_SERVICE_NAME = "agent_run_service"

# ---------------------------------------------------------------------------
# X-06 · Run Budget（token/cost/time/tool_calls 四维；fail-closed + 明确终态）
# ---------------------------------------------------------------------------

#: budget 限额键的封闭词表（四维；AGENT_RUNTIME.md §3 Run contract budget）。
BUDGET_LIMIT_KEYS: frozenset[str] = frozenset(
    {
        "max_total_tokens",  # LLM token 总量
        "max_cost_usd",  # 成本（USD，工具 cost_usd + LLM 估计）
        "max_duration_seconds",  # 墙钟时长
        "max_tool_calls",  # 工具调用次数
    }
)

#: usage 计数键（run.budget["usage"]；record_run_usage 维护）。
BUDGET_USAGE_KEYS: frozenset[str] = frozenset({"tool_calls", "total_tokens", "cost_usd"})


class BudgetExceededError(ValueError):
    """预算超限（评估结果为超时的显式信号；executor 据此拒绝调用）。"""


@dataclass(frozen=True)
class BudgetEvaluation:
    """一次预算评估的只读快照（纯数据，不落库）。

    ``exceeded`` 为超限维度列表（空 = 未超限）。维度名 ∈
    {"tool_calls", "total_tokens", "cost_usd", "duration_seconds"}。
    """

    limits: dict[str, float]
    usage: dict[str, float]
    elapsed_seconds: float | None
    exceeded: list[str]

    @property
    def is_exceeded(self) -> bool:
        return bool(self.exceeded)


def normalize_budget(budget: dict[str, Any] | None) -> dict[str, Any]:
    """归一化 + 校验 budget 形状（fail-closed：未知键/非正数/垃圾值一律 ValueError）。

    canonical 形状：``{"limits": {…四维可选…}, "usage": {tool_calls, total_tokens,
    cost_usd}}``。空/缺失 → 无限额（unlimited）。X-05 之前无任何 budget 生产者，
    无 legacy 形状兼容负担。
    """
    if budget is None:
        budget = {}
    if not isinstance(budget, dict):
        raise ValueError(f"budget must be a dict, got {type(budget).__name__}")
    unknown = set(budget) - {"limits", "usage"}
    if unknown:
        raise ValueError(f"unknown budget keys {sorted(unknown)} (allowed: limits, usage)")

    limits_in = budget.get("limits") or {}
    usage_in = budget.get("usage") or {}
    if not isinstance(limits_in, dict) or not isinstance(usage_in, dict):
        raise ValueError("budget.limits and budget.usage must be dicts")

    limits: dict[str, float] = {}
    for key, value in limits_in.items():
        if key not in BUDGET_LIMIT_KEYS:
            raise ValueError(f"unknown budget limit {key!r} (closed vocabulary: {sorted(BUDGET_LIMIT_KEYS)})")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"budget limit {key!r} must be a positive number, got {value!r}")
        limits[key] = float(value)

    usage: dict[str, float] = {"tool_calls": 0.0, "total_tokens": 0.0, "cost_usd": 0.0}
    for key, value in usage_in.items():
        if key not in BUDGET_USAGE_KEYS:
            raise ValueError(f"unknown budget usage key {key!r} (closed vocabulary: {sorted(BUDGET_USAGE_KEYS)})")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"budget usage {key!r} must be a non-negative number, got {value!r}")
        usage[key] = float(value)

    return {"limits": limits, "usage": usage}


def evaluate_budget(
    run: AgentRun,
    *,
    now: datetime | None = None,
    prospective_tool_calls: int = 0,
) -> BudgetEvaluation:
    """评估 run 预算（纯读；不迁移状态）。

    - ``max_tool_calls``：已记录 usage.tool_calls + prospective（本次待执行
      调用数）超过限额即超限——闸门语义（先检后执行）；
    - ``max_duration_seconds``：elapsed = now − (started_at|created_at)；
    - token/cost：usage 计数对比限额。
    """
    budget = run.budget if isinstance(run.budget, dict) else {}
    limits = budget.get("limits") or {}
    usage = budget.get("usage") or {}
    elapsed_seconds: float | None = None
    exceeded: list[str] = []

    now = now or _utcnow()
    usage_tool_calls = float(usage.get("tool_calls") or 0)
    usage_tokens = float(usage.get("total_tokens") or 0)
    usage_cost = float(usage.get("cost_usd") or 0)

    max_tool_calls = limits.get("max_tool_calls")
    if max_tool_calls is not None and usage_tool_calls + max(0, int(prospective_tool_calls)) > float(max_tool_calls):
        exceeded.append("tool_calls")
    max_tokens = limits.get("max_total_tokens")
    if max_tokens is not None and usage_tokens > float(max_tokens):
        exceeded.append("total_tokens")
    max_cost = limits.get("max_cost_usd")
    if max_cost is not None and usage_cost > float(max_cost):
        exceeded.append("cost_usd")
    max_duration = limits.get("max_duration_seconds")
    if max_duration is not None:
        origin = run.started_at or run.created_at
        if origin is not None:
            elapsed_seconds = max(0.0, (now - origin).total_seconds())
            if elapsed_seconds > float(max_duration):
                exceeded.append("duration_seconds")

    return BudgetEvaluation(
        limits={k: float(v) for k, v in limits.items()},
        usage={"tool_calls": usage_tool_calls, "total_tokens": usage_tokens, "cost_usd": usage_cost},
        elapsed_seconds=elapsed_seconds,
        exceeded=exceeded,
    )


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

#: 客户端 cancel 允许的终态归因子集（FIX-29 N3）。取消是**用户语义**操作，
#: 合法归因只有 ``user_cancelled``；terminal_reason_vocabulary 内其余词
#: （timeout/queue_stale/worker_restart_orphan/...）是系统侧判定词，客户端
#: 不得借 cancel 代系统归因（词表内子集白名单，拒绝任意串）。
CLIENT_CANCEL_REASON_WHITELIST: frozenset[str] = frozenset({"user_cancelled"})

#: 步进里程碑驱动的 EXECUTING 投影允许的源状态（X-05B）。里程碑事件是执行
#: 进度的**增强可见性**，不是状态真源——只允许从"未在等待"的活跃态落
#: EXECUTING；AWAITING_* 等待态不因（重投/乱序的）迟到步进被覆盖（等待的
#: 解除属于 intent 状态漏斗或用户 resume/cancel，单一真源）。
_MILESTONE_LANDING_SOURCES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.QUEUED,
        RunStatus.RUNNING,
    }
)


#: intent 投影创建 run 的确定性幂等键（同 intent 同 attempt 恰一次 run.created）。
def intent_attempt_key(intent_id: UUID | str, attempt: int) -> str:
    return f"intent:{str(intent_id)}:attempt:{int(attempt)}"


def normalize_run_permissions(permissions: dict[str, Any] | None) -> dict[str, Any]:
    """校验/归一化 run 权限声明（X-06 fail-closed：能力词越表即 ValueError）。

    canonical 形状：``{"granted": [cap...]|None, "denied": [cap...]}``（均可省）。
    granted=None 语义 = 用服务端默认授权集（DEFAULT_AGENT_TOOL_GRANTS）。
    """
    from app.tools.metadata import TOOL_PERMISSION_VOCABULARY  # 局部导入避免环

    if permissions is None:
        permissions = {}
    if not isinstance(permissions, dict):
        raise ValueError(f"permissions must be a dict, got {type(permissions).__name__}")
    unknown = set(permissions) - {"granted", "denied"}
    if unknown:
        raise ValueError(f"unknown permissions keys {sorted(unknown)} (allowed: granted, denied)")
    normalized: dict[str, Any] = {}
    for key in ("granted", "denied"):
        if key not in permissions or permissions[key] is None:
            normalized[key] = None if key == "granted" else []
            continue
        raw = permissions[key]
        if not isinstance(raw, (list, tuple, set)):
            raise ValueError(f"permissions.{key} must be a list of capability names")
        caps: list[str] = []
        for item in raw:
            cap = str(item).strip()
            if cap not in TOOL_PERMISSION_VOCABULARY:
                raise ValueError(
                    f"permissions.{key} contains unknown capability {cap!r} "
                    f"(closed vocabulary: {sorted(TOOL_PERMISSION_VOCABULARY)})"
                )
            caps.append(cap)
        normalized[key] = sorted(set(caps))
    return normalized


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _stamp_step_awaiting(
    steps: list[dict[str, Any]],
    *,
    step_id: str,
    prompt: str | None,
    artifact_refs: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    """在目标步骤上落 ``awaiting`` 戳（prompt + Agent 准备好的产物引用）。

    X-07 · Agent 产物持久化面：artifacts 以 ``{"scheme","ref"}`` 引用内嵌步骤
    记录（本体真源留在既有机制——action_proposal receipt / tool_call 账本 /
    evidence；C-01 scheme 对齐，不复制本体）。重复落戳（重投）以最后一次为
    准（提示文案可更新；引用同 key 语义收敛）。
    """
    stamped = str(step_id).strip()
    updated: list[dict[str, Any]] = []
    for step in steps:
        if step.get("step_id") == stamped:
            entry = dict(step)
            awaiting: dict[str, Any] = {"awaited_at": _utcnow().isoformat(timespec="milliseconds")}
            if prompt:
                awaiting["prompt"] = str(prompt)[:500]
            refs = normalize_artifact_refs(artifact_refs)
            if refs:
                awaiting["artifacts"] = refs
            entry["awaiting"] = awaiting
            updated.append(entry)
        else:
            updated.append(step)
    return updated


class RunNotFoundError(ValueError):
    """run 不存在或不属于该用户（API 层 404；与 _get_user_intent 同形）。"""


class InvalidCancelReasonError(RunStateError):
    """cancel reason 不在客户端白名单内（FIX-29 N3；API 层 422）。

    与 :class:`InvalidResumeTargetError` 同族：服务端封闭白名单拒绝客户端
    自选任意串。注意先于 ``RunStateError`` 捕获（子类）。
    """


class TransitionActor(StrEnum):
    USER = "user"
    WORKER = "worker"
    SYSTEM = "system"
    RECOVERY = "recovery"
    PROJECTION = "projection"


# ---------------------------------------------------------------------------
# X-07 · Hybrid Handoff（run step owner/完成条件/产物引用 + awaiting/resume）
# ---------------------------------------------------------------------------


class UnknownRunStepError(RunStateError):
    """step_id 不在该 run 的步骤计划中（API 层 404）。"""


class RunStepPlanConflictError(RunStateError):
    """步骤计划与已持久化计划冲突（plan 只许定义一次；同内容重投幂等 no-op）。"""


class RunNotAwaitingUserStepError(RunStateError):
    """complete_user_step 前置不满足：run 未处于等待用户步骤状态（API 层 409）。"""


class MissingIdempotencyKeyError(RunStateError):
    """complete_user_step 必须携带幂等键（「两次确认只 resume 一次」的服务端
    依据；API 层 422，resume/cancel 白名单拒绝同族）。"""


@dataclass(frozen=True)
class UserStepResult:
    """一次用户步骤完成（confirm/edit）的结果.

    ``applied=False`` = 幂等重放（该步骤已有完成戳——双击/重试/换 key 重发
    一律收敛到第一次，绝不二次 resume）；``resumed`` = 本次调用实际触发了
    run 恢复迁移（``run.user_resumed``）。
    """

    run: AgentRun
    step: dict[str, Any]
    applied: bool
    resumed: bool = False
    event_name: str | None = None
    replay: bool = False


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
        steps: list[dict[str, Any]] | None = None,
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

        # X-06 fail-closed 契约校验：budget 四维/permissions 能力词越表即拒绝创建。
        # O-07 · budget by user/run/tier：未显式携带 budget 时按 entitlement 派生
        # 四维默认限额（薄派生层 app/core/budget_matrix.py；词表/校验仍是本模块
        # normalize_budget 单一真源）。派生读 users.entitlement；读取异常按 free
        # 收敛（宁降不升，与 entitlement.py fail-safe 同向），run 不再默认无界。
        if budget is None:
            budget = await self._derive_default_budget_for_user(user_uuid)
        budget_canonical = normalize_budget(budget)
        permissions_canonical = normalize_run_permissions(permissions)
        steps_canonical = normalize_run_steps(steps)  # X-07：计划契约 fail-closed（越表拒绝创建）

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
            allowed_tools=[str(t) for t in (allowed_tools or [])],
            permissions=permissions_canonical,
            budget=budget_canonical,
            completion_condition=dict(completion_condition or {}),
            risk_class=risk_class,
            status=initial,
            wait_kind=None,
            wait_expires_at=None,
            steps=steps_canonical,
            # X-07 P2-1：有计划时计划长度即步骤总数真源（显式 steps_total 仅
            # 在无计划时生效——两处进度不得分叉）。
            steps_total=len(steps_canonical) or (int(steps_total) if steps_total else None),
            task_id=UUID(str(task_id)) if task_id else None,
            intent_id=UUID(str(intent_id)) if intent_id else None,
            session_id=str(session_id)[:64] if session_id else None,
            trace_id=str(trace_id)[:64] if trace_id else None,
            attempt=int(attempt) or 1,
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
        # X-07 P2-1 · 双计数统一：有计划时计数收口到计划派生值（单调兜底）；
        # 无计划原值透传（X-05 轨道零改动）。
        run.steps_done, run.steps_total = reconcile_step_counters(
            steps_done=run.steps_done,
            steps_total=run.steps_total,
            steps=run.steps,
        )
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
    # X-06 · run budget（四维预算：评估/强制/记账；超限 → BUDGET_EXCEEDED）
    # ------------------------------------------------------------------

    async def evaluate_run_budget(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str | None = None,
        now: datetime | None = None,
        prospective_tool_calls: int = 0,
    ) -> tuple[AgentRun, BudgetEvaluation]:
        """只读评估（不迁移状态）；返回 (run, evaluation) 供调度层决策。"""
        run = await self.get_run(run_id, user_id=user_id)
        evaluation = evaluate_budget(run, now=now, prospective_tool_calls=prospective_tool_calls)
        return run, evaluation

    async def enforce_budget(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str | None = None,
        prospective_tool_calls: int = 1,
        now: datetime | None = None,
    ) -> BudgetEvaluation:
        """预算强制闸门（executor 每次工具调用前调用；超限 → 明确终态）。

        - 未超限 → 返回 evaluation（exceeded 空），调用放行；
        - 超限 → 经封闭迁移图迁移 ``→ BUDGET_EXCEEDED``（reason=
          ``budget_exceeded``，审计行 + run.status_changed 事件同事务，与
          其他终态迁移同构——卡面「非无限执行、非静默截断」）；
        - run 已终态（含已是 BUDGET_EXCEEDED）→ 不迁移（FOR UPDATE+复查/
          IllegalRunTransitionError 吸收），exceeded 如实返回。

        Raises:
            BudgetExceededError: 超限（携带 evaluation；executor 据此拒绝调用）。
        """
        run = await self.get_run(run_id, user_id=user_id)
        evaluation = evaluate_budget(run, now=now, prospective_tool_calls=prospective_tool_calls)
        if not evaluation.is_exceeded:
            return evaluation

        details = {
            "budget_exceeded": evaluation.exceeded,
            "limits": evaluation.limits,
            "usage": evaluation.usage,
            "elapsed_seconds": evaluation.elapsed_seconds,
        }
        try:
            await self.transition(
                run.id,
                RunStatus.BUDGET_EXCEEDED,
                user_id=user_id,
                actor=TransitionActor.WORKER,
                reason="budget_exceeded",
                error_category="budget_exceeded",
                error_message=f"run budget exceeded: {', '.join(evaluation.exceeded)}",
                details=details,
                source=EventSource.WORKER,
            )
        except (ValueError, RunNotFoundError) as exc:
            # 已终态（终态封闭）/并发迁移已收敛：终态即结论，不掩盖超限事实。
            logger.info(
                "budget terminal transition converged run_id={} status_now={} error={}",
                run.id,
                run.status,
                exc,
            )
        raise BudgetExceededError(f"run {run.id} budget exceeded: {', '.join(evaluation.exceeded)}") from None

    async def record_run_usage(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str | None = None,
        tool_calls: int = 0,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> AgentRun:
        """记录预算消耗（FOR UPDATE 行锁串行化；终态 run 拒绝记账）。

        usage 计数是 budget 维度的唯一真源（agent_runs.budget.usage）；
        agent_tool_calls 是审计账本，两者不互为计数器。
        """
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        if is_terminal_run_status(run.status):
            raise ValueError(f"run {run_id} is terminal ({run.status.value}); usage recording rejected")

        budget = dict(run.budget) if isinstance(run.budget, dict) else {}  # 拷贝后再改（JSON 列原地改不触发脏检测）
        usage = dict(budget.get("usage") or {})
        usage["tool_calls"] = float(usage.get("tool_calls") or 0) + max(0, int(tool_calls))
        usage["total_tokens"] = float(usage.get("total_tokens") or 0) + max(0, int(tokens))
        usage["cost_usd"] = round(float(usage.get("cost_usd") or 0) + max(0.0, float(cost_usd)), 6)
        budget["usage"] = usage
        run.budget = budget
        run.heartbeat_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def _derive_default_budget_for_user(self, user_id: UUID) -> dict[str, Any] | None:
        """O-07 · budget 缺省时的派生入口（entitlement → 四维 run 预算默认值）。

        真源分工：判级只认 ``users.entitlement``（经 ``normalize_entitlement``
        归一）；派生逻辑在 ``app/core/budget_matrix``（薄层，非第二真源）。
        D-REDEEM: 有效判级走 ``entitlement_effective``——``entitlement_expires_at``
        已过判 free（到期降级，宁降不升同向）。
        任何读取/派生异常一律回落 free 档派生值——预算派生是收紧面，故障方向
        必须是「更保守」而不是「更无界」。
        """
        from app.core.budget_matrix import derive_default_run_budget_if_enabled
        from app.core.entitlement import (
            ENTITLEMENT_FREE,
            entitlement_effective,
        )
        from app.models.user import User

        try:
            row = (
                await self.db.execute(
                    select(User.entitlement, User.entitlement_expires_at).where(User.id == user_id)
                )
            ).one_or_none()
            entitlement = ENTITLEMENT_FREE if row is None else entitlement_effective(row[0], row[1])
        except Exception as exc:  # noqa: BLE001 — 判级读失败 → free（宁降不升）
            logger.warning("run budget derivation: entitlement read failed user_id={} -> free ({!r})", user_id, exc)
            entitlement = ENTITLEMENT_FREE
        return derive_default_run_budget_if_enabled(entitlement)

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
        # X-06：resume 前预算闸门——等待中的 run 时间/token 预算已耗尽时，恢复
        # 执行只会立即越限；直接落 BUDGET_EXCEEDED 明确终态（非无限执行）。
        evaluation = evaluate_budget(await self.get_run(run_id, user_id=user_id))
        if evaluation.is_exceeded:
            return await self._terminalize_budget_exceeded(
                run_id,
                user_id=user_id,
                evaluation=evaluation,
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

    async def _terminalize_budget_exceeded(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str,
        evaluation: BudgetEvaluation,
    ) -> RunMutationResult:
        """resume 闸门的超限落终态（迁移 + 审计 + 事件同构）后抛 BudgetExceededError。"""
        try:
            result = await self.transition(
                run_id,
                RunStatus.BUDGET_EXCEEDED,
                user_id=user_id,
                actor=TransitionActor.USER,
                reason="budget_exceeded",
                error_category="budget_exceeded",
                error_message=f"run budget exceeded: {', '.join(evaluation.exceeded)}",
                details={
                    "budget_exceeded": evaluation.exceeded,
                    "limits": evaluation.limits,
                    "usage": evaluation.usage,
                    "elapsed_seconds": evaluation.elapsed_seconds,
                    "via": "resume_gate",
                },
                source=EventSource.SERVER_SERVICE,
            )
        except ValueError as exc:
            # 已终态（终态封闭）：FOR UPDATE+复查/非法迁移吸收——终态即结论。
            logger.info("resume budget gate converged run_id={} error={}", run_id, exc)
            result = RunMutationResult(
                run=await self.get_run(run_id, user_id=user_id),
                applied=False,
                created=False,
                event_name=None,
                event_written=False,
            )
        logger.info("resume budget gate → BUDGET_EXCEEDED run_id={} applied={}", run_id, result.applied)
        raise BudgetExceededError(f"run {run_id} budget exceeded: {', '.join(evaluation.exceeded)}") from None

    async def cancel(
        self,
        run_id: UUID | str,
        *,
        user_id: UUID | str,
        reason: str = "user_cancelled",
        idempotency_key: str | None = None,
    ) -> RunMutationResult:
        """用户取消（AGENT_RUNTIME.md §6：状态变更 + 下游协作取消）。

        ``reason`` 服务端白名单（FIX-29 N3）：客户端只能归因
        ``user_cancelled``（:data:`CLIENT_CANCEL_REASON_WHITELIST`，
        terminal_reason_vocabulary 的用户语义子集）——词表内其余终态归因是
        系统侧判定词，任意串一律 ``InvalidCancelReasonError``（API 层 422）。
        """
        reason = str(reason)
        if reason not in CLIENT_CANCEL_REASON_WHITELIST:
            raise InvalidCancelReasonError(
                f"cancel reason {reason!r} is not a client-selectable reason "
                f"(allowed: {sorted(CLIENT_CANCEL_REASON_WHITELIST)})"
            )
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
        # X-07 P2-1 · 双计数统一：有计划时 total 收口到计划长度、done 不低于
        # 计划完成戳数（max 单调兜底，序号语义不被拉回）；无计划原值透传。
        run.steps_done, run.steps_total = reconcile_step_counters(
            steps_done=run.steps_done,
            steps_total=run.steps_total,
            steps=run.steps,
        )
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
    # X-07 · Hybrid Handoff：步骤计划 / 轮到用户 / 用户完成触发 resume
    # ------------------------------------------------------------------

    async def define_run_steps(
        self,
        run_id: UUID | str,
        *,
        steps: list[dict[str, Any]],
        user_id: UUID | str | None = None,
        actor: str = TransitionActor.WORKER,
        source: EventSource | str = EventSource.WORKER,
    ) -> RunMutationResult:
        """定义/重投 run 步骤计划（``agent_runs.steps``；**计划只定义一次**）.

        - 首次定义：归一化（``normalize_run_steps`` fail-closed，越表 ValueError）
          后落库 + 刷新心跳 + 同步 ``steps_total``（未显式给过时）；
        - 同内容重投（at-least-once 生产者）：幂等 no-op（``applied=False``）；
        - 不同内容：:class:`RunStepPlanConflictError`（409）——计划是 run 契约
          的一部分，中途换计划会破坏「轮到谁」的可信度，必须显式开新 run；
        - 终态 run 拒绝（终态封闭）。

        计划定义**不改 run 状态、不发 outbox 事件**（status/事件只属于状态机；
        计划经 GET /runs 只读可见——与 ``record_step`` 的 outbox 事件面分工）。
        """
        normalized = normalize_run_steps(steps)
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        if is_terminal_run_status(run.status):
            raise ValueError(f"run {run_id} is terminal ({run.status.value}); step plan rejected")

        existing = list(run.steps or [])
        if existing:
            if normalize_run_steps(existing) == normalized:
                return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)
            raise RunStepPlanConflictError(
                f"run {run_id} already has a different step plan ({len(existing)} steps); "
                "open a new run to change the plan"
            )

        run.steps = normalized
        run.heartbeat_at = _utcnow()
        # X-07 P2-1 · 双计数统一：计划落库即步骤总数真源（len(plan) 收口，
        # 不再仅在本列为空时同步）；done 单调兜底（计划先于重投场景不回退）。
        run.steps_done, run.steps_total = reconcile_step_counters(
            steps_done=run.steps_done,
            steps_total=run.steps_total,
            steps=normalized,
        )
        await self.db.commit()
        await self.db.refresh(run)
        return RunMutationResult(run=run, applied=True, created=False, event_name=None, event_written=False)

    async def await_user_step(
        self,
        run_id: UUID | str,
        *,
        step_id: str,
        user_id: UUID | str | None = None,
        prompt: str | None = None,
        artifact_refs: list[dict[str, str]] | None = None,
        wait_expires_at: datetime | None = None,
        actor: str = TransitionActor.WORKER,
        source: EventSource | str = EventSource.WORKER,
    ) -> RunMutationResult:
        """把 run 交给用户做某一步（「轮到你」；``run.awaiting_user`` 事件）.

        - 步骤必须存在且未完成（``UnknownRunStepError`` / ValueError）；
        - 同一时刻至多一个 awaiting step（其余步骤尚未轮到——顺序执行语义）；
        - 步骤上落 ``awaiting`` 戳（prompt + Agent 准备好的 artifacts 引用——
          **Agent 产物持久化**：引用挂既有机制本体，如 ``action_proposal``/
          ``tool_call``/``evidence``，不在 run 内复制本体）；
        - run 经**既有合法边** ``→ AWAITING_USER``（wait_kind=user_step，
          wait_expires_at 供 sweep 过期 → TIMED_OUT(wait_expired)）——状态机
          词表/迁移图零改动；已在 AWAITING_USER 时只落戳（事件不重发，幂等），
          在 AWAITING_APPROVAL 时拒绝（等待类型变更无业务语义，与迁移图
          USER↔APPROVAL 禁边同哲学）；
        - 戳 + 状态迁移同事务（transition 的 commit 统一冲刷）。
        """
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        if is_terminal_run_status(run.status):
            raise ValueError(f"run {run_id} is terminal ({run.status.value}); awaiting rejected")

        steps = list(run.steps or [])
        step = find_step(steps, step_id)
        if step is None:
            raise UnknownRunStepError(f"step {step_id!r} is not in run {run_id} step plan")
        if step.get("completion"):
            raise ValueError(f"step {step_id!r} already completed; cannot await again")
        if first_incomplete_step(steps) is not step:
            raise ValueError(f"step {step_id!r} is not the next pending step; steps run in ordinal order")

        current = RunStatus(run.status)
        if current in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
            if current is RunStatus.AWAITING_APPROVAL or run.wait_kind != RunWaitKind.USER_STEP.value:
                raise ValueError(
                    f"run {run_id} is {current.value} (wait_kind={run.wait_kind}); "
                    "awaiting a user step requires a non-waiting or user_step run"
                )
            # 已在等待用户步骤：幂等落戳（同一 step 重投不重发 run.awaiting_user）。
            run.steps = _stamp_step_awaiting(steps, step_id=step_id, prompt=prompt, artifact_refs=artifact_refs)
            run.heartbeat_at = _utcnow()
            await self.db.commit()
            await self.db.refresh(run)
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)

        run.steps = _stamp_step_awaiting(steps, step_id=step_id, prompt=prompt, artifact_refs=artifact_refs)
        return await self.transition(
            run.id,
            RunStatus.AWAITING_USER,
            user_id=user_id,
            actor=actor,
            wait_kind=RunWaitKind.USER_STEP,
            wait_expires_at=wait_expires_at,
            current_stage=step.get("label"),
            details={"step_id": step["step_id"], "schema_version": RUN_STEPS_CONTRACT_VERSION},
            source=source,
        )

    async def complete_agent_step(
        self,
        run_id: UUID | str,
        *,
        step_id: str,
        user_id: UUID | str | None = None,
        artifact_refs: list[dict[str, str]] | None = None,
        idempotency_key: str | None = None,
        actor: str = TransitionActor.WORKER,
        source: EventSource | str = EventSource.WORKER,
    ) -> RunMutationResult:
        """Agent 完成自己那一步（handoff 前半段：``Agent prepares`` → 交棒）.

        - **owner 纪律**：只允许完成 ``owner=agent`` 的步骤——AGENT 不得代替
          用户完成 HUMAN/HYBRID 步骤（认知归属不可越权，HUMAN_AGENT_HYBRID.md
          §2/§3；用户的确认/编辑只能走 :meth:`complete_user_step`）；
        - 必须是下一个未完成步骤（ordinal 顺序执行）；重复完成 → 幂等 no-op；
        - 产物引用落 ``completion.artifacts``（挂既有机制本体，不复制）；
        - 发 ``run.step_completed`` 事件（D-01 既有名，进度事件不改状态）——
          **不 resume**：Agent 完成后是否交棒用户由编排层显式调用
          :meth:`await_user_step`，两个语义时刻分开（可审计）。
        """
        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")
        if is_terminal_run_status(run.status):
            raise ValueError(f"run {run_id} is terminal ({run.status.value}); step completion rejected")

        steps = list(run.steps or [])
        step = find_step(steps, step_id)
        if step is None:
            raise UnknownRunStepError(f"step {step_id!r} is not in run {run_id} step plan")
        if step.get("owner") != "agent":
            raise ValueError(
                f"step {step_id!r} is owner={step.get('owner')!r}; only agent-owned steps "
                "can be completed by the agent (human/hybrid steps go through the user path)"
            )
        if step.get("completion"):
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)
        if first_incomplete_step(steps) is not step:
            raise ValueError(f"step {step_id!r} is not the next pending step; steps run in ordinal order")

        now = _utcnow()
        updated, applied = step_completion_stamped(
            steps,
            step_id=step["step_id"],
            completed_by="agent",
            idempotency_key=str(idempotency_key or f"agent:{step['step_id']}")[:255],
            action="agent_output",
            artifact_refs=artifact_refs,
            completed_at=now.isoformat(timespec="milliseconds"),
        )
        if not applied:
            return RunMutationResult(run=run, applied=False, created=False, event_name=None, event_written=False)
        run.steps = updated
        run.heartbeat_at = now
        # X-07 P2-1 · 双计数统一：完成戳推进即计数推进（steps_done 派生自计划
        # 完成戳数，单调兜底）——此前只盖戳不动计数，UI 两处进度脱节（债项）。
        run.steps_done, run.steps_total = reconcile_step_counters(
            steps_done=run.steps_done,
            steps_total=run.steps_total,
            steps=updated,
        )
        event_written = await self._write_run_event_in_txn(
            run=run,
            event_name="run.step_completed",
            source=source,
            service=AGENT_RUN_SERVICE_NAME,
            payload={
                "schema_version": RUN_STEPS_CONTRACT_VERSION,
                "run_id": str(run.id),
                "step_id": step["step_id"],
                "ordinal": step.get("ordinal"),
                "by": "agent",
                "effective_change": True,
            },
        )
        await self.db.commit()
        await self.db.refresh(run)
        return RunMutationResult(
            run=run, applied=True, created=False, event_name="run.step_completed", event_written=event_written
        )

    async def complete_user_step(
        self,
        run_id: UUID | str,
        *,
        step_id: str,
        user_id: UUID | str,
        idempotency_key: str,
        action: str = "confirm",
        artifact_refs: list[dict[str, str]] | None = None,
        note: str | None = None,
        to_status: RunStatus | str = RunStatus.RUNNING,
        current_stage: str | None = None,
    ) -> UserStepResult:
        """用户完成（确认/编辑）当前 awaiting step —— 完成戳 + resume 原子化.

        **幂等是灵魂**（acceptance：「用户操作两次不会 resume 两次」）：

        1. ``FOR UPDATE`` 锁 run 行后先查步骤完成戳——已带戳（**无论 key 是否
           相同**，first-wins）直接返回 ``replay`` 结果，不重发事件、不再次
           resume；并发双击串行化后第二个调用看到已完成步骤同样 no-op；
        2. 完成戳（含幂等键 + 用户输入/artifact 引用）与 run 恢复迁移在同一
           事务冲刷（``transition`` 的 commit）——crash 一致性：要么「完成 +
           恢复」都落库，要么都没有；
        3. resume 复用 :meth:`resume` 全部契约（目标白名单 R2 F4 / 预算闸门 /
           ``run.user_resumed`` 事件），X-09 幂等键语义服务端强制。

        前置：run 处于等待用户步骤状态（``RunNotAwaitingUserStepError`` 409）
        ——过期（wait_expired→TIMED_OUT）/取消（user_cancelled→CANCELLED）后的
        迟到确认被明确拒绝（acceptance：「取消/过期明确」），错误信息携带当前
        终态。
        """
        key = str(idempotency_key or "").strip()
        if not key:
            raise MissingIdempotencyKeyError("complete_user_step requires an idempotency_key")

        stmt = select(AgentRun).where(AgentRun.id == UUID(str(run_id)), AgentRun.deleted_at.is_(None)).with_for_update()
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == UUID(str(user_id)))
        run = (await self.db.execute(stmt)).scalar_one_or_none()
        if run is None:
            raise RunNotFoundError(f"agent run {run_id} not found")

        steps = list(run.steps or [])
        step = find_step(steps, step_id)
        if step is None:
            raise UnknownRunStepError(f"step {step_id!r} is not in run {run_id} step plan")
        if step.get("completion"):
            # 幂等重放：完成戳已存在（双击/重试/换 key 重发一律 first-wins）。
            # 放在状态检查**之前**——第一次确认已提交、run 已回 RUNNING 后，
            # 迟到的重试同样收敛为 no-op，而不是 409 假失败。
            return UserStepResult(run=run, step=step, applied=False, resumed=False, replay=True)

        if step.get("owner") not in ("human", "hybrid"):
            # owner 纪律先于状态检查：步骤归属是固有属性，状态是瞬态。
            raise ValueError(
                f"step {step_id!r} is owner={step.get('owner')!r}; agent-owned steps are completed "
                "by the agent (user confirmation cannot substitute the agent's work)"
            )

        status = RunStatus(run.status)
        if status in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
            if run.wait_kind != RunWaitKind.USER_STEP.value:
                raise RunNotAwaitingUserStepError(
                    f"run {run_id} is {status.value} waiting for approval, not a user step"
                )
        elif is_terminal_run_status(status):
            reason = f", reason={run.terminal_reason}" if run.terminal_reason else ""
            raise RunNotAwaitingUserStepError(
                f"run {run_id} is terminal ({status.value}{reason}); "
                "late confirm rejected — cancel/expire is explicit"
            )
        else:
            raise RunNotAwaitingUserStepError(f"run {run_id} is {status.value}; no user step is being awaited")

        if first_incomplete_step(steps) is not step:
            raise ValueError(f"step {step_id!r} is not the next pending step; steps run in ordinal order")

        normalized_refs = normalize_artifact_refs(artifact_refs)
        now = _utcnow()
        updated, applied = step_completion_stamped(
            steps,
            step_id=step["step_id"],
            completed_by="user",
            idempotency_key=key,
            action=action,
            artifact_refs=normalized_refs or None,
            note=note,
            completed_at=now.isoformat(timespec="milliseconds"),
        )
        if not applied:  # 防御：上方显式重放分支已覆盖；此路径理论不可达
            return UserStepResult(run=run, step=step, applied=False, resumed=False, replay=True)
        run.steps = updated
        run.heartbeat_at = now
        # X-07 P2-1 · 双计数统一：用户步完成戳同样计入 steps_done（与
        # complete_agent_step 同法；随 resume 同事务提交）。
        run.steps_done, run.steps_total = reconcile_step_counters(
            steps_done=run.steps_done,
            steps_total=run.steps_total,
            steps=updated,
        )
        # resume（含预算闸门/目标白名单/事件）与完成戳同事务提交；超限 →
        # BUDGET_EXCEEDED 明确终态（完成戳随迁移落库——事实不被掩盖）。
        resume_result = await self.resume(
            run.id,
            user_id=user_id,
            to_status=to_status,
            idempotency_key=f"{key}:resume",
            current_stage=current_stage or step.get("label"),
        )
        return UserStepResult(
            run=resume_result.run,
            step=step,
            applied=True,
            resumed=resume_result.applied,
            event_name=resume_result.event_name,
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

    # ------------------------------------------------------------------
    # execution 步进 → run 投影（消费 event_bus run.status_changed 里程碑）
    # ------------------------------------------------------------------

    async def project_execution_step(
        self,
        *,
        intent_id: UUID | str,
        user_id: UUID | str,
        task_id: UUID | str | None = None,
        milestone: str | None = None,
        to_status: str | None = None,
        ordinal: int | None = None,
        stage: str | None = None,
        steps_total: int | None = None,
    ) -> RunMutationResult | None:
        """把 execution 轨道步进里程碑（``run.status_changed`` 漏斗事件）投影到 run。

        X-05B · EXECUTING 执行面接线。步进事件是**增强可见性**，不是 run 生命
        周期真源（真源是 intent 状态漏斗 ``execution.status_changed``），因此：

        - **无活跃 run → no-op 不铸造**：run 创建只属于状态漏斗（catch-up/
          attempt 语义在那里）；步进事件先到/状态事件丢失时静默跳过，恢复
          sweep + 漂移修复兜底（与 X-05 F1 幻影守卫同哲学）；
        - **run 已终态 → no-op**：迟到步进（终态事件先行）不上 DLQ——终态
          即结论，进度回放无意义；
        - **to_status 只从 QUEUED/RUNNING 落 EXECUTING**（:data:`_MILESTONE_
          LANDING_SOURCES`）：AWAITING_* 等待态不因迟到/乱序步进被覆盖——
          等待解除属于 intent 漏斗或用户 resume/cancel，单一真源；
        - **幂等（同 intent+attempt+step 重投恰一次）**：transition 的
          FOR UPDATE+复查吸收重复 to_status；record_step 的绝对序号单调吸收
          重复 step（ordinal ≤ steps_done → no-op）。审计同构：迁移走
          agent_run_transitions+outbox（run.status_changed），步进走
          outbox（run.step_completed）+ steps_done/current_stage/heartbeat。
        """
        intent_uuid = UUID(str(intent_id))
        target: RunStatus | None = None
        if to_status is not None and str(to_status).strip():
            try:
                target = RunStatus(str(to_status).strip())
            except ValueError:
                raise RunStateError(f"unmapped run status in step event {to_status!r}") from None

        run = await self._find_active_run_for_intent(intent_uuid)
        if run is None:
            logger.debug("run step projection skipped: no active run for intent {}", intent_uuid)
            return None
        if is_terminal_run_status(run.status):
            logger.debug("run step projection skipped: run {} already terminal ({})", run.id, run.status.value)
            return None

        results: list[RunMutationResult] = []
        if target is not None:
            current = RunStatus(run.status)
            if current is target:
                pass  # 重复投递 no-op（FOR UPDATE+复查语义在此前置吸收）
            elif current in _MILESTONE_LANDING_SOURCES:
                results.append(
                    await self.transition(
                        run.id,
                        target,
                        actor=TransitionActor.PROJECTION,
                        current_stage=stage,
                        steps_total=steps_total,
                        source=EventSource.WORKER,
                        details={"milestone": milestone, "execution_step": True},
                    )
                )
            else:
                # AWAITING_*：迟到/乱序步进不覆盖等待态（见 docstring）。
                logger.info(
                    "run step projection held status: run {} in {} keeps waiting (late milestone {})",
                    run.id,
                    current.value,
                    milestone,
                )
        if ordinal is not None:
            results.append(
                await self.record_step(
                    run.id,
                    user_id=user_id,
                    step_id=str(milestone or f"step-{ordinal}"),
                    ordinal=int(ordinal),
                    label=stage,
                    steps_total=steps_total,
                    source=EventSource.WORKER,
                )
            )
        return results[-1] if results else None

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
    # X-09 · 主动崩溃恢复（in-flight side effect 的证据驱动裁决）
    # ------------------------------------------------------------------

    async def recover_inflight_runs(
        self,
        *,
        stale_after_seconds: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """进程重启后的主动恢复决策（X-05 sweep 是兜底，本路径是主动面）.

        与 :meth:`recover_stale_runs` 的分工（协同不冲突）：

        - sweep 处理**时间陈旧**（QUEUED 陈旧 / wait 过期 / 心跳孤儿）——大窗口
          兜底（默认 6h），不依赖崩溃证据；
        - 本 pass 处理**中断证据**（账本 in_progress/interrupted 残留 = side
          effect 无法核实），窗口只覆盖工具超时长尾（默认 ~5min 起）——杀进程
          重启后**立即**可执行，不等 sweep。

        决策表（证据驱动，不依赖 worker 所有权/租约——没有租约列时全局决策
        只对**有中断证据**的 run 做不可逆裁决，其余只输出建议）：

        1. intent 已终态 → 漂移修复（真值优先，与 sweep 同构路径）；
        2. 有中断账本证据（本轮收敛或此前已 interrupted）→ ``UNKNOWN_OUTCOME``
           (worker_restart_orphan)：绝不自动重驱动——效果不可核实，重驱动可能
           造成 duplicate side effect；
        3. 无中断证据 → ``reattach_candidate``：不迁终态、不刷新心跳（避免
           掩盖真孤儿被 sweep 误判），由所属轨道（execution/chat 续驱）自行
           续驱并刷新心跳；终态 run → ``terminal_noop``。
        """
        from app.services.tool_call_ledger_service import ToolCallLedgerService

        ledger_result = await ToolCallLedgerService(self.db).reconcile_stale_in_progress(
            stale_after_seconds=stale_after_seconds,
        )

        decisions: list[dict[str, Any]] = []
        seen_runs: set[UUID] = set()
        for run_id_str in ledger_result.affected_run_ids:
            run_uuid = UUID(run_id_str)
            if run_uuid in seen_runs:
                continue
            seen_runs.add(run_uuid)
            run = await self.db.get(AgentRun, run_uuid)
            if run is None or run.deleted_at is not None:
                continue
            if is_terminal_run_status(run.status):
                decisions.append({"run_id": run_id_str, "decision": "terminal_noop", "status": run.status})
                continue
            try:
                drift = await self._intent_drift_target(run)
                if drift is not None:
                    target, reason = drift
                    result = await self.transition(
                        run.id,
                        target,
                        actor=TransitionActor.RECOVERY,
                        reason=reason,
                        source=EventSource.WORKER,
                        details={"inflight_recovery": True},
                    )
                    decisions.append(
                        {
                            "run_id": run_id_str,
                            "decision": "drift_repaired",
                            "applied": result.applied,
                            "to": target.value,
                        }
                    )
                    continue
                result = await self.transition(
                    run.id,
                    RunStatus.UNKNOWN_OUTCOME,
                    actor=TransitionActor.RECOVERY,
                    reason="worker_restart_orphan",
                    error_category="unknown_outcome",
                    error_message="in-flight side-effecting tool call interrupted by process restart; outcome unverifiable",
                    source=EventSource.WORKER,
                    details={"inflight_recovery": True, "ledger_reconciled": ledger_result.reconciled},
                )
                decisions.append(
                    {
                        "run_id": run_id_str,
                        "decision": "unknown_outcome",
                        "applied": result.applied,
                        "to": RunStatus.UNKNOWN_OUTCOME.value,
                    }
                )
            except ValueError as exc:
                logger.warning("inflight recovery skipped run_id={} error={}", run_id_str, exc)
                decisions.append({"run_id": run_id_str, "decision": "skipped", "error": str(exc)})

        # 无中断证据的活跃 run：只输出 reattach 建议（不做不可逆动作）。
        active_stmt = (
            select(AgentRun.id)
            .where(
                AgentRun.deleted_at.is_(None),
                AgentRun.status.in_([s.value for s in ACTIVE_RUN_STATUSES]),
            )
            .limit(max(1, min(int(limit), 1000)))
        )
        active_ids = {str(row) for row in (await self.db.execute(active_stmt)).scalars().all()}
        for run_id_str in sorted(active_ids - {str(r) for r in seen_runs}):
            decisions.append({"run_id": run_id_str, "decision": "reattach_candidate"})

        return {
            "mode": "inflight",
            "ledger_reconciled": ledger_result.reconciled,
            "ledger_already_resolved": ledger_result.already_resolved,
            "ledger_stale_after_seconds": ledger_result.stale_after_seconds,
            "decided": len([d for d in decisions if d.get("decision") not in ("reattach_candidate",)]),
            "decisions": decisions,
        }

    # ------------------------------------------------------------------
    # X-09 · 失败终态化（三族分类 → 合法终态 + 部分完成证据 + 补偿提示）
    # ------------------------------------------------------------------

    async def terminalize_execution_failure(
        self,
        run_id: UUID | str,
        *,
        classification: Any,
        user_id: UUID | str | None = None,
        error_message: str | None = None,
        details: dict[str, Any] | None = None,
        retries_exhausted: bool = False,
    ) -> RunMutationResult:
        """把 :class:`app.core.failure_semantics.FailureClassification` 落成 run 终态.

        语义（卡面工作项 1/3）：

        - 分类器映射的终态/归因经封闭迁移图落库（非法/已终态 → ValueError/no-op
          由 transition 的既有契约吸收——终态即结论）；
        - **部分完成不静默**：终态化时从账本物化部分完成证据（succeeded/failed/
          interrupted + 补偿提示），写入 ``run.result_ref``（GET /runs 可见）；
          有元数据确认的写效果成功步且失败族非 CANCELLED 时，终态升格
          ``PARTIAL``（completed_partial——部分完成是诚实的结局）；CANCELLED
          保持 CANCELLED（用户语义归因不被系统覆盖，证据仍随 result_ref 可见）；
        - 重试耗尽（死信）在审计 details 记 ``retries_exhausted``——非无限执行、
          非静默截断。
        """
        from app.core.failure_semantics import FailureFamily, is_legal_failure_terminal
        from app.services.tool_call_ledger_service import ToolCallLedgerService

        target = RunStatus(classification.run_terminal_status)
        if not is_legal_failure_terminal(target):
            raise RunStateError(f"classification produced non-terminal status {target.value}")

        run = await self.get_run(run_id, user_id=user_id)
        evidence = await ToolCallLedgerService(self.db).partial_completion_evidence(run.id)

        effective_target = target
        effective_reason = classification.terminal_reason
        if (
            target in (RunStatus.FAILED, RunStatus.UNKNOWN_OUTCOME)
            and evidence.durable_progress
            and classification.family is not FailureFamily.USER_CANCELLED
        ):
            # 已确认的写效果进度 + 执行失败 → PARTIAL 是诚实终态（AGENT_RUNTIME
            # §6：不假装回滚，不静默丢弃已完成部分）。
            effective_target = RunStatus.PARTIAL
            effective_reason = "completed_partial"

        merged_details: dict[str, Any] = {
            "failure_kind": classification.failure_kind,
            "failure_family": classification.family.value,
            "side_effect_state": classification.side_effect_state,
            "partial_steps": {
                "succeeded": len(evidence.succeeded),
                "failed": len(evidence.failed),
                "interrupted": len(evidence.interrupted),
            },
        }
        if retries_exhausted:
            merged_details["retries_exhausted"] = True
        if details:
            merged_details.update(details)

        try:
            result = await self.transition(
                run.id,
                effective_target,
                user_id=user_id,
                actor=TransitionActor.WORKER,
                reason=effective_reason,
                error_category=classification.error_category,
                error_message=error_message or classification.failure_kind,
                result_ref=evidence.to_result_ref(),
                details=merged_details,
                source=EventSource.WORKER,
            )
        except ValueError as exc:
            # 已终态（终态封闭）/非法边：终态即结论，不覆盖、不双终态。
            logger.info("failure terminalization converged run_id={} error={}", run_id, exc)
            result = RunMutationResult(
                run=await self.get_run(run_id, user_id=user_id),
                applied=False,
                created=False,
                event_name=None,
                event_written=False,
            )
        return result

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
