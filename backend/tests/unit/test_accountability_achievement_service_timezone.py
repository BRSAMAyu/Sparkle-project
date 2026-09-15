from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.user import PushPreference, User
from app.services.accountability_achievement_service import accountability_achievement_service


@pytest.mark.asyncio
async def test_calculate_streak_uses_user_local_timezone(db_session, monkeypatch):
    fixed_now = datetime(2026, 4, 1, 1, 0, 0)
    monkeypatch.setattr(
        "app.services.accountability_achievement_service._utcnow",
        lambda: fixed_now,
    )

    user_id = uuid4()
    partner_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="hashed",
    )
    partner = User(
        id=partner_id,
        username=f"partner_{partner_id.hex[:8]}",
        email=f"{partner_id.hex[:8]}@example.com",
        hashed_password="hashed",
    )
    db_session.add_all(
        [
            user,
            partner,
            PushPreference(user_id=user_id, timezone="Asia/Shanghai"),
            PushPreference(user_id=partner_id, timezone="Asia/Shanghai"),
        ]
    )
    await db_session.flush()

    partnership = AccountabilityPartnership(
        initiator_id=user_id,
        partner_id=partner_id,
        initiator_goal="坚持打卡",
        partner_goal="互相监督",
        check_in_days=1,
        status=AccountabilityStatus.ACTIVE,
    )
    db_session.add(partnership)
    await db_session.flush()

    # UTC 上是 3/31 和 3/30，但在上海时区分别是 4/1 00:30 和 3/31 00:30
    db_session.add_all(
        [
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=user_id,
                content="day 1",
                mood=4,
                minutes=20,
                created_at=datetime(2026, 3, 31, 16, 30, 0, tzinfo=timezone.utc).replace(tzinfo=None),
            ),
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=user_id,
                content="day 2",
                mood=4,
                minutes=20,
                created_at=datetime(2026, 3, 30, 16, 30, 0, tzinfo=timezone.utc).replace(tzinfo=None),
            ),
        ]
    )
    await db_session.commit()

    streak = await accountability_achievement_service._calculate_streak(
        db_session,
        partnership.id,
        user_id,
    )

    assert streak == 2
