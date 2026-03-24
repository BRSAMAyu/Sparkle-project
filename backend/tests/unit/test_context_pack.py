from datetime import timezone, datetime, timedelta
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.core.intent_router import IntentRouter
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_budget_trimming(db_session):
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
        pref_key="depth_preference",
        pref_value={"value": "x" * 120},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="curiosity_preference",
        pref_value={"value": "y" * 120},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    await memory_service.create_goal(
        user_id=user_id,
        title="Goal A",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Goal B",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_4"}],
    )

    now = _utcnow()
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory A " + ("z" * 120),
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_5"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory B " + ("z" * 120),
        source_type="analysis",
        source_id="src_2",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.4,
        tags=["cognitive"],
        evidence_refs=[{"type": "event", "id": "evt_6"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 5, "goals": 5, "episodic": 5}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert pack.token_usage["preferences"] <= pack.budgets["preferences"]
    assert pack.token_usage["goals"] <= pack.budgets["goals"]
    assert pack.token_usage["episodic"] <= pack.budgets["episodic"]


@pytest.mark.asyncio
async def test_context_pack_intent_budget(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    scheduler = ContextBudgetScheduler(
        budgets={
            "chat": {"preferences": 5, "goals": 5, "episodic": 5},
            "planning": {"preferences": 1, "goals": 2, "episodic": 3},
        }
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="planning")

    assert pack.budgets["goals"] == 2
    assert pack.intent == "planning"

    router = IntentRouter()
    assert router.get_intent({"context": {"intent": "planning"}}) == "planning"


@pytest.mark.asyncio
async def test_context_pack_marks_consumed_memory_records(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)

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
    pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_consumed"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "depth_preference" in pack.preferences

    refreshed = await db_session.get(MemoryPreference, pref.id)
    assert refreshed is not None
    assert refreshed.last_consumed_at is not None
