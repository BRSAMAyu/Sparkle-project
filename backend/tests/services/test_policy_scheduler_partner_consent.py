from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.models.memory import EpisodicMemory
from app.services.accountability_notification_service import accountability_notification_service
from app.services.policy_scheduler_service import PolicySchedulerService


def _commitment(tags: list[str]) -> EpisodicMemory:
    return EpisodicMemory(
        id=uuid4(),
        user_id=uuid4(),
        summary="完成伙伴共同承诺",
        source_type="chat",
        source_id="session-1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=datetime(2026, 4, 24, 18, 0, 0),
        tags=tags,
        evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
    )


@pytest.mark.asyncio
async def test_partner_policy_is_blocked_without_consent(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(
        [
            "accountability:partnership_id:11111111-1111-1111-1111-111111111111",
            f"accountability:partner_id:{uuid4()}",
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
            "partnership_id": "11111111-1111-1111-1111-111111111111",
            "missed_days": 3,
        },
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert result["matched_count"] == 1
    assert result["triggered_count"] == 0
    assert notify.await_count == 0


@pytest.mark.asyncio
async def test_partner_policy_requires_partner_id(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(
        [
            "accountability:partner_consent:true",
            "accountability:partnership_id:11111111-1111-1111-1111-111111111111",
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
            "partnership_id": "11111111-1111-1111-1111-111111111111",
            "missed_days": 3,
        },
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert result["matched_count"] == 1
    assert result["triggered_count"] == 0
    assert notify.await_count == 0


@pytest.mark.asyncio
async def test_partner_policy_triggers_when_consent_and_partner_are_present(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(
        [
            "accountability:partner_consent:true",
            f"accountability:partner_id:{uuid4()}",
            "accountability:partnership_id:11111111-1111-1111-1111-111111111111",
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
            "partnership_id": "11111111-1111-1111-1111-111111111111",
            "missed_days": 3,
        },
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert result["triggered_count"] == 1
    assert notify.await_count == 1
