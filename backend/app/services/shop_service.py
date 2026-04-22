"""
Shop Service - 商城核心业务逻辑
处理商城物品查询、购买流程、物品发放等
"""

from __future__ import annotations
from datetime import timezone, datetime
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.event_bus import event_bus_reliable
from app.models.shop import ItemRarity, ShopItem, ShopItemType, ShopPurchase, UserConsumable
from app.services.equipment_service import EquipmentService
from app.services.photon_service import PhotonService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ShopService:
    """
    商城服务

    功能：
    - 获取商城物品列表
    - 购买物品（含事务性处理）
    - 发放物品到用户背包
    - 查询购买历史
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.photon_service = PhotonService(db)

    async def _publish_purchase_event(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            await event_bus_reliable.publish(event_type, payload)
        except Exception as exc:
            logger.warning("Failed to publish {}: {}", event_type, exc)

    async def get_available_items(
        self,
        item_type: ShopItemType | None = None,
        category: str | None = None,
        rarity: ItemRarity | None = None,
        only_available: bool = True,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取商城物品列表

        Args:
            item_type: 物品类型筛选
            category: 分类筛选
            rarity: 稀有度筛选
            only_available: 仅显示可购买物品
            user_id: 用户ID（用于标记已拥有物品）

        Returns:
            物品列表（含是否已拥有标记）
        """
        # 构建查询
        query = select(ShopItem)

        if only_available:
            query = query.where(ShopItem.is_available)

        if item_type:
            query = query.where(ShopItem.item_type == item_type)

        if category:
            query = query.where(ShopItem.category == category)

        if rarity:
            query = query.where(ShopItem.rarity == rarity)

        # 按排序权重和稀有度排序
        query = query.order_by(ShopItem.sort_order.desc(), ShopItem.rarity.desc(), ShopItem.price_photons.asc())

        result = await self.db.execute(query)
        items = result.scalars().all()

        # 转换为字典列表
        items_data = []
        for item in items:
            item_dict = {
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
                "is_owned": False,
            }

            # 如果提供了用户ID，检查是否已拥有
            if user_id:
                item_dict["is_owned"] = await self._check_item_ownership(user_id, item.id, item.item_type)

            items_data.append(item_dict)

        return items_data

    async def _check_item_ownership(self, user_id: str, item_id: str, item_type: ShopItemType) -> bool:
        """
        检查用户是否已拥有物品

        Args:
            user_id: 用户ID
            item_id: 物品ID
            item_type: 物品类型

        Returns:
            是否已拥有
        """
        # 对于消耗品，检查背包中是否有库存
        if item_type in ["consumable", "boost"]:
            query = select(UserConsumable).where(
                and_(
                    UserConsumable.user_id == user_id,
                    UserConsumable.consumable_id == item_id,
                    UserConsumable.quantity > 0,
                )
            )
            result = await self.db.execute(query)
            consumable = result.scalar_one_or_none()
            return consumable is not None

        # 对于皮肤和称号，检查购买记录（修复bug：之前永远返回False）
        if item_type in ["skin", "title"]:
            query = select(ShopPurchase).where(and_(ShopPurchase.user_id == user_id, ShopPurchase.item_id == item_id))
            result = await self.db.execute(query)
            purchase = result.scalar_one_or_none()
            return purchase is not None

        # 对于视觉元素，检查是否已解锁
        if item_type == "visual_element":
            from app.models.visual_element import UserVisualElement

            query = select(UserVisualElement).where(
                and_(UserVisualElement.user_id == user_id, UserVisualElement.element_id == item_id)
            )
            result = await self.db.execute(query)
            element = result.scalar_one_or_none()
            return element is not None

        return False

    async def purchase_item(self, user_id: str, item_id: str) -> dict[str, Any]:
        """
        购买物品（事务性处理）

        购买流程：
        1. 验证物品存在且可购买
        2. 检查库存（限量物品）
        3. 检查用户余额
        4. 计算实际价格
        5. 扣除光子（事务性）
        6. 发放物品到背包
        7. 记录购买历史
        8. 发送 WebSocket 通知

        Args:
            user_id: 用户ID
            item_id: 物品ID

        Returns:
            购买结果

        Raises:
            ValueError: 物品不存在、不可购买、库存不足、余额不足等
        """
        attempt_id = str(uuid4())
        try:
            await self._publish_purchase_event(
                "shop.purchase_initiated",
                {
                    "event_type": "shop.purchase_initiated",
                    "user_id": str(user_id),
                    "item_id": str(item_id),
                    "purchase_attempt_id": attempt_id,
                    "timestamp": _utcnow().isoformat(),
                },
            )
            owns_transaction = not self.db.in_transaction()
            tx_context = self.db.begin() if owns_transaction else self.db.begin_nested()
            async with tx_context:
                # 1. 查询物品（加行锁防止并发超卖）
                query = (
                    select(ShopItem).where(and_(ShopItem.id == item_id, ShopItem.is_available)).with_for_update()
                )  # 行锁

                result = await self.db.execute(query)
                item = result.scalar_one_or_none()

                if not item:
                    raise ValueError(f"Item {item_id} not found or not available")

                actual_price = item.price_photons

                # 2. 检查库存
                if item.is_limited and item.stock_quantity <= 0:
                    raise ValueError(f"Item {item_id} is out of stock")

                # 3. 检查是否已拥有（非消耗品）
                if item.item_type not in ["consumable", "boost"]:
                    already_owned = await self._check_item_ownership(user_id, item_id, item.item_type)
                    if already_owned:
                        raise ValueError(f"User already owns item {item_id}")

                # 4. 扣除光子（使用内部方法，不提交事务）
                old_balance, new_balance, _ = await self.photon_service._update_balance(
                    user_id, -actual_price, delete_cache=False, lock_for_update=True
                )

                # 5. 记录交易历史（修复bug：购买未记录交易）
                await self.photon_service.record_transaction(
                    user_id=user_id,
                    transaction_type="purchase",
                    amount=-actual_price,
                    balance_before=old_balance,
                    balance_after=new_balance,
                    source=f"Shop purchase: {item.name}",
                    related_item_id=item_id,
                    extra_data={"item_name": item.name, "item_type": item.item_type, "item_rarity": item.rarity},
                )

                # 6. 更新库存（限量物品）
                if item.is_limited:
                    item.stock_quantity -= 1
                    await self.db.flush()

                # 7. 发放物品到背包
                await self._grant_item_to_user(user_id, item)

                # 8. 创建购买记录
                purchase = ShopPurchase(
                    id=str(uuid4()),
                    user_id=user_id,
                    item_id=item_id,
                    price_paid=actual_price,
                    photon_balance_before=old_balance,
                    photon_balance_after=new_balance,
                )
                self.db.add(purchase)
                await self.db.flush()

                if item.item_type == ShopItemType.SKIN:
                    await EquipmentService(self.db).equip_shop_skin(user_id, item.id)
                elif item.item_type == ShopItemType.TITLE:
                    await EquipmentService(self.db).equip_shop_title(user_id, item.id)

            # 9. 删除缓存（事务提交后）
            from app.config import settings
            from app.core.cache import cache_service

            cache_key = f"{settings.APP_NAME}:photon:balance:{user_id}"
            await cache_service.delete(cache_key)

            await self.db.refresh(purchase)

            logger.info(f"User {user_id} purchased item {item_id}, price={actual_price}, balance={new_balance}")

            await self._publish_purchase_event(
                "shop.purchase_completed",
                {
                    "event_type": "shop.purchase_completed",
                    "user_id": str(user_id),
                    "item_id": str(item_id),
                    "purchase_attempt_id": attempt_id,
                    "purchase_id": str(purchase.id),
                    "price_paid": actual_price,
                    "balance_before": old_balance,
                    "balance_after": new_balance,
                    "item_type": str(item.item_type),
                    "timestamp": _utcnow().isoformat(),
                },
            )

            # 10. 发送 WebSocket 通知（异步，不阻塞）
            # TRACKED(TD-006): 实现购买成功通知
            # await websocket_manager.broadcast_to_user(
            #     user_id,
            #     {
            #         "type": "item_purchased",
            #         "item_id": item_id,
            #         "item_name": item.name,
            #         "price_paid": actual_price,
            #         "new_balance": new_balance
            #     }
            # )

            return {
                "success": True,
                "purchase_id": str(purchase.id),
                "item_id": item_id,
                "item_name": item.name,
                "price_paid": actual_price,
                "balance_before": old_balance,
                "balance_after": new_balance,
                "item_type": item.item_type,
                "rarity": item.rarity,
            }

        except Exception as e:
            # 仅回滚当前方法创建的顶层事务，避免破坏外层会话中的已成功操作
            if owns_transaction and self.db.in_transaction():
                await self.db.rollback()
            await self._publish_purchase_event(
                "shop.purchase_failed",
                {
                    "event_type": "shop.purchase_failed",
                    "user_id": str(user_id),
                    "item_id": str(item_id),
                    "purchase_attempt_id": attempt_id,
                    "error": str(e),
                    "timestamp": _utcnow().isoformat(),
                },
            )
            logger.error(f"Purchase failed: user_id={user_id}, item_id={item_id}, error={e}")
            raise

    async def _grant_item_to_user(self, user_id: str, item: ShopItem) -> None:
        """
        发放物品到用户背包

        Args:
            user_id: 用户ID
            item: 物品对象
        """
        # 消耗品类型：添加到 user_consumables 表
        if item.item_type in ["consumable", "boost"]:
            # 检查是否已有该消耗品
            query = select(UserConsumable).where(
                and_(UserConsumable.user_id == user_id, UserConsumable.consumable_id == item.id)
            )
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # 增加数量
                existing.quantity += 1
                existing.updated_at = _utcnow()
            else:
                # 创建新记录
                effect_type = item.item_config.get("effect_type") if item.item_config else None

                consumable = UserConsumable(
                    id=str(uuid4()),
                    user_id=user_id,
                    consumable_id=item.id,
                    effect_type=effect_type if effect_type else "exp_boost",
                    quantity=1,
                    expires_at=item.item_config.get("expires_at") if item.item_config else None,
                )
                self.db.add(consumable)

        elif item.item_type in ["skin", "title"]:
            # 非消耗品 ownership 以购买记录为准，自动装备在购买记录落库后统一处理
            pass

        elif item.item_type == "visual_element":
            # 视觉元素：解锁对应的视觉元素
            from app.services.visual_element_service import VisualElementService

            visual_service = VisualElementService(self.db)

            element_id = item.item_config.get("element_id") if item.item_config else None
            if element_id:
                await visual_service.unlock_element_for_user(
                    user_id=user_id, element_id=element_id, unlock_source="shop", source_id=item.id
                )

        await self.db.flush()

    async def get_user_purchases(self, user_id: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """
        查询用户购买历史

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            购买历史列表和分页信息
        """
        # 查询购买记录
        query = (
            select(ShopPurchase)
            .where(ShopPurchase.user_id == user_id)
            .order_by(ShopPurchase.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(ShopPurchase.item))
        )

        result = await self.db.execute(query)
        purchases = result.scalars().all()

        # 查询总数
        count_query = select(func.count(ShopPurchase.id)).where(ShopPurchase.user_id == user_id)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()

        # 转换为字典列表
        purchases_data = []
        for purchase in purchases:
            purchases_data.append(
                {
                    "id": str(purchase.id),
                    "item_id": purchase.item_id,
                    "item_name": purchase.item.name if purchase.item else "Unknown",
                    "item_icon_url": purchase.item.icon_url if purchase.item else None,
                    "item_type": purchase.item.item_type if purchase.item else None,
                    "price_paid": purchase.price_paid,
                    "photon_balance_before": purchase.photon_balance_before,
                    "photon_balance_after": purchase.photon_balance_after,
                    "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
                }
            )

        return {"purchases": purchases_data, "total_count": total_count, "limit": limit, "offset": offset}

    async def get_item_by_id(self, item_id: str) -> ShopItem | None:
        """
        根据 ID 获取物品详情

        Args:
            item_id: 物品ID

        Returns:
            物品对象或 None
        """
        query = select(ShopItem).where(ShopItem.id == item_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


# 全局单例获取函数
def get_shop_service(db: AsyncSession) -> ShopService:
    """
    获取商城服务实例

    Args:
        db: 数据库会话

    Returns:
        ShopService 实例
    """
    return ShopService(db)
