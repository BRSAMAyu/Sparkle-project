"""
责任伙伴系统 API
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.achievement import UserAchievement
from app.models.community import Friendship, FriendshipStatus
from app.models.user import User
from app.schemas.community import UserBrief as CommunityUserBrief

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─── Schemas ─────────────────────────────────────────────────────────────────


class PartnershipRequestSchema(BaseModel):
    partner_id: UUID
    initiator_goal: str
    check_in_days: int = Field(default=1, ge=1, le=7)


class PartnershipRespondSchema(BaseModel):
    accept: bool
    partner_goal: Optional[str] = None


class CheckinCreateSchema(BaseModel):
    content: str
    mood: int = Field(default=3, ge=1, le=5)  # 1-5
    minutes: int = Field(default=0, ge=0)


class EncourageSchema(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class PartnershipOut(BaseModel):
    id: UUID
    initiator_id: UUID
    partner_id: UUID
    initiator_goal: str
    partner_goal: Optional[str]
    check_in_days: int
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    initiator: CommunityUserBrief | None = None
    partner: CommunityUserBrief | None = None
    my_role: str | None = None
    my_checked_in_today: bool | None = None
    partner_checked_in_today: bool | None = None
    last_checkin_at: datetime | None = None

    class Config:
        from_attributes = True


class CheckinOut(BaseModel):
    id: UUID
    partnership_id: UUID
    user_id: UUID
    content: str
    mood: int
    minutes: int
    created_at: datetime
    likes: int = 0
    encouragements: list = []
    author: CommunityUserBrief | None = None

    class Config:
        from_attributes = True


class PartnershipStatsOut(BaseModel):
    my_streak_days: int
    partner_streak_days: int
    my_checked_in_today: bool = False
    partner_checked_in_today: bool
    total_checkins: int


def _user_timezone(user: User) -> str:
    timezone_name = getattr(getattr(user, "push_preference", None), "timezone", None) or "Asia/Shanghai"
    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "Asia/Shanghai"
    return timezone_name


def _day_range_for_timezone(timezone_name: str, *, reference: datetime | None = None) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    now_local = (reference or datetime.now(zone)).astimezone(zone)
    local_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _to_local_date(timestamp: datetime, timezone_name: str):
    zone = ZoneInfo(timezone_name)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(zone).date()


def _build_user_brief(user: User | None) -> CommunityUserBrief | None:
    if user is None:
        return None
    return CommunityUserBrief.model_validate(user)


async def _has_checkin_today(
    db: AsyncSession,
    *,
    partnership_id: UUID,
    user_id: UUID,
    timezone_name: str,
) -> bool:
    start_at, end_at = _day_range_for_timezone(timezone_name)
    result = await db.execute(
        select(AccountabilityCheckin.id).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == user_id,
                AccountabilityCheckin.created_at >= start_at,
                AccountabilityCheckin.created_at <= end_at,
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def _get_last_checkin_at(db: AsyncSession, partnership_id: UUID) -> datetime | None:
    result = await db.execute(
        select(AccountabilityCheckin.created_at)
        .where(AccountabilityCheckin.partnership_id == partnership_id)
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _build_partnership_out(
    db: AsyncSession,
    partnership: AccountabilityPartnership,
    current_user: User,
) -> PartnershipOut:
    initiator = partnership.initiator
    partner = partnership.partner
    if initiator is None:
        initiator = await db.get(User, partnership.initiator_id)
    if partner is None:
        partner = await db.get(User, partnership.partner_id)
    timezone_name = _user_timezone(current_user)
    partner_user_id = (
        partnership.partner_id if str(partnership.initiator_id) == str(current_user.id) else partnership.initiator_id
    )
    my_checked_in_today = False
    partner_checked_in_today = False
    if partnership.status == AccountabilityStatus.ACTIVE:
        my_checked_in_today = await _has_checkin_today(
            db,
            partnership_id=partnership.id,
            user_id=current_user.id,
            timezone_name=timezone_name,
        )
        partner_checked_in_today = await _has_checkin_today(
            db,
            partnership_id=partnership.id,
            user_id=partner_user_id,
            timezone_name=timezone_name,
        )
    last_checkin_at = await _get_last_checkin_at(db, partnership.id)
    return PartnershipOut(
        id=partnership.id,
        initiator_id=partnership.initiator_id,
        partner_id=partnership.partner_id,
        initiator_goal=partnership.initiator_goal,
        partner_goal=partnership.partner_goal,
        check_in_days=partnership.check_in_days,
        status=partnership.status.value if hasattr(partnership.status, "value") else str(partnership.status),
        started_at=partnership.started_at,
        ended_at=partnership.ended_at,
        created_at=partnership.created_at,
        initiator=_build_user_brief(initiator),
        partner=_build_user_brief(partner),
        my_role="initiator" if str(partnership.initiator_id) == str(current_user.id) else "partner",
        my_checked_in_today=my_checked_in_today,
        partner_checked_in_today=partner_checked_in_today,
        last_checkin_at=last_checkin_at,
    )


async def _build_checkin_out(db: AsyncSession, checkin: AccountabilityCheckin) -> CheckinOut:
    author = checkin.user
    if author is None:
        author = await db.get(User, checkin.user_id)
    return CheckinOut(
        id=checkin.id,
        partnership_id=checkin.partnership_id,
        user_id=checkin.user_id,
        content=checkin.content,
        mood=checkin.mood,
        minutes=checkin.minutes,
        created_at=checkin.created_at,
        likes=checkin.likes or 0,
        encouragements=checkin.encouragements or [],
        author=_build_user_brief(author),
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/request", response_model=PartnershipOut, status_code=201)
async def request_partnership(
    body: PartnershipRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """发起责任伙伴邀请"""
    if str(body.partner_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot invite yourself as an accountability partner",
        )

    # Check friendship exists
    result = await db.execute(
        select(Friendship).where(
            and_(
                Friendship.status == FriendshipStatus.ACCEPTED,
                or_(
                    and_(
                        Friendship.user_id == current_user.id,
                        Friendship.friend_id == body.partner_id,
                    ),
                    and_(
                        Friendship.user_id == body.partner_id,
                        Friendship.friend_id == current_user.id,
                    ),
                ),
            )
        )
    )
    friendship = result.scalar_one_or_none()
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be friends before becoming accountability partners",
        )

    # Check existing partnership
    existing = await db.execute(
        select(AccountabilityPartnership).where(
            or_(
                and_(
                    AccountabilityPartnership.initiator_id == current_user.id,
                    AccountabilityPartnership.partner_id == body.partner_id,
                ),
                and_(
                    AccountabilityPartnership.initiator_id == body.partner_id,
                    AccountabilityPartnership.partner_id == current_user.id,
                ),
            )
        )
    )
    partnership = existing.scalar_one_or_none()
    if partnership and partnership.status in {AccountabilityStatus.PENDING, AccountabilityStatus.ACTIVE}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active or pending partnership already exists",
        )

    if partnership:
        partnership.initiator_id = current_user.id
        partnership.partner_id = body.partner_id
        partnership.friendship_id = friendship.id
        partnership.initiator_goal = body.initiator_goal
        partnership.partner_goal = None
        partnership.check_in_days = body.check_in_days
        partnership.status = AccountabilityStatus.PENDING
        partnership.started_at = None
        partnership.ended_at = None
    else:
        partnership = AccountabilityPartnership(
            initiator_id=current_user.id,
            partner_id=body.partner_id,
            friendship_id=friendship.id,
            initiator_goal=body.initiator_goal,
            check_in_days=body.check_in_days,
            status=AccountabilityStatus.PENDING,
        )
    await partnership.save(db)
    await db.refresh(partnership)

    # Send notification to partner
    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    await accountability_notification_service.send_partner_request(
        db, partnership.id, current_user.id, body.partner_id, body.initiator_goal
    )

    return await _build_partnership_out(db, partnership, current_user)


@router.post("/{partnership_id}/respond", response_model=PartnershipOut)
async def respond_to_partnership(
    partnership_id: UUID,
    body: PartnershipRespondSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """接受或拒绝责任伙伴邀请"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only the invited partner can respond")

    if partnership.status != AccountabilityStatus.PENDING:
        raise HTTPException(status_code=400, detail="Partnership is not in pending state")

    if body.accept:
        partnership.status = AccountabilityStatus.ACTIVE
        partnership.started_at = _utcnow()
        if body.partner_goal:
            partnership.partner_goal = body.partner_goal
    else:
        partnership.status = AccountabilityStatus.ENDED
        partnership.ended_at = _utcnow()

    await partnership.save(db)
    await db.refresh(partnership)

    # Send notification
    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    if body.accept:
        await accountability_notification_service.send_partner_accepted(
            db, partnership.id, current_user.id, partnership.initiator_id
        )
    else:
        await accountability_notification_service.send_partner_declined(db, partnership.initiator_id, current_user.id)

    return await _build_partnership_out(db, partnership, current_user)


@router.get("/mine", response_model=list[PartnershipOut])
async def get_my_partnerships(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取我的责任伙伴列表"""
    result = await db.execute(
        select(AccountabilityPartnership).where(
            and_(
                AccountabilityPartnership.status.in_([AccountabilityStatus.PENDING, AccountabilityStatus.ACTIVE]),
                or_(
                    AccountabilityPartnership.initiator_id == current_user.id,
                    AccountabilityPartnership.partner_id == current_user.id,
                ),
            )
        ).order_by(
            case(
                (AccountabilityPartnership.status == AccountabilityStatus.ACTIVE, 0),
                (AccountabilityPartnership.status == AccountabilityStatus.PENDING, 1),
                else_=2,
            ),
            AccountabilityPartnership.updated_at.desc(),
            AccountabilityPartnership.created_at.desc(),
        )
    )
    partnerships = result.scalars().all()
    return [await _build_partnership_out(db, p, current_user) for p in partnerships]


@router.delete("/{partnership_id}", status_code=204)
async def end_partnership(
    partnership_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """结束伙伴关系"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    partner_id = (
        partnership.partner_id if str(partnership.initiator_id) == str(current_user.id) else partnership.initiator_id
    )

    partnership.status = AccountabilityStatus.ENDED
    partnership.ended_at = _utcnow()
    await partnership.save(db)

    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    await accountability_notification_service.send_partnership_ended(
        db, partner_id, partnership_id, current_user.id, current_user.id
    )
    await accountability_notification_service.send_partnership_ended(
        db, current_user.id, partnership_id, partner_id, current_user.id
    )


@router.post("/{partnership_id}/checkin", response_model=CheckinOut, status_code=201)
async def daily_checkin(
    partnership_id: UUID,
    body: CheckinCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """今日打卡"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    if partnership.status != AccountabilityStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Partnership is not active")

    timezone_name = _user_timezone(current_user)
    today_start, today_end = _day_range_for_timezone(timezone_name)

    existing_checkin = await db.execute(
        select(AccountabilityCheckin).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == current_user.id,
                AccountabilityCheckin.created_at >= today_start,
                AccountabilityCheckin.created_at <= today_end,
            )
        )
    )
    if existing_checkin.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You have already checked in today",
        )

    checkin = AccountabilityCheckin(
        partnership_id=partnership_id,
        user_id=current_user.id,
        content=body.content,
        mood=body.mood,
        minutes=body.minutes,
        liked_by=[],
        encouragements=[],
    )
    await checkin.save(db)
    await db.refresh(checkin)

    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    partner_id = (
        partnership.partner_id if str(partnership.initiator_id) == str(current_user.id) else partnership.initiator_id
    )
    await accountability_notification_service.send_partner_checked_in(
        db, partner_id, partnership_id, current_user.full_name or current_user.username
    )

    from app.services.accountability_achievement_service import (
        accountability_achievement_service,
    )

    try:
        await accountability_achievement_service.check_streak_achievements(db, current_user.id, partnership_id)
        await accountability_achievement_service.check_partnership_achievements(db, current_user.id, partnership_id)
    except Exception as e:
        logger.error(
            f"Failed to check achievements for user {current_user.id}, partnership {partnership_id}: {e}", exc_info=True
        )

    return await _build_checkin_out(db, checkin)


@router.get("/{partnership_id}/stats", response_model=PartnershipStatsOut)
async def get_partnership_stats(
    partnership_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取伙伴关系统计"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    partner_id = (
        partnership.partner_id if str(partnership.initiator_id) == str(current_user.id) else partnership.initiator_id
    )

    from datetime import date, timedelta
    from sqlalchemy import func as sql_func

    timezone_name = _user_timezone(current_user)
    today_local = datetime.now(ZoneInfo(timezone_name)).date()
    today_start, today_end = _day_range_for_timezone(timezone_name)

    async def _streak(user_id) -> int:
        """Calculate consecutive check-in days ending today or yesterday."""
        result = await db.execute(
            select(AccountabilityCheckin.created_at)
            .where(
                and_(
                    AccountabilityCheckin.partnership_id == partnership_id,
                    AccountabilityCheckin.user_id == user_id,
                )
            )
            .order_by(AccountabilityCheckin.created_at.desc())
        )
        checkin_dates: set[date] = set()
        for (ts,) in result.all():
            checkin_dates.add(_to_local_date(ts, timezone_name))
        streak = 0
        current = today_local
        while current in checkin_dates:
            streak += 1
            current -= timedelta(days=1)
        return streak

    my_streak = await _streak(current_user.id)
    partner_streak = await _streak(partner_id)
    my_checked_in_today = await _has_checkin_today(
        db,
        partnership_id=partnership_id,
        user_id=current_user.id,
        timezone_name=timezone_name,
    )

    total_result = await db.execute(
        select(sql_func.count(AccountabilityCheckin.id)).where(AccountabilityCheckin.partnership_id == partnership_id)
    )
    total_checkins = total_result.scalar_one() or 0

    partner_today = await db.execute(
        select(AccountabilityCheckin).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == partner_id,
                AccountabilityCheckin.created_at >= today_start,
                AccountabilityCheckin.created_at <= today_end,
            )
        )
    )

    return PartnershipStatsOut(
        my_streak_days=my_streak,
        partner_streak_days=partner_streak,
        my_checked_in_today=my_checked_in_today,
        partner_checked_in_today=partner_today.scalar_one_or_none() is not None,
        total_checkins=total_checkins,
    )


@router.get("/{partnership_id}/timeline", response_model=list[CheckinOut])
async def get_partnership_timeline(
    partnership_id: UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取打卡历史时间线"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        select(AccountabilityCheckin)
        .where(AccountabilityCheckin.partnership_id == partnership_id)
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(limit)
    )
    checkins = []
    for item in result.scalars().all():
        checkins.append(await _build_checkin_out(db, item))
    return checkins


@router.get("/{partnership_id}/heatmap")
async def get_partnership_heatmap(
    partnership_id: UUID,
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取伙伴关系打卡热力图数据

    返回每月每天的打卡状态，用于热力图可视化
    """
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # 默认为当前年份
    if year is None:
        year = _utcnow().year

    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31, 23, 59, 59)

    # 获取当年的所有打卡记录
    result = await db.execute(
        select(AccountabilityCheckin)
        .where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.created_at >= year_start,
                AccountabilityCheckin.created_at <= year_end,
            )
        )
        .order_by(AccountabilityCheckin.created_at)
    )
    checkins = result.scalars().all()

    # 构建热力图数据
    heatmap_data = {}
    for checkin in checkins:
        date_key = checkin.created_at.strftime("%Y-%m-%d")
        if date_key not in heatmap_data:
            heatmap_data[date_key] = {
                "date": date_key,
                "initiator_checkins": 0,
                "partner_checkins": 0,
            }

        user_id_str = str(checkin.user_id)
        if user_id_str == str(partnership.initiator_id):
            heatmap_data[date_key]["initiator_checkins"] += 1
        else:
            heatmap_data[date_key]["partner_checkins"] += 1

    return {
        "year": year,
        "partnership_id": str(partnership_id),
        "heatmap": list(heatmap_data.values()),
        "total_days": len(heatmap_data),
    }


@router.post("/checkin/{checkin_id}/like")
async def like_checkin(
    checkin_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """点赞打卡"""
    checkin = await db.get(AccountabilityCheckin, checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="Checkin not found")

    partnership = await AccountabilityPartnership.get_by_id(db, checkin.partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(current_user.id) != str(partnership.initiator_id) and str(current_user.id) != str(partnership.partner_id):
        raise HTTPException(status_code=403, detail="Only partners can like checkins")

    if str(checkin.user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot like your own checkin")

    liked_by_list = list(checkin.liked_by) if isinstance(checkin.liked_by, list) else []
    current_user_id_str = str(current_user.id)

    if current_user_id_str in liked_by_list:
        raise HTTPException(status_code=400, detail="You have already liked this checkin")

    liked_by_list.append(current_user_id_str)
    checkin.liked_by = liked_by_list
    checkin.likes = len(liked_by_list)
    await db.commit()

    return {
        "checkin_id": str(checkin_id),
        "likes": checkin.likes,
        "liked": True,
        "message": "Checkin liked successfully",
    }


@router.post("/checkin/{checkin_id}/encourage")
async def encourage_checkin(
    checkin_id: UUID,
    body: EncourageSchema = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """发送鼓励消息到打卡"""
    checkin = await db.get(AccountabilityCheckin, checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="Checkin not found")

    partnership = await AccountabilityPartnership.get_by_id(db, checkin.partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(current_user.id) != str(partnership.initiator_id) and str(current_user.id) != str(partnership.partner_id):
        raise HTTPException(status_code=403, detail="Only partners can send encouragement")

    if str(checkin.user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot encourage your own checkin")

    encouragement = {
        "id": str(uuid4()),
        "user_id": str(current_user.id),
        "message": body.message.strip(),
        "created_at": _utcnow().isoformat(),
    }

    encouragements_list = list(checkin.encouragements) if isinstance(checkin.encouragements, list) else []
    encouragements_list.append(encouragement)
    checkin.encouragements = encouragements_list

    await db.commit()

    return {
        "checkin_id": str(checkin_id),
        "encouragement": encouragement,
        "total_encouragements": len(encouragements_list),
        "message": "Encouragement sent successfully",
    }


@router.get("/achievements")
async def get_accountability_achievements(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取责任伙伴相关的成就定义和用户解锁状态"""
    from app.services.accountability_achievement_service import (
        accountability_achievement_service,
    )

    achievements = accountability_achievement_service.ACCOUNTABILITY_ACHIEVEMENTS

    # 获取用户已解锁的成就
    result = await db.execute(
        select(UserAchievement).where(
            and_(
                UserAchievement.user_id == current_user.id,
                UserAchievement.achievement_id.in_(achievements.keys()),
            )
        )
    )
    unlocked = {ua.achievement_id: ua for ua in result.scalars().all()}

    # 构建响应
    achievement_list = []
    for achievement_id, definition in achievements.items():
        user_achievement = unlocked.get(achievement_id)
        achievement_list.append(
            {
                "id": achievement_id,
                "name": definition["name"],
                "description": definition["description"],
                "icon": definition.get("icon", "🏆"),
                "type": definition["type"].value,
                "points": definition.get("points", 0),
                "unlocked": user_achievement is not None,
                "unlocked_at": user_achievement.unlocked_at.isoformat() if user_achievement else None,
            }
        )

    return {
        "achievements": achievement_list,
        "total_unlocked": len(unlocked),
        "total_available": len(achievements),
    }


@router.get("/{partnership_id}/achievements")
async def get_partnership_achievements(
    partnership_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取伙伴关系双方的成就状态"""
    partnership = await AccountabilityPartnership.get_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(current_user.id) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.services.accountability_achievement_service import (
        accountability_achievement_service,
    )

    achievements = accountability_achievement_service.ACCOUNTABILITY_ACHIEVEMENTS
    partner_id = (
        partnership.partner_id if str(partnership.initiator_id) == str(current_user.id) else partnership.initiator_id
    )

    # 获取双方成就
    my_achievements = set()
    partner_achievements = set()

    for user_id, is_me in [(current_user.id, True), (partner_id, False)]:
        result = await db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id.in_(achievements.keys()),
                )
            )
        )
        unlocked = {ua.achievement_id for ua in result.scalars().all()}
        if is_me:
            my_achievements = unlocked
        else:
            partner_achievements = unlocked

    return {
        "partnership_id": str(partnership_id),
        "my_achievements": list(my_achievements),
        "partner_achievements": list(partner_achievements),
    }
