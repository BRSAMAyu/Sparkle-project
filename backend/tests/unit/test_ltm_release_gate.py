from datetime import datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.core.business_metrics import LTM_EVAL_AVG_SCORE, LTM_EVAL_TOTAL
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.ltm_release_gate import LtmReleaseGate
from app.services.memory_jobs import MemoryJobsService


@pytest.mark.asyncio
async def test_release_gate_passes_with_metrics(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_EVIDENCE_HEALTH_JOB", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_BUDGET_TUNING", False, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_EVIDENCE_MISSING_THRESHOLD", 1.0, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_EVAL_THRESHOLD", 0.6, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_JOB_SUCCESS_THRESHOLD", 0.5, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    db_session.add(
        MemoryPreference(
            user_id=user_id,
            pref_key="feedback_tone",
            pref_value={"value": "direct"},
            version=1,
            evidence_refs=[{"type": "event", "id": "evt_1"}],
            evidence_missing=False,
        )
    )
    await db_session.commit()

    LTM_EVAL_AVG_SCORE.set(0.9)
    LTM_EVAL_TOTAL.labels(status="ok").inc()

    job_service = MemoryJobsService(db_session)
    await job_service.run_evidence_health_job(limit_per_type=10)

    gate = LtmReleaseGate(db_session)
    result = await gate.check()
    assert result.ok is True
    assert result.reasons == []


@pytest.mark.asyncio
async def test_release_gate_fails_without_eval(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BUDGET_TUNING", False, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_EVIDENCE_MISSING_THRESHOLD", 0.5, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_EVAL_THRESHOLD", 0.6, raising=False)
    monkeypatch.setattr(settings, "LTM_RELEASE_JOB_SUCCESS_THRESHOLD", 0.5, raising=False)
    LTM_EVAL_AVG_SCORE.set(0)
    LTM_EVAL_TOTAL._metrics.clear()  # type: ignore[attr-defined]

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    db_session.add(
        MemoryPreference(
            user_id=user_id,
            pref_key="feedback_tone",
            pref_value={"value": "direct"},
            version=1,
            evidence_refs=[{"type": "event", "id": "evt_1"}],
            evidence_missing=False,
        )
    )
    await db_session.commit()

    gate = LtmReleaseGate(db_session)
    result = await gate.check()
    assert result.ok is False
    assert any(
        reason in result.reasons
        for reason in ("ltm_eval_score_unavailable", "ltm_eval_below_threshold")
    )
