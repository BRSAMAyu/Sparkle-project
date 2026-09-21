"""Unified Agent Run API —— run 状态的单一权威读写端点（X-05）.

- ``GET /runs/{run_id}``：App 杀进程重开后按 run_id 权威查询（状态持久于
  ``agent_runs``，不依赖 App 内存或 WS 连接）；
- ``GET /runs``：按 task/intent/session/active 过滤列表（重开旅程「找回我的
  run」不需要记住 run_id）；
- ``GET /runs/{run_id}/transitions``：append-only 审计轨迹；
- ``POST /runs``：创建（幂等：携带 idempotency_key 时重复提交恰一次）；
- ``POST /runs/{run_id}/resume`` / ``/cancel``：用户侧语义操作；
- ``POST /runs/{run_id}/steps``：步进进度（绝对序号，幂等）；
- ``POST /runs/recover``：worker restart 恢复 sweep（admin）。

错误映射（house 先例）：ValueError → 400/409（IllegalRunTransitionError 属
ValueError 子类 → 409，tasks.py:999 先例）；RunNotFoundError → 404；跨用户
读取按 404 处理（与 _get_user_intent 同形，不泄露存在性）。FIX-29 硬化：
POST /runs 挂 intent 前归属校验（他人/不存在 intent 一律 404，不抢占投影
不窥时间线，N1）；cancel reason 服务端白名单 ``{user_cancelled}``（词表内
子集，越界 → 422，N3，resume 白名单同族）。

网关侧由 ``backend/gateway/internal/handler/proxy_routes.go`` 的 /runs 代理组
转发（Go 无业务逻辑，纯 proxy，分层边界不变）。

X-07 · Hybrid Handoff 增量（全部走既有 run 聚合与状态机，零新真源）：
- ``PUT /runs/{run_id}/steps``：定义步骤计划（owner/完成条件；只许一次，
  同内容重投幂等）；
- ``POST /runs/{run_id}/steps/{step_id}/await``：把 run 交给用户做该步
  （``run.awaiting_user`` 事件 + wait_expires_at 过期面）；
- ``POST /runs/{run_id}/steps/{step_id}/complete``：用户确认/编辑该步 →
  完成戳 + resume 同事务，幂等键必填（「两次确认只 resume 一次」服务端
  强制：步骤已有完成戳时无论 key 是否相同一律重放 no-op）；
- run 读取面（GET /runs、GET /runs/{id}）新增 ``steps`` 投影与推导的
  ``awaiting_step``（含 ownership/prompt/artifacts/expires_at/state）——
  通知点击/冷启动重开据此恢复到 awaiting step，不靠内存。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.core.run_state_machine import IllegalRunTransitionError, InvalidResumeTargetError, RunStateError
from app.db.session import get_db
from app.models.agent_run import AgentRunKind
from app.models.execution_intent import ExecutionIntent
from app.models.user import User
from app.services.agent_run_service import (
    AgentRunService,
    BudgetExceededError,
    InvalidCancelReasonError,
    MissingIdempotencyKeyError,
    RunNotAwaitingUserStepError,
    RunNotFoundError,
    RunStepPlanConflictError,
    UnknownRunStepError,
)
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/runs", tags=["agent-runs"])


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --- 请求/响应模型 -----------------------------------------------------------


class CreateRunRequest(BaseModel):
    """创建 run（幂等键强烈建议携带：重复提交恰一次的客户端侧依据）。"""

    objective: str = Field(min_length=1, max_length=2000)
    kind: str = Field(default="execution", max_length=16)
    idempotency_key: str | None = Field(default=None, max_length=255)
    task_id: UUID | None = None
    intent_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=64)
    trace_id: str | None = Field(default=None, max_length=64)
    context_refs: list[str] = Field(default_factory=list, max_length=32)
    allowed_tools: list[str] = Field(default_factory=list, max_length=64)
    permissions: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    completion_condition: dict[str, Any] = Field(default_factory=dict)
    risk_class: str | None = Field(default=None, max_length=16)
    steps_total: int | None = Field(default=None, ge=1, le=1000)
    steps: list[RunStepPlanEntry] = Field(default_factory=list, max_length=64)  # X-07 创建时携带步骤计划


class ResumeRunRequest(BaseModel):
    to_status: str = Field(default="RUNNING", max_length=24)
    idempotency_key: str | None = Field(default=None, max_length=255)
    current_stage: str | None = Field(default=None, max_length=64)


class CancelRunRequest(BaseModel):
    """取消请求。reason 只接受服务端白名单 ``user_cancelled``（FIX-29 N3）。"""

    reason: str = Field(default="user_cancelled", max_length=32)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RunStepRequest(BaseModel):
    step_id: str = Field(min_length=1, max_length=64)
    ordinal: int = Field(ge=1, le=1000)
    label: str | None = Field(default=None, max_length=64)
    effects: list[str] | None = Field(default=None, max_length=16)
    steps_total: int | None = Field(default=None, ge=1, le=1000)
    dedup_key: str | None = Field(default=None, max_length=128)


class RunStepPlanEntry(BaseModel):
    """X-07 · 步骤计划条目（契约：app/core/run_steps.py，服务端 fail-closed）。"""

    step_id: str = Field(min_length=1, max_length=64)
    ordinal: int = Field(ge=1, le=1000)
    label: str | None = Field(default=None, max_length=64)
    owner: str = Field(pattern="^(agent|human|hybrid)$")
    completion_condition: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[dict[str, Any]] | None = Field(default=None, max_length=16)


class RunStepPlanRequest(BaseModel):
    """步骤计划定义（PUT /runs/{id}/steps；只许一次，同内容重投幂等）。"""

    steps: list[RunStepPlanEntry] = Field(min_length=0, max_length=64)


class RunStepAwaitRequest(BaseModel):
    """把 run 交给用户做某步（POST /runs/{id}/steps/{step_id}/await）。"""

    prompt: str | None = Field(default=None, max_length=500)
    artifact_refs: list[dict[str, Any]] | None = Field(default=None, max_length=16)
    wait_expires_at: datetime | None = None


class RunStepCompleteRequest(BaseModel):
    """用户完成 awaiting step（确认/编辑）→ 完成戳 + resume（幂等键必填）。

    双击/重试/换 key 重发都收敛到第一次（服务端 first-wins）：步骤已有完成
    戳时返回 ``step_replay=true`` 且不再次 resume——「用户操作两次不会
    resume 两次」的服务端强制面。
    """

    idempotency_key: str = Field(min_length=1, max_length=255)
    action: str = Field(default="confirm", pattern="^(confirm|edit)$", max_length=32)
    artifact_refs: list[dict[str, Any]] | None = Field(default=None, max_length=16)
    note: str | None = Field(default=None, max_length=500)
    to_status: str = Field(default="RUNNING", max_length=24)
    current_stage: str | None = Field(default=None, max_length=64)


class RunAgentStepCompleteRequest(BaseModel):
    """Agent 完成 agent-owned 步骤（POST /runs/{id}/steps/{step_id}/agent-complete）。

    owner 纪律的服务端面：HUMAN/HYBRID 步骤只能走用户 complete 端点——
    Agent 不得代替用户完成认知归属属于用户的步骤（HUMAN_AGENT_HYBRID §2/§3）。
    """

    artifact_refs: list[dict[str, Any]] | None = Field(default=None, max_length=16)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RecoverRunsRequest(BaseModel):
    """恢复 sweep 入口（X-05 sweep / X-09 主动 inflight 恢复）.

    ``mode``（X-09 增补，缺省 ``sweep`` 保持既有行为）：

    - ``sweep``：X-05 时间陈旧兜底（QUEUED 陈旧→CANCELLED、wait 过期→
      TIMED_OUT、心跳孤儿→UNKNOWN_OUTCOME、intent 漂移修复）；
    - ``inflight``：X-09 主动崩溃恢复——陈旧 in_progress 账本行收敛为
      interrupted + 受影响活跃 run 的证据驱动裁决（intent 真值优先 /
      UNKNOWN_OUTCOME / reattach 建议），进程重启后立即可执行。
    """

    stale_after_seconds: int | None = Field(default=None, ge=60, le=30 * 86400)
    mode: str = Field(default="sweep", pattern="^(sweep|inflight)$")


class RunToolCallListResponse(BaseModel):
    """run 维度账本明细（X-09：部分完成/中断的审计可见面）."""

    items: list[dict[str, Any]]
    total: int
    partial_completion: dict[str, Any] | None = None


class RunResponse(BaseModel):
    run: dict[str, Any]
    idempotent_replay: bool = False
    transition_applied: bool = True
    step_replay: bool = False  # X-07：用户步骤完成重放（步骤已带完成戳，未再次 resume）


class RunListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


class RunTransitionListResponse(BaseModel):
    items: list[dict[str, Any]]


# --- 读端点（App kill/reopen 的权威查询面） ----------------------------------


# route-tier: authed
@router.get("", response_model=RunListResponse)
async def list_runs(
    task_id: UUID | None = None,
    intent_id: UUID | None = None,
    session_id: str | None = None,
    active: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    runs = await service.list_runs(
        user_id=current_user.id,
        task_id=task_id,
        intent_id=intent_id,
        session_id=session_id,
        active_only=active,
        limit=limit,
    )
    items = [run.to_dict() for run in runs]
    return RunListResponse(items=items, total=len(items))


# route-tier: authed
@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    try:
        run = await service.get_run(run_id, user_id=current_user.id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunResponse(run=run.to_dict())


# route-tier: authed
@router.get("/{run_id}/transitions", response_model=RunTransitionListResponse)
async def list_run_transitions(
    run_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    try:
        transitions = await service.list_transitions(run_id, user_id=current_user.id, limit=limit)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunTransitionListResponse(items=[t.to_dict() for t in transitions])


# route-tier: authed
@router.get("/{run_id}/tool-calls", response_model=RunToolCallListResponse)
async def list_run_tool_calls(
    run_id: UUID,
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """run 的工具调用账本明细（X-09：部分完成/中断不静默的审计与用户可见面）.

    每步的 succeeded/failed/interrupted 状态、幂等键、错误归因直接可见；
    ``partial_completion`` 携带部分完成证据与补偿提示（AGENT_RUNTIME §6：
    显示已完成部分与可补偿动作，不假装回滚）。
    """
    from app.services.tool_call_ledger_service import ToolCallLedgerService

    service = AgentRunService(db)
    try:
        await service.get_run(run_id, user_id=current_user.id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    ledger = ToolCallLedgerService(db)
    rows = await ledger.list_tool_calls_for_run(run_id, limit=limit)
    evidence = await ledger.partial_completion_evidence(run_id)
    return RunToolCallListResponse(
        items=[row.to_dict() for row in rows],
        total=len(rows),
        partial_completion=evidence.to_result_ref(),
    )


# --- 写端点 ------------------------------------------------------------------


async def _ensure_intent_owned(db: AsyncSession, *, intent_id: UUID, user_id: UUID) -> None:
    """FIX-29 N1：POST /runs 挂 intent 前校验归属。

    挂他人 intent 的 run 会抢占该 intent 的投影（活跃 run 按 intent_id 检索、
    不分 user）并借 transitions 时间线窥见他人执行轨迹。跨用户/不存在一律
    404（与 _get_user_intent 同形，不泄露存在性）。
    """
    intent = await db.get(ExecutionIntent, intent_id)
    if intent is None or str(intent.user_id) != str(user_id):
        raise HTTPException(status_code=404, detail=f"execution intent {intent_id} not found")


# route-tier: authed
@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    request: CreateRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.intent_id is not None:
        await _ensure_intent_owned(db, intent_id=request.intent_id, user_id=current_user.id)
    service = AgentRunService(db)
    try:
        result = await service.create_run(
            user_id=current_user.id,
            objective=request.objective,
            kind=request.kind,
            idempotency_key=request.idempotency_key,
            task_id=request.task_id,
            intent_id=request.intent_id,
            session_id=request.session_id,
            trace_id=request.trace_id,
            context_refs=request.context_refs,
            allowed_tools=request.allowed_tools,
            permissions=request.permissions,
            budget=request.budget,
            completion_condition=request.completion_condition,
            risk_class=request.risk_class,
            steps_total=request.steps_total,
            steps=[entry.model_dump(exclude_none=True) for entry in request.steps] if request.steps else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunResponse(
        run=result.run.to_dict(),
        idempotent_replay=not result.created,
    )


# route-tier: authed
@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(
    run_id: UUID,
    request: ResumeRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    try:
        result = await service.resume(
            run_id,
            user_id=current_user.id,
            to_status=request.to_status,
            idempotency_key=request.idempotency_key,
            current_stage=request.current_stage,
        )
    except IllegalRunTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BudgetExceededError as exc:
        # X-07 P2-2：预算闸门超限（已落 BUDGET_EXCEEDED 终态）→ 409 非 500
        # （对齐 complete_user_step 同款映射；非 RunStateError 子类，需显式接住）。
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidResumeTargetError as exc:
        # 服务端白名单拒绝（R2 F4）：注入终态/等待态/未知串 → 422（非 500）。
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunResponse(run=result.run.to_dict(), transition_applied=result.applied)


async def _propagate_cancel_to_intent(
    db: AsyncSession,
    *,
    user_id: UUID,
    intent_id: UUID,
) -> bool:
    """run 取消 → 下游协作取消（AGENT_RUNTIME.md §6；R2 F2 返修）。

    对 kind=execution 且挂 intent 的 run，取消必须传播到 ExecutionIntent：
    调执行侧 ``ExecutionService.cancel``（撤销执行资格：OpenClaw 远端 best-effort
    取消 + intent 行→CANCELED + 状态事件发布），而不是只改 run 自己的状态、
    让 intent 继续执行后被状态事件"复活"。

    返回是否传播成功。intent 已终态/不存在（ValueError）视为已收敛；
    其余异常不向上抛（run 取消本身已提交、幂等可重试，5xx 会让客户端误判
    取消失败），打 error 级日志留观测痕迹——投影侧 ``user_cancelled`` 防复活
    守卫兜底保证真源不被污染。
    """
    try:
        await ExecutionService(db).cancel(intent_id=intent_id, user_id=user_id)
        return True
    except ValueError as exc:
        logger.info("run cancel propagation converged (intent already terminal/missing): {}", exc)
        return True
    except Exception as exc:  # noqa: BLE001 — run 取消已提交；传播失败可由幂等重试补
        logger.error("run cancel propagation failed intent_id={} error={!r}", intent_id, exc)
        return False


# route-tier: authed
@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: UUID,
    request: CancelRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    try:
        result = await service.cancel(
            run_id,
            user_id=current_user.id,
            reason=request.reason,
            idempotency_key=request.idempotency_key,
        )
    except IllegalRunTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidCancelReasonError as exc:
        # 服务端白名单拒绝（FIX-29 N3）：非 user_cancelled 归因 → 422（与
        # resume 白名单拒绝同族），不落到 400/500。
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 取消传播（R2 F2）：run 状态变更（已提交）+ 下游协作取消。
    run = result.run
    if run.kind == AgentRunKind.EXECUTION and run.intent_id is not None:
        propagated = await _propagate_cancel_to_intent(db, user_id=current_user.id, intent_id=run.intent_id)
        logger.info(
            "run cancel propagated run_id={} intent_id={} applied={} propagated={}",
            run_id,
            run.intent_id,
            result.applied,
            propagated,
        )
    return RunResponse(run=run.to_dict(), transition_applied=result.applied)


# route-tier: authed
@router.post("/{run_id}/steps", response_model=RunResponse)
async def record_run_step(
    run_id: UUID,
    request: RunStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentRunService(db)
    try:
        result = await service.record_step(
            run_id,
            user_id=current_user.id,
            step_id=request.step_id,
            ordinal=request.ordinal,
            label=request.label,
            effects=request.effects,
            steps_total=request.steps_total,
            dedup_key=request.dedup_key,
        )
    except IllegalRunTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunResponse(run=result.run.to_dict(), transition_applied=result.applied)


# route-tier: authed
@router.put("/{run_id}/steps", response_model=RunResponse)
async def define_run_step_plan(
    run_id: UUID,
    request: RunStepPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """定义 run 步骤计划（X-07；只许一次，同内容重投幂等 no-op）。"""
    service = AgentRunService(db)
    try:
        result = await service.define_run_steps(
            run_id,
            steps=[entry.model_dump(exclude_none=True) for entry in request.steps],
            user_id=current_user.id,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunStepPlanConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RunResponse(run=result.run.to_dict(), transition_applied=result.applied)


# route-tier: authed
@router.post("/{run_id}/steps/{step_id}/await", response_model=RunResponse)
async def await_run_user_step(
    run_id: UUID,
    step_id: str,
    request: RunStepAwaitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """把 run 交给用户做某步（X-07「轮到你」；run.awaiting_user 事件同事务）。

    通知/重开恢复的数据面：事件带 run_id（aurora RUN_AWAITING 既有消费），
    App 冷启动经 GET /runs/{id} 的 ``awaiting_step`` 推导恢复到本步。
    """
    service = AgentRunService(db)
    try:
        result = await service.await_user_step(
            run_id,
            step_id=step_id,
            user_id=current_user.id,
            prompt=request.prompt,
            artifact_refs=request.artifact_refs,
            wait_expires_at=request.wait_expires_at.replace(tzinfo=None) if request.wait_expires_at else None,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownRunStepError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IllegalRunTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunResponse(run=result.run.to_dict(), transition_applied=result.applied)


# route-tier: authed
@router.post("/{run_id}/steps/{step_id}/complete", response_model=RunResponse)
async def complete_run_user_step(
    run_id: UUID,
    step_id: str,
    request: RunStepCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户确认/编辑 awaiting step（X-07）→ 完成戳 + resume 同事务、幂等强制.

    - 重放（步骤已有完成戳，无论 key 是否相同）：200 + ``step_replay=true``，
      **不第二次 resume**；
    - 过期/取消后的迟到确认：409（终态明确，错误携带终态与归因）；
    - 缺幂等键：422（幂等是本路径的强制前提，不是可选项）。
    """
    service = AgentRunService(db)
    try:
        result = await service.complete_user_step(
            run_id,
            step_id=step_id,
            user_id=current_user.id,
            idempotency_key=request.idempotency_key,
            action=request.action,
            artifact_refs=request.artifact_refs,
            note=request.note,
            to_status=request.to_status,
            current_stage=request.current_stage,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownRunStepError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingIdempotencyKeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidResumeTargetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (IllegalRunTransitionError, RunNotAwaitingUserStepError, BudgetExceededError) as exc:
        # 409：并发迁移收敛 / 未在等待 / 预算闸门落 BUDGET_EXCEEDED 终态
        # （响应 run 字段携带权威终态，客户端刷新即得明确取消/过期/超限面）。
        run_payload: dict[str, Any] | None = None
        try:
            run_payload = (await service.get_run(run_id, user_id=current_user.id)).to_dict()
        except RunNotFoundError:
            run_payload = None
        detail: dict[str, Any] = {"message": str(exc)}
        if run_payload is not None:
            detail["run"] = run_payload
        raise HTTPException(status_code=409, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunResponse(
        run=result.run.to_dict(),
        transition_applied=result.resumed,
        step_replay=not result.applied,
    )


# route-tier: authed
@router.post("/{run_id}/steps/{step_id}/agent-complete", response_model=RunResponse)
async def complete_run_agent_step(
    run_id: UUID,
    step_id: str,
    request: RunAgentStepCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent 完成 agent-owned 步骤（X-07 handoff 前半段；不发 resume）。

    交棒用户由编排层显式调用 ``POST …/await``——「Agent 完成」与「轮到用户」
    是两个可审计的语义时刻。
    """
    service = AgentRunService(db)
    try:
        result = await service.complete_agent_step(
            run_id,
            step_id=step_id,
            user_id=current_user.id,
            artifact_refs=request.artifact_refs,
            idempotency_key=request.idempotency_key,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownRunStepError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunResponse(run=result.run.to_dict(), transition_applied=result.applied)


# route-tier: authed
@router.post("/recover", response_model=dict)
async def recover_runs(
    request: RecoverRunsRequest | None = None,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    del current_user
    service = AgentRunService(db)
    mode = (request.mode if request else "sweep") or "sweep"
    if mode == "inflight":
        # X-09 主动崩溃恢复（进程重启后立即执行；证据驱动裁决）。
        payload = await service.recover_inflight_runs(
            stale_after_seconds=request.stale_after_seconds if request else None,
        )
        logger.info(
            "run inflight recovery executed: ledger_reconciled={} decided={}",
            payload.get("ledger_reconciled"),
            payload.get("decided"),
        )
        return payload
    payload = await service.recover_stale_runs(
        stale_after_seconds=request.stale_after_seconds if request else None,
    )
    logger.info("run recovery sweep executed: applied={} scanned={}", payload.get("applied"), payload.get("scanned"))
    return payload
