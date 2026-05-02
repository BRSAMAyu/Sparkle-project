"""Community accountability experience BFF.

This router intentionally aggregates existing accountability primitives into a
single mobile-friendly payload. Registration is left to the closeout
integration pass so parallel agents do not contend on the central router.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.user import User
from app.services.accountability_mvp_service import AccountabilityMvpService

router = APIRouter(prefix="/experience", tags=["experience"])


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _display_name(user: User | None) -> str:
    if user is None:
        return "Accountability Partner"
    return user.nickname or user.full_name or user.username or "Accountability Partner"


def _other_user(partnership: AccountabilityPartnership, current_user_id: UUID) -> User | None:
    if str(partnership.initiator_id) == str(current_user_id):
        return partnership.partner
    return partnership.initiator


def _my_goal(partnership: AccountabilityPartnership, current_user_id: UUID) -> str:
    if str(partnership.initiator_id) == str(current_user_id):
        return partnership.initiator_goal
    return partnership.partner_goal or partnership.initiator_goal


def _partner_goal(partnership: AccountabilityPartnership, current_user_id: UUID) -> str:
    if str(partnership.initiator_id) == str(current_user_id):
        return partnership.partner_goal or partnership.initiator_goal
    return partnership.initiator_goal


class CommitmentCardPayload(BaseModel):
    id: str
    summary: str
    due_at: datetime | None = None
    witness_names: list[str] = Field(default_factory=list)
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = "active"
    success_criteria: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    allow_partner_reminders: bool = True


class PartnerProgressItem(BaseModel):
    partnership_id: str
    partner_id: str
    partner_name: str
    goal_summary: str
    today_done: bool = False
    my_today_done: bool = False
    weekly_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    last_checkin_at: datetime | None = None


class SharedGoalItem(BaseModel):
    id: str
    title: str
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    member_names: list[str] = Field(default_factory=list)
    status: str = "active"


class SquadRiskItem(BaseModel):
    partnership_id: str
    member_name: str
    reason: str
    severity: str = "medium"
    suggested_action: str = "send_gentle_checkin"


class HelpableItem(BaseModel):
    partnership_id: str
    member_name: str
    need: str
    action: str = "encourage"


class CommunityAccountabilityOut(BaseModel):
    my_commitments: list[CommitmentCardPayload] = Field(default_factory=list)
    partner_progress: list[PartnerProgressItem] = Field(default_factory=list)
    shared_goals: list[SharedGoalItem] = Field(default_factory=list)
    squad_risks: list[SquadRiskItem] = Field(default_factory=list)
    helpable: list[HelpableItem] = Field(default_factory=list)


async def _checked_in_since(
    db: AsyncSession,
    *,
    partnership_id: UUID,
    user_id: UUID,
    since: datetime,
) -> bool:
    result = await db.execute(
        select(AccountabilityCheckin.id)
        .where(
            AccountabilityCheckin.partnership_id == partnership_id,
            AccountabilityCheckin.user_id == user_id,
            AccountabilityCheckin.created_at >= since,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _last_checkin_at(db: AsyncSession, partnership_id: UUID, user_id: UUID | None = None) -> datetime | None:
    query = select(func.max(AccountabilityCheckin.created_at)).where(
        AccountabilityCheckin.partnership_id == partnership_id,
    )
    if user_id is not None:
        query = query.where(AccountabilityCheckin.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _weekly_progress(
    db: AsyncSession,
    *,
    partnership_id: UUID,
    partner_id: UUID,
    check_in_days: int,
    since: datetime,
) -> float:
    result = await db.execute(
        select(func.count(AccountabilityCheckin.id)).where(
            AccountabilityCheckin.partnership_id == partnership_id,
            AccountabilityCheckin.user_id == partner_id,
            AccountabilityCheckin.created_at >= since,
        )
    )
    checkins = int(result.scalar_one() or 0)
    expected = max(1, min(7, check_in_days or 1))
    return min(1.0, checkins / expected)


@router.get("/community-accountability", response_model=CommunityAccountabilityOut)
async def get_community_accountability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityAccountabilityOut:
    now = _utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    partnerships_result = await db.execute(
        select(AccountabilityPartnership)
        .options(
            selectinload(AccountabilityPartnership.initiator),
            selectinload(AccountabilityPartnership.partner),
        )
        .where(
            and_(
                or_(
                    AccountabilityPartnership.initiator_id == current_user.id,
                    AccountabilityPartnership.partner_id == current_user.id,
                ),
                AccountabilityPartnership.status.in_(
                    [AccountabilityStatus.ACTIVE, AccountabilityStatus.PENDING],
                ),
            )
        )
        .order_by(AccountabilityPartnership.updated_at.desc())
        .limit(12)
    )
    partnerships = list(partnerships_result.scalars().all())
    active_partnerships = [item for item in partnerships if item.status == AccountabilityStatus.ACTIVE]

    pending_commitments = await AccountabilityMvpService(db).list_pending_commitments(user_id=current_user.id, now=now)
    my_commitments = [
        CommitmentCardPayload(
            id=item.id,
            summary=item.summary,
            due_at=item.due_at,
            witness_names=[_display_name(_other_user(active_partnerships[0], current_user.id))]
            if active_partnerships
            else [],
            progress=0.25 if item.due_at and item.due_at > now else 0.1,
            status="due_soon" if item.due_at and item.due_at <= now + timedelta(days=1) else "active",
            success_criteria=["Evidence captured", "Partner can verify"],
            milestones=["Start", "Show evidence", "Close loop"],
            evidence_refs=[item.evidence_token] if item.evidence_token else [],
            allow_partner_reminders=True,
        )
        for item in pending_commitments[:6]
    ]

    partner_progress: list[PartnerProgressItem] = []
    shared_goals: list[SharedGoalItem] = []
    squad_risks: list[SquadRiskItem] = []
    helpable: list[HelpableItem] = []

    for partnership in active_partnerships:
        partner = _other_user(partnership, current_user.id)
        partner_id = (
            partnership.partner_id
            if str(partnership.initiator_id) == str(current_user.id)
            else partnership.initiator_id
        )
        partner_name = _display_name(partner)
        partner_today = await _checked_in_since(
            db,
            partnership_id=partnership.id,
            user_id=partner_id,
            since=day_start,
        )
        my_today = await _checked_in_since(
            db,
            partnership_id=partnership.id,
            user_id=current_user.id,
            since=day_start,
        )
        last_partner_checkin = await _last_checkin_at(db, partnership.id, partner_id)
        weekly = await _weekly_progress(
            db,
            partnership_id=partnership.id,
            partner_id=partner_id,
            check_in_days=partnership.check_in_days,
            since=week_start,
        )

        partner_progress.append(
            PartnerProgressItem(
                partnership_id=str(partnership.id),
                partner_id=str(partner_id),
                partner_name=partner_name,
                goal_summary=_partner_goal(partnership, current_user.id),
                today_done=partner_today,
                my_today_done=my_today,
                weekly_progress=weekly,
                last_checkin_at=last_partner_checkin,
            )
        )
        shared_goals.append(
            SharedGoalItem(
                id=str(partnership.id),
                title=_my_goal(partnership, current_user.id),
                progress=(weekly + (1.0 if my_today else 0.0)) / 2,
                member_names=[_display_name(current_user), partner_name],
                status=partnership.status.value,
            )
        )
        if not partner_today:
            helpable.append(
                HelpableItem(
                    partnership_id=str(partnership.id),
                    member_name=partner_name,
                    need="No check-in yet today",
                    action="send_gentle_checkin",
                )
            )
        is_rhythm_cooling = last_partner_checkin is None or last_partner_checkin < now - timedelta(
            days=max(2, partnership.check_in_days),
        )
        if is_rhythm_cooling:
            squad_risks.append(
                SquadRiskItem(
                    partnership_id=str(partnership.id),
                    member_name=partner_name,
                    reason="Partner rhythm is cooling down",
                    severity="medium",
                )
            )

    if not my_commitments:
        my_commitments = [
            CommitmentCardPayload(
                id=str(item.id),
                summary=_my_goal(item, current_user.id),
                due_at=None,
                witness_names=[_display_name(_other_user(item, current_user.id))],
                progress=(
                    0.7
                    if await _checked_in_since(
                        db,
                        partnership_id=item.id,
                        user_id=current_user.id,
                        since=day_start,
                    )
                    else 0.35
                ),
                status="active",
                success_criteria=["Daily check-in", "Partner-visible evidence"],
                milestones=["Today", "This week", "Review"],
                evidence_refs=[],
                allow_partner_reminders=True,
            )
            for item in active_partnerships[:4]
        ]

    return CommunityAccountabilityOut(
        my_commitments=my_commitments,
        partner_progress=partner_progress,
        shared_goals=shared_goals,
        squad_risks=squad_risks,
        helpable=helpable,
    )
