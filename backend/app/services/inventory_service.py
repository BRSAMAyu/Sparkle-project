"""
Inventory Service - 物品管理服务
处理用户物品查询、装备物品、消耗品使用等
"""
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shop import ConsumableEffectType, ShopItem, ShopItemType, ShopPurchase, UserConsumable
from app.models.user import User
from app.services.equipment_service import EquipmentService, EquipmentSource


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class InventoryService:
    """
    物品管理服务

    功能：
    - 获取用户物品背包
    - 装备皮肤/称号
    - 查询已拥有物品
    - 使用消耗品
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_inventory(
        self,
        user_id: str
    ) -> dict[str, list[dict[str, Any]]]:
        """
        获取用户物品背包（按类型分组）

        Args:
            user_id: 用户ID

        Returns:
            分组的物品字典 {"skins": [...], "titles": [...], "consumables": [...]}
        """
        inventory = {
            "skins": [],
            "titles": [],
            "consumables": [],
            "boosts": []
        }

        # 1. 获取用户当前装备的皮肤和称号
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if user:
            # 当前装备的皮肤
            if user.equipped_skin and user.equipped_skin_source == EquipmentSource.SHOP:
                skin_item = await self._get_shop_item(user.equipped_skin)
                if skin_item:
                    inventory["skins"].append({
                        "id": skin_item.id,
                        "name": skin_item.name,
                        "icon_url": skin_item.icon_url,
                        "item_type": skin_item.item_type,
                        "rarity": skin_item.rarity,
                        "category": skin_item.category,
                        "is_equipped": True,
                        "item_config": skin_item.item_config
                    })

            # 当前装备的称号
            if user.equipped_title and user.equipped_title_source == EquipmentSource.SHOP:
                title_item = await self._get_shop_item(user.equipped_title)
                if title_item:
                    inventory["titles"].append({
                        "id": title_item.id,
                        "name": title_item.name,
                        "icon_url": title_item.icon_url,
                        "item_type": title_item.item_type,
                        "rarity": title_item.rarity,
                        "category": title_item.category,
                        "is_equipped": True,
                        "item_config": title_item.item_config
                    })

        # 2. 获取已购买的皮肤和称号
        exclude_ids: list[str] = []
        if user:
            if user.equipped_skin and user.equipped_skin_source == EquipmentSource.SHOP:
                exclude_ids.append(user.equipped_skin)
            if user.equipped_title and user.equipped_title_source == EquipmentSource.SHOP:
                exclude_ids.append(user.equipped_title)

        purchase_query = select(ShopPurchase).where(
            ShopPurchase.user_id == user_id
        )
        if exclude_ids:
            purchase_query = purchase_query.where(
                ShopPurchase.item_id.notin_(exclude_ids)
            )
        purchase_query = purchase_query.options(selectinload(ShopPurchase.item))

        purchase_result = await self.db.execute(purchase_query)
        purchases = purchase_result.scalars().all()

        for purchase in purchases:
            if not purchase.item:
                continue

            item_data = {
                "id": purchase.item.id,
                "name": purchase.item.name,
                "icon_url": purchase.item.icon_url,
                "item_type": purchase.item.item_type,
                "rarity": purchase.item.rarity,
                "category": purchase.item.category,
                "is_equipped": False,
                "item_config": purchase.item.item_config,
                "purchased_at": purchase.created_at.isoformat()
            }

            if purchase.item.item_type == ShopItemType.SKIN:
                inventory["skins"].append(item_data)
            elif purchase.item.item_type == ShopItemType.TITLE:
                inventory["titles"].append(item_data)

        # 3. 获取消耗品
        consumable_query = select(UserConsumable).where(
            and_(
                UserConsumable.user_id == user_id,
                UserConsumable.quantity > 0
            )
        ).options(selectinload(UserConsumable.consumable_item))

        consumable_result = await self.db.execute(consumable_query)
        consumables = consumable_result.scalars().all()

        for consumable in consumables:
            if not consumable.consumable_item:
                continue

            item_data = {
                "id": consumable.consumable_item.id,
                "name": consumable.consumable_item.name,
                "icon_url": consumable.consumable_item.icon_url,
                "item_type": consumable.consumable_item.item_type,
                "rarity": consumable.consumable_item.rarity,
                "category": consumable.consumable_item.category,
                "quantity": consumable.quantity,
                "is_equipped": False,
                "effect_type": consumable.effect_type,
                "expires_at": consumable.expires_at.isoformat() if consumable.expires_at else None,
                "is_expired": consumable.is_expired,
                "is_valid": consumable.is_valid,
                "item_config": consumable.consumable_item.item_config
            }

            if consumable.consumable_item.item_type == ShopItemType.BOOST:
                inventory["boosts"].append(item_data)
            else:
                inventory["consumables"].append(item_data)

        return inventory

    async def _get_shop_item(self, item_id: str) -> ShopItem | None:
        """获取商城物品"""
        query = select(ShopItem).where(ShopItem.id == item_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def equip_skin(
        self,
        user_id: str,
        item_id: str | None
    ) -> dict[str, Any]:
        """
        装备皮肤

        Args:
            user_id: 用户ID
            item_id: 皮肤物品ID

        Returns:
            装备结果

        Raises:
            ValueError: 物品不存在或未拥有
        """
        equipment_service = EquipmentService(self.db)
        if item_id is None:
            result = await equipment_service.unequip_skin(user_id)
            logger.info(f"User {user_id} unequipped skin")
            return {
                "success": True,
                "item_id": None,
                "item_name": None,
                "equipped_at": result["equipped_at"],
            }

        result = await equipment_service.equip_shop_skin(user_id, item_id)
        logger.info(f"User {user_id} equipped skin {item_id}")
        return {
            "success": True,
            "item_id": item_id,
            "item_name": result.get("item_name"),
            "equipped_at": result["equipped_at"],
        }

    async def equip_title(
        self,
        user_id: str,
        item_id: str | None
    ) -> dict[str, Any]:
        """
        装备称号

        Args:
            user_id: 用户ID
            item_id: 称号物品ID

        Returns:
            装备结果

        Raises:
            ValueError: 物品不存在或未拥有
        """
        equipment_service = EquipmentService(self.db)
        if item_id is None:
            result = await equipment_service.unequip_title(user_id)
            logger.info(f"User {user_id} unequipped title")
            return {
                "success": True,
                "item_id": None,
                "item_name": None,
                "equipped_at": result["equipped_at"],
            }

        result = await equipment_service.equip_shop_title(user_id, item_id)
        logger.info(f"User {user_id} equipped title {item_id}")
        return {
            "success": True,
            "item_id": item_id,
            "item_name": result.get("item_name"),
            "equipped_at": result["equipped_at"],
        }

    async def _check_item_ownership(
        self,
        user_id: str,
        item_id: str,
        item_type: ShopItemType
    ) -> bool:
        """
        检查用户是否拥有物品

        Args:
            user_id: 用户ID
            item_id: 物品ID
            item_type: 物品类型

        Returns:
            是否拥有
        """
        # 检查购买记录
        purchase_query = select(ShopPurchase).where(
            and_(
                ShopPurchase.user_id == user_id,
                ShopPurchase.item_id == item_id
            )
        )
        result = await self.db.execute(purchase_query)
        purchase = result.scalar_one_or_none()

        return purchase is not None

    async def get_owned_items(
        self,
        user_id: str,
        item_type: ShopItemType | None = None
    ) -> list[str]:
        """
        查询用户已拥有的物品ID列表

        Args:
            user_id: 用户ID
            item_type: 可选的物品类型筛选

        Returns:
            物品ID列表
        """
        query = select(ShopPurchase.item_id).where(
            ShopPurchase.user_id == user_id
        )

        if item_type:
            query = query.join(ShopItem).where(ShopItem.item_type == item_type)

        result = await self.db.execute(query)
        item_ids = result.scalars().all()

        return list(item_ids)

    async def use_consumable(
        self,
        user_id: str,
        consumable_id: str,
        quantity: int = 1
    ) -> dict[str, Any]:
        """
        使用消耗品

        Args:
            user_id: 用户ID
            consumable_id: 消耗品ID
            quantity: 使用数量

        Returns:
            使用结果

        Raises:
            ValueError: 消耗品不存在、数量不足、已过期等
        """
        # 1. 查询消耗品记录
        query = select(UserConsumable).where(
            and_(
                UserConsumable.user_id == user_id,
                UserConsumable.consumable_id == consumable_id
            )
        ).options(selectinload(UserConsumable.consumable_item))

        result = await self.db.execute(query)
        consumable = result.scalar_one_or_none()

        if not consumable:
            raise ValueError(f"Consumable {consumable_id} not found in user inventory")

        # 2. 检查是否过期
        if consumable.is_expired:
            raise ValueError(f"Consumable {consumable_id} has expired")

        # 3. 检查数量
        if consumable.quantity < quantity:
            raise ValueError(
                f"Insufficient consumable quantity: {consumable.quantity} < {quantity}"
            )

        # 4. 应用效果
        effect_result = await self._apply_consumable_effect(user_id, consumable, quantity)

        # 5. 更新数量
        consumable.quantity -= quantity
        consumable.updated_at = _utcnow()

        # 如果数量为0，可以选择删除记录或保留为0
        if consumable.quantity == 0:
            # 可选：删除记录
            # await self.db.delete(consumable)
            pass

        await self.db.commit()
        await self.db.refresh(consumable)

        logger.info(
            f"User {user_id} used consumable {consumable_id}, "
            f"quantity={quantity}, remaining={consumable.quantity}"
        )

        return {
            "success": True,
            "consumable_id": consumable_id,
            "consumable_name": consumable.consumable_item.name if consumable.consumable_item else "Unknown",
            "quantity_used": quantity,
            "remaining_quantity": consumable.quantity,
            "effect_type": consumable.effect_type,
            "effect_result": effect_result
        }

    async def _apply_consumable_effect(
        self,
        user_id: str,
        consumable: UserConsumable,
        quantity: int
    ) -> dict[str, Any]:
        """
        应用消耗品效果

        Args:
            user_id: 用户ID
            consumable: 消耗品对象
            quantity: 使用数量

        Returns:
            效果结果
        """
        # 根据效果类型应用不同逻辑
        effect_type = consumable.effect_type

        if effect_type == ConsumableEffectType.EXP_BOOST:
            # 经验加成：记录到用户状态
            # TODO: 实现 exp boost 效果
            return {"effect": "exp_boost", "duration_hours": 24, "multiplier": 2.0}

        elif effect_type == ConsumableEffectType.PHOTON_BOOST:
            # 光子加成：记录到用户状态
            # TODO: 实现 photon boost 效果
            return {"effect": "photon_boost", "duration_hours": 24, "multiplier": 1.5}

        elif effect_type == ConsumableEffectType.STREAK_FREEZE:
            # 连击冻结：增加冻结次数
            # TODO: 实现 streak freeze 效果
            return {"effect": "streak_freeze", "charges_added": quantity}

        elif effect_type == ConsumableEffectType.HINT_REVEAL:
            # 提示解锁：增加提示次数
            # TODO: 实现 hint reveal 效果
            return {"effect": "hint_reveal", "hints_added": quantity}

        elif effect_type == ConsumableEffectType.ENERGY_RESTORE:
            # 能量恢复：恢复能量值
            # TODO: 实现 energy restore 效果
            return {"effect": "energy_restore", "energy_restored": quantity * 10}

        elif effect_type == ConsumableEffectType.CUSTOM_AVATAR:
            # 自定义头像：解锁自定义头像权限
            # TODO: 实现 custom avatar 效果
            return {"effect": "custom_avatar", "unlocked": True}

        else:
            return {"effect": "unknown"}


# 全局单例获取函数
def get_inventory_service(db: AsyncSession) -> InventoryService:
    """
    获取物品管理服务实例

    Args:
        db: 数据库会话

    Returns:
        InventoryService 实例
    """
    return InventoryService(db)
