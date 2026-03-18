"""
Shop API Endpoints
商城系统 API 端点
"""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.shop import ItemRarity, ShopItemType
from app.models.user import User
from app.schemas.shop import (
    PurchaseRequest,
)
from app.services.shop_service import get_shop_service

router = APIRouter()


@router.get("/items", response_model=dict[str, Any])
async def get_shop_items(
    item_type: ShopItemType | None = Query(None, description="Filter by item type"),
    category: str | None = Query(None, description="Filter by category"),
    rarity: ItemRarity | None = Query(None, description="Filter by rarity"),
    only_available: bool = Query(True, description="Show only available items"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取商城物品列表

    Returns shop items with optional filters. Shows ownership status for current user.
    """
    shop_service = get_shop_service(db)
    items = await shop_service.get_available_items(
        item_type=item_type,
        category=category,
        rarity=rarity,
        only_available=only_available,
        user_id=str(current_user.id)
    )

    return {
        "success": True,
        "data": items,
        "meta": {
            "total_count": len(items),
            "filters": {
                "item_type": item_type.value if item_type else None,
                "category": category,
                "rarity": rarity.value if rarity else None
            }
        }
    }


@router.get("/items/{item_id}", response_model=dict[str, Any])
async def get_shop_item_detail(
    item_id: str = Path(..., description="Item ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取商城物品详情

    Returns detailed information about a specific shop item.
    """
    shop_service = get_shop_service(db)
    item = await shop_service.get_item_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    is_owned = await shop_service._check_item_ownership(
        str(current_user.id), item_id, item.item_type
    )

    return {
        "success": True,
        "data": {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "item_type": item.item_type,
            "category": item.category,
            "price_photons": item.price_photons,
            "original_price": item.original_price,
            "discount_percent": item.discount_percent,
            "is_available": item.is_available,
            "is_limited": item.is_limited,
            "stock_quantity": item.stock_quantity,
            "icon_url": item.icon_url,
            "rarity": item.rarity,
            "item_config": item.item_config,
            "sort_order": item.sort_order,
            "has_discount": item.has_discount,
            "is_in_stock": item.is_in_stock,
            "is_owned": is_owned
        }
    }


@router.post("/purchase", response_model=dict[str, Any])
async def purchase_item(
    request: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    购买商城物品

    Purchases an item from the shop. Deducts photons and adds item to user inventory.
    """
    shop_service = get_shop_service(db)

    try:
        result = await shop_service.purchase_item(
            user_id=str(current_user.id),
            item_id=request.item_id
        )

        return {
            "success": True,
            "message": f"Successfully purchased {result.get('item_name', 'item')}",
            "data": result,
            "item": result,
            "balance_before": result["balance_before"],
            "balance_after": result["balance_after"],
            "price_paid": result["price_paid"]
        }

    except ValueError as e:
        logger.error(f"Purchase error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected purchase error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete purchase")


@router.get("/purchases", response_model=dict[str, Any])
async def get_purchase_history(
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取购买历史

    Returns user's purchase history with pagination.
    """
    shop_service = get_shop_service(db)
    result = await shop_service.get_user_purchases(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset
    )

    return {
        "success": True,
        "data": result["purchases"],
        "meta": {
            "total_count": result["total_count"],
            "limit": result["limit"],
            "offset": result["offset"],
            "has_next": result["offset"] + result["limit"] < result["total_count"]
        }
    }
