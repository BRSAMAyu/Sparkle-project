from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock

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


@pytest.mark.asyncio
async def test_memory_preference_version_uses_global_max_after_retraction(db_session):
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
        pref_key="community_engagement_level",
        pref_value={"value": "moderate"},
        evidence_refs=[{"type": "event", "id": "evt_1", "schema_version": "event.v1"}],
    )
    second = await service.upsert_preference(
        user_id=user_id,
        pref_key="community_engagement_level",
        pref_value={"value": "high"},
        evidence_refs=[{"type": "event", "id": "evt_2", "schema_version": "event.v1"}],
    )

    second.retracted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db_session.commit()

    third = await service.upsert_preference(
        user_id=user_id,
        pref_key="community_engagement_level",
        pref_value={"value": "low"},
        evidence_refs=[{"type": "event", "id": "evt_3", "schema_version": "event.v1"}],
    )

    assert first.version == 1
    assert second.version == 2
    assert third.version == 3


@pytest.mark.asyncio
async def test_create_episodic_memory_falls_back_when_vector_runtime_unavailable(monkeypatch):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = RuntimeError("vector.so unavailable")

    enqueue = AsyncMock()
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", enqueue)

    service = MemoryService(db)
    monkeypatch.setattr(service, "_allow_write", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_advanced_features_enabled", AsyncMock(return_value=False))
    record = await service.create_episodic_memory(
        user_id=uuid4(),
        summary="memory summary",
        source_type="analysis",
        source_id="analysis-1",
        occurred_at=datetime.utcnow(),
        importance_score=0.7,
        tags=["analysis"],
        evidence_refs=[{"type": "event", "id": "evt_1", "schema_version": "event.v1"}],
    )

    assert record is None
    db.rollback.assert_awaited_once()
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_episodic_memory_retries_without_embedding_when_vector_runtime_unavailable(monkeypatch):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = [RuntimeError("vector.so unavailable"), None]

    enqueue = AsyncMock()
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", enqueue)

    service = MemoryService(db)
    monkeypatch.setattr(service, "_allow_write", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_advanced_features_enabled", AsyncMock(return_value=False))
    record = await service.create_episodic_memory(
        user_id=uuid4(),
        summary="memory summary",
        source_type="analysis",
        source_id="analysis-1",
        occurred_at=datetime.utcnow(),
        importance_score=0.7,
        tags=["analysis"],
        evidence_refs=[{"type": "event", "id": "evt_1", "schema_version": "event.v1"}],
        embedding=[0.1, 0.2, 0.3],
    )

    assert record is not None
    assert db.commit.await_count == 2
    assert db.rollback.await_count == 1
    assert db.add.call_count == 2
    assert db.add.call_args_list[0].args[0].embedding == [0.1, 0.2, 0.3]
    assert db.add.call_args_list[1].args[0].embedding is None
    enqueue.assert_awaited_once()
