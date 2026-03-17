"""
责任伙伴系统 API
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.community import Friendship, FriendshipStatus

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────


class PartnershipRequestSchema(BaseModel):
    partner_id: UUID
    initiator_goal: str
    check_in_days: int = 1


class PartnershipRespondSchema(BaseModel):
    accept: bool
    partner_goal: Optional[str] = None


class CheckinCreateSchema(BaseModel):
    content: str
    mood: int = 3  # 1-5
    minutes: int = 0


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

    class Config:
        from_attributes = True


class PartnershipStatsOut(BaseModel):
    my_streak_days: int
    partner_streak_days: int
    partner_checked_in_today: bool
    total_checkins: int


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/request", response_model=PartnershipOut, status_code=201)
async def request_partnership(
    body: PartnershipRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """发起责任伙伴邀请"""
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

    # Check existing active partnership
    existing = await db.execute(
        select(AccountabilityPartnership).where(
            and_(
                AccountabilityPartnership.status.in_(
                    [AccountabilityStatus.PENDING, AccountabilityStatus.ACTIVE]
                ),
                or_(
                    and_(
                        AccountabilityPartnership.initiator_id
                        == current_user.id,
                        AccountabilityPartnership.partner_id
                        == body.partner_id,
                    ),
                    and_(
                        AccountabilityPartnership.initiator_id
                        == body.partner_id,
                        AccountabilityPartnership.partner_id
                        == current_user.id,
                    ),
                ),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active or pending partnership already exists",
        )

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
    return PartnershipOut.model_validate(partnership)


@router.post("/{partnership_id}/respond", response_model=PartnershipOut)
async def respond_to_partnership(
    partnership_id: UUID,
    body: PartnershipRespondSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """接受或拒绝责任伙伴邀请"""
    partnership = await AccountabilityPartnership.get_by_id(
        db, partnership_id
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only the invited partner can respond"
        )

    if partnership.status != AccountabilityStatus.PENDING:
        raise HTTPException(
            status_code=400, detail="Partnership is not in pending state"
        )

    if body.accept:
        partnership.status = AccountabilityStatus.ACTIVE
        partnership.started_at = datetime.now(timezone.utc)
        if body.partner_goal:
            partnership.partner_goal = body.partner_goal
    else:
        partnership.status = AccountabilityStatus.ENDED
        partnership.ended_at = datetime.now(timezone.utc)

    await partnership.save(db)
    await db.refresh(partnership)
    return PartnershipOut.model_validate(partnership)


@router.get("/mine", response_model=list[PartnershipOut])
async def get_my_partnerships(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取我的责任伙伴列表"""
    result = await db.execute(
        select(AccountabilityPartnership).where(
            and_(
                AccountabilityPartnership.status.in_(
                    [AccountabilityStatus.PENDING, AccountabilityStatus.ACTIVE]
                ),
                or_(
                    AccountabilityPartnership.initiator_id == current_user.id,
                    AccountabilityPartnership.partner_id == current_user.id,
                ),
            )
        )
    )
    partnerships = result.scalars().all()
    return [PartnershipOut.model_validate(p) for p in partnerships]


@router.delete("/{partnership_id}", status_code=204)
async def end_partnership(
    partnership_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """结束伙伴关系"""
    partnership = await AccountabilityPartnership.get_by_id(
        db, partnership_id
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(
        current_user.id
    ) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    partnership.status = AccountabilityStatus.ENDED
    partnership.ended_at = datetime.now(timezone.utc)
    await partnership.save(db)


@router.post("/{partnership_id}/checkin", response_model=CheckinOut, status_code=201)
async def daily_checkin(
    partnership_id: UUID,
    body: CheckinCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """今日打卡"""
    partnership = await AccountabilityPartnership.get_by_id(
        db, partnership_id
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(
        current_user.id
    ) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    if partnership.status != AccountabilityStatus.ACTIVE:
        raise HTTPException(
            status_code=400, detail="Partnership is not active"
        )

    # Validate mood range
    if not 1 <= body.mood <= 5:
        raise HTTPException(status_code=400, detail="Mood must be between 1 and 5")

    checkin = AccountabilityCheckin(
        partnership_id=partnership_id,
        user_id=current_user.id,
        content=body.content,
        mood=body.mood,
        minutes=body.minutes,
    )
    await checkin.save(db)
    await db.refresh(checkin)
    return CheckinOut.model_validate(checkin)


@router.get("/{partnership_id}/stats", response_model=PartnershipStatsOut)
async def get_partnership_stats(
    partnership_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取伙伴关系统计"""
    partnership = await AccountabilityPartnership.get_by_id(
        db, partnership_id
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(
        current_user.id
    ) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    partner_id = (
        partnership.partner_id
        if str(partnership.initiator_id) == str(current_user.id)
        else partnership.initiator_id
    )

    # Count checkins per user (simplified streak: consecutive days from today)
    from sqlalchemy import func as sql_func

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = await db.execute(
        select(
            AccountabilityCheckin.user_id,
            sql_func.count(AccountabilityCheckin.id).label("count"),
        )
        .where(
            AccountabilityCheckin.partnership_id == partnership_id
        )
        .group_by(AccountabilityCheckin.user_id)
    )
    rows = result.all()
    counts = {str(r.user_id): r.count for r in rows}

    partner_today = await db.execute(
        select(AccountabilityCheckin).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == partner_id,
                AccountabilityCheckin.created_at >= today_start,
            )
        )
    )

    return PartnershipStatsOut(
        my_streak_days=counts.get(str(current_user.id), 0),
        partner_streak_days=counts.get(str(partner_id), 0),
        partner_checked_in_today=partner_today.scalar_one_or_none()
        is not None,
        total_checkins=sum(counts.values()),
    )


@router.get("/{partnership_id}/timeline", response_model=list[CheckinOut])
async def get_partnership_timeline(
    partnership_id: UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取打卡历史时间线"""
    partnership = await AccountabilityPartnership.get_by_id(
        db, partnership_id
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")

    if str(partnership.initiator_id) != str(
        current_user.id
    ) and str(partnership.partner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        select(AccountabilityCheckin)
        .where(AccountabilityCheckin.partnership_id == partnership_id)
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(limit)
    )
    return [CheckinOut.model_validate(c) for c in result.scalars().all()]
