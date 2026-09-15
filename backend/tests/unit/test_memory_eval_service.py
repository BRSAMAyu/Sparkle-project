from datetime import timezone, datetime, timedelta
from pathlib import Path
from uuid import UUID

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.models.user import User
from app.services.memory_eval_service import MemoryEvalService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_memory_eval_service_runs_dataset(db_session):
    dataset_path = Path("backend/tests/fixtures/ltm_eval_sample.jsonl")
    user_id = UUID("11111111-1111-1111-1111-111111111111")

    user = User(
        id=user_id,
        username="eval_user",
        email="eval@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"style": "visual"},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="curiosity_preference",
        pref_value={"value": 0.9},
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="schedule_preferences",
        pref_value={"weekday": "morning"},
        evidence_refs=[{"type": "event", "id": "evt_4"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="language",
        pref_value={"value": "en"},
        evidence_refs=[{"type": "event", "id": "evt_5"}],
    )

    await service.create_goal(
        user_id=user_id,
        title="Math mastery",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_6"}],
    )
    await service.create_goal(
        user_id=user_id,
        title="Plan weekly review",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_7"}],
    )
    await service.create_goal(
        user_id=user_id,
        title="Vocabulary sprint",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_8"}],
    )

    now = _utcnow()
    await service.create_episodic_memory(
        user_id=user_id,
        summary="Had a study session on algebra",
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(days=2),
        importance_score=0.6,
        tags=["learning"],
        evidence_refs=[{"type": "event", "id": "evt_9"}],
    )
    await service.create_episodic_memory(
        user_id=user_id,
        summary="Did extra practice on geometry",
        source_type="analysis",
        source_id="src_2",
        occurred_at=now - timedelta(days=10),
        importance_score=0.4,
        tags=["practice"],
        evidence_refs=[{"type": "event", "id": "evt_10"}],
    )
    await service.create_episodic_memory(
        user_id=user_id,
        summary="Reviewed flashcards for vocabulary",
        source_type="analysis",
        source_id="src_3",
        occurred_at=now - timedelta(days=5),
        importance_score=0.5,
        tags=["vocab"],
        evidence_refs=[{"type": "event", "id": "evt_11"}],
    )

    eval_service = MemoryEvalService(db_session)
    summary = await eval_service.run_dataset(dataset_path, threshold=0.0)

    assert summary["case_count"] >= 1
    assert summary["avg_score"] >= 0.0
    first_case = summary["cases"][0]
    metrics = first_case["metrics"]
    assert "pref_hit_rate" in metrics
    assert "evidence_quality" in metrics
