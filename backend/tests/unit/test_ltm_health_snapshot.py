from datetime import timezone, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.core.business_metrics import CONTEXT_PACK_BUILD, CONTEXT_PACK_OVER_BUDGET
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory, MemoryCorrection
from app.models.user import User
from app.services.ltm_health_snapshot import LtmHealthSnapshotService


@pytest.mark.asyncio
async def test_ltm_health_snapshot_keys(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)

    pref = MemoryPreference(
        user_id=user_id,
        pref_key="feedback_tone",
        pref_value={"value": "direct"},
        version=1,
        evidence_refs=[{"type": "event", "id": "evt_1"}],
        evidence_missing=False,
        evidence_score=0.7,
        correction_count=2,
    )
    goal = MemoryGoal(
        user_id=user_id,
        title="Ship quality report",
        status="active",
        evidence_refs=[],
        evidence_score=0.4,
        correction_count=0,
    )
    episodic = EpisodicMemory(
        user_id=user_id,
        summary="Snapshot test",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.4,
        evidence_refs=[{"type": "event", "id": "evt_2"}],
        evidence_score=0.5,
        correction_count=1,
    )
    db_session.add_all([pref, goal, episodic])
    await db_session.commit()

    db_session.add_all(
        [
            MemoryCorrection(
                user_id=user_id,
                memory_type="preference",
                memory_id=pref.id,
                action="lower_confidence",
                reason="user_feedback",
            ),
            MemoryCorrection(
                user_id=user_id,
                memory_type="preference",
                memory_id=pref.id,
                action="lower_confidence",
                reason="user_feedback",
            ),
        ]
    )
    await db_session.commit()

    CONTEXT_PACK_BUILD.labels(intent="chat").inc()
    CONTEXT_PACK_OVER_BUDGET.labels(intent="chat", section="episodic").inc()

    service = LtmHealthSnapshotService(db_session)
    snapshot = await service.compute_snapshot()

    assert "evidence_missing_rate" in snapshot
    assert "avg_evidence_score" in snapshot
    assert "avg_correction_count" in snapshot
    assert "pack_build_count" in snapshot
    assert "pack_over_budget_rate" in snapshot
    assert "top_corrected" in snapshot
    assert "job_runs_24h" in snapshot
