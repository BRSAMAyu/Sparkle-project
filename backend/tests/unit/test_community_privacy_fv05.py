from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.community import Group, GroupTask, GroupTaskClaim, GroupType
from app.models.community_privacy import PrivacyBudgetLedger
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.community_signal_bridge import CommunitySignalBridge


async def _user(db, idx: int, *, enabled: bool = True) -> User:
    user = User(
        username=f"privacy-user-{idx}",
        email=f"privacy-{idx}@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    db.add(UserSettings(user_id=user.id, community_intelligence_enabled=enabled))
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_group_task_aggregate_enforces_k_anonymity(db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_ENABLED", True,
    )
    group = Group(name="tiny", type=GroupType.SPRINT)
    db_session.add(group)
    await db_session.flush()
    task = GroupTask(group_id=group.id, created_by=test_user.id, title="T", total_claims=3)
    db_session.add(task)
    await db_session.flush()
    for idx in range(3):
        user = await _user(db_session, idx)
        db_session.add(GroupTaskClaim(group_task_id=task.id, user_id=user.id, is_completed=True))
    await db_session.commit()

    result = await CommunitySignalBridge(db_session).build_privacy_preserving_cohort_signal(
        requester_user_id=test_user.id,
        cohort_criteria={"group_id": str(group.id)},
        stat_name="task_completion_rate",
        contributor_values=[1.0, 1.0, 1.0],
    )

    assert result["allowed"] is False
    assert result["reason"] == "below_privacy_floor"


@pytest.mark.asyncio
async def test_group_task_aggregate_persists_budget_and_excludes_opt_out(db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_ENABLED", True,
    )
    group = Group(name="cohort", type=GroupType.SPRINT)
    db_session.add(group)
    await db_session.flush()

    contributor_values = [1.0, 1.0, 1.0, 1.0, 0.0]  # 5 opted-in (idx 5 = opt-out, excluded)

    result = await CommunitySignalBridge(db_session).build_privacy_preserving_cohort_signal(
        requester_user_id=test_user.id,
        cohort_criteria={"group_id": str(group.id)},
        stat_name="task_completion_rate",
        contributor_values=contributor_values,
    )

    assert result["allowed"] is True
    assert result["cohort"]["member_count"] >= 5

    ledger = (await db_session.execute(select(PrivacyBudgetLedger))).scalars().all()
    assert len(ledger) == 1
    assert ledger[0].allowed is True
    assert ledger[0].epsilon_spent > 0


@pytest.mark.asyncio
async def test_budget_exhaustion_rejects_aggregate(db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_ENABLED", True,
    )
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_DAILY_EPSILON", 0.1,
    )
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_QUERY_EPSILON", 0.1,
    )

    contributor_values = [1.0] * 6

    bridge = CommunitySignalBridge(db_session)
    first = await bridge.build_privacy_preserving_cohort_signal(
        requester_user_id=test_user.id,
        cohort_criteria={"group_id": "budget"},
        stat_name="task_completion_rate",
        contributor_values=contributor_values,
    )
    second = await bridge.build_privacy_preserving_cohort_signal(
        requester_user_id=test_user.id,
        cohort_criteria={"group_id": "budget"},
        stat_name="task_completion_rate",
        contributor_values=contributor_values,
    )

    assert first["allowed"] is True
    assert second["allowed"] is False
    assert "budget" in second.get("reason", "")
    ledgers = (await db_session.execute(select(PrivacyBudgetLedger).order_by(PrivacyBudgetLedger.created_at))).scalars().all()
    assert [entry.allowed for entry in ledgers] == [True, False]


@pytest.mark.asyncio
async def test_user_opt_out_prevents_consumption(db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        "app.services.community_signal_bridge.settings.COMMUNITY_INTELLIGENCE_ENABLED", True,
    )
    db_session.add(UserSettings(user_id=test_user.id, community_intelligence_enabled=False))
    await db_session.commit()
    result = await CommunitySignalBridge(db_session).build_privacy_preserving_cohort_signal(
        requester_user_id=test_user.id,
        cohort_criteria={"group_id": str(test_user.id)},
        stat_name="task_completion_rate",
        contributor_values=[1.0] * 5,
    )
    assert result["allowed"] is False
    assert result["reason"] == "requester_opted_out"
