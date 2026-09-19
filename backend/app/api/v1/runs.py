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
读取按 404 处理（与 _get_user_intent 同形，不泄露存在性）。

网关侧由 ``backend/gateway/internal/handler/proxy_routes.go`` 的 /runs 代理组
转发（Go 无业务逻辑，纯 proxy，分层边界不变）。
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
from app.models.user import User
from app.services.agent_run_service import AgentRunService, RunNotFoundError
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


class ResumeRunRequest(BaseModel):
    to_status: str = Field(default="RUNNING", max_length=24)
    idempotency_key: str | None = Field(default=None, max_length=255)
    current_stage: str | None = Field(default=None, max_length=64)


class CancelRunRequest(BaseModel):
    reason: str = Field(default="user_cancelled", max_length=32)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RunStepRequest(BaseModel):
    step_id: str = Field(min_length=1, max_length=64)
    ordinal: int = Field(ge=1, le=1000)
    label: str | None = Field(default=None, max_length=64)
    effects: list[str] | None = Field(default=None, max_length=16)
    steps_total: int | None = Field(default=None, ge=1, le=1000)
    dedup_key: str | None = Field(default=None, max_length=128)


class RecoverRunsRequest(BaseModel):
    stale_after_seconds: int | None = Field(default=None, ge=60, le=30 * 86400)


class RunResponse(BaseModel):
    run: dict[str, Any]
    idempotent_replay: bool = False
    transition_applied: bool = True


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


# --- 写端点 ------------------------------------------------------------------


# route-tier: authed
@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    request: CreateRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
@router.post("/recover", response_model=dict)
async def recover_runs(
    request: RecoverRunsRequest | None = None,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    del current_user
    service = AgentRunService(db)
    payload = await service.recover_stale_runs(
        stale_after_seconds=request.stale_after_seconds if request else None,
    )
    logger.info("run recovery sweep executed: applied={} scanned={}", payload.get("applied"), payload.get("scanned"))
    return payload
