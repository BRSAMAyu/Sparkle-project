from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.user import User
from app.services.community_signal_bridge import CommunitySignalBridge
from app.services.social_signal_bridge import SocialSignalBridge


@pytest.mark.asyncio
async def test_social_signal_bridge_prioritizes_partner_checkin_without_identity_leak(
    db_session,
    monkeypatch,
):
    user = User(username="learner", email="learner@example.com", hashed_password="hashed")
    partner = User(
        username="partner_real_name",
        email="partner@example.com",
        hashed_password="hashed",
        nickname="小张",
    )
    db_session.add_all([user, partner])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(partner)

    partnership = AccountabilityPartnership(
        initiator_id=user.id,
        partner_id=partner.id,
        initiator_goal="这周完成第三章",
        partner_goal="复盘 TCP",
        check_in_days=1,
        status=AccountabilityStatus.ACTIVE,
        started_at=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(partnership)
    await db_session.commit()
    await db_session.refresh(partnership)

    checkin = AccountabilityCheckin(
        partnership_id=partnership.id,
        user_id=partner.id,
        content="我今天完成了 TCP 任务，还复习了握手细节",
        mood=4,
        minutes=45,
        likes=0,
        liked_by=[],
        encouragements=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(checkin)
    await db_session.commit()

    service = SocialSignalBridge(db_session)
    monkeypatch.setattr(service, "_social_mode", AsyncMock(return_value="live"))
    monkeypatch.setattr(
        service,
        "_fetch_for_user",
        AsyncMock(
            return_value={
                "snapshot": SimpleNamespace(
                    recent_person_mentions=[],
                    relationship_count=0,
                    pending_commitments_count=0,
                ),
                "inferred": {},
                "explicit": {"use_social_signals": True},
            }
        ),
    )

    signals = await service.build_social_signals_v1(user.id)

    assert signals is not None
    assert signals.active_accountability_contract_count == 1
    assert signals.high_relevance_events[0]["kind"] == "partner_checkin"
    rendered = str(signals.to_payload())
    assert "学习伙伴" in rendered
    assert "小张" not in rendered
    assert "partner_real_name" not in rendered
    assert "握手细节" not in rendered
    assert signals.social_context_receipt is not None
    assert signals.social_context_receipt["type"] == "social_context_receipt"
    assert signals.social_context_receipt["decision_reason"] == "参考了学习伙伴的动态"
    assert any("这不是你一个人的目标" in item for item in signals.tone_guidance)


@pytest.mark.asyncio
async def test_social_signal_bridge_respects_user_opt_out(db_session, monkeypatch):
    service = SocialSignalBridge(db_session)
    monkeypatch.setattr(service, "_social_mode", AsyncMock(return_value="live"))
    monkeypatch.setattr(
        service,
        "_fetch_for_user",
        AsyncMock(
            return_value={
                "snapshot": SimpleNamespace(
                    recent_person_mentions=[object()],
                    relationship_count=1,
                    pending_commitments_count=1,
                ),
                "inferred": {},
                "explicit": {"use_social_signals": False},
            }
        ),
    )

    assert await service.build_social_signals_v1(uuid4()) is None


def test_community_signal_bridge_sanitizes_aurora_social_events():
    sanitized = CommunitySignalBridge.sanitize_for_aurora_context(
        {
            "kind": "partner_checkin",
            "actor_id": str(uuid4()),
            "display_name": "真实姓名",
            "raw_content": "我完成了具体章节",
            "summary_line": "你的学习伙伴刚完成了一次 check-in。",
            "relevance": 0.94,
        },
        viewer_user_id=uuid4(),
    )

    assert sanitized is not None
    assert sanitized["label"] == "你的学习伙伴"
    assert "真实姓名" not in str(sanitized)
    assert "具体章节" not in str(sanitized)
    assert "privacy_boundary" in sanitized
    assert CommunitySignalBridge.sanitize_for_aurora_context({"kind": "general_chat"}) is None
