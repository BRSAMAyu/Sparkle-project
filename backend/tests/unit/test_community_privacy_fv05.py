from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.community import Group, GroupTask, GroupTaskClaim, GroupType
from app.models.community_privacy import CommunityAggregateSignal, PrivacyBudgetLedger
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
async def test_group_task_aggregate_enforces_k_anonymity(db_session, test_user):
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

    result = await CommunitySignalBridge(db_session).build_group_task_completion_aggregate(
        group_id=group.id,
        requester_user_id=test_user.id,
    )

    assert result["computed"] is False
    assert result["reason"] == "k_anonymity_floor"
    persisted = await db_session.execute(select(CommunityAggregateSignal))
    assert persisted.scalars().all() == []


@pytest.mark.asyncio
async def test_group_task_aggregate_persists_budget_and_excludes_opt_out(db_session, test_user):
    group = Group(name="cohort", type=GroupType.SPRINT)
    db_session.add(group)
    await db_session.flush()
    task = GroupTask(group_id=group.id, created_by=test_user.id, title="T", total_claims=6, total_completions=4)
    db_session.add(task)
    await db_session.flush()
    for idx in range(6):
        user = await _user(db_session, idx, enabled=idx != 5)
        db_session.add(GroupTaskClaim(group_task_id=task.id, user_id=user.id, is_completed=idx < 4))
    await db_session.commit()

    result = await CommunitySignalBridge(db_session).build_group_task_completion_aggregate(
        group_id=group.id,
        requester_user_id=test_user.id,
    )

    assert result["stat_name"] == "task_completion_rate"
    assert result["cohort_size"] == 5
    assert result["policy_bias_only"] is True
    assert result["directive_payload"]["allowed_effect"] == "soft_bias_only"

    ledger = (await db_session.execute(select(PrivacyBudgetLedger))).scalars().all()
    assert len(ledger) == 1
    assert ledger[0].status == "accepted"
    assert ledger[0].epsilon_spent > 0


@pytest.mark.asyncio
async def test_budget_exhaustion_rejects_aggregate(db_session, test_user, monkeypatch):
    monkeypatch.setattr("app.services.community_signal_bridge.settings.COMMUNITY_PRIVACY_MAX_EPSILON", 0.1)
    monkeypatch.setattr("app.services.community_signal_bridge.settings.COMMUNITY_PRIVACY_QUERY_COST", 0.1)
    group = Group(name="budget", type=GroupType.SPRINT)
    db_session.add(group)
    await db_session.flush()
    task = GroupTask(group_id=group.id, created_by=test_user.id, title="T")
    db_session.add(task)
    await db_session.flush()
    for idx in range(5):
        user = await _user(db_session, idx)
        db_session.add(GroupTaskClaim(group_task_id=task.id, user_id=user.id, is_completed=True))
    await db_session.commit()

    bridge = CommunitySignalBridge(db_session)
    first = await bridge.build_group_task_completion_aggregate(group_id=group.id, requester_user_id=test_user.id)
    second = await bridge.build_group_task_completion_aggregate(group_id=group.id, requester_user_id=test_user.id)

    assert first["stat_name"] == "task_completion_rate"
    assert second["computed"] is False
    assert second["reason"] == "privacy_budget_exhausted"
    ledgers = (await db_session.execute(select(PrivacyBudgetLedger).order_by(PrivacyBudgetLedger.created_at))).scalars().all()
    assert [entry.status for entry in ledgers] == ["accepted", "denied"]


@pytest.mark.asyncio
async def test_user_opt_out_prevents_consumption(db_session, test_user):
    db_session.add(UserSettings(user_id=test_user.id, community_intelligence_enabled=False))
    await db_session.commit()
    result = await CommunitySignalBridge(db_session).build_group_task_completion_aggregate(
        group_id=test_user.id,
        requester_user_id=test_user.id,
    )
    assert result["computed"] is False
    assert result["reason"] == "community_intelligence_disabled"
