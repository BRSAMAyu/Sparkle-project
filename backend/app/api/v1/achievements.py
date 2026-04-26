"""
Achievements API Endpoints
成就系统 API 端点
"""

from __future__ import annotations
import secrets
from datetime import timezone, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.achievement import AchievementRarity
from app.models.user import User
from app.schemas.achievement import (
    AchievementDetail,
    AchievementDetailResponse,
    AchievementEventProcessResponse,
    AchievementPinResponse,
    AchievementShareRequest,
    AchievementShareResponse,
    CloseToUnlockAchievementListResponse,
    ContractCreateRequest,
    ContractResponse,
    ShareCardPrivacySettings,
    ShareTemplateInfo,
    ShareTemplateListResponse,
    StreakHistoryResponse,
)
from app.services.achievement_engine import AchievementEngine, ContractService
from app.services.equipment_service import EquipmentService, EquipmentSource
from app.services.share_card_service import ShareCardService
from app.services.share_card_templates import get_all_templates

router = APIRouter()

SUPPORTED_ACHIEVEMENT_LOCALES = {"zh", "en"}


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
    if candidate in SUPPORTED_ACHIEVEMENT_LOCALES:
        return candidate
    return None


async def verify_internal_token(x_internal_token: str | None = Header(None)) -> None:
    """Protect internal-only achievement endpoints with a shared key."""
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=503, detail="Internal API key not configured")
    if not x_internal_token or not secrets.compare_digest(x_internal_token, settings.INTERNAL_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid internal token")


async def _build_achievement_detail_response(
    achievement_id: str,
    current_user: User,
    db: AsyncSession,
    locale: str | None = None,
) -> AchievementDetailResponse:
    engine = AchievementEngine(db)
    achievement = await engine.get_achievement(achievement_id)

    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    user_progress = await engine._get_user_achievement_progress(current_user.id, achievement_id)
    user_progress_payload = engine._build_user_progress_payload(user_progress, achievement)
    is_unlocked = bool(user_progress and user_progress.unlocked_at is not None)
    return AchievementDetailResponse(
        data=engine.build_achievement_detail(achievement, locale),
        is_unlocked=is_unlocked,
        user_progress=user_progress_payload,
        context_snapshot=user_progress_payload.context_snapshot if user_progress_payload else None,
        context_story=user_progress_payload.context_story if user_progress_payload else None,
    )


async def _share_achievement_card(
    achievement_id: str,
    current_user: User,
    db: AsyncSession,
    locale: str | None = None,
    template_id: str = "cosmic",
    privacy: ShareCardPrivacySettings | None = None,
) -> AchievementShareResponse:
    if privacy is None:
        privacy = ShareCardPrivacySettings()

    service = ShareCardService(db)

    try:
        result, achievement, _ = await service.generate_achievement_share_card(
            current_user.id,
            achievement_id,
            template_id=template_id,
            privacy=privacy,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Achievement not found":
            raise HTTPException(status_code=404, detail=message) from exc
        if message == "Achievement not unlocked yet":
            raise HTTPException(status_code=400, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    engine = AchievementEngine(db)
    return AchievementShareResponse(
        card_url=result.card_url,
        mime_type=result.mime_type,
        width=result.width,
        height=result.height,
        generated_at=result.generated_at,
        template_id=result.template_id,
        privacy_settings=result.privacy_settings,
        achievement=engine._build_achievement_detail(achievement, locale),
    )


async def _pin_achievement_state(
    achievement_id: str,
    pinned: bool,
    current_user: User,
    db: AsyncSession,
) -> AchievementPinResponse:
    from sqlalchemy import and_, select

    from app.models.achievement import UserAchievement

    query = select(UserAchievement).where(
        and_(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == achievement_id,
        )
    )
    result = await db.execute(query)
    user_achievement = result.scalar_one_or_none()

    if not user_achievement:
        raise HTTPException(status_code=404, detail="Achievement progress not found")

    user_achievement.is_pinned = pinned
    await db.commit()
    return AchievementPinResponse(success=True, pinned=pinned)


@router.get("", response_model=dict[str, Any])
async def list_achievements(
    category: str | None = Query(None, description="Filter by category"),
    rarity: AchievementRarity | None = Query(None, description="Filter by rarity"),
    include_hidden: bool = Query(False, description="Include hidden achievements"),
    include_inactive: bool = Query(False, description="Include inactive achievements"),
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户成就列表

    Returns achievements with user progress and unlock status.
    """
    engine = AchievementEngine(db)
    resolved_locale = _resolve_locale(locale, accept_language)
    result = await engine.get_user_achievements(
        current_user.id,
        category=category,
        rarity=rarity,
        include_hidden=include_hidden,
        include_inactive=include_inactive,
        locale=resolved_locale,
    )
    return result


@router.get("/stats", response_model=dict[str, Any])
async def get_achievement_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取用户成就统计

    Returns total achievements, unlocked count, streak, etc.
    """
    engine = AchievementEngine(db)
    stats = await engine.get_achievement_stats(current_user.id)
    return stats


@router.get("/map", response_model=dict[str, Any])
async def get_achievement_map(
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取成就地图（可视化展示）

    Returns nodes and connections for achievement map visualization.
    """
    engine = AchievementEngine(db)
    resolved_locale = _resolve_locale(locale, accept_language)
    return await engine.get_achievement_map(current_user.id, locale=resolved_locale)


@router.get("/streak", response_model=dict[str, Any])
async def get_streak_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取连胜统计

    Returns current streak, max streak, freeze charges, etc.
    """
    engine = AchievementEngine(db)
    return await engine.get_streak_stats(current_user.id)


@router.get("/streak/history", response_model=StreakHistoryResponse)
async def get_streak_history(
    days: int = Query(90, ge=1, le=365, description="Number of days to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取连胜日历历史

    Returns daily streak status for calendar rendering.
    """
    engine = AchievementEngine(db)
    return await engine.get_streak_history(current_user.id, days=days)


@router.get(
    "/achievements/{achievement_id}",
    response_model=AchievementDetailResponse,
    deprecated=True,
)
async def get_achievement_detail(
    achievement_id: str = Path(..., description="Achievement ID"),
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个成就详情

    Returns achievement details with user progress.
    """
    resolved_locale = _resolve_locale(locale, accept_language)
    return await _build_achievement_detail_response(
        achievement_id,
        current_user,
        db,
        locale=resolved_locale,
    )


@router.post(
    "/achievements/{achievement_id}/share",
    response_model=AchievementShareResponse,
    deprecated=True,
)
async def share_achievement(
    achievement_id: str = Path(..., description="Achievement ID"),
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成成就分享卡片

    Returns a shareable image URL for the achievement.
    """
    resolved_locale = _resolve_locale(locale, accept_language)
    return await _share_achievement_card(
        achievement_id,
        current_user,
        db,
        locale=resolved_locale,
    )


@router.post(
    "/achievements/{achievement_id}/pin",
    response_model=AchievementPinResponse,
    deprecated=True,
)
async def pin_achievement(
    achievement_id: str = Path(..., description="Achievement ID"),
    pinned: bool = Query(..., description="Pin state"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    置顶/取消置顶成就

    Updates the pinned state of an achievement.
    """
    return await _pin_achievement_state(achievement_id, pinned, current_user, db)


@router.get("/contracts", response_model=dict[str, Any])
async def get_contract_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取当前契约状态

    Returns active contract or null if no active contract.
    """
    service = ContractService(db)
    status_result = await service.check_contract_status(current_user.id)
    contract = await service._get_active_contract(current_user.id)

    if not contract:
        return {"has_active_contract": False, "contract": None}

    return {
        "has_active_contract": True,
        "contract": ContractResponse.model_validate(
            contract,
            from_attributes=True,
        ).model_dump(),
        "status": status_result,
    }


@router.post("/contracts", response_model=dict[str, Any])
async def create_contract(
    request: ContractCreateRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建星火契约

    Creates a new study contract with photon stake.
    """
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    service = ContractService(db)

    try:
        contract = await service.create_contract(
            current_user.id, request.target_study_minutes, request.target_days, request.photon_stake
        )
        return {
            "success": True,
            "data": ContractResponse.model_validate(
                contract,
                from_attributes=True,
            ).model_dump(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/contracts", response_model=dict[str, Any])
async def cancel_contract(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    取消当前契约

    Cancels active contract (forfeits staked photons).
    """
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    from sqlalchemy import and_, select

    from app.models.achievement import ContractStatus, SparkContract

    query = select(SparkContract).where(
        and_(SparkContract.user_id == current_user.id, SparkContract.status == ContractStatus.ACTIVE)
    )
    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="No active contract found")

    contract.status = ContractStatus.FAILED
    contract.failed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    contract.failure_reason = "User cancelled"

    try:
        from app.services.achievement_engine import AchievementEngine, AchievementEvent

        await AchievementEngine(db).process_event(
            user_id=str(current_user.id),
            event_type=AchievementEvent.CONTRACT_FAILED,
            contract_id=str(contract.id),
            target_days=int(contract.target_days or 0),
            current_days=int(contract.current_days or 0),
            target_study_minutes=int(contract.target_study_minutes or 0),
            photon_stake=int(contract.photon_stake or 0),
            source="contract_cancelled",
        )
    except Exception as exc:
        logger.warning(f"Failed to publish contract failed achievement event for contract {contract.id}: {exc}")

    await db.commit()

    return {"success": True, "message": "Contract cancelled", "photons_lost": contract.photon_stake}


@router.get("/skins", response_model=dict[str, Any])
async def list_galaxy_skins(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取星系皮肤列表

    Returns all galaxy skins with unlock status.
    """
    from sqlalchemy import select

    from app.models.achievement import GalaxySkin, UserGalaxySkin

    # 获取所有皮肤
    query = select(GalaxySkin).order_by(GalaxySkin.sort_order)
    result = await db.execute(query)
    skins = result.scalars().all()

    # 获取用户已解锁的皮肤
    user_skin_query = select(UserGalaxySkin).where(UserGalaxySkin.user_id == current_user.id)
    user_skin_result = await db.execute(user_skin_query)
    user_skins = {us.skin_id: us for us in user_skin_result.scalars().all()}

    # 组装结果
    from app.schemas.achievement import GalaxySkinDetail

    skin_list = []
    equipped_skin_id = (
        current_user.equipped_skin if current_user.equipped_skin_source == EquipmentSource.ACHIEVEMENT else None
    )

    for skin in skins:
        user_skin = user_skins.get(skin.id)
        is_unlocked = user_skin is not None
        is_equipped = (
            current_user.equipped_skin_source == EquipmentSource.ACHIEVEMENT and current_user.equipped_skin == skin.id
        )
        skin_list.append(
            GalaxySkinDetail(
                id=skin.id,
                name=skin.name,
                description=skin.description,
                preview_url=skin.preview_url,
                rarity=skin.rarity,
                sort_order=skin.sort_order,
                unlock_type=skin.unlock_type,
                unlock_requirement=skin.unlock_requirement or {},
                skin_config=skin.skin_config or {},
                is_unlocked=is_unlocked,
                is_equipped=is_equipped,
            )
        )

    return {"data": [s.model_dump() for s in skin_list], "equipped_skin_id": equipped_skin_id}


@router.post("/skins/{skin_id}/equip", response_model=dict[str, Any])
async def equip_galaxy_skin(
    skin_id: str = Path(..., description="Skin ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    装备星系皮肤

    Equips a galaxy skin.
    """
    service = EquipmentService(db)
    try:
        result = await service.equip_achievement_skin(str(current_user.id), skin_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/titles", response_model=dict[str, Any])
async def list_user_titles(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取用户称号列表

    Returns all user titles with equip status.
    """
    from sqlalchemy import select

    from app.models.achievement import UserTitle

    query = select(UserTitle).where(UserTitle.user_id == current_user.id).order_by(UserTitle.unlocked_at.desc())
    result = await db.execute(query)
    titles = result.scalars().all()

    from app.schemas.achievement import UserTitleResponse

    equipped_title = (
        current_user.equipped_title if current_user.equipped_title_source == EquipmentSource.ACHIEVEMENT else None
    )
    title_list = [
        UserTitleResponse.model_validate(title, from_attributes=True).model_copy(
            update={
                "is_equipped": (
                    current_user.equipped_title_source == EquipmentSource.ACHIEVEMENT
                    and current_user.equipped_title == title.title_id
                )
            }
        )
        for title in titles
    ]

    return {"data": [t.model_dump() for t in title_list], "equipped_title": equipped_title}


@router.post("/titles/{title_id}/equip", response_model=dict[str, Any])
async def equip_title(
    title_id: str = Path(..., description="Title ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    装备称号

    Equips a user title.
    """
    service = EquipmentService(db)
    try:
        result = await service.equip_achievement_title(str(current_user.id), title_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ========== Internal Event Endpoint ==========


# route-tier: internal
@router.post("/events/process", response_model=AchievementEventProcessResponse)
async def process_achievement_event(
    user_id: str = Query(..., description="Target user ID"),
    event_type: str = Query(..., description="Event type"),
    event_data: dict[str, Any] | None = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    _: None = Depends(verify_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """
    处理成就事件（内部API）

    Processes an achievement event and returns unlocked achievements.
    This endpoint is called by other services when user actions occur.
    """
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    if event_data is None:
        event_data = {}

    engine = AchievementEngine(db)
    unlocked = await engine.process_event(user_id, event_type, **event_data)

    return AchievementEventProcessResponse(
        success=True,
        unlocked_count=len(unlocked),
        unlocked=unlocked,
    )


# ========== Enhancement Endpoints ==========


@router.get("/close-to-unlock", response_model=CloseToUnlockAchievementListResponse)
async def get_close_to_unlock_achievements(
    category: str | None = Query(None, description="Filter by category (e.g., 'sprint')"),
    threshold: float = Query(0.8, description="Progress threshold (0.0-1.0)"),
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取接近解锁的成就（用于临界提示）

    Returns achievements that are close to being unlocked but not yet unlocked.
    Useful for showing "X more to unlock" prompts.
    """
    engine = AchievementEngine(db)
    resolved_locale = _resolve_locale(locale, accept_language)
    close_achievements = await engine.get_close_to_unlock_achievements(
        current_user.id,
        threshold=threshold,
        category=category,
        locale=resolved_locale,
    )

    return {"data": close_achievements, "count": len(close_achievements)}


@router.get("/share-templates", response_model=ShareTemplateListResponse)
async def get_share_templates(
    locale: str | None = Query(None, description="Locale for template names"),
    accept_language: str | None = Header(None),
):
    """
    获取分享卡片模板列表

    Returns available share card templates.
    """
    from app.services.share_card_templates import get_all_templates

    resolved_locale = _resolve_locale(locale, accept_language)
    templates = get_all_templates()

    template_infos = []
    for template in templates:
        # Localize template name
        name = template.name
        if resolved_locale == "zh":
            name_map = {
                "cosmic": "星空",
                "minimal": "简约",
                "neon": "霓虹",
                "elegant": "典雅",
            }
            name = name_map.get(template.id, template.name)

            description_map = {
                "cosmic": "渐变背景 + 粒子 + 光晕效果",
                "minimal": "纯色背景 + 极简装饰",
                "neon": "深色背景 + 霓虹发光效果",
                "elegant": "金色边框 + 优雅字体",
            }
            description = description_map.get(template.id, template.description or "")
        else:
            description = template.description or ""

        template_infos.append(
            ShareTemplateInfo(
                id=template.id,
                name=name,
                description=description,
                preview_url=template.preview_url,
            )
        )

    return ShareTemplateListResponse(templates=template_infos)


@router.get("/{achievement_id}", response_model=AchievementDetailResponse)
async def get_achievement_detail_canonical(
    achievement_id: str = Path(..., description="Achievement ID"),
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Canonical achievement detail endpoint."""
    resolved_locale = _resolve_locale(locale, accept_language)
    return await _build_achievement_detail_response(
        achievement_id,
        current_user,
        db,
        locale=resolved_locale,
    )


@router.post("/{achievement_id}/share", response_model=AchievementShareResponse)
async def share_achievement_canonical(
    achievement_id: str = Path(..., description="Achievement ID"),
    request: AchievementShareRequest | None = None,
    locale: str | None = Query(None, description="Locale for localized fields"),
    accept_language: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成成就分享卡片

    Returns a shareable image URL for the achievement.
    Supports template selection and privacy settings.
    """
    resolved_locale = _resolve_locale(locale, accept_language)

    if request is None:
        request = AchievementShareRequest()

    return await _share_achievement_card(
        achievement_id,
        current_user,
        db,
        locale=resolved_locale,
        template_id=request.template_id,
        privacy=request.privacy,
    )


@router.post("/{achievement_id}/pin", response_model=AchievementPinResponse)
async def pin_achievement_canonical(
    achievement_id: str = Path(..., description="Achievement ID"),
    pinned: bool = Query(..., description="Pin state"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Canonical achievement pin endpoint."""
    return await _pin_achievement_state(achievement_id, pinned, current_user, db)
