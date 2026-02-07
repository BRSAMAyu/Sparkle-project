from datetime import UTC, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest

from app.models.event import TrackingEvent
from app.models.user import User
from app.services.evidence_health_service import EvidenceHealthService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_evidence_health_marks_missing_event(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    event = TrackingEvent(
        event_id="evt_missing",
        user_id=user_id,
        event_type="test",
        schema_version="event.v1",
        source="unit",
        ts_ms=int(_utcnow().timestamp() * 1000),
        entities=None,
        payload=None,
        received_at=_utcnow(),
    )
    db_session.add(event)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    episodic = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Testing missing event",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_missing"}],
    )
    assert episodic.evidence_score == pytest.approx(0.5)

    event.deleted_at = _utcnow()
    await db_session.commit()

    health_service = EvidenceHealthService(db_session)
    await health_service.run_health_check(user_id, limit=10)

    await db_session.refresh(episodic)
    assert episodic.evidence_missing is True
    assert episodic.evidence_checked_at is not None
    assert episodic.evidence_score == pytest.approx(0.0)
