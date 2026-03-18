"""
Equipment Service
统一处理用户装备真源与派生字段同步
"""
from __future__ import annotations
from datetime import timezone, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.achievement import UserGalaxySkin, UserTitle
from app.models.shop import ShopItem, ShopItemType, ShopPurchase
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EquipmentSource:
    ACHIEVEMENT = "achievement"
    SHOP = "shop"


class EquipmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def equip_achievement_skin(self, user_id: str, skin_id: str) -> dict[str, Any]:
        user_skin = await self._get_achievement_skin_ownership(user_id, skin_id)
        if not user_skin:
            raise ValueError(f"Skin {skin_id} not unlocked")

        await self._set_equipped_skin(user_id, skin_id, EquipmentSource.ACHIEVEMENT)
        return {
            "success": True,
            "equipped_skin_id": skin_id,
            "equipped_skin_source": EquipmentSource.ACHIEVEMENT,
            "equipped_at": _utcnow().isoformat(),
        }

    async def equip_shop_skin(self, user_id: str, shop_item_id: str) -> dict[str, Any]:
        item = await self._get_owned_shop_item(user_id, shop_item_id, ShopItemType.SKIN)
        if not item:
            raise ValueError(f"User does not own skin {shop_item_id}")

        await self._set_equipped_skin(user_id, shop_item_id, EquipmentSource.SHOP)
        return {
            "success": True,
            "equipped_skin_id": shop_item_id,
            "equipped_skin_source": EquipmentSource.SHOP,
            "item_name": item.name,
            "equipped_at": _utcnow().isoformat(),
        }

    async def unequip_skin(self, user_id: str) -> dict[str, Any]:
        await self._set_equipped_skin(user_id, None, None)
        return {
            "success": True,
            "equipped_skin_id": None,
            "equipped_skin_source": None,
            "equipped_at": _utcnow().isoformat(),
        }

    async def equip_achievement_title(self, user_id: str, title_id: str) -> dict[str, Any]:
        user_title = await self._get_achievement_title_ownership(user_id, title_id)
        if not user_title:
            raise ValueError(f"Title {title_id} not found")

        await self._set_equipped_title(user_id, title_id, EquipmentSource.ACHIEVEMENT)
        return {
            "success": True,
            "equipped_title": title_id,
            "equipped_title_source": EquipmentSource.ACHIEVEMENT,
            "equipped_at": _utcnow().isoformat(),
        }

    async def equip_shop_title(self, user_id: str, shop_item_id: str) -> dict[str, Any]:
        item = await self._get_owned_shop_item(user_id, shop_item_id, ShopItemType.TITLE)
        if not item:
            raise ValueError(f"User does not own title {shop_item_id}")

        await self._set_equipped_title(user_id, shop_item_id, EquipmentSource.SHOP)
        return {
            "success": True,
            "equipped_title": shop_item_id,
            "equipped_title_source": EquipmentSource.SHOP,
            "item_name": item.name,
            "equipped_at": _utcnow().isoformat(),
        }

    async def unequip_title(self, user_id: str) -> dict[str, Any]:
        await self._set_equipped_title(user_id, None, None)
        return {
            "success": True,
            "equipped_title": None,
            "equipped_title_source": None,
            "equipped_at": _utcnow().isoformat(),
        }

    async def sync_derived_flags(self, user_id: str) -> None:
        user = await self._get_locked_user(user_id)
        await self._sync_derived_flags_for_user(user)
        await self.db.commit()

    async def backfill_user_equipment_state(self) -> dict[str, int]:
        users_result = await self.db.execute(select(User))
        users = users_result.scalars().all()

        skin_backfilled = 0
        title_backfilled = 0

        for user in users:
            if await self._backfill_skin_for_user(user):
                skin_backfilled += 1
            if await self._backfill_title_for_user(user):
                title_backfilled += 1
            await self._sync_derived_flags_for_user(user)

        await self.db.commit()
        return {
            "users_processed": len(users),
            "skins_backfilled": skin_backfilled,
            "titles_backfilled": title_backfilled,
        }

    async def _set_equipped_skin(self, user_id: str, equipped_id: str | None, source: str | None) -> None:
        async with self._transaction():
            user = await self._get_locked_user(user_id)
            user.equipped_skin = equipped_id
            user.equipped_skin_source = source
            await self._sync_derived_flags_for_user(user)
            await self.db.flush()

    async def _set_equipped_title(self, user_id: str, equipped_id: str | None, source: str | None) -> None:
        async with self._transaction():
            user = await self._get_locked_user(user_id)
            user.equipped_title = equipped_id
            user.equipped_title_source = source
            await self._sync_derived_flags_for_user(user)
            await self.db.flush()

    async def _get_locked_user(self, user_id: str) -> User:
        # Use options(noload()) to prevent eager loading of relationships that cause
        # "FOR UPDATE cannot be applied to the nullable side of an outer join" error
        from sqlalchemy.orm import noload
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(noload(User.push_preference), noload(User.intervention_settings))
            .with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    async def _sync_derived_flags_for_user(self, user: User) -> None:
        await self.db.execute(
            update(UserGalaxySkin)
            .where(UserGalaxySkin.user_id == user.id)
            .values(is_equipped=False)
        )
        await self.db.execute(
            update(UserTitle)
            .where(UserTitle.user_id == user.id)
            .values(is_equipped=False)
        )

        if user.equipped_skin_source == EquipmentSource.ACHIEVEMENT and user.equipped_skin:
            await self.db.execute(
                update(UserGalaxySkin)
                .where(
                    and_(
                        UserGalaxySkin.user_id == user.id,
                        UserGalaxySkin.skin_id == user.equipped_skin,
                    )
                )
                .values(is_equipped=True)
            )

        if user.equipped_title_source == EquipmentSource.ACHIEVEMENT and user.equipped_title:
            await self.db.execute(
                update(UserTitle)
                .where(
                    and_(
                        UserTitle.user_id == user.id,
                        UserTitle.title_id == user.equipped_title,
                    )
                )
                .values(is_equipped=True)
            )

    async def _get_achievement_skin_ownership(self, user_id: str, skin_id: str) -> UserGalaxySkin | None:
        result = await self.db.execute(
            select(UserGalaxySkin).where(
                and_(
                    UserGalaxySkin.user_id == user_id,
                    UserGalaxySkin.skin_id == skin_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_achievement_title_ownership(self, user_id: str, title_id: str) -> UserTitle | None:
        result = await self.db.execute(
            select(UserTitle).where(
                and_(
                    UserTitle.user_id == user_id,
                    UserTitle.title_id == title_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_owned_shop_item(
        self,
        user_id: str,
        item_id: str,
        item_type: ShopItemType,
    ) -> ShopItem | None:
        result = await self.db.execute(
            select(ShopItem)
            .join(ShopPurchase, ShopPurchase.item_id == ShopItem.id)
            .where(
                and_(
                    ShopPurchase.user_id == user_id,
                    ShopItem.id == item_id,
                    ShopItem.item_type == item_type,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _backfill_skin_for_user(self, user: User) -> bool:
        original_value = user.equipped_skin
        original_source = user.equipped_skin_source

        if original_value:
            owned_shop_skin = await self._get_owned_shop_item(user.id, original_value, ShopItemType.SKIN)
            if owned_shop_skin:
                user.equipped_skin_source = EquipmentSource.SHOP
                return original_source != EquipmentSource.SHOP

        result = await self.db.execute(
            select(UserGalaxySkin)
            .where(
                and_(
                    UserGalaxySkin.user_id == user.id,
                    UserGalaxySkin.is_equipped.is_(True),
                )
            )
            .order_by(UserGalaxySkin.unlocked_at.desc())
        )
        user_skins = result.scalars().all()
        if user_skins:
            if len(user_skins) > 1:
                logger.warning(
                    "User {} has multiple achievement skins equipped; picking latest unlocked_at",
                    user.id,
                )
            user.equipped_skin = user_skins[0].skin_id
            user.equipped_skin_source = EquipmentSource.ACHIEVEMENT
            return original_value != user.equipped_skin or original_source != EquipmentSource.ACHIEVEMENT

        user.equipped_skin = None
        user.equipped_skin_source = None
        return original_value is not None or original_source is not None

    async def _backfill_title_for_user(self, user: User) -> bool:
        original_value = user.equipped_title
        original_source = user.equipped_title_source

        if original_value:
            owned_shop_title = await self._get_owned_shop_item(user.id, original_value, ShopItemType.TITLE)
            if owned_shop_title:
                user.equipped_title_source = EquipmentSource.SHOP
                return original_source != EquipmentSource.SHOP

        result = await self.db.execute(
            select(UserTitle)
            .where(
                and_(
                    UserTitle.user_id == user.id,
                    UserTitle.is_equipped.is_(True),
                )
            )
            .order_by(UserTitle.unlocked_at.desc())
        )
        user_titles = result.scalars().all()
        if user_titles:
            if len(user_titles) > 1:
                logger.warning(
                    "User {} has multiple achievement titles equipped; picking latest unlocked_at",
                    user.id,
                )
            user.equipped_title = user_titles[0].title_id
            user.equipped_title_source = EquipmentSource.ACHIEVEMENT
            return original_value != user.equipped_title or original_source != EquipmentSource.ACHIEVEMENT

        user.equipped_title = None
        user.equipped_title_source = None
        return original_value is not None or original_source is not None

    def _transaction(self):
        owns_transaction = not self.db.in_transaction()
        return self.db.begin() if owns_transaction else self.db.begin_nested()


def get_equipment_service(db: AsyncSession) -> EquipmentService:
    return EquipmentService(db)
