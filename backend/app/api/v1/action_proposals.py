"""X-03 · Action Proposal API —— 统一 command path 的权威端点面.

- ``POST /action-proposals``：生成 proposal（所有入口共用；幂等键建议携带：
  重复提交恰一次；``execute_if_authorized`` 供已授予低风险自动权限的直通路径）；
- ``GET /action-proposals``：本人 proposal 列表（确认卡收件箱；status 过滤）；
- ``GET /action-proposals/{id}``：详情（diff 前后对照 + 过期即时标志）；
- ``GET /action-proposals/{id}/receipt``：**权威回执**（仅 COMMITTED；重复确认
  的重放响应即此 receipt）；
- ``GET /action-proposals/{id}/transitions``：append-only 生命周期审计；
- ``POST /action-proposals/{id}/approve``：确认 → 验证(版本/授权) → 落账
  （幂等：重复 approve 恰一次 commit，重放返回原 receipt + already_committed）；
- ``POST /action-proposals/{id}/cancel`` / ``/reject``：取消（X-05 user_cancelled
  归因对齐）/ 拒绝（终态封闭，幂等 no-op）;
- ``POST /action-proposals/expire``：过期 sweep（admin）。

错误映射（runs.py house 先例）：ActionCommandError 家族按 error_code→HTTP：
404 NOT_FOUND / 409 VERSION_CONFLICT・NOT_PENDING / 410 EXPIRED / 403
UNAUTHORIZED / 422 INVALID_COMMAND。

网关侧由 backend/gateway/internal/handler/proxy_routes.go 的 /action-proposals
代理组转发（Go 纯 proxy，无业务逻辑，分层边界不变）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.core.action_command import ActionCommandError, ProposalStatus
from app.db.session import get_db
from app.models.user import User
from app.services.action_command_service import ActionCommandService

router = APIRouter(prefix="/action-proposals", tags=["action-proposals"])


# --- 请求/响应模型 -----------------------------------------------------------


#: 信任边界（R2 P2-3 返修）：授权输入不接受客户端值——user_auto_grant 读
#: UserSettings.low_risk_auto_execute（服务端真源），requires_human_approval 由
#: 服务端按 X-02 R1 语义推导。客户端携带任一字段 → 422 显式拒收（不静默忽略，
#: 防止调用方对"被忽略"形成依赖）。
_CLIENT_FORBIDDEN_AUTH_FIELDS: tuple[str, ...] = ("user_auto_grant", "requires_human_approval")


class CreateProposalRequest(BaseModel):
    """生成 proposal（统一入口；chat/task/Aurora 仅 source 不同，路径同一）."""

    model_config = ConfigDict(extra="forbid")

    command_type: str = Field(min_length=1, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="api", max_length=16)
    idempotency_key: str | None = Field(default=None, max_length=255)
    ttl_seconds: int | None = Field(default=None, ge=60, le=24 * 3600)
    summary: str | None = Field(default=None, max_length=2000)
    execute_if_authorized: bool = False  # auto 模式直通意图（无授权时本旗标无效）
    session_id: str | None = Field(default=None, max_length=64)
    trace_id: str | None = Field(default=None, max_length=64)
    run_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_client_auth_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            present = sorted(set(values) & set(_CLIENT_FORBIDDEN_AUTH_FIELDS))
            if present:
                # ValueError → FastAPI 422（校验错误通道）
                raise ValueError(
                    "client-supplied authorization inputs are not accepted " f"(server-side truth only): {present}"
                )
        return values


class ApproveProposalRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=255)


class CancelProposalRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=255)


class RejectProposalRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)
    idempotency_key: str | None = Field(default=None, max_length=255)


class ExpireSweepRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=1000)


class ProposalMutationResponse(BaseModel):
    proposal: dict[str, Any]
    created: bool = False
    applied: bool = True
    already_committed: bool = False  # 重复确认的重放标志（不重复写）


class ProposalListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


class TransitionListResponse(BaseModel):
    items: list[dict[str, Any]]


def _to_http_error(exc: ActionCommandError) -> HTTPException:
    return HTTPException(status_code=exc.http_status, detail=exc.to_payload())


# --- 读端点（UI 权威查询面） ---------------------------------------------------


@router.get("", response_model=ProposalListResponse)
async def list_proposals(
    status: str | None = None,
    subject_id: UUID | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if status is not None and status not in {s.value for s in ProposalStatus}:
        raise HTTPException(status_code=422, detail=f"unknown status {status!r}")
    service = ActionCommandService(db)
    proposals = await service.list_proposals(user_id=current_user.id, status=status, subject_id=subject_id, limit=limit)
    items = [service.proposal_projection(p) for p in proposals]
    return ProposalListResponse(items=items, total=len(items))


@router.get("/{proposal_id}", response_model=ProposalMutationResponse)
async def get_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActionCommandService(db)
    try:
        proposal = await service.get_proposal(proposal_id, user_id=current_user.id)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return ProposalMutationResponse(proposal=service.proposal_projection(proposal), applied=True)


@router.get("/{proposal_id}/receipt")
async def get_receipt(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """权威回执查询端点（未落账 → 409，语义明确）."""
    service = ActionCommandService(db)
    try:
        receipt = await service.get_receipt(proposal_id, user_id=current_user.id)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return receipt


@router.get("/{proposal_id}/transitions", response_model=TransitionListResponse)
async def list_proposal_transitions(
    proposal_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActionCommandService(db)
    try:
        rows = await service.list_transitions(proposal_id, user_id=current_user.id, limit=limit)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    items = [
        {
            "from_status": r.from_status,
            "to_status": r.to_status,
            "event_name": r.event_name,
            "actor": r.actor,
            "idempotency_key": r.idempotency_key,
            "reason": r.reason,
            "details": r.details,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ]
    return TransitionListResponse(items=items)


# --- 写端点（统一 command path） ------------------------------------------------


@router.post("", response_model=ProposalMutationResponse, status_code=201)
async def create_proposal(
    request: CreateProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActionCommandService(db)
    try:
        result = await service.create_proposal(
            user_id=current_user.id,
            command_type=request.command_type,
            payload=request.payload,
            source=request.source,
            idempotency_key=request.idempotency_key,
            ttl_seconds=request.ttl_seconds,
            summary=request.summary,
            execute_if_authorized=request.execute_if_authorized,
            session_id=request.session_id,
            trace_id=request.trace_id,
            run_id=request.run_id,
        )
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ProposalMutationResponse(
        proposal=service.proposal_projection(result.proposal),
        created=result.created,
        applied=result.applied,
        already_committed=result.already_committed,
    )


@router.post("/{proposal_id}/approve", response_model=ProposalMutationResponse)
async def approve_proposal(
    proposal_id: UUID,
    request: ApproveProposalRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认：验证版本/权限后落账。重复确认 → already_committed=True + 原 receipt."""
    service = ActionCommandService(db)
    key = request.idempotency_key if request is not None else None
    try:
        result = await service.approve(proposal_id, user_id=current_user.id, idempotency_key=key)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return ProposalMutationResponse(
        proposal=service.proposal_projection(result.proposal),
        applied=result.applied,
        already_committed=result.already_committed,
    )


@router.post("/{proposal_id}/cancel", response_model=ProposalMutationResponse)
async def cancel_proposal(
    proposal_id: UUID,
    request: CancelProposalRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActionCommandService(db)
    key = request.idempotency_key if request is not None else None
    try:
        result = await service.cancel(proposal_id, user_id=current_user.id, idempotency_key=key)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ProposalMutationResponse(
        proposal=service.proposal_projection(result.proposal),
        applied=result.applied,
    )


@router.post("/{proposal_id}/reject", response_model=ProposalMutationResponse)
async def reject_proposal(
    proposal_id: UUID,
    request: RejectProposalRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActionCommandService(db)
    key = request.idempotency_key if request is not None else None
    try:
        result = await service.reject(proposal_id, user_id=current_user.id, idempotency_key=key)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return ProposalMutationResponse(
        proposal=service.proposal_projection(result.proposal),
        applied=result.applied,
    )


@router.post("/expire", response_model=dict[str, Any])
async def expire_stale_proposals(
    request: ExpireSweepRequest | None = None,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """过期 sweep（admin）：把过期仍 PENDING 的 proposal 显式转为 EXPIRED."""
    service = ActionCommandService(db)
    limit = request.limit if request is not None else 200
    expired = await service.expire_stale_proposals(limit=limit)
    return {"expired": expired}
