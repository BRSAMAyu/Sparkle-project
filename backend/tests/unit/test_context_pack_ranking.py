from datetime import UTC, datetime, timedelta
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest
from sqlalchemy import select

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_ranking_applied(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_EPISODIC", 10, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_GOALS", 10, raising=False)

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
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="response_style",
        pref_value={"value": "x"},
        evidence_refs=[{"type": "event", "id": "evt_1"}, {"type": "concept", "id": "c_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"value": "y"},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    result = await db_session.execute(
        select(MemoryPreference).where(
            MemoryPreference.user_id == user_id,
            MemoryPreference.pref_key == "response_style",
        )
    )
    stale_record = result.scalar_one()
    stale_record.updated_at = _utcnow() - timedelta(days=200)
    await db_session.commit()

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 10, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "learning_style" in pack.preferences
    assert "response_style" not in pack.preferences
    assert pack.metadata is not None
    assert "ranking" in pack.metadata


@pytest.mark.asyncio
async def test_context_pack_soft_caps(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_EPISODIC", 1, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_GOALS", 1, raising=False)

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
    for idx in range(3):
        await memory_service.create_goal(
            user_id=user_id,
            title=f"Goal {idx}",
            status="active",
            evidence_refs=[{"type": "event", "id": f"evt_goal_{idx}"}],
        )

    now = _utcnow()
    for idx in range(3):
        await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=f"Memory {idx}",
            source_type="analysis",
            source_id=f"src_{idx}",
            occurred_at=now - timedelta(hours=idx),
            importance_score=0.5,
            tags=["tag_a" if idx == 0 else "tag_b"],
            evidence_refs=[{"type": "event", "id": f"evt_epi_{idx}"}],
        )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert len(pack.goals) <= 1
    assert len(pack.episodic_memories) <= 1
