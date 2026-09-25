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

分层边界：本 router 只做参数/错误映射，链路语义在
``app.services.first_action_service``；proposal 生命周期权威仍是 X-03
``ActionCommandService``。网关侧由 proxy_routes.go 的 ``/journey`` 代理组
转发（Go 纯 proxy，无业务逻辑）。
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
from app.services import first_action_service
from app.services.action_command_service import ActionCommandService
from app.services.first_action_service import (
    EDITABLE_FIRST_ACTION_FIELDS,
    FIRST_ACTION_TRACE_ID,
    FirstActionError,
    FirstActionGenerationError,
    NoActiveGoalError,
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
