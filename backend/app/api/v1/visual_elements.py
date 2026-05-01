"""
Visual Elements API Endpoints
视觉元素系统 API 端点
"""
from __future__ import annotations
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.achievement import UserAchievement
from app.models.user import User
from app.models.visual_element import VisualElementRarity, VisualElementType
from app.schemas.visual_element import (
    EquipElementResponse,
    UnlockElementRequest,
    UnlockElementResponse,
    UserVisualConfigResponse,
    VisualElementListResponse,
)
from app.services.visual_element_service import VisualElementService

router = APIRouter()

SUPPORTED_LOCALES = {"zh", "en"}


def _normalize_locale(value: str | None) -> str | None:
    if not value:
        return None
    primary = value.split(",")[0].strip()
    if not primary:
        return None
    primary = primary.split(";")[0].strip()
    if not primary:
        return None
    return primary.split("-")[0].lower()


def _resolve_locale(locale: str | None, accept_language: str | None) -> str | None:
    candidate = _normalize_locale(locale) or _normalize_locale(accept_language)
    if candidate in SUPPORTED_LOCALES:
        return candidate
    return None


async def verify_internal_token(x_internal_token: str | None = Header(None)) -> None:
    """保护内部 API 端点"""
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=503, detail="Internal API key not configured")
    if not x_internal_token or not secrets.compare_digest(x_internal_token, settings.INTERNAL_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid internal token")


@router.get("", response_model=VisualElementListResponse)
async def list_visual_elements(
    element_type: VisualElementType | None = Query(None, description="按类型过滤"),
    rarity: VisualElementRarity | None = Query(None, description="按稀有度过滤"),
    category: str | None = Query(None, description="按分类过滤"),
    unlocked_only: bool = Query(False, description="只返回已解锁的"),
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisualElementListResponse:
    """
    获取视觉元素列表

    - 支持按类型、稀有度、分类过滤
    - 返回元素的解锁和装备状态
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    if unlocked_only:
        items = await service.get_user_elements(
            current_user.id,
            element_type=element_type,
            locale=resolved_locale,
        )
    else:
        items = await service.get_all_elements(
            element_type=element_type,
            rarity=rarity,
            category=category,
            locale=resolved_locale,
        )

        # 获取用户解锁状态
        user_elements = await service.get_user_elements(current_user.id, locale=resolved_locale)
        unlocked_ids = {el.id for el in user_elements}

        # 获取用户装备状态
        config = await service.get_user_config(current_user.id, locale=resolved_locale)
        equipped_ids = set()
        if config.equipped_background:
            equipped_ids.add(config.equipped_background.id)
        if config.equipped_particle:
            equipped_ids.add(config.equipped_particle.id)
        if config.equipped_effect:
            equipped_ids.add(config.equipped_effect.id)

        # 更新解锁和装备状态
        for item in items:
            item.is_unlocked = item.id in unlocked_ids
            item.is_equipped = item.id in equipped_ids

    return VisualElementListResponse(items=items, total=len(items))


@router.get("/unlocked", response_model=VisualElementListResponse)
async def list_unlocked_elements(
    element_type: VisualElementType | None = Query(None, description="按类型过滤"),
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisualElementListResponse:
    """
    获取用户已解锁的视觉元素
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    items = await service.get_user_elements(
        current_user.id,
        element_type=element_type,
        locale=resolved_locale,
    )

    return VisualElementListResponse(items=items, total=len(items))


@router.get("/config", response_model=UserVisualConfigResponse)
async def get_visual_config(
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserVisualConfigResponse:
    """
    获取用户当前视觉配置
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    return await service.get_user_config(current_user.id, resolved_locale)


@router.post("/{element_id}/equip", response_model=EquipElementResponse)
async def equip_element(
    element_id: str,
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquipElementResponse:
    """
    装备视觉元素

    - 用户必须先解锁元素才能装备
    - 套装类型会同时装备多个元素
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    return await service.equip_element(current_user.id, element_id, resolved_locale)


@router.post("/{element_type}/unequip", response_model=EquipElementResponse)
async def unequip_element(
    element_type: VisualElementType,
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquipElementResponse:
    """
    卸下视觉元素

    - 卸下后该层将显示默认效果
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    return await service.unequip_element(current_user.id, element_type, resolved_locale)


# route-tier: internal
@router.post("/unlock", response_model=UnlockElementResponse)
async def unlock_element_internal(
    request: UnlockElementRequest,
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    _: None = Depends(verify_internal_token),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnlockElementResponse:
    """
    解锁视觉元素（内部 API）

    - 供成就系统等内部服务调用
    - 需要 internal token 验证
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    try:
        return await service.unlock_element(current_user.id, request, resolved_locale)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Element not found or cannot be unlocked") from e


@router.post("/unlock-by-achievement", response_model=list[UnlockElementResponse])
async def unlock_by_achievement(
    achievement_id: str,
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UnlockElementResponse]:
    """
    根据成就解锁视觉元素

    - 当用户解锁成就时，自动解锁关联的视觉元素
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    achievement_result = await db.execute(
        select(UserAchievement).where(
            and_(
                UserAchievement.user_id == current_user.id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
    )
    achievement = achievement_result.scalar_one_or_none()
    if achievement is None or achievement.unlocked_at is None:
        raise HTTPException(status_code=403, detail="Achievement not unlocked")

    return await service.unlock_element_by_achievement(
        current_user.id, achievement_id, resolved_locale
    )


@router.get("/defaults", response_model=VisualElementListResponse)
async def get_default_elements(
    locale: str | None = Query(None, description="语言偏好"),
    accept_language: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> VisualElementListResponse:
    """
    获取默认视觉元素

    - 无需认证
    - 返回所有默认元素
    """
    service = VisualElementService(db)
    resolved_locale = _resolve_locale(locale, accept_language)

    items = await service.get_default_elements(resolved_locale)
    return VisualElementListResponse(items=items, total=len(items))
