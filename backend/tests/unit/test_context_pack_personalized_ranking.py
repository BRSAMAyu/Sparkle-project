from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.services.memory_rank_policy_service import MemoryRankPolicyService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_uses_personalized_weights(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PERSONALIZED_RANKING", True, raising=False)
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
        pref_key="stale_high_evidence",
        pref_value={"value": "x" * 40},
        evidence_refs=[{"type": "event", "id": "evt_1"}, {"type": "concept", "id": "c_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="fresh_lower_evidence",
        pref_value={"value": "y" * 40},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    await db_session.execute(
        text(
            "UPDATE memory_preferences SET updated_at = :ts WHERE user_id = :uid AND pref_key = :key"
        ),
        {
            "ts": datetime.utcnow() - timedelta(days=200),
            "uid": str(user_id),
            "key": "stale_high_evidence",
        },
    )
    await db_session.commit()

    policy_service = MemoryRankPolicyService(db_session)
    await policy_service.upsert_policy(
        scope_type="user",
        scope_key=str(user_id),
        weights={"evidence": 0.1, "freshness": 0.8, "correction": 0.1},
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 5, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "fresh_lower_evidence" in pack.preferences
    assert "stale_high_evidence" not in pack.preferences
