"""
Visual Element Service
视觉元素服务 - 处理视觉元素的解锁、装备、查询等逻辑
"""
from __future__ import annotations
from datetime import timezone, datetime
from typing import Any
import uuid

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.visual_element import (
    UserVisualConfig,
    UserVisualElement,
    VisualElement,
    VisualElementRarity,
    VisualElementType,
    VisualElementUnlockSource,
)
from app.schemas.visual_element import (
    EquipElementResponse,
    EquipElementRequest,
    UnlockElementRequest,
    UnlockElementResponse,
    UserVisualConfigResponse,
    VisualElementResponse,
)


class VisualElementService:
    """视觉元素服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_user_id(user_id: uuid.UUID | str) -> uuid.UUID:
        return user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))

    def _is_transaction_managed_externally(self) -> bool:
        return bool(self.db.sync_session.info.get("external_transaction_managed"))

    async def get_all_elements(
        self,
        element_type: VisualElementType | None = None,
        rarity: VisualElementRarity | None = None,
        category: str | None = None,
        include_inactive: bool = False,
        locale: str | None = None,
    ) -> list[VisualElementResponse]:
        """获取所有视觉元素"""
        query = select(VisualElement)

        if not include_inactive:
            query = query.where(VisualElement.is_active == True)

        if element_type:
            query = query.where(VisualElement.element_type == element_type)

        if rarity:
            query = query.where(VisualElement.rarity == rarity)

        if category:
            query = query.where(VisualElement.category == category)

        query = query.order_by(VisualElement.sort_order.desc(), VisualElement.created_at)

        result = await self.db.execute(query)
        elements = result.scalars().all()

        return [self._build_element_response(el, locale) for el in elements]

    async def get_user_elements(
        self,
        user_id: uuid.UUID,
        element_type: VisualElementType | None = None,
        locale: str | None = None,
    ) -> list[VisualElementResponse]:
        """获取用户已解锁的视觉元素。

        默认视觉元素对所有用户都应可见、可装备，即使历史账号没有初始化解锁记录。
        """
        # 查询用户解锁的元素
        query = (
            select(VisualElement)
            .join(UserVisualElement, UserVisualElement.element_id == VisualElement.id)
            .where(UserVisualElement.user_id == user_id)
            .where(VisualElement.is_active == True)
        )

        if element_type:
            query = query.where(VisualElement.element_type == element_type)

        query = query.order_by(UserVisualElement.unlocked_at.desc())

        result = await self.db.execute(query)
        elements = list(result.scalars().all())

        default_query = select(VisualElement).where(
            VisualElement.is_default == True,
            VisualElement.is_active == True,
        )
        if element_type:
            default_query = default_query.where(
                VisualElement.element_type == element_type,
            )
        default_result = await self.db.execute(default_query)
        defaults = default_result.scalars().all()

        seen_ids = {element.id for element in elements}
        for element in defaults:
            if element.id not in seen_ids:
                elements.append(element)

        # 获取用户当前装备
        config = await self._get_or_create_user_config(user_id)

        return [
            self._build_element_response(el, locale, is_unlocked=True, config=config)
            for el in elements
        ]

    async def get_user_config(
        self,
        user_id: uuid.UUID,
        locale: str | None = None,
    ) -> UserVisualConfigResponse:
        """获取用户当前视觉配置"""
        config = await self._get_or_create_user_config(user_id)
        default_elements = await self._get_default_elements_by_type()

        # 获取装备的元素详情
        equipped_background = None
        equipped_particle = None
        equipped_effect = None

        background_id = config.equipped_background_id or (
            default_elements.get(VisualElementType.BACKGROUND).id
            if default_elements.get(VisualElementType.BACKGROUND)
            else None
        )
        if background_id:
            bg = await self._get_element_by_id(background_id)
            if bg:
                equipped_background = self._build_element_response(
                    bg, locale, is_unlocked=True, is_equipped=True
                )

        particle_id = config.equipped_particle_id or (
            default_elements.get(VisualElementType.PARTICLE).id
            if default_elements.get(VisualElementType.PARTICLE)
            else None
        )
        if particle_id:
            pt = await self._get_element_by_id(particle_id)
            if pt:
                equipped_particle = self._build_element_response(
                    pt, locale, is_unlocked=True, is_equipped=True
                )

        effect_id = config.equipped_effect_id or (
            default_elements.get(VisualElementType.EFFECT).id
            if default_elements.get(VisualElementType.EFFECT)
            else None
        )
        if effect_id:
            ef = await self._get_element_by_id(effect_id)
            if ef:
                equipped_effect = self._build_element_response(
                    ef, locale, is_unlocked=True, is_equipped=True
                )

        return UserVisualConfigResponse(
            equipped_background=equipped_background,
            equipped_particle=equipped_particle,
            equipped_effect=equipped_effect,
            background_equipped_at=config.background_equipped_at,
            particle_equipped_at=config.particle_equipped_at,
            effect_equipped_at=config.effect_equipped_at,
        )

    async def equip_element(
        self,
        user_id: uuid.UUID,
        element_id: str,
        locale: str | None = None,
    ) -> EquipElementResponse:
        """装备视觉元素"""
        # 获取元素
        element = await self._get_element_by_id(element_id)
        if not element:
            return EquipElementResponse(
                success=False,
                message="Element not found",
                config=UserVisualConfigResponse(
                    equipped_background=None,
                    equipped_particle=None,
                    equipped_effect=None,
                ),
            )

        # 检查是否已解锁
        is_unlocked = await self._is_element_unlocked(user_id, element_id)
        if not is_unlocked:
            return EquipElementResponse(
                success=False,
                message="Element not unlocked",
                config=UserVisualConfigResponse(
                    equipped_background=None,
                    equipped_particle=None,
                    equipped_effect=None,
                ),
            )

        # 获取或创建用户配置
        config = await self._get_or_create_user_config(user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 处理套装
        if element.element_type == VisualElementType.BUNDLE:
            bundle_config = element.config
            if isinstance(bundle_config, dict):
                if bundle_config.get("background_id"):
                    config.equipped_background_id = bundle_config["background_id"]
                    config.background_equipped_at = now
                if bundle_config.get("particle_id"):
                    config.equipped_particle_id = bundle_config["particle_id"]
                    config.particle_equipped_at = now
                if bundle_config.get("effect_id"):
                    config.equipped_effect_id = bundle_config["effect_id"]
                    config.effect_equipped_at = now
        else:
            # 根据类型装备
            if element.element_type == VisualElementType.BACKGROUND:
                config.equipped_background_id = element_id
                config.background_equipped_at = now
            elif element.element_type == VisualElementType.PARTICLE:
                config.equipped_particle_id = element_id
                config.particle_equipped_at = now
            elif element.element_type == VisualElementType.EFFECT:
                config.equipped_effect_id = element_id
                config.effect_equipped_at = now

        await self.db.commit()

        # 返回更新后的配置
        updated_config = await self.get_user_config(user_id, locale)

        return EquipElementResponse(
            success=True,
            message=f"Successfully equipped {element.name}",
            config=updated_config,
        )

    async def unequip_element(
        self,
        user_id: uuid.UUID,
        element_type: VisualElementType,
        locale: str | None = None,
    ) -> EquipElementResponse:
        """卸下视觉元素"""
        config = await self._get_or_create_user_config(user_id)

        if element_type == VisualElementType.BACKGROUND:
            config.equipped_background_id = None
            config.background_equipped_at = None
        elif element_type == VisualElementType.PARTICLE:
            config.equipped_particle_id = None
            config.particle_equipped_at = None
        elif element_type == VisualElementType.EFFECT:
            config.equipped_effect_id = None
            config.effect_equipped_at = None

        await self.db.commit()

        updated_config = await self.get_user_config(user_id, locale)

        return EquipElementResponse(
            success=True,
            message=f"Successfully unequipped {element_type.value}",
            config=updated_config,
        )

    async def unlock_element(
        self,
        user_id: uuid.UUID | str,
        request: UnlockElementRequest,
        locale: str | None = None,
    ) -> UnlockElementResponse:
        """解锁视觉元素（内部使用，供成就系统等调用）"""
        normalized_user_id = self._normalize_user_id(user_id)

        # 获取元素
        element = await self._get_element_by_id(request.element_id)
        if not element:
            raise ValueError(f"Element not found: {request.element_id}")

        # 检查是否已解锁
        is_already_unlocked = await self._is_element_unlocked(normalized_user_id, request.element_id)
        if is_already_unlocked:
            # 返回已解锁的元素
            return UnlockElementResponse(
                success=True,
                element=self._build_element_response(element, locale, is_unlocked=True),
                message="Element already unlocked",
            )

        # 创建解锁记录
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user_element = UserVisualElement(
            user_id=normalized_user_id,
            element_id=request.element_id,
            unlocked_at=now,
            unlock_source=request.source,
            source_id=request.source_id,
        )

        self.db.add(user_element)
        await self.db.flush()
        if not self._is_transaction_managed_externally():
            await self.db.commit()

        return UnlockElementResponse(
            success=True,
            element=self._build_element_response(element, locale, is_unlocked=True),
            message=f"Successfully unlocked {element.name}",
        )

    async def unlock_element_for_user(
        self,
        user_id: uuid.UUID | str,
        element_id: str,
        unlock_source: str,
        source_id: str | None = None,
        locale: str | None = None,
    ) -> UnlockElementResponse:
        """Compatibility wrapper for internal callers."""
        return await self.unlock_element(
            user_id=user_id,
            request=UnlockElementRequest(
                element_id=element_id,
                source=unlock_source,
                source_id=source_id,
            ),
            locale=locale,
        )

    async def unlock_element_by_achievement(
        self,
        user_id: uuid.UUID,
        achievement_id: str,
        locale: str | None = None,
    ) -> list[UnlockElementResponse]:
        """根据成就解锁视觉元素"""
        # 查找与成就关联的元素
        query = select(VisualElement).where(
            VisualElement.unlock_source == VisualElementUnlockSource.ACHIEVEMENT,
            VisualElement.is_active == True,
        )

        result = await self.db.execute(query)
        elements = result.scalars().all()

        unlocked = []
        for element in elements:
            unlock_req = element.unlock_requirement
            if isinstance(unlock_req, dict) and unlock_req.get("achievement_id") == achievement_id:
                try:
                    response = await self.unlock_element(
                        user_id,
                        UnlockElementRequest(
                            element_id=element.id,
                            source="achievement",
                            source_id=achievement_id,
                        ),
                        locale,
                    )
                    if response.success:
                        unlocked.append(response)
                except Exception:
                    pass

        return unlocked

    async def get_default_elements(self, locale: str | None = None) -> list[VisualElementResponse]:
        """获取默认视觉元素"""
        query = select(VisualElement).where(
            VisualElement.is_default == True,
            VisualElement.is_active == True,
        )

        result = await self.db.execute(query)
        elements = result.scalars().all()

        return [self._build_element_response(el, locale) for el in elements]

    async def initialize_user_with_defaults(self, user_id: uuid.UUID) -> None:
        """为新用户初始化默认视觉元素"""
        # 获取默认元素
        defaults = await self.get_default_elements()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 解锁所有默认元素
        for element in defaults:
            user_element = UserVisualElement(
                user_id=user_id,
                element_id=element.id,
                unlocked_at=now,
                unlock_source="system",
                source_id=None,
            )
            self.db.add(user_element)

        # 创建用户配置，装备默认元素
        config = UserVisualConfig(user_id=user_id)

        for element in defaults:
            if element.element_type == VisualElementType.BACKGROUND:
                config.equipped_background_id = element.id
                config.background_equipped_at = now
            elif element.element_type == VisualElementType.PARTICLE:
                config.equipped_particle_id = element.id
                config.particle_equipped_at = now
            elif element.element_type == VisualElementType.EFFECT:
                config.equipped_effect_id = element.id
                config.effect_equipped_at = now

        self.db.add(config)
        await self.db.commit()

    # Private helper methods

    async def _get_element_by_id(self, element_id: str) -> VisualElement | None:
        """根据 ID 获取元素"""
        query = select(VisualElement).where(VisualElement.id == element_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _is_element_unlocked(self, user_id: uuid.UUID, element_id: str) -> bool:
        """检查元素是否已解锁"""
        element = await self._get_element_by_id(element_id)
        if element and element.is_default:
            return True

        query = select(UserVisualElement).where(
            UserVisualElement.user_id == user_id,
            UserVisualElement.element_id == element_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def _get_default_elements_by_type(self) -> dict[VisualElementType, VisualElement]:
        query = select(VisualElement).where(
            VisualElement.is_default == True,
            VisualElement.is_active == True,
        )
        result = await self.db.execute(query)
        defaults = result.scalars().all()
        grouped: dict[VisualElementType, VisualElement] = {}
        for element in defaults:
            grouped.setdefault(element.element_type, element)
        return grouped

    async def _get_or_create_user_config(self, user_id: uuid.UUID) -> UserVisualConfig:
        """获取或创建用户视觉配置"""
        query = select(UserVisualConfig).where(UserVisualConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            config = UserVisualConfig(user_id=user_id)
            self.db.add(config)
            await self.db.flush()

        return config

    def _build_element_response(
        self,
        element: VisualElement,
        locale: str | None = None,
        is_unlocked: bool = False,
        config: UserVisualConfig | None = None,
        is_equipped: bool = False,
    ) -> VisualElementResponse:
        """构建元素响应"""
        # 检查是否装备
        if config and not is_equipped:
            is_equipped = (
                (element.element_type == VisualElementType.BACKGROUND and config.equipped_background_id == element.id)
                or (element.element_type == VisualElementType.PARTICLE and config.equipped_particle_id == element.id)
                or (element.element_type == VisualElementType.EFFECT and config.equipped_effect_id == element.id)
            )

        return VisualElementResponse(
            id=element.id,
            name=element.get_localized_name(locale) or element.name,
            description=element.get_localized_description(locale) or element.description,
            element_type=element.element_type,
            rarity=element.rarity,
            unlock_source=element.unlock_source,
            is_default=element.is_default,
            preview_url=element.preview_url,
            icon_url=element.icon_url,
            category=element.category,
            sort_order=element.sort_order,
            config=element.config or {},
            is_unlocked=is_unlocked,
            is_equipped=is_equipped,
        )
