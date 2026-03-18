"""
Inventory API Endpoints
物品背包系统 API 端点
"""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.shop import ShopItemType
from app.models.user import User
from app.schemas.shop import (
    EquipRequest,
    UseConsumableRequest,
)
from app.services.inventory_service import get_inventory_service

router = APIRouter()


@router.get("", response_model=dict[str, Any])
async def get_inventory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户物品背包

    Returns user's inventory grouped by item type (skins, titles, consumables, boosts).
    """
    inventory_service = get_inventory_service(db)
    inventory = await inventory_service.get_user_inventory(str(current_user.id))

    # Count totals
    total_skins = len(inventory["skins"])
    total_titles = len(inventory["titles"])
    total_consumables = len(inventory["consumables"])
    total_boosts = len(inventory["boosts"])

    return {
        "success": True,
        "data": inventory,
        "meta": {
            "total_skins": total_skins,
            "total_titles": total_titles,
            "total_consumables": total_consumables,
            "total_boosts": total_boosts,
            "total_items": total_skins + total_titles + total_consumables + total_boosts
        }
    }


@router.post("/equip", response_model=dict[str, Any])
async def equip_item(
    request: EquipRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    装备物品（皮肤或称号）

    Equips a skin or title to the user's profile.
    """
    inventory_service = get_inventory_service(db)

    try:
        if request.item_type == ShopItemType.SKIN:
            result = await inventory_service.equip_skin(
                user_id=str(current_user.id),
                item_id=request.item_id
            )
        elif request.item_type == ShopItemType.TITLE:
            result = await inventory_service.equip_title(
                user_id=str(current_user.id),
                item_id=request.item_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot equip item type: {request.item_type}"
            )

        return {
            "success": True,
            "message": f"Successfully equipped {result['item_name']}",
            "data": result
        }

    except ValueError as e:
        logger.error(f"Equip error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected equip error: {e}")
        raise HTTPException(status_code=500, detail="Failed to equip item")


@router.get("/owned", response_model=dict[str, Any])
async def get_owned_items(
    item_type: ShopItemType | None = Query(None, description="Filter by item type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查询已拥有的物品ID列表

    Returns list of item IDs owned by the user.
    """
    inventory_service = get_inventory_service(db)
    owned_ids = await inventory_service.get_owned_items(
        user_id=str(current_user.id),
        item_type=item_type
    )

    return {
        "success": True,
        "data": owned_ids,
        "meta": {
            "total_count": len(owned_ids),
            "item_type": item_type.value if item_type else "all"
        }
    }


@router.post("/consumables/use", response_model=dict[str, Any])
async def use_consumable(
    request: UseConsumableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    使用消耗品

    Uses a consumable item from user's inventory.
    """
    inventory_service = get_inventory_service(db)

    try:
        result = await inventory_service.use_consumable(
            user_id=str(current_user.id),
            consumable_id=request.consumable_id,
            quantity=request.quantity
        )

        return {
            "success": True,
            "message": f"Successfully used {result['consumable_name']}",
            "data": result,
            "remaining_quantity": result["remaining_quantity"]
        }

    except ValueError as e:
        logger.error(f"Use consumable error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected use consumable error: {e}")
        raise HTTPException(status_code=500, detail="Failed to use consumable")
