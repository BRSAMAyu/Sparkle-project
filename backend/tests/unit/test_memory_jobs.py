from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.models.event import TrackingEvent
from app.models.user import User
from app.services.memory_jobs import MemoryJobsService
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_memory_jobs_evidence_health_marks_missing(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_EVIDENCE_HEALTH_JOB", True, raising=False)

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
        event_id="evt_job_missing",
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
        summary="Job missing event",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["job"],
        evidence_refs=[{"type": "event", "id": "evt_job_missing"}],
    )

    event.deleted_at = _utcnow()
    await db_session.commit()

    service = MemoryJobsService(db_session)
    await service.run_evidence_health_job(limit_per_type=10)

    await db_session.refresh(episodic)
    assert episodic.evidence_missing is True
    assert episodic.evidence_checked_at is not None


@pytest.mark.asyncio
async def test_memory_jobs_repair_restores_evidence(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_EVIDENCE_HEALTH_JOB", True, raising=False)

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
        event_id="evt_job_restore",
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
        summary="Restore event",
        source_type="analysis",
        source_id="src_2",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["job"],
        evidence_refs=[{"type": "event", "id": "evt_job_restore"}],
    )
    episodic.evidence_missing = True
    await db_session.commit()

    service = MemoryJobsService(db_session)
    await service.run_repair_job(limit=10)

    await db_session.refresh(episodic)
    assert episodic.evidence_missing is False
    assert episodic.evidence_snapshot is not None
