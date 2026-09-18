"""
Photon API Endpoints
光子积分系统 API 端点
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.photon import (
    PhotonAdjustmentRequest,
    PhotonTransferRequest,
)
from app.services.photon_service import get_photon_service

router = APIRouter()


@router.get("/balance", response_model=dict[str, Any])
async def get_photon_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取光子余额

    Returns current user's photon balance.
    """
    photon_service = get_photon_service(db)
    balance = await photon_service.get_balance(str(current_user.id))

    return {
        "success": True,
        "data": {
            "user_id": str(current_user.id),
            "balance": balance,
            "updated_at": current_user.photon_updated_at
        }
    }


@router.get("/transactions", response_model=dict[str, Any])
async def get_transaction_history(
    transaction_type: str | None = Query(None, description="Filter by transaction type"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取光子交易历史

    Returns user's photon transaction history with optional filtering.
    """
    photon_service = get_photon_service(db)
    result = await photon_service.get_transaction_history(
        user_id=str(current_user.id),
        transaction_type=transaction_type,
        limit=limit,
        offset=offset
    )

    return {
        "success": True,
        "data": result["transactions"],
        "meta": {
            "total_count": result["total_count"],
            "limit": result["limit"],
            "offset": result["offset"],
            "has_next": result["offset"] + result["limit"] < result["total_count"]
        }
    }


@router.get("/transactions/summary", response_model=dict[str, Any])
async def get_transaction_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取交易汇总统计

    Returns summary statistics for user's photon transactions.
    """
    photon_service = get_photon_service(db)
    summary = await photon_service.get_transaction_summary(
        user_id=str(current_user.id),
        days=days
    )

    return {
        "success": True,
        "data": summary,
        "meta": {
            "period_days": days
        }
    }


@router.post("/transfer", response_model=dict[str, Any])
async def transfer_photons(
    request: PhotonTransferRequest,
    http_request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    转账光子给其他用户

    Transfers photons from current user to another user.

    R2-8 契约复审：移动端 IdempotencyInterceptor 注入的是 ``X-Idempotency-Key``，
    本端点同时接受两个头别名（与 shop/purchase 同一修复类）。
    """
    # 访客禁止转账：以 JWT 的 is_guest 声明为准（网关/引擎签发访客令牌时
    # 都注入 is_guest=True）。旧实现只比对遗留演示常量
    # GUEST_USER_ID="guest_sparkle_demo_visitor"，真实游客（UUID 主键 +
    # guest_* 用户名）可绕过守卫完成越权转账。
    token_payload = getattr(http_request.state, "token_payload", None) or {}
    if token_payload.get("is_guest"):
        raise HTTPException(
            status_code=403,
            detail="Guest users cannot transfer photons. Please register for a full account."
        )
    idempotency_key = idempotency_key or x_idempotency_key
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    photon_service = get_photon_service(db)

    try:
        result = await photon_service.transfer_photons(
            from_user_id=str(current_user.id),
            to_user_id=str(request.recipient_id),
            amount=request.amount,
            reason=request.message or "User transfer"
        )

        # Get recipient username
        from sqlalchemy import select
        recipient_query = select(User.username).where(User.id == request.recipient_id)
        recipient_result = await db.execute(recipient_query)
        recipient_username = recipient_result.scalar_one_or_none()

        return {
            "success": True,
            "message": f"Successfully transferred {request.amount} photons",
            "data": result,
            "transfer_id": result["transfer_id"],
            "sender_balance_before": result["from_balance"] + request.amount,
            "sender_balance_after": result["from_balance"],
            "recipient_username": recipient_username,
            "amount_transferred": request.amount
        }

    except ValueError as e:
        logger.error(f"Transfer error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected transfer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete transfer") from e


@router.post("/adjust", response_model=dict[str, Any])
async def adjust_photons(
    request: PhotonAdjustmentRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    调整用户光子积分（管理员功能）

    Adjusts a user's photon balance. Admin only.
    """
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    photon_service = get_photon_service(db)

    try:
        if request.amount > 0:
            result = await photon_service.grant_photons(
                user_id=str(request.user_id),
                amount=request.amount,
                source=request.reason,
                transaction_type=request.transaction_type.value,
                metadata=request.extra_data
            )
        else:
            result = await photon_service.deduct_photons(
                user_id=str(request.user_id),
                amount=abs(request.amount),
                reason=request.reason,
                transaction_type=request.transaction_type.value,
                metadata=request.extra_data
            )

        # Record transaction history
        await photon_service.record_transaction(
            user_id=str(request.user_id),
            transaction_type=request.transaction_type.value,
            amount=request.amount,
            balance_before=result["old_balance"],
            balance_after=result["new_balance"],
            source=request.reason,
            related_item_id=request.related_item_id,
            metadata=request.extra_data
        )

        return {
            "success": True,
            "message": "Successfully adjusted photon balance",
            "data": {
                "user_id": result["user_id"],
                "balance": result["new_balance"],
                "change": request.amount
            }
        }

    except ValueError as e:
        logger.error(f"Adjustment error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected adjustment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete adjustment") from e
