import hashlib
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


@pytest.mark.asyncio
async def test_conflict_resolver_load_records_stays_user_scoped(db_session):
    owner = await _create_user(db_session)
    other = await _create_user(db_session)
    owner_record = EpisodicMemory(
        user_id=owner.id,
        summary="owner record",
        source_type="chat",
        source_id="session-owner",
        source_lane="working_memory",
        subject_type="self",
        occurred_at=datetime(2026, 4, 21, 12, 0, 0),
        confidence=0.6,
        evidence_refs=[{"type": "chat_turn", "id": "owner"}],
        evidence_token="owner",
        semantic_key="owner:key",
    )
    foreign_record = EpisodicMemory(
        user_id=other.id,
        summary="foreign record",
        source_type="chat",
        source_id="session-foreign",
        source_lane="working_memory",
        subject_type="self",
        occurred_at=datetime(2026, 4, 21, 12, 5, 0),
        confidence=0.6,
        evidence_refs=[{"type": "chat_turn", "id": "foreign"}],
        evidence_token="foreign",
        semantic_key="foreign:key",
    )
    db_session.add_all([owner_record, foreign_record])
    await db_session.commit()

    records = await ConflictResolverService(db_session)._load_records(
        (owner_record.id, foreign_record.id),
        user_id=owner.id,
    )

    assert [record.id for record in records] == [owner_record.id]


# ---------------------------------------------------------------------------
# D1 死门：has_unresolved_conflict 曾用人类可读 topic 双向子串匹配 sha1 十六进制
# conflict_key（=semantic_key），数学上永不命中。修复后 topic 应对齐可读范围
# （left/right_summary、payload 里的 semantic_key），semantic key 应精确对齐。
# ---------------------------------------------------------------------------


def _sha1_semantic_key(text: str) -> str:
    # 复刻 MemoryInferredWriteLaneService 的生产写法：sha1(规范化句子)
    normalized = "".join(text.split()).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_has_unresolved_conflict_matches_topics_against_readable_scope(db_session):
    user = await _create_user(db_session)
    semantic_key = _sha1_semantic_key("我决定今晚早睡")
    assert semantic_key != "我决定今晚早睡"  # 生产形态：40 位十六进制，非可读文本
    db_session.add(
        UnresolvedConflict(
            user_id=user.id,
            conflict_key=semantic_key,
            left_summary="我决定今晚早睡",
            right_summary="昨晚我又熬夜到三点",
            left_lane="inferred_extraction",
            right_lane="inferred_extraction",
            left_payload={"semantic_key": semantic_key, "summary": "我决定今晚早睡"},
            right_payload={"semantic_key": semantic_key, "summary": "昨晚我又熬夜到三点"},
            surfaced_at=datetime(2026, 4, 21, 20, 0, 0),
        )
    )
    await db_session.commit()

    service = ConflictResolverService(db_session)
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("早睡",)) is True
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("熬夜",)) is True
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("早睡", "复习")) is True
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("健身",)) is False
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=()) is False


@pytest.mark.asyncio
async def test_has_unresolved_conflict_matches_semantic_keys_exactly(db_session):
    user = await _create_user(db_session)
    semantic_key = _sha1_semantic_key("我决定今晚早睡")
    db_session.add(
        UnresolvedConflict(
            user_id=user.id,
            conflict_key=semantic_key,
            left_summary="我决定今晚早睡",
            right_summary="昨晚我又熬夜到三点",
            left_lane="inferred_extraction",
            right_lane="inferred_extraction",
            surfaced_at=datetime(2026, 4, 21, 20, 0, 0),
        )
    )
    await db_session.commit()

    service = ConflictResolverService(db_session)
    assert (
        await service.has_unresolved_conflict(
            user_id=user.id,
            topic_keys=(),
            semantic_keys=(semantic_key,),
        )
        is True
    )
    assert (
        await service.has_unresolved_conflict(
            user_id=user.id,
            topic_keys=(),
            semantic_keys=(_sha1_semantic_key("无关事实"),),
        )
        is False
    )


@pytest.mark.asyncio
async def test_same_key_candidates_with_different_confidence_arbitrate_and_audit(db_session):
    """两条同 semantic_key、不同置信的候选必须被检出冲突并落仲裁审计。"""
    user = await _create_user(db_session)
    semantic_key = _sha1_semantic_key("今晚复习线代")
    existing = EpisodicMemory(
        user_id=user.id,
        summary="今晚复习线代到十点",
        source_type="chat",
        source_id="session-d1",
        source_lane="working_memory",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.55,
        evidence_refs=[{"type": "chat_turn", "id": "wm-d1"}],
        evidence_token="wm-d1",
        semantic_key=semantic_key,
    )
    db_session.add(existing)
    await db_session.commit()

    service = ConflictResolverService(db_session)
    candidate = ConflictCandidate(
        user_id=user.id,
        summary="今晚复习线代到十二点",
        source_lane="inferred_extraction",
        confidence=0.92,
        occurred_at=datetime(2026, 4, 21, 19, 0, 0),
        evidence_token="turn-d1",
        semantic_key=semantic_key,
        subject_type="commitment",
        evidence_refs=({"type": "chat_turn", "id": "turn-d1"},),
    )
    decision = service.resolve(candidate=candidate, existing_records=[existing])

    # 不同置信 → 确定性裁决（不需要用户投票），但冲突必须被检出且留下审计
    assert decision.action == "accept"
    assert decision.reason != "no_conflict"
    assert decision.loser_record_ids == (existing.id,)

    new_record = EpisodicMemory(
        user_id=user.id,
        summary="今晚复习线代到十二点",
        source_type="chat",
        source_id="session-d1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 19, 0, 0),
        confidence=0.92,
        evidence_refs=[{"type": "chat_turn", "id": "turn-d1"}],
        evidence_token="turn-d1",
        semantic_key=semantic_key,
    )
    db_session.add(new_record)
    await db_session.commit()
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)

    await db_session.refresh(existing)
    assert existing.retracted_at is not None  # 输者被撤回
    unresolved_rows = (await db_session.execute(select(UnresolvedConflict))).scalars().all()
    assert unresolved_rows == []  # 确定性裁决不进 pending_user 队列
    audits = (await db_session.execute(select(ConflictResolutionRecord))).scalars().all()
    assert any(
        audit.resolution_action == "accept"
        and audit.conflict_key == semantic_key
        and audit.resolution_reason == "candidate_overrides_lower_priority"
        for audit in audits
    )


@pytest.mark.asyncio
async def test_same_key_tie_candidates_surface_to_unresolved_conflicts_and_block_topic(db_session):
    """同 key 平级候选落 unresolved_conflicts 后，topic 门必须能拦住（原死门）。"""
    user = await _create_user(db_session)
    semantic_key = _sha1_semantic_key("准备周末和同学讨论复习计划")
    existing = EpisodicMemory(
        user_id=user.id,
        summary="准备周末和同学讨论复习计划",
        source_type="chat",
        source_id="session-d1-tie",
        source_lane="inferred_extraction",
        subject_type="relationship",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.88,
        evidence_refs=[{"type": "chat_turn", "id": "turn-tie-old"}],
        evidence_token="turn-tie-old",
        semantic_key=semantic_key,
    )
    db_session.add(existing)
    await db_session.commit()

    service = ConflictResolverService(db_session)
    candidate = ConflictCandidate(
        user_id=user.id,
        summary="准备周末和同学讨论复习计划",
        source_lane="inferred_extraction",
        confidence=0.88,
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        evidence_token="turn-tie-new",
        semantic_key=semantic_key,
        subject_type="relationship",
        evidence_refs=({"type": "chat_turn", "id": "turn-tie-new"},),
    )
    decision = service.resolve(candidate=candidate, existing_records=[existing])
    assert decision.action == "surface_to_user"
    await service.apply_live_decision(candidate=candidate, decision=decision)

    unresolved = (await db_session.execute(select(UnresolvedConflict))).scalar_one()
    assert unresolved.status == "pending_user"
    assert unresolved.conflict_key == semantic_key

    # 死门修复后：可读 topic（技能激活条件关键词）必须能命中 sha1 形态的 conflict_key
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("复习计划",)) is True
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("复习",)) is True
    assert await service.has_unresolved_conflict(user_id=user.id, topic_keys=("健身",)) is False


# ---------------------------------------------------------------------------
# D2 优先级兜底：未知 source_lane（如 aurora_calibration_receipt）曾被 fallback
# 判为最高档 explicit(4)，可压过 direct_capture。修复后未知 lane 落最低档。
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_known_lanes_keep_registered_priorities(db_session):
    service = ConflictResolverService(db_session)
    assert service._priority("direct_capture") == 4
    assert service._priority("user_confirmed") == 4
    assert service._priority("llm_extractor") == 2
    assert service._priority("llm_extraction") == 2
    assert service._priority("inferred_extraction") == 3
    assert service._priority("working_memory") == 1


@pytest.mark.asyncio
async def test_unknown_lane_falls_to_lowest_priority_and_loses_to_direct_capture(db_session):
    service = ConflictResolverService(db_session)
    # aurora_calibration_receipt：保留位红线样例（曾由 correction_feedback 写入，
    # V3-FIX-06 裁决=迁移写入点后保留为未登记 lane，登记完备性守卫见
    # test_memory_epistemic_contract.test_all_app_source_lane_literals_are_registered）
    assert service._priority("aurora_calibration_receipt") == 0
    assert service._priority("") == 0
    assert service._priority("some_future_lane") == 0

    user = await _create_user(db_session)
    existing = EpisodicMemory(
        user_id=user.id,
        summary="今晚只做一套真题",
        source_type="chat",
        source_id="session-d2",
        source_lane="direct_capture",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 21, 18, 0, 0),
        confidence=0.5,
        evidence_refs=[{"type": "chat_turn", "id": "direct-d2"}],
        evidence_token="direct-d2",
        semantic_key="commitment:real-exam-set",
    )
    db_session.add(existing)
    await db_session.commit()

    # 未知 lane 的候选即使更新、同置信，也不得压过已登记的 direct_capture 记录
    decision = service.resolve(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="今晚只做一套真题（校准回执）",
            source_lane="aurora_calibration_receipt",
            confidence=0.5,
            occurred_at=datetime(2026, 4, 21, 19, 0, 0),
            evidence_token="receipt-d2",
            semantic_key="commitment:real-exam-set",
            subject_type="commitment",
            evidence_refs=({"type": "chat_turn", "id": "receipt-d2"},),
        ),
        existing_records=[existing],
    )
    assert decision.action == "reject"
    assert decision.reason == "higher_priority_existing"
    assert decision.winner_lane == "direct_capture"
