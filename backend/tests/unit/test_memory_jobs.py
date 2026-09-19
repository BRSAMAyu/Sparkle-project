from datetime import timezone, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.models.event import TrackingEvent
from app.models.memory import EpisodicMemory, MemoryPreference
from app.models.user import User
from app.services.memory_jobs import MemoryJobsService
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_memory_jobs_evidence_health_marks_missing(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_EVIDENCE_HEALTH_JOB", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    event = TrackingEvent(
        event_id="evt_job_missing",
        user_id=user_id,
        event_type="test",
        schema_version="event.v1",
        source="unit",
        ts_ms=int(_utcnow().timestamp() * 1000),
        entities=None,
        payload=None,
        received_at=_utcnow(),
    )
    db_session.add(event)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    episodic = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Job missing event",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["job"],
        evidence_refs=[{"type": "event", "id": "evt_job_missing"}],
    )

    event.deleted_at = _utcnow()
    await db_session.commit()

    service = MemoryJobsService(db_session)
    await service.run_evidence_health_job(limit_per_type=10)

    await db_session.refresh(episodic)
    assert episodic.evidence_missing is True
    assert episodic.evidence_checked_at is not None


@pytest.mark.asyncio
async def test_memory_jobs_repair_restores_evidence(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_EVIDENCE_HEALTH_JOB", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    event = TrackingEvent(
        event_id="evt_job_restore",
        user_id=user_id,
        event_type="test",
        schema_version="event.v1",
        source="unit",
        ts_ms=int(_utcnow().timestamp() * 1000),
        entities=None,
        payload=None,
        received_at=_utcnow(),
    )
    db_session.add(event)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    episodic = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Restore event",
        source_type="analysis",
        source_id="src_2",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["job"],
        evidence_refs=[{"type": "event", "id": "evt_job_restore"}],
    )
    episodic.evidence_missing = True
    await db_session.commit()

    service = MemoryJobsService(db_session)
    await service.run_repair_job(limit=10)

    await db_session.refresh(episodic)
    assert episodic.evidence_missing is False
    assert episodic.evidence_snapshot is not None


@pytest.mark.asyncio
async def test_memory_jobs_governance_archives_stale_unconsumed_memory(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_BEHAVIOR_DECAY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_DECAY", False, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    stale_pref = MemoryPreference(
        user_id=user_id,
        pref_key="old_preference",
        pref_value={"value": "过时偏好"},
        version=1,
        confidence=0.2,
        evidence_score=0.2,
        last_consumed_at=_utcnow() - timedelta(days=95),
        evidence_refs=[{"type": "event", "id": "evt_old"}],
    )
    db_session.add(stale_pref)
    await db_session.commit()

    service = MemoryJobsService(db_session)
    summary = await service.run_decay_job(window_days=14)

    await db_session.refresh(stale_pref)
    assert stale_pref.archived_at is not None
    assert summary["detail"]["memory_governance_archived"] == 1


@pytest.mark.asyncio
async def test_episodic_decay_policies_consume_7d_policy(db_session):
    """D4 回归：decay_policy=7d（时敏记忆）此前无任何消费者执行衰减；
    提取后的 apply_episodic_decay_policies 必须按半衰期衰减并归档，
    而需 due_at 调度的 due_at+7d（承诺类）仍为 V3 待办、保持原样。"""
    import math

    from app.services.memory_jobs import apply_episodic_decay_policies

    user_id = uuid4()
    user = User(
        id=user_id, username=f"user_{user_id.hex[:8]}", email=f"{user_id.hex[:8]}@example.com", hashed_password="test"
    )
    db_session.add(user)
    await db_session.flush()

    now = _utcnow()

    async def _seed(policy: str, age_days: float, importance: float, token: str):
        record = EpisodicMemory(
            user_id=user_id,
            summary=f"decay probe {token}",
            source_type="chat",
            source_id=f"session-{token}",
            source_lane="inferred_extraction",
            subject_type="self",
            occurred_at=now - timedelta(days=age_days),
            importance_score=importance,
            confidence=0.9,
            evidence_refs=[{"type": "chat_turn", "id": token}],
            evidence_token=token,
            decay_policy=policy,
        )
        db_session.add(record)
        return record

    # 7d 策略 + 60 天前：0.8 * 0.5^(60/7) ≈ 0.002 < 0.15 → 衰减且归档
    probe_7d = await _seed("7d", 60, 0.8, "decay-7d-old")
    # 7d 策略 + 2 天前：0.8 * 0.5^(2/7) ≈ 0.735 → 仅衰减不归档
    probe_7d_fresh = await _seed("7d", 2, 0.8, "decay-7d-fresh")
    # 30d 策略 + 10 天前：0.8 * 0.5^(10/30) ≈ 0.635 → 仅衰减不归档（既有行为不回归）
    probe_30d = await _seed("30d", 10, 0.8, "decay-30d")
    # due_at+7d：V3 待办（需按 due_at 调度），本次必须保持原样
    probe_due = await _seed("due_at+7d", 60, 0.8, "decay-due")
    await db_session.commit()

    summary = await apply_episodic_decay_policies(db_session)

    assert summary["decayed"] == 3  # due_at+7d 不动
    assert summary["archived"] == 1

    await db_session.refresh(probe_7d)
    expected = round(0.8 * math.pow(0.5, 60 / 7), 4)
    assert probe_7d.importance_score == expected
    assert probe_7d.archived_at is not None

    await db_session.refresh(probe_7d_fresh)
    assert probe_7d_fresh.archived_at is None
    assert probe_7d_fresh.importance_score == round(0.8 * math.pow(0.5, 2 / 7), 4)

    await db_session.refresh(probe_30d)
    assert probe_30d.importance_score == round(0.8 * math.pow(0.5, 10 / 30), 4)
    assert probe_30d.archived_at is None

    await db_session.refresh(probe_due)
    assert probe_due.importance_score == 0.8
    assert probe_due.archived_at is None
