from uuid import uuid4

import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock

from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_memory_preference_version_chain(db_session):
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
    first = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.6},
        evidence_refs=[{"type": "event", "id": "evt_1", "schema_version": "event.v1"}],
        confidence=0.7,
    )
    second = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "event", "id": "evt_2", "schema_version": "event.v1"}],
        confidence=0.8,
    )

    result = await db_session.execute(
        select(MemoryPreference).where(MemoryPreference.id == first.id)
    )
    refreshed_first = result.scalar_one()

    assert first.version == 1
    assert second.version == 2
    assert refreshed_first.replaced_by_id == second.id


@pytest.mark.asyncio
async def test_memory_preference_update_enqueues_evolution_update(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    enqueue = AsyncMock()
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", enqueue)

    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "event", "id": "evt_1", "schema_version": "event.v1"}],
        confidence=0.7,
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.2},
        evidence_refs=[{"type": "event", "id": "evt_2", "schema_version": "event.v1"}],
        confidence=0.8,
    )

    assert enqueue.await_count == 2
    payload = enqueue.await_args_list[-1].args[1]
    assert payload["category"] == "evolution"
    assert payload["metadata"]["evolution_kind"] == "preference_learning"
    assert "简洁概览" in payload["description"]
