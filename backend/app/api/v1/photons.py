"""
Photon API Endpoints
光子积分系统 API 端点
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    转账光子给其他用户

    Transfers photons from current user to another user.
    """
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
            "transfer_id": str(UUID("00000000-0000-0000-0000-000000000000")),  # Placeholder
            "sender_balance_before": result["from_balance"] + request.amount,
            "sender_balance_after": result["from_balance"],
            "recipient_username": recipient_username,
            "amount_transferred": request.amount
        }

    except ValueError as e:
        logger.error(f"Transfer error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected transfer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete transfer")


@router.post("/adjust", response_model=dict[str, Any])
async def adjust_photons(
    request: PhotonAdjustmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    调整用户光子积分（管理员功能）

    Adjusts a user's photon balance. Admin only.
    """
    # TODO: Add admin check
    # if not current_user.is_superuser:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    photon_service = get_photon_service(db)

    try:
        if request.amount > 0:
            result = await photon_service.grant_photons(
                user_id=str(request.user_id),
                amount=request.amount,
                source=request.reason,
                transaction_type=request.transaction_type.value,
                metadata=request.metadata
            )
        else:
            result = await photon_service.deduct_photons(
                user_id=str(request.user_id),
                amount=abs(request.amount),
                reason=request.reason,
                transaction_type=request.transaction_type.value,
                metadata=request.metadata
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
            metadata=request.metadata
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected adjustment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete adjustment")
