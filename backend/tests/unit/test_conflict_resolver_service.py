from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.aurora_stage20 import ConflictResolutionRecord, UnresolvedConflict
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services.conflict_resolver_service import ConflictCandidate, ConflictResolverService
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate, MemoryInferredWriteLaneService


async def _create_user(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_conflict_resolver_accepts_rule_candidate_over_working_memory_record(db_session):
    user = await _create_user(db_session)
    existing = EpisodicMemory(
        user_id=user.id,
        summary="今晚复习线代",
        source_type="chat",
        source_id="session-1",
        source_lane="working_memory",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.55,
        evidence_refs=[{"type": "chat_turn", "id": "wm-1"}],
        evidence_token="wm-1",
        semantic_key="commitment:review-linear-algebra",
    )
    db_session.add(existing)
    await db_session.commit()

    service = ConflictResolverService(db_session)
    decision = service.resolve(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="今晚复习线代",
            source_lane="inferred_extraction",
            confidence=0.92,
            occurred_at=datetime(2026, 4, 21, 19, 0, 0),
            evidence_token="turn-1",
            semantic_key="commitment:review-linear-algebra",
            subject_type="commitment",
            evidence_refs=({"type": "chat_turn", "id": "turn-1"},),
        ),
        existing_records=[existing],
    )

    assert decision.action == "accept"
    assert decision.reason == "candidate_overrides_lower_priority"
    assert decision.loser_record_ids == (existing.id,)


@pytest.mark.asyncio
async def test_conflict_resolver_surfaces_tie_for_user_arbitration(db_session):
    user = await _create_user(db_session)
    existing = EpisodicMemory(
        user_id=user.id,
        summary="准备周末和同学讨论复习计划",
        source_type="chat",
        source_id="session-2",
        source_lane="inferred_extraction",
        subject_type="relationship",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.88,
        evidence_refs=[{"type": "chat_turn", "id": "turn-old"}],
        evidence_token="turn-old",
        semantic_key="relationship:study-plan",
    )
    db_session.add(existing)
    await db_session.commit()

    service = ConflictResolverService(db_session)
    decision = service.resolve(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="准备周末和同学讨论复习计划",
            source_lane="inferred_extraction",
            confidence=0.88,
            occurred_at=datetime(2026, 4, 21, 18, 0, 0),
            evidence_token="turn-new",
            semantic_key="relationship:study-plan",
            subject_type="relationship",
            evidence_refs=({"type": "chat_turn", "id": "turn-new"},),
        ),
        existing_records=[existing],
    )

    assert decision.action == "surface_to_user"
    await service.apply_live_decision(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="准备周末和同学讨论复习计划",
            source_lane="inferred_extraction",
            confidence=0.88,
            occurred_at=datetime(2026, 4, 21, 18, 0, 0),
            evidence_token="turn-new",
            semantic_key="relationship:study-plan",
            subject_type="relationship",
            evidence_refs=({"type": "chat_turn", "id": "turn-new"},),
        ),
        decision=decision,
    )

    unresolved = (await db_session.execute(select(UnresolvedConflict))).scalar_one()
    assert unresolved.status == "pending_user"
    assert unresolved.left_summary == "准备周末和同学讨论复习计划"


@pytest.mark.asyncio
async def test_conflict_resolver_user_arbitration_materializes_selected_candidate(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    user = await _create_user(db_session)
    existing = EpisodicMemory(
        user_id=user.id,
        summary="今晚先写英语作文",
        source_type="chat",
        source_id="session-3",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.75,
        evidence_refs=[{"type": "chat_turn", "id": "turn-old"}],
        evidence_token="turn-old",
        semantic_key="commitment:english-essay",
    )
    db_session.add(existing)
    await db_session.commit()

    service = ConflictResolverService(db_session)
    decision = service.resolve(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="今晚先改英语作文提纲",
            source_lane="inferred_extraction",
            confidence=0.75,
            occurred_at=datetime(2026, 4, 21, 18, 0, 0),
            evidence_token="turn-new",
            semantic_key="commitment:english-essay",
            subject_type="commitment",
            evidence_refs=({"type": "chat_turn", "id": "turn-new"},),
        ),
        existing_records=[existing],
    )
    await service.apply_live_decision(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="今晚先改英语作文提纲",
            source_lane="inferred_extraction",
            confidence=0.75,
            occurred_at=datetime(2026, 4, 21, 18, 0, 0),
            evidence_token="turn-new",
            semantic_key="commitment:english-essay",
            subject_type="commitment",
            evidence_refs=({"type": "chat_turn", "id": "turn-new"},),
        ),
        decision=decision,
    )
    unresolved = (await db_session.execute(select(UnresolvedConflict))).scalar_one()

    resolved = await service.arbitrate_unresolved_conflict(
        user_id=user.id,
        conflict_id=unresolved.id,
        selection="left",
    )

    assert resolved is not None
    assert resolved.selected_side == "left"
    records = (await db_session.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == user.id))).scalars().all()
    assert len(records) == 2
    assert any(record.summary == "今晚先改英语作文提纲" for record in records)
    audit = (
        await db_session.execute(
            select(ConflictResolutionRecord).where(
                ConflictResolutionRecord.resolution_reason == "user_arbitrated"
            )
        )
    ).scalar_one()
    assert audit is not None


@pytest.mark.asyncio
async def test_memory_inferred_write_lane_shadow_mode_preserves_legacy_blocking_behavior(db_session, monkeypatch):
    user = await _create_user(db_session)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE", True, raising=False)
    monkeypatch.setattr(settings, "MEMORY_INFERRED_MIN_CONFIDENCE", 0.6, raising=False)

    existing = EpisodicMemory(
        user_id=user.id,
        summary="今晚复习概率论",
        source_type="chat",
        source_id="session-wm",
        source_lane="working_memory",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.4,
        evidence_refs=[{"type": "chat_turn", "id": "wm"}],
        evidence_token="wm",
        semantic_key="commitment:probability",
    )
    db_session.add(existing)
    await db_session.commit()

    lane = MemoryInferredWriteLaneService(db_session)
    record = await lane.write_candidate_to_l1(
        user_id=user.id,
        session_id=uuid4(),
        candidate=InferredEpisodicCandidate(
            candidate_text="今晚复习概率论",
            subject_type="commitment",
            confidence=0.9,
            evidence_token="turn-shadow",
            decay_policy="7d",
            source_lane="inferred_extraction",
            semantic_key="commitment:probability",
            evidence_refs=[{"type": "chat_turn", "id": "turn-shadow"}],
            occurred_at=datetime(2026, 4, 21, 19, 0, 0),
            due_at=None,
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=None,
        ),
        force_write=True,
    )

    assert record is None
    audits = (await db_session.execute(select(ConflictResolutionRecord))).scalars().all()
    assert any(audit.resolution_reason.startswith("shadow_compare:") for audit in audits)
