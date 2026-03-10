"""
Achievements API Endpoints
成就系统 API 端点
"""
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.achievement import AchievementRarity
from app.models.user import User
from app.schemas.achievement import (
    CloseToUnlockAchievementListResponse,
    ContractCreateRequest,
    ContractResponse,
)
from app.services.achievement_engine import AchievementEngine, ContractService
from app.services.equipment_service import EquipmentService, EquipmentSource

router = APIRouter()


@router.get("", response_model=dict[str, Any])
async def list_achievements(
    category: str | None = Query(None, description="Filter by category"),
    rarity: AchievementRarity | None = Query(None, description="Filter by rarity"),
    include_hidden: bool = Query(False, description="Include hidden achievements"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户成就列表

    Returns achievements with user progress and unlock status.
    """
    engine = AchievementEngine(db)
    result = await engine.get_user_achievements(
        current_user.id,
        category=category,
        rarity=rarity,
        include_hidden=include_hidden
    )
    return result


@router.get("/stats", response_model=dict[str, Any])
async def get_achievement_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户成就统计

    Returns total achievements, unlocked count, streak, etc.
    """
    engine = AchievementEngine(db)
    stats = await engine.get_achievement_stats(current_user.id)
    return stats


@router.get("/map", response_model=dict[str, Any])
async def get_achievement_map(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取成就地图（可视化展示）

    Returns nodes and connections for achievement map visualization.
    """
    engine = AchievementEngine(db)
    return await engine.get_achievement_map(current_user.id)


@router.get("/streak", response_model=dict[str, Any])
async def get_streak_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取连胜统计

    Returns current streak, max streak, freeze charges, etc.
    """
    engine = AchievementEngine(db)
    return await engine.get_streak_stats(current_user.id)


@router.get("/achievements/{achievement_id}", response_model=dict[str, Any])
async def get_achievement_detail(
    achievement_id: str = Path(..., description="Achievement ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个成就详情

    Returns achievement details with user progress.
    """
    engine = AchievementEngine(db)
    achievement = await engine._get_achievement(achievement_id)

    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    is_unlocked = await engine._is_unlocked(current_user.id, achievement_id)

    from app.schemas.achievement import AchievementDetail
    return {
        "data": AchievementDetail.model_validate(achievement).model_dump(),
        "is_unlocked": is_unlocked
    }


@router.post("/achievements/{achievement_id}/share", response_model=dict[str, Any])
async def share_achievement(
    achievement_id: str = Path(..., description="Achievement ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    生成成就分享卡片

    Returns a shareable image URL for the achievement.
    """
    engine = AchievementEngine(db)
    achievement = await engine._get_achievement(achievement_id)

    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    is_unlocked = await engine._is_unlocked(current_user.id, achievement_id)

    if not is_unlocked:
        raise HTTPException(status_code=400, detail="Achievement not unlocked yet")

    # TODO: Generate actual share card image
    card_url = f"/api/v1/achievements/{achievement_id}/card/{current_user.id}"

    return {
        "card_url": card_url,
        "achievement": achievement
    }


@router.post("/achievements/{achievement_id}/pin", response_model=dict[str, Any])
async def pin_achievement(
    achievement_id: str = Path(..., description="Achievement ID"),
    pinned: bool = Query(..., description="Pin state"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    置顶/取消置顶成就

    Updates the pinned state of an achievement.
    """
    from sqlalchemy import and_, select

    from app.models.achievement import UserAchievement

    query = select(UserAchievement).where(
        and_(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == achievement_id
        )
    )
    result = await db.execute(query)
    user_achievement = result.scalar_one_or_none()

    if not user_achievement:
        raise HTTPException(status_code=404, detail="Achievement progress not found")

    user_achievement.is_pinned = pinned
    await db.commit()

    return {
        "success": True,
        "pinned": pinned
    }


@router.get("/contracts", response_model=dict[str, Any])
async def get_contract_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前契约状态

    Returns active contract or null if no active contract.
    """
    service = ContractService(db)
    contract = await service._get_active_contract(current_user.id)

    if not contract:
        return {"has_active_contract": False, "contract": None}

    return {
        "has_active_contract": True,
        "contract": ContractResponse.model_validate(contract).model_dump()
    }


@router.post("/contracts", response_model=dict[str, Any])
async def create_contract(
    request: ContractCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建星火契约

    Creates a new study contract with photon stake.
    """
    service = ContractService(db)

    try:
        contract = await service.create_contract(
            current_user.id,
            request.target_study_minutes,
            request.target_days,
            request.photon_stake
        )
        return {
            "success": True,
            "data": ContractResponse.model_validate(contract).model_dump()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/contracts", response_model=dict[str, Any])
async def cancel_contract(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消当前契约

    Cancels active contract (forfeits staked photons).
    """
    from sqlalchemy import and_, select

    from app.models.achievement import ContractStatus, SparkContract

    query = select(SparkContract).where(
        and_(
            SparkContract.user_id == current_user.id,
            SparkContract.status == ContractStatus.ACTIVE
        )
    )
    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="No active contract found")

    contract.status = ContractStatus.FAILED
    contract.failed_at = datetime.now(UTC).replace(tzinfo=None)
    contract.failure_reason = "User cancelled"

    await db.commit()

    return {
        "success": True,
        "message": "Contract cancelled",
        "photons_lost": contract.photon_stake
    }


@router.get("/skins", response_model=dict[str, Any])
async def list_galaxy_skins(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    user_skin_query = select(UserGalaxySkin).where(
        UserGalaxySkin.user_id == current_user.id
    )
    user_skin_result = await db.execute(user_skin_query)
    user_skins = {us.skin_id: us for us in user_skin_result.scalars().all()}

    # 组装结果
    from app.schemas.achievement import GalaxySkinDetail
    skin_list = []
    equipped_skin_id = current_user.equipped_skin if current_user.equipped_skin_source == EquipmentSource.ACHIEVEMENT else None

    for skin in skins:
        user_skin = user_skins.get(skin.id)
        is_unlocked = user_skin is not None
        is_equipped = (
            current_user.equipped_skin_source == EquipmentSource.ACHIEVEMENT
            and current_user.equipped_skin == skin.id
        )

        skin_list.append(GalaxySkinDetail(
            **skin.__dict__,
            is_unlocked=is_unlocked,
            is_equipped=is_equipped
        ))

    return {
        "data": [s.model_dump() for s in skin_list],
        "equipped_skin_id": equipped_skin_id
    }


@router.post("/skins/{skin_id}/equip", response_model=dict[str, Any])
async def equip_galaxy_skin(
    skin_id: str = Path(..., description="Skin ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
async def list_user_titles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户称号列表

    Returns all user titles with equip status.
    """
    from sqlalchemy import select

    from app.models.achievement import UserTitle

    query = select(UserTitle).where(
        UserTitle.user_id == current_user.id
    ).order_by(UserTitle.unlocked_at.desc())
    result = await db.execute(query)
    titles = result.scalars().all()

    from app.schemas.achievement import UserTitleResponse
    equipped_title = current_user.equipped_title if current_user.equipped_title_source == EquipmentSource.ACHIEVEMENT else None
    title_list = [
        UserTitleResponse.model_validate(title).model_copy(
            update={
                "is_equipped": (
                    current_user.equipped_title_source == EquipmentSource.ACHIEVEMENT
                    and current_user.equipped_title == title.title_id
                )
            }
        )
        for title in titles
    ]

    return {
        "data": [t.model_dump() for t in title_list],
        "equipped_title": equipped_title
    }


@router.post("/titles/{title_id}/equip", response_model=dict[str, Any])
async def equip_title(
    title_id: str = Path(..., description="Title ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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

@router.post("/events/process", response_model=dict[str, Any])
async def process_achievement_event(
    event_type: str = Query(..., description="Event type"),
    event_data: dict[str, Any] | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    处理成就事件（内部API）

    Processes an achievement event and returns unlocked achievements.
    This endpoint is called by other services when user actions occur.
    """
    if event_data is None:
        event_data = {}

    engine = AchievementEngine(db)
    unlocked = await engine.process_event(
        current_user.id,
        event_type,
        **event_data
    )

    return {
        "success": True,
        "unlocked_count": len(unlocked),
        "unlocked": unlocked
    }


# ========== Enhancement Endpoints ==========

@router.get("/close-to-unlock", response_model=CloseToUnlockAchievementListResponse)
async def get_close_to_unlock_achievements(
    category: str | None = Query(None, description="Filter by category (e.g., 'sprint')"),
    threshold: float = Query(0.8, description="Progress threshold (0.0-1.0)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取接近解锁的成就（用于临界提示）

    Returns achievements that are close to being unlocked but not yet unlocked.
    Useful for showing "X more to unlock" prompts.
    """
    engine = AchievementEngine(db)
    close_achievements = await engine.get_close_to_unlock_achievements(
        current_user.id,
        threshold=threshold,
        category=category
    )

    return {
        "data": close_achievements,
        "count": len(close_achievements)
    }
