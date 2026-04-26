# FIXED: 2026-04-25 - Integration DB schema was behind task planning migrations - verified LTM repair flow after Alembic head.
from datetime import timezone, datetime, timedelta
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.event import TrackingEvent
from app.models.user import User
from app.services.evidence_health_service import EvidenceHealthService
from app.services.memory_jobs import MemoryJobsService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_ltm_write_inject_correct(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    preference = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="response_style",
        pref_value={"value": "structured"},
        evidence_refs=[{"type": "event", "id": "evt_pref_1"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Finish LTM rollout",
        status="active",
        target_date=_utcnow().date() + timedelta(days=7),
        evidence_refs=[{"type": "event", "id": "evt_goal_1"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Agreed on LTM rollout plan",
        source_type="analysis",
        source_id="analysis_1",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["planning"],
        evidence_refs=[{"type": "event", "id": "evt_ep_1"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")
    assert "response_style" in pack.preferences

    corrected = await memory_service.apply_correction(
        kind="preference",
        memory_id=preference.id,
        user_id=user_id,
        action="reject",
        reason="user_reject",
    )
    assert corrected is not None
    assert corrected.retracted_at is not None

    pack_after = await builder.build(user_id, intent="chat")
    assert "response_style" not in pack_after.preferences


@pytest.mark.asyncio
async def test_evidence_missing_and_repair_flow(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)

    event = TrackingEvent(
        event_id=f"evt_health_{uuid4().hex[:8]}",
        user_id=user_id,
        event_type="memory_test",
        schema_version="event.v1",
        source="test",
        ts_ms=int(_utcnow().timestamp() * 1000),
    )
    db_session.add(event)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    episodic = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Evidence health check",
        source_type="analysis",
        source_id="analysis_health",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["health"],
        evidence_refs=[{"type": "event", "id": event.event_id}],
    )

    health_service = EvidenceHealthService(db_session)
    resolved_ok = await health_service.check_memory_item(episodic, user_id)
    assert resolved_ok["missing"] is False

    event.deleted_at = _utcnow()
    await db_session.commit()

    resolved_missing = await health_service.check_memory_item(episodic, user_id)
    assert resolved_missing["missing"] is True
    assert {entry["status"] for entry in resolved_missing["resolved"]} == {"redacted"}

    episodic.evidence_missing = True
    await db_session.commit()

    event.deleted_at = None
    await db_session.commit()

    jobs = MemoryJobsService(db_session)
    await jobs.run_repair_job()
    await db_session.refresh(episodic)
    assert episodic.evidence_missing is False
