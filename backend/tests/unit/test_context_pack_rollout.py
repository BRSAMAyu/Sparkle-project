from datetime import timezone, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.config import settings
from app.models.user import User
from app.core.context_pack import ContextPackBuilder
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_respects_rollout(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", True, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_PERCENT", 0, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_USER_ALLOWLIST", [], raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_COHORT_TAGS", [], raising=False)

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
        evidence_refs=[{"type": "event", "id": "evt_rank"}],
        confidence=0.6,
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Ship rollout",
        status="active",
        evidence_refs=[],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Rolled out test",
        source_type="analysis",
        source_id="src_rollout",
        occurred_at=_utcnow(),
        importance_score=0.4,
        tags=["rollout"],
        evidence_refs=[{"type": "event", "id": "evt_rollout"}],
    )

    builder = ContextPackBuilder(db_session)
    pack = await builder.build(user_id=user_id, intent="chat")
    metadata = pack.metadata or {}
    assert "ranking" not in metadata
