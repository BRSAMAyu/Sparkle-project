from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.api.v1.accountability import (
    _build_checkin_out,
    _build_partnership_out,
    _day_range_for_timezone,
    _to_local_date,
)
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.community import Friendship, FriendshipStatus
from app.models.user import PushPreference, User


def _make_user(*, username: str) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_day_range_for_timezone_uses_local_midnight() -> None:
    reference = datetime(2026, 3, 19, 10, 30, tzinfo=timezone.utc)

    start_at, end_at = _day_range_for_timezone("Asia/Shanghai", reference=reference)

    assert start_at == datetime(2026, 3, 18, 16, 0)
    assert end_at == datetime(2026, 3, 19, 15, 59, 59, 999999)


def test_to_local_date_converts_utc_timestamp() -> None:
    timestamp = datetime(2026, 3, 18, 16, 30, tzinfo=timezone.utc)

    local_date = _to_local_date(timestamp, "Asia/Shanghai")

    assert local_date.isoformat() == "2026-03-19"


@pytest.mark.asyncio
async def test_build_partnership_out_includes_nested_users_and_checkin_state(db_session) -> None:
    owner = _make_user(username="owner")
    partner = _make_user(username="partner")
    owner.push_preference = PushPreference(timezone="Asia/Shanghai")
    partner.push_preference = PushPreference(timezone="Asia/Shanghai")
    db_session.add_all([owner, partner])
    await db_session.commit()
    await db_session.refresh(owner)
    await db_session.refresh(partner)

    friendship = Friendship(
        user_id=owner.id,
        friend_id=partner.id,
        initiated_by=owner.id,
        status=FriendshipStatus.ACCEPTED,
    )
    db_session.add(friendship)
    await db_session.commit()
    await db_session.refresh(friendship)

    partnership = AccountabilityPartnership(
        initiator_id=owner.id,
        partner_id=partner.id,
        friendship_id=friendship.id,
        initiator_goal="每天专注学习 45 分钟",
        partner_goal="每天给伙伴一句反馈",
        check_in_days=2,
        status=AccountabilityStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db_session.add(partnership)
    await db_session.commit()
    await db_session.refresh(partnership)

    today_start, _ = _day_range_for_timezone("Asia/Shanghai")
    owner_checkin_at = today_start + timedelta(hours=9)
    partner_checkin_at = today_start + timedelta(hours=10)

    db_session.add_all(
        [
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=owner.id,
                content="完成了英语精读。",
                mood=4,
                minutes=45,
                created_at=owner_checkin_at,
            ),
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=partner.id,
                content="做了复盘并发来鼓励。",
                mood=5,
                minutes=30,
                created_at=partner_checkin_at,
            ),
        ]
    )
    await db_session.commit()
    await db_session.refresh(partnership)

    payload = await _build_partnership_out(db_session, partnership, owner)

    assert str(payload.initiator.id) == str(owner.id)
    assert str(payload.partner.id) == str(partner.id)
    assert payload.my_role == "initiator"
    assert payload.my_checked_in_today is True
    assert payload.partner_checked_in_today is True
    assert payload.last_checkin_at == partner_checkin_at


@pytest.mark.asyncio
async def test_build_checkin_out_includes_author_payload(db_session) -> None:
    owner = _make_user(username="author")
    partner = _make_user(username="buddy")
    db_session.add_all([owner, partner])
    await db_session.commit()
    await db_session.refresh(owner)
    await db_session.refresh(partner)

    partnership = AccountabilityPartnership(
        initiator_id=owner.id,
        partner_id=partner.id,
        initiator_goal="记录学习进展",
        check_in_days=1,
        status=AccountabilityStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db_session.add(partnership)
    await db_session.commit()
    await db_session.refresh(partnership)

    encouragement = {
        "id": str(uuid4()),
        "user_id": str(partner.id),
        "message": "继续保持，节奏很好。",
        "created_at": datetime(2026, 3, 19, 3, 0).isoformat(),
    }
    checkin = AccountabilityCheckin(
        partnership_id=partnership.id,
        user_id=owner.id,
        content="今天把两个难点都啃下来了。",
        mood=5,
        minutes=55,
        likes=1,
        liked_by=[str(partner.id)],
        encouragements=[encouragement],
        created_at=datetime(2026, 3, 19, 2, 30),
    )
    db_session.add(checkin)
    await db_session.commit()
    await db_session.refresh(checkin)

    payload = await _build_checkin_out(db_session, checkin)

    assert str(payload.author.id) == str(owner.id)
    assert payload.likes == 1
    assert payload.encouragements == [encouragement]
    assert payload.content == "今天把两个难点都啃下来了。"
