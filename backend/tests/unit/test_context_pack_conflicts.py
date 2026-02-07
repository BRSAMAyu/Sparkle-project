from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_conflicts_metadata(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
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
        pref_key="feedback_tone",
        pref_value={"value": "direct"},
        evidence_refs=[{"type": "event", "id": "evt_1"}, {"type": "concept", "id": "c_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="feedback_tone",
        pref_value={"value": "soft"},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    await memory_service.create_goal(
        user_id=user_id,
        title="Learn Rust",
        status="active",
        target_date=date.today(),
        evidence_refs=[{"type": "event", "id": "evt_goal_1"}, {"type": "concept", "id": "c_2"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="learn rust",
        status="active",
        target_date=date.today(),
        evidence_refs=[{"type": "event", "id": "evt_goal_2"}],
    )

    now = _utcnow()
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Completed the sprint planning session",
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.5,
        tags=["work"],
        evidence_refs=[{"type": "event", "id": "evt_ep_1"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Completed the sprint planning session with the team",
        source_type="analysis",
        source_id="src_2",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.5,
        tags=["work"],
        evidence_refs=[{"type": "event", "id": "evt_ep_2"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert pack.metadata is not None
    assert pack.metadata.get("conflicts")
    assert pack.preferences["feedback_tone"]["value"] == "direct"

    # Conflict resolution suppresses duplicate/conflicting items.
    # Current behavior keeps at most one canonical item after dedupe.
    assert len(pack.goals) <= 1
    assert len(pack.episodic_memories) <= 1

    # Verify conflicts were detected
    conflicts = pack.metadata.get("conflicts", [])
    goal_conflicts = [c for c in conflicts if c.get("type") == "goal"]
    episodic_conflicts = [c for c in conflicts if c.get("type") == "episodic"]
    assert len(goal_conflicts) > 0, "Expected goal conflicts to be detected"
    assert len(episodic_conflicts) > 0, "Expected episodic conflicts to be detected"
