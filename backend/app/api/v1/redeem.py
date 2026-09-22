"""
Core: <execution|bridge>
Phase: <execute>
Stage: D-REDEEM

兑换码 API（billing 面）：
- ``POST /api/v1/billing/redeem``：用户核销（authed，走 get_current_active_user）；
- ``POST /api/v1/billing/redeem-codes``：admin 批量生成（既有 admin 鉴权面
  get_current_active_superuser + admin_audit 审计装饰器，与 dlq_admin 同款）。

网关代理：/billing/redeem 走 gateway proxy（route-tier: authed）；admin 生成面
按 marketplace/seed-libraries admin 先例 engine-side only（BA-ROUTES 守卫
ENGINE_ONLY 挂账）。业务失败（invalid/expired/exhausted）返回 4xx + 结构化
status；核销成功 200。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_active_user, get_db
from app.middleware.admin_audit import audit_admin_action
from app.schemas.redeem import (
    RedeemBatchCreateRequest,
    RedeemBatchCreateResponse,
    RedeemRequest,
    RedeemResponse,
)
from app.services import redeem_service
from app.services.redeem_service import (
    REDEEM_EXHAUSTED,
    REDEEM_EXPIRED,
    REDEEM_INVALID,
)

router = APIRouter(prefix="/billing", tags=["billing"])

#: 核销业务终态 → HTTP 状态码（成功 200；其余演示期封闭映射）
_REDEEM_HTTP_STATUS = {
    REDEEM_INVALID: status.HTTP_404_NOT_FOUND,
    REDEEM_EXPIRED: status.HTTP_410_GONE,
    REDEEM_EXHAUSTED: status.HTTP_409_CONFLICT,
}


# route-tier: authed
@router.post("/redeem", response_model=RedeemResponse)
async def redeem_code(
    request: RedeemRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> RedeemResponse:
    """用户核销兑换码：成功 → entitlement 升 pro（带到期时间）。"""
    outcome = await redeem_service.redeem(db, user_id=current_user.id, code=request.code)
    if outcome.status in _REDEEM_HTTP_STATUS:
        raise HTTPException(
            status_code=_REDEEM_HTTP_STATUS[outcome.status],
            detail={"status": outcome.status, "message": outcome.message},
        )
    return RedeemResponse(
        status=outcome.status,
        tier=outcome.tier,
        entitlement_expires_at=outcome.entitlement_expires_at,
        message=outcome.message,
    )


# route-tier: authed —— superuser 面；gateway 不代理（BA-ROUTES ENGINE_ONLY 挂账）
@router.post(
    "/redeem-codes",
    response_model=RedeemBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@audit_admin_action(category="billing", risk="high", action="create_redeem_batch")
async def create_redeem_batch(
    request: RedeemBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_active_superuser),
) -> RedeemBatchCreateResponse:
    """admin 批量生成兑换码。响应含明文（唯一出口），不落库不进日志。"""
    if request.batch_id:
        existing = await redeem_service.get_batch_summary(db, batch_id=request.batch_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"batch_id 已存在：{request.batch_id}",
            )
    batch = await redeem_service.generate_batch(
        db,
        tier=request.tier,
        duration_days=request.duration_days,
        count=request.count,
        max_uses=request.max_uses,
        created_by=admin.id,
        batch_id=request.batch_id,
        expires_in_days=request.expires_in_days,
    )
    return RedeemBatchCreateResponse(
        batch_id=batch.batch_id,
        tier=request.tier,
        duration_days=request.duration_days,
        max_uses=request.max_uses,
        expires_at=batch.expires_at,
        codes=batch.codes,
    )
