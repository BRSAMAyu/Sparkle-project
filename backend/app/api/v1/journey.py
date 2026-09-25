"""J-04 · Journey First Action API —— First Meaningful Action 链路的入口面.

全链（Goal→Context→Aurora→Proposal→confirm→Task）的唯一 HTTP 入口：
- ``POST /journey/first-action``：生成 first-action proposal（Context→Aurora→
  X-03 统一 command path）。**诚实失败**：无 active goal → 422；Aurora 推导
  失败 → 503 ``{"error": "first_action_generation_failed", "retryable": true}``
  （错误可见可重试，不假装成功，不写半成品 proposal）。
- ``GET /journey/first-action``：链路状态读面（重开 App 的持久化回放：
  goal + 最新 first-action proposal（含 receipt）+ 已建任务投影）。
- ``POST /journey/first-action/{proposal_id}/edit``：编辑 = 拒绝旧提案（编辑
  delta 进 feedback 审计）+ 同链路重提案（统一 path，不旁路）。

J-06 · ``/journey/hybrid``：Hybrid 旗舰旅程（Agent prep → Human judgment →
Agent execute/check → Outcome）——与 first-action 同一 ``/journey`` 面、同一
X-03 trace 惯例、同一鉴权；handoff 全部走 X-07 run 步骤机制（统一 Runtime/UI，
零第二交接面）。语义在 ``app.services.hybrid_journey_service``。

分层边界：本 router 只做参数/错误映射，链路语义在 service 层；proposal 生命
周期权威仍是 X-03 ``ActionCommandService``。网关侧由 proxy_routes.go 的
``/journey`` 代理组转发（Go 纯 proxy，无业务逻辑）。
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.action_command import ActionCommandError
from app.models.user import User
from app.services import first_action_service, hybrid_journey_service
from app.services.action_command_service import ActionCommandService
from app.services.first_action_service import (
    EDITABLE_FIRST_ACTION_FIELDS,
    FIRST_ACTION_TRACE_ID,
    FirstActionError,
    FirstActionGenerationError,
    NoActiveGoalError,
)
from app.services.hybrid_journey_service import (
    HybridJourneyStateError,
    JourneyCheckError,
    JourneyGenerationError,
    JudgmentRequiredError,
    JudgmentUnknownSourceError,
    NoMaterialError,
    NoTaskAnchorError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journey", tags=["journey"])


class FirstActionRequest(BaseModel):
    """生成 first-action proposal（幂等键建议携带：重复提交恰一次）."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str | None = Field(default=None, max_length=255)
    session_id: str | None = Field(default=None, max_length=64)


class FirstActionEditRequest(BaseModel):
    """编辑 first-action 提案（封闭可改字段；编辑 delta 进 feedback 审计）."""

    model_config = ConfigDict(extra="forbid")

    edited_fields: dict[str, Any]
    reason: str | None = Field(default=None, max_length=200)
    idempotency_key: str | None = Field(default=None, max_length=255)


# route-tier: authed
@router.post("/first-action", status_code=201)
async def create_first_action(
    request: FirstActionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    body = request or FirstActionRequest()
    try:
        result = await first_action_service.propose_first_action(
            db,
            user_id=current_user.id,
            idempotency_key=body.idempotency_key,
            session_id=body.session_id,
        )
    except NoActiveGoalError:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_active_goal", "message": "先设定一个真实目标，才会有第一步。"},
        ) from None
    except FirstActionGenerationError as exc:
        # 诚实失败：503 结构化错误，不假装成功；不写任何 proposal（服务保证）
        logger.warning("first action generation failed user=%s reason=%s", current_user.id, exc.reason)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "first_action_generation_failed",
                "reason": exc.reason,
                "retryable": exc.retryable,
                "message": "第一步生成暂时失败，请重试。",
            },
        ) from None
    service = ActionCommandService(db)
    return {
        "proposal": service.proposal_projection(result.proposal),
        "created": result.created,
        "applied": result.applied,
    }


# route-tier: authed
@router.get("/first-action")
async def get_first_action(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    state = await first_action_service.get_first_action_state(db, user_id=current_user.id)
    return {**state, "trace_id": FIRST_ACTION_TRACE_ID}


# route-tier: authed
@router.post("/first-action/{proposal_id}/edit")
async def edit_first_action(
    proposal_id: UUID,
    request: FirstActionEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    illegal = sorted(set(request.edited_fields) - EDITABLE_FIRST_ACTION_FIELDS)
    if illegal:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_edit_fields",
                "editable": sorted(EDITABLE_FIRST_ACTION_FIELDS),
                "illegal": illegal,
            },
        )
    try:
        result = await first_action_service.edit_first_action_proposal(
            db,
            user_id=current_user.id,
            proposal_id=proposal_id,
            edited_fields=request.edited_fields,
            reason=request.reason,
            idempotency_key=request.idempotency_key,
        )
    except ActionCommandError as exc:
        status = exc.http_status if getattr(exc, "http_status", None) else 409
        raise HTTPException(status_code=status, detail=exc.to_payload()) from None
    except NoActiveGoalError:
        raise HTTPException(status_code=422, detail={"error": "no_active_goal"}) from None
    except FirstActionError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_edit", "message": str(exc)}) from None
    service = ActionCommandService(db)
    return {
        "proposal": service.proposal_projection(result.proposal),
        "created": result.created,
        "applied": result.applied,
    }


# ===========================================================================
# J-06 · Hybrid Flagship Journey（Agent prep → Human judgment →
# Agent execute/check → Outcome；handoff 全走 X-07 run 机制）
# ===========================================================================


class HybridJourneyStartRequest(BaseModel):
    """启动 Hybrid 旅程（task 缺省时解析最近在飞任务；幂等键建议携带）."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)
    session_id: str | None = Field(default=None, max_length=64)


class HybridJudgmentRequest(BaseModel):
    """用户判断：选择进入交付的材料引用（空选择 = 服务层结构性拒绝代决）."""

    model_config = ConfigDict(extra="forbid")

    selected_refs: list[str] = Field(min_length=0, max_length=16)
    focus_note: str | None = Field(default=None, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=255)


class HybridOutcomeConfirmRequest(BaseModel):
    """确认交付：确认后任务经既有完成路径落终态并记录 outcome."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=255)


def _hybrid_http_error(exc: Exception) -> HTTPException:
    """J-06 错误面 → 诚实 HTTP 码（422 判断/材料缺失、409 状态、503 生成失败）。"""
    if isinstance(exc, (NoActiveGoalError, NoTaskAnchorError, NoMaterialError)):
        detail_by_type = {
            NoActiveGoalError: "no_active_goal",
            NoTaskAnchorError: "no_task_anchor",
            NoMaterialError: "no_materials",
        }
        return HTTPException(
            status_code=422, detail={"error": detail_by_type[type(exc)], "message": str(exc)}
        )
    if isinstance(exc, JudgmentRequiredError):
        return HTTPException(
            status_code=422,
            detail={"error": "judgment_required", "message": "这一步需要你决定：选择哪些材料、聚焦什么方向。"},
        )
    if isinstance(exc, JudgmentUnknownSourceError):
        return HTTPException(status_code=422, detail={"error": "unknown_sources", "message": str(exc)})
    if isinstance(exc, HybridJourneyStateError):
        return HTTPException(status_code=409, detail={"error": "journey_state", "message": str(exc)})
    if isinstance(exc, JourneyCheckError):
        return HTTPException(
            status_code=503,
            detail={
                "error": "journey_check_failed",
                "reason": exc.reason,
                "retryable": exc.retryable,
                "message": "草稿引用核对未通过，请重试或调整选择。",
            },
        )
    if isinstance(exc, JourneyGenerationError):
        return HTTPException(
            status_code=503,
            detail={
                "error": "journey_generation_failed",
                "retryable": exc.retryable,
                "message": "起草暂时失败，请重试。",
            },
        )
    raise exc


# route-tier: authed
@router.post("/hybrid", status_code=201)
async def start_hybrid_journey(
    request: HybridJourneyStartRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """启动 Hybrid 旗舰旅程：Agent prep（真实材料检索）→ 轮到你判断。"""
    body = request or HybridJourneyStartRequest()
    try:
        return await hybrid_journey_service.start_hybrid_journey(
            db,
            user_id=current_user.id,
            task_id=body.task_id,
            idempotency_key=body.idempotency_key,
            session_id=body.session_id,
        )
    except (
        NoActiveGoalError,
        NoTaskAnchorError,
        NoMaterialError,
        HybridJourneyStateError,
    ) as exc:
        raise _hybrid_http_error(exc) from None


# route-tier: authed
@router.post("/hybrid/{run_id}/judgment")
async def submit_hybrid_judgment(
    run_id: UUID,
    request: HybridJudgmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """判断段提交（AI 不代决）：选择材料引用 → Agent 起草并核对 → 等你确认。"""
    try:
        return await hybrid_journey_service.submit_judgment(
            db,
            user_id=current_user.id,
            run_id=run_id,
            selected_refs=request.selected_refs,
            focus_note=request.focus_note,
            idempotency_key=request.idempotency_key,
        )
    except (
        JudgmentRequiredError,
        JudgmentUnknownSourceError,
        HybridJourneyStateError,
        JourneyCheckError,
        JourneyGenerationError,
    ) as exc:
        raise _hybrid_http_error(exc) from None


# route-tier: authed
@router.post("/hybrid/{run_id}/outcome/confirm")
async def confirm_hybrid_outcome(
    run_id: UUID,
    request: HybridOutcomeConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """确认交付（幂等）：任务完成 + outcome 记录 + run SUCCEEDED。"""
    try:
        return await hybrid_journey_service.confirm_outcome(
            db,
            user_id=current_user.id,
            run_id=run_id,
            idempotency_key=request.idempotency_key,
            note=request.note,
        )
    except HybridJourneyStateError as exc:
        raise _hybrid_http_error(exc) from None


# route-tier: authed
@router.get("/hybrid/{run_id}")
async def get_hybrid_journey(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """旅程状态读面（重开 App 持久化回放：run + 分段产物 + 判断面）。"""
    try:
        return await hybrid_journey_service.get_hybrid_journey_state(
            db,
            user_id=current_user.id,
            run_id=run_id,
        )
    except HybridJourneyStateError as exc:
        raise _hybrid_http_error(exc) from None
