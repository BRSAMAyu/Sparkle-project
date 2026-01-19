from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.memory import EpisodicMemory, MemoryPreference
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_memory_service_blocks_when_disabled(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_USER_MEMORY_CONTROLS", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    db_session.add(
        UserMemorySettings(
            user_id=user_id,
            enabled=False,
            allow_preferences=True,
            allow_goals=True,
            allow_episodic=True,
            capture_level="medium",
            blocked_pref_keys=[],
            blocked_sources=[],
        )
    )
    await db_session.commit()

    service = MemoryService(db_session)
    result = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.6},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    assert result is None

    query = await db_session.execute(
        select(MemoryPreference).where(MemoryPreference.user_id == user_id)
    )
    assert query.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_memory_service_blocks_source(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_USER_MEMORY_CONTROLS", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    db_session.add(
        UserMemorySettings(
            user_id=user_id,
            enabled=True,
            allow_preferences=True,
            allow_goals=True,
            allow_episodic=True,
            capture_level="medium",
            blocked_pref_keys=[],
            blocked_sources=["analysis"],
        )
    )
    await db_session.commit()

    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user_id,
        summary="Memory One",
        source_type="analysis",
        source_id="src_1",
        occurred_at=datetime.utcnow(),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    assert record is None

    query = await db_session.execute(
        select(EpisodicMemory).where(EpisodicMemory.user_id == user_id)
    )
    assert query.scalar_one_or_none() is None
