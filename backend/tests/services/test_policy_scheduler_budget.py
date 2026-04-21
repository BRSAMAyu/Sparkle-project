from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.models.memory import EpisodicMemory
from app.services.accountability_notification_service import accountability_notification_service
from app.services.policy_scheduler_service import PolicySchedulerService


def _commitment(user_id, due_at: datetime) -> EpisodicMemory:
    return EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary="补齐今天的练习",
        source_type="chat",
        source_id="session-1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=due_at,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
    )


@pytest.mark.asyncio
async def test_policy_scheduler_applies_daily_budget_cap(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    user_id = uuid4()
    commitments = [
        _commitment(user_id, datetime(2026, 4, 24, 9, 0, 0)),
        _commitment(user_id, datetime(2026, 4, 24, 9, 0, 0)),
        _commitment(user_id, datetime(2026, 4, 24, 9, 0, 0)),
    ]
    db_session.add_all(commitments)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    for commitment in commitments:
        await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    result = await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))

    assert result["due_count"] >= 3
    assert notify.await_count == 2


@pytest.mark.asyncio
async def test_policy_scheduler_budget_is_per_user(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment_a = _commitment(uuid4(), datetime(2026, 4, 24, 9, 0, 0))
    commitment_b = _commitment(uuid4(), datetime(2026, 4, 24, 9, 0, 0))
    db_session.add_all([commitment_a, commitment_b])
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment_a.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    await scheduler.ensure_policies_for_user(user_id=commitment_b.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))

    assert notify.await_count == 2


@pytest.mark.asyncio
async def test_shadow_mode_does_not_consume_budget(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "shadow")
    user_id = uuid4()
    commitment = _commitment(user_id, datetime(2026, 4, 24, 9, 0, 0))
    db_session.add(commitment)
    await db_session.commit()
    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))
    exhausted = await scheduler._budget_exhausted(user_id, datetime(2026, 4, 21, 9, 0, 0))

    assert exhausted is False
