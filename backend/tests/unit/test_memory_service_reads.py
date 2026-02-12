from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_memory_service_list_reads(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.3},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    now = _utcnow()
    await service.create_episodic_memory(
        user_id=user_id,
        summary="First memory",
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(days=1),
        importance_score=0.5,
        tags=["cognitive"],
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    second = await service.create_episodic_memory(
        user_id=user_id,
        summary="Second memory",
        source_type="analysis",
        source_id="src_2",
        occurred_at=now,
        importance_score=0.7,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_4"}],
    )

    prefs = await service.list_preferences(user_id)
    assert prefs["depth_preference"]["value"] == 0.8

    recent = await service.list_recent_episodic(user_id, limit=1)
    assert recent[0].id == second.id

    windowed = await service.list_recent_episodic(
        user_id, start=now - timedelta(hours=2), end=now + timedelta(hours=1)
    )
    assert len(windowed) == 1
    assert windowed[0].id == second.id
