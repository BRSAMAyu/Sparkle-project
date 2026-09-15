from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.accountability_policy import AccountabilityPolicy
from app.models.memory import EpisodicMemory
from app.services.accountability_notification_service import accountability_notification_service
from app.services.policy_scheduler_service import PolicySchedulerService


def _commitment(*, tags: list[str] | None = None, due_at: datetime | None = None) -> EpisodicMemory:
    return EpisodicMemory(
        id=uuid4(),
        user_id=uuid4(),
        summary="整理这一章的错题",
        source_type="chat",
        source_id="session-1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=datetime(2026, 4, 24, 18, 0, 0) if due_at is None else due_at,
        tags=tags or [],
        evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        evidence_token="turn_1",
    )


@pytest.mark.asyncio
async def test_policy_scheduler_registers_next_trigger_times(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()

    rows = await PolicySchedulerService(db_session).ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    reminder = next(row for row in rows if row.policy_id.startswith("due_reminder_3d"))
    overdue = next(row for row in rows if row.policy_id.startswith("overdue_priority_2d"))
    assert reminder.next_trigger_at == datetime(2026, 4, 21, 18, 0, 0)
    assert overdue.next_trigger_at == datetime(2026, 4, 26, 18, 0, 0)


@pytest.mark.asyncio
async def test_policy_scheduler_triggers_due_notifications_live(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(due_at=datetime(2026, 4, 24, 9, 0, 0))
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    result = await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))
    rows = (await db_session.execute(select(AccountabilityPolicy).where(AccountabilityPolicy.commitment_id == commitment.id))).scalars().all()

    assert result["triggered_count"] == 1
    assert notify.await_count == 1
    assert next(row for row in rows if row.policy_id.startswith("due_reminder_3d")).next_trigger_at is None


@pytest.mark.asyncio
async def test_policy_scheduler_respects_shadow_mode(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "shadow")
    commitment = _commitment(due_at=datetime(2026, 4, 24, 9, 0, 0))
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    result = await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))
    row = (await db_session.execute(select(AccountabilityPolicy).where(AccountabilityPolicy.policy_id.like("due_reminder_3d:%")))).scalar_one()

    assert result["triggered_count"] == 0
    assert notify.await_count == 0
    assert row.last_skip_reason == "shadow"
    assert row.cooldown_until is not None


@pytest.mark.asyncio
async def test_policy_scheduler_downgrades_priority_by_tag(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(due_at=datetime(2026, 4, 24, 9, 0, 0))
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    result = await scheduler.process_due_policies(now=datetime(2026, 4, 26, 9, 0, 1))
    refreshed = await db_session.get(EpisodicMemory, commitment.id)

    assert result["triggered_count"] >= 1
    assert "policy:priority:downgraded" in (refreshed.tags or [])


@pytest.mark.asyncio
async def test_policy_scheduler_lowers_difficulty_by_tag(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(due_at=datetime(2026, 4, 24, 9, 0, 0))
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    await scheduler.process_due_policies(now=datetime(2026, 4, 29, 9, 0, 1))
    refreshed = await db_session.get(EpisodicMemory, commitment.id)

    assert "policy:difficulty:lowered" in (refreshed.tags or [])
    assert "policy:next_step:smallest_viable" in (refreshed.tags or [])


@pytest.mark.asyncio
async def test_policy_scheduler_handles_success_streak_events(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(tags=["accountability:partnership_id:11111111-1111-1111-1111-111111111111"])
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    result = await scheduler.handle_event(
        event_type="success_streak",
        payload={
            "user_id": str(commitment.user_id),
            "partnership_id": "11111111-1111-1111-1111-111111111111",
            "success_days": 7,
        },
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert result["triggered_count"] == 1
    assert notify.await_count == 1


@pytest.mark.asyncio
async def test_policy_scheduler_handles_peer_missed_events(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    partner_id = uuid4()
    commitment = _commitment(
        tags=[
            "accountability:partner_consent:true",
            f"accountability:partner_id:{partner_id}",
            "accountability:partnership_id:22222222-2222-2222-2222-222222222222",
        ]
    )
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    result = await scheduler.handle_event(
        event_type="peer_missed",
        payload={
            "user_id": str(commitment.user_id),
            "partnership_id": "22222222-2222-2222-2222-222222222222",
            "missed_days": 3,
        },
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert result["triggered_count"] == 1
    assert notify.await_count == 1


@pytest.mark.asyncio
async def test_policy_scheduler_can_revoke_single_policy(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    rows = await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    ok = await scheduler.revoke_policy(rows[0].policy_id)
    refreshed = await db_session.get(AccountabilityPolicy, rows[0].id)

    assert ok is True
    assert refreshed.is_enabled is False
