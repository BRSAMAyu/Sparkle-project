"""M-04 矛盾仲裁矩阵与修复钉子（红绿基线测试）。

覆盖：
1. priority tuple 与 TEMPORAL/SCOPE/SOURCE/INFERENCE 四类别仲裁矩阵（≥30 组，
   CONFLICT_RESOLVER.md §2-§4）；
2. clarification 路径：高信息增益且不确定 → 显式澄清输出（ask-once），
   钉死「不静默选」；
3. V3-FIX-10 前置验收（M-01 REVIEW_RECEIPT_2 F2/F4/F6/F7）：
   - F2: apply_live_decision 生命周期过滤 + 行锁 + 幂等重放；
   - F4: arbitrate_unresolved_conflict 补 epoch bump + memory.invalidated
     + 仲裁败者 SUPERSEDED 语义对称 + 重放幂等；
   - F6: 偏好 provenance 显式 source_type 权威（机器/人类边界显式化）；
   - F7: 守卫跳过计数指标。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.models.aurora_stage20 import ConflictResolutionRecord, UnresolvedConflict
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.services.conflict_resolver_service import (
    CONFLICT_RESOLVER_VERSION,
    ConflictCandidate,
    ConflictResolverService,
)
from app.services.memory_epistemic_contract import preference_write_provenance

# ---------------------------------------------------------------------------
# 测试基建（hermetic：sqlite + FakeRedis，绝不碰 dev Redis/PG）
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key)
                deleted += 1
        return deleted


_OUTBOX_DDL = [
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id CHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        sequence_number INTEGER NOT NULL,
        payload JSON NOT NULL,
        metadata JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
]


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


async def _user(db_session) -> User:
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


def _t(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 9, day, hour)


async def _episodic(
    db_session,
    user: User,
    summary: str,
    *,
    lane: str = "inferred_extraction",
    source_type: str = "chat",
    confidence: float = 0.8,
    occurred_at: datetime | None = None,
    day: int | None = None,
    decay_policy: str | None = None,
    due_at: datetime | None = None,
    entity_hash: str | None = None,
    epistemic_class: str | None = None,
    semantic_key: str = "sk:test",
) -> EpisodicMemory:
    record = EpisodicMemory(
        user_id=user.id,
        summary=summary,
        source_type=source_type,
        source_id="session-x",
        source_lane=lane,
        subject_type="commitment",
        occurred_at=occurred_at or (_t(day) if day is not None else _t(1)),
        confidence=confidence,
        evidence_refs=[{"type": "chat_turn", "id": f"ev-{uuid4().hex[:6]}"}],
        evidence_token=f"tok-{uuid4().hex[:8]}",
        semantic_key=semantic_key,
        decay_policy=decay_policy,
        due_at=due_at,
        mentioned_entity_hash=entity_hash,
        epistemic_class=epistemic_class,
    )
    db_session.add(record)
    await db_session.commit()
    return record


def _cand(
    user: User,
    summary: str,
    *,
    lane: str = "inferred_extraction",
    source_type: str = "chat",
    confidence: float = 0.8,
    occurred_at: datetime | None = None,
    day: int | None = None,
    decay_policy: str | None = None,
    due_at: datetime | None = None,
    entity_hash: str | None = None,
    epistemic_class: str | None = None,
    semantic_key: str = "sk:test",
) -> ConflictCandidate:
    return ConflictCandidate(
        user_id=user.id,
        summary=summary,
        source_lane=lane,
        source_type=source_type,
        confidence=confidence,
        occurred_at=occurred_at or (_t(day) if day is not None else _t(1)),
        evidence_token=f"cand-{uuid4().hex[:8]}",
        semantic_key=semantic_key,
        subject_type="commitment",
        evidence_refs=({"type": "chat_turn", "id": "turn-new"},),
        due_at=due_at,
        decay_policy=decay_policy,
        mentioned_entity_hash=entity_hash,
        epistemic_class=epistemic_class,
    )


def _spec_kwargs(spec: dict) -> dict:
    """Matrix spec keys (conf/day/decay/entity/epistemic) → helper kwargs."""
    spec = dict(spec)
    out: dict = {}
    keymap = {
        "lane": "lane",
        "source_type": "source_type",
        "conf": "confidence",
        "day": "day",
        "decay": "decay_policy",
        "due": "due_at",
        "entity": "entity_hash",
        "epistemic": "epistemic_class",
    }
    for src, dst in keymap.items():
        if src in spec:
            out[dst] = spec[src]
    return out


def _resolver(db_session) -> ConflictResolverService:
    return ConflictResolverService(db_session, redis_client=FakeRedis())


async def _epoch(db_session, user: User) -> int:
    row = (
        await db_session.execute(select(UserMemorySettings).where(UserMemorySettings.user_id == user.id))
    ).scalar_one_or_none()
    return int(row.memory_epoch) if row is not None else 1


async def _invalidation_events(db_session) -> list[dict]:
    rows = (
        await db_session.execute(text("SELECT payload FROM event_outbox WHERE event_type = 'memory.invalidated'"))
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


# ---------------------------------------------------------------------------
# 1. 四类别仲裁矩阵（≥30 组）
# ---------------------------------------------------------------------------

# 每行：(场景名, 期望类别, 期望 action, 期望 reason, 期望败者数, candidate spec, record specs)
# spec 键：lane/source_type/conf/day/decay/due/entity/epistemic/summary
_M = {
    "lane": "inferred_extraction",
    "source_type": "chat",
    "conf": 0.8,
    "day": 2,
    "decay": None,
    "due": None,
    "entity": None,
    "epistemic": None,
}


def _spec(**over):
    base = dict(_M)
    base.update(over)
    return base


MATRIX: list[tuple[str, str, str, str, int, dict, list[dict]]] = [
    # --- TEMPORAL_CHANGE：同类同档，时间/证据决定 --------------------------------
    (
        "temporal.newer_rule_beats_older",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(),
        [_spec(day=1, conf=0.5)],
    ),
    (
        "temporal.newer_lower_conf_still_wins_recency_first",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(conf=0.3),
        [_spec(day=1, conf=0.95)],
    ),
    (
        "temporal.older_candidate_loses",
        "TEMPORAL_CHANGE",
        "reject",
        "higher_priority_existing",
        0,
        _spec(day=1),
        [_spec(day=2)],
    ),
    (
        "temporal.user_statement_changed_newer_wins",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="direct_capture", source_type="user_registered", day=2, conf=0.5),
        [_spec(lane="direct_capture", source_type="user_registered", day=1, conf=0.95)],
    ),
    (
        "temporal.same_time_confidence_decides",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(conf=0.9),
        [_spec(conf=0.6)],
    ),
    (
        "temporal.same_time_lower_conf_loses",
        "TEMPORAL_CHANGE",
        "reject",
        "higher_priority_existing",
        0,
        _spec(conf=0.4),
        [_spec(conf=0.9)],
    ),
    (
        "temporal.working_memory_recency",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="working_memory"),
        [_spec(lane="working_memory", day=1, conf=0.99)],
    ),
    (
        "temporal.tier_beats_recency_within_class",
        "TEMPORAL_CHANGE",
        "reject",
        "higher_priority_existing",
        0,
        _spec(lane="llm_extractor", day=3),
        [_spec(lane="inferred_extraction", day=1)],
    ),
    # --- SCOPE_DIFFERENCE：范围不同，两者都真，可共存 ----------------------------
    (
        "scope.today_candidate_vs_global_record",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(decay="today"),
        [_spec()],
    ),
    (
        "scope.bounded_candidate_vs_global_record",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(due=datetime(2026, 9, 5)),
        [_spec()],
    ),
    (
        "scope.global_candidate_vs_today_record",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(),
        [_spec(decay="1d", day=1)],
    ),
    (
        "scope.today_candidate_vs_bounded_record",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(decay="today"),
        [_spec(due=datetime(2026, 9, 10))],
    ),
    (
        "scope.entity_anchors_differ",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(entity="ent-a"),
        [_spec(entity="ent-b", day=1)],
    ),
    (
        "scope.soft_decay_is_not_time_scope",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(decay="30d"),
        [_spec(decay="7d", day=1)],
    ),
    # --- SOURCE_DISAGREEMENT：用户事实 vs 系统观察/结果 ---------------------------
    (
        "source.user_fact_beats_newer_observation",
        "SOURCE_DISAGREEMENT",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="direct_capture", source_type="user_registered", day=1, conf=0.3),
        [_spec(lane="direct_capture", source_type="chat_turn", day=3, conf=0.99)],
    ),
    (
        "source.observation_loses_to_older_fact",
        "SOURCE_DISAGREEMENT",
        "reject",
        "higher_priority_existing",
        0,
        _spec(lane="direct_capture", source_type="chat_turn", day=3, conf=0.99),
        [_spec(lane="direct_capture", source_type="user_registered", day=1, conf=0.3)],
    ),
    (
        "source.user_confirmed_beats_observation",
        "SOURCE_DISAGREEMENT",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="user_confirmed", day=1, conf=0.5),
        [_spec(lane="direct_capture", source_type="chat_turn", day=3, conf=0.9)],
    ),
    (
        "source.observation_vs_observation_temporal",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="direct_capture", source_type="chat_turn", day=2),
        [_spec(lane="direct_capture", source_type="chat_turn", day=1)],
    ),
    (
        "source.user_corrected_again",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="user_confirmed", day=2),
        [_spec(lane="user_confirmed", day=1)],
    ),
    # --- INFERENCE_CONTRADICTION：明确事实反驳推断 -------------------------------
    (
        "inference.explicit_correction_beats_old_inference",
        "INFERENCE_CONTRADICTION",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="direct_capture", source_type="user_registered", day=2, conf=0.4),
        [_spec(lane="inferred_extraction", day=1, conf=0.99)],
    ),
    (
        "inference.new_inference_loses_to_old_fact",
        "INFERENCE_CONTRADICTION",
        "reject",
        "higher_priority_existing",
        0,
        _spec(lane="inferred_extraction", day=3, conf=0.99),
        [_spec(lane="direct_capture", source_type="user_registered", day=1, conf=0.3)],
    ),
    (
        "inference.hypothesis_loses_to_observation",
        "INFERENCE_CONTRADICTION",
        "reject",
        "higher_priority_existing",
        0,
        _spec(lane="inferred_extraction", day=3, conf=0.99),
        [_spec(lane="direct_capture", source_type="chat_turn", day=1, conf=0.4)],
    ),
    (
        "inference.explicit_class_column_outranks_derived",
        "INFERENCE_CONTRADICTION",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="llm_extractor", epistemic="OBSERVATION", day=1, conf=0.4),
        [_spec(lane="llm_extractor", day=3, conf=0.99)],
    ),
    (
        "inference.hypothesis_vs_hypothesis_is_temporal",
        "TEMPORAL_CHANGE",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="inferred_extraction", day=2),
        [_spec(lane="llm_extractor", day=1)],
    ),
    (
        "inference.experience_outranks_hypothesis",
        "INFERENCE_CONTRADICTION",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="inferred_extraction", epistemic="EXPERIENCE", day=1, conf=0.4),
        [_spec(lane="inferred_extraction", day=3, conf=0.99)],
    ),
    # --- UNSAFE_AMBIGUITY：完全平级 → ask once（不静默选）------------------------
    (
        "ambiguity.full_tie_surfaces",
        "UNSAFE_AMBIGUITY",
        "surface_to_user",
        "unresolved_conflict",
        0,
        _spec(),
        [_spec(summary="另一条同样可信的说法")],
    ),
    (
        "ambiguity.fact_vs_fact_tie_surfaces",
        "UNSAFE_AMBIGUITY",
        "surface_to_user",
        "unresolved_conflict",
        0,
        _spec(lane="direct_capture", source_type="user_registered", summary="我说我每天背五十词"),
        [_spec(lane="direct_capture", source_type="user_registered", day=2, summary="我说我每天背一百词")],
    ),
    (
        "ambiguity.llm_tie_surfaces",
        "UNSAFE_AMBIGUITY",
        "surface_to_user",
        "unresolved_conflict",
        0,
        _spec(lane="llm_extractor", summary="推断A"),
        [_spec(lane="llm_extractor", summary="推断B")],
    ),
    (
        "ambiguity.both_unknown_lanes_abstain",
        "UNSAFE_AMBIGUITY",
        "reject",
        "abstain_unsafe_ambiguity",
        0,
        _spec(lane="aurora_calibration_receipt", summary="未知来源甲"),
        [_spec(lane="some_unregistered_lane", summary="未知来源乙")],
    ),
    # --- 混合：scope 优先于其他类别；多记录部分共存 -------------------------------
    (
        "mixed.scope_beats_inference_revocation",
        "SCOPE_DIFFERENCE",
        "accept",
        "scope_difference_preserve_both",
        0,
        _spec(lane="direct_capture", source_type="user_registered", decay="today"),
        [_spec(lane="inferred_extraction", day=1)],
    ),
    (
        "mixed.one_coexisting_one_loser",
        "INFERENCE_CONTRADICTION",
        "accept",
        "candidate_overrides_lower_priority",
        1,
        _spec(lane="direct_capture", source_type="user_registered", day=2),
        [_spec(decay="today", day=1), _spec(lane="inferred_extraction", day=1)],
    ),
    (
        "mixed.one_coexisting_one_stronger",
        "INFERENCE_CONTRADICTION",
        "reject",
        "higher_priority_existing",
        0,
        _spec(lane="inferred_extraction", day=3, conf=0.99),
        [_spec(decay="today", day=1), _spec(lane="direct_capture", source_type="user_registered", day=1)],
    ),
    (
        "mixed.one_coexisting_one_tie",
        "UNSAFE_AMBIGUITY",
        "surface_to_user",
        "unresolved_conflict",
        0,
        _spec(summary="平级候选"),
        [_spec(decay="today", day=1), _spec(summary="同样平级的既有记录")],
    ),
]


def _matrix_count_guard() -> int:
    return len(MATRIX)


@pytest.mark.parametrize(
    "name,category,action,reason,loser_count,cand_spec,record_specs",
    MATRIX,
    ids=[row[0] for row in MATRIX],
)
@pytest.mark.asyncio
async def test_conflict_arbitration_matrix(
    db_session, name, category, action, reason, loser_count, cand_spec, record_specs
):
    """四类别仲裁矩阵：每组的类别标签、action、reason、败者集合都必须确定性命中。"""
    user = await _user(db_session)
    summaries = iter([f"记录{i}" for i in range(len(record_specs))])
    records = []
    for spec in record_specs:
        spec = dict(spec)
        summary = spec.pop("summary", None) or next(summaries)
        records.append(await _episodic(db_session, user, summary, **_spec_kwargs(spec)))
    cand_spec = dict(cand_spec)
    cand_summary = cand_spec.pop("summary", None) or "候选说法"
    candidate = _cand(user, cand_summary, **_spec_kwargs(cand_spec))

    decision = _resolver(db_session).resolve(candidate=candidate, existing_records=records)

    assert decision.action == action, f"{name}: action"
    assert decision.reason == reason, f"{name}: reason"
    assert len(decision.loser_record_ids) == loser_count, f"{name}: losers"
    assert decision.metadata.get("conflict_category") == category, f"{name}: category"
    prov = decision.metadata.get("provenance", {})
    assert prov.get("resolver_version") == CONFLICT_RESOLVER_VERSION


def test_matrix_has_at_least_30_scenarios():
    """验收：矛盾测试 ≥30 组。"""
    by_category: dict[str, int] = {}
    for _name, category, *_rest in MATRIX:
        by_category[category] = by_category.get(category, 0) + 1
    assert len(MATRIX) >= 30
    # 四类别 + 混合都要有覆盖（混合行以其命中类别计入）
    for required in ("TEMPORAL_CHANGE", "SCOPE_DIFFERENCE", "SOURCE_DISAGREEMENT", "INFERENCE_CONTRADICTION"):
        assert by_category.get(required, 0) >= 3, f"{required} 覆盖不足: {by_category}"


# ---------------------------------------------------------------------------
# 2. 关键验收语义的独立钉子（不依赖矩阵实现的细节）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_correction_supersedes_and_retracts_old_inference(db_session):
    """验收核心：explicit correction 胜过旧 inference，败者走 supersede+retract。"""
    user = await _user(db_session)
    old_inference = await _episodic(
        db_session, user, "系统推断用户晚上学习", lane="inferred_extraction", confidence=0.9
    )
    candidate = _cand(
        user,
        "用户纠正：其实是早上学习",
        lane="direct_capture",
        source_type="user_registered",
        confidence=0.4,
    )
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[old_inference])
    assert decision.action == "accept"
    assert decision.loser_record_ids == (old_inference.id,)

    new_record = await _episodic(
        db_session,
        user,
        "用户纠正：其实是早上学习",
        lane="direct_capture",
        source_type="user_registered",
        confidence=0.4,
    )
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)
    await db_session.refresh(old_inference)
    assert old_inference.retracted_at is not None
    assert old_inference.superseded_by_id == new_record.id  # revoke inference = supersede 链指向新事实


@pytest.mark.asyncio
async def test_scope_difference_coexist_keeps_both_records_active(db_session):
    """验收核心：scope difference 可共存——两条都保持 active，无 supersede/retract。"""
    user = await _user(db_session)
    global_record = await _episodic(db_session, user, "通常晚上能学习一小时", lane="inferred_extraction")
    candidate = _cand(user, "今天只有二十分钟", decay_policy="today")
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[global_record])

    assert decision.action == "accept"
    assert decision.reason == "scope_difference_preserve_both"
    assert decision.loser_record_ids == ()
    assert decision.metadata["coexisting_record_ids"] == [str(global_record.id)]

    new_record = await _episodic(db_session, user, "今天只有二十分钟", decay_policy="today")
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)
    await db_session.refresh(global_record)
    assert global_record.retracted_at is None
    assert global_record.superseded_by_id is None


@pytest.mark.asyncio
async def test_resolution_record_carries_provenance_and_category(db_session):
    """验收：resolution record + provenance 落库。"""
    user = await _user(db_session)
    old_inference = await _episodic(db_session, user, "旧推断", lane="inferred_extraction", day=1)
    candidate = _cand(user, "用户纠正", lane="direct_capture", source_type="user_registered", day=2)
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[old_inference])
    new_record = await _episodic(db_session, user, "用户纠正", lane="direct_capture", source_type="user_registered")
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)

    audit = (
        await db_session.execute(select(ConflictResolutionRecord).where(ConflictResolutionRecord.user_id == user.id))
    ).scalar_one()
    assert audit.resolution_action == "accept"
    assert audit.winner_record_id == new_record.id
    assert audit.loser_record_id == old_inference.id
    assert audit.conflict_key == candidate.semantic_key
    assert candidate.evidence_token in (audit.evidence_tokens or [])
    assert old_inference.evidence_token in (audit.evidence_tokens or [])
    meta = audit.metadata_payload or {}
    assert meta["conflict_category"] == "INFERENCE_CONTRADICTION"
    prov = meta["provenance"]
    assert prov["candidate"]["epistemic_class"] == "FACT"
    assert prov["deciding"]["epistemic_class"] == "HYPOTHESIS"
    assert prov["epistemic_contract_version"]  # 契约版本入 provenance


# ---------------------------------------------------------------------------
# 3. clarification：高信息增益且不确定 → 显式澄清，不静默选
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_gain_uncertain_conflict_emits_clarification_not_silent_pick(db_session):
    """平级不确定 + 两种说法都在 → 必须输出 clarification（ask once），绝不静默选边。"""
    user = await _user(db_session)
    existing = await _episodic(db_session, user, "我每天背五十个单词", lane="inferred_extraction")
    candidate = _cand(user, "我每天背一百个单词")
    decision = _resolver(db_session).resolve(candidate=candidate, existing_records=[existing])

    assert decision.action == "surface_to_user"
    assert decision.action not in {"accept", "reject"}  # 钉死：不静默选
    clarification = decision.metadata["clarification"]
    assert clarification["policy"] == "ask_once"
    assert clarification["conflict_category"] == "UNSAFE_AMBIGUITY"
    options = clarification["options"]
    assert {option["side"] for option in options} == {"left", "right"}
    by_side = {option["side"]: option for option in options}
    assert by_side["left"]["summary"] == candidate.summary
    assert by_side["right"]["summary"] == existing.summary
    assert by_side["left"]["lane"] == candidate.source_lane


@pytest.mark.asyncio
async def test_clarification_surfaces_unresolved_conflict_for_ask_once(db_session):
    """surface 落 unresolved_conflicts（pending_user），clarification 随 payload 可取。"""
    user = await _user(db_session)
    existing = await _episodic(db_session, user, "旧说法", lane="inferred_extraction")
    candidate = _cand(user, "新说法")
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[existing])
    await service.apply_live_decision(candidate=candidate, decision=decision)

    unresolved = (await db_session.execute(select(UnresolvedConflict))).scalar_one()
    assert unresolved.status == "pending_user"
    assert unresolved.left_summary == "新说法"
    assert unresolved.right_summary == "旧说法"
    assert unresolved.left_payload["clarification"]["policy"] == "ask_once"


@pytest.mark.asyncio
async def test_abstain_rejects_without_creating_user_question(db_session):
    """双方均未登记 lane：abstain——不写、不问、留审计。"""
    user = await _user(db_session)
    existing = await _episodic(db_session, user, "未知来源乙", lane="some_unregistered_lane")
    candidate = _cand(user, "未知来源甲", lane="aurora_calibration_receipt")
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[existing])

    assert decision.action == "reject"
    assert decision.reason == "abstain_unsafe_ambiguity"
    assert decision.metadata["conflict_category"] == "UNSAFE_AMBIGUITY"
    await service.apply_live_decision(candidate=candidate, decision=decision)
    assert (await db_session.execute(select(UnresolvedConflict))).scalars().all() == []
    audits = (await db_session.execute(select(ConflictResolutionRecord))).scalars().all()
    assert len(audits) == 1 and audits[0].resolution_reason == "abstain_unsafe_ambiguity"


@pytest.mark.asyncio
async def test_registered_lane_beats_unknown_lane_without_abstain(db_session):
    """负控：候选未登记但对手已登记 → 正常裁决（不 abstain），维持既有语义。"""
    user = await _user(db_session)
    existing = await _episodic(db_session, user, "用户直采", lane="direct_capture", source_type="user_registered")
    candidate = _cand(user, "校准回执", lane="aurora_calibration_receipt", day=3, confidence=0.99)
    decision = _resolver(db_session).resolve(candidate=candidate, existing_records=[existing])
    assert decision.action == "reject"
    assert decision.reason == "higher_priority_existing"


# ---------------------------------------------------------------------------
# 4. F2：apply_live_decision 生命周期过滤 / 行锁 / 幂等重放
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f2_revoked_loser_never_touched(db_session):
    """用户已 revoke 的行不得被自动仲裁写 retracted/supersede。"""
    user = await _user(db_session)
    revoked = await _episodic(db_session, user, "已撤销记录", lane="inferred_extraction")
    revoked.revoked_at = datetime.now(UTC).replace(tzinfo=None)
    await db_session.commit()

    candidate = _cand(user, "新推断", lane="inferred_extraction", day=2)
    new_record = await _episodic(db_session, user, "新推断", lane="inferred_extraction", day=2)
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[revoked])
    # 已撤销行不再是 contender：等同无冲突
    assert decision.reason == "no_conflict"

    # 直接打 _load_records + apply 的防御面：即便败者清单含 revoked 行也不得改写
    await service.apply_live_decision(
        candidate=candidate,
        decision=type(decision)(
            action="accept",
            reason="candidate_overrides_lower_priority",
            winner_lane=candidate.source_lane,
            loser_record_ids=(revoked.id,),
            loser_lanes=(revoked.source_lane,),
            evidence_tokens=(candidate.evidence_token,),
            conflict_key=candidate.semantic_key,
        ),
        new_record=new_record,
    )
    await db_session.refresh(revoked)
    assert revoked.retracted_at is None
    assert revoked.superseded_by_id is None


@pytest.mark.asyncio
async def test_f2_superseded_loser_keeps_first_chain_pointer(db_session, outbox_tables):
    """已 superseded 的 loser 保留首链指针，不被新 winner 静默改指。"""
    user = await _user(db_session)
    w_old = await _episodic(db_session, user, "旧胜者", lane="inferred_extraction", day=1)
    loser = await _episodic(db_session, user, "连续败者", lane="working_memory", day=1, confidence=0.4)
    loser.retracted_at = datetime.now(UTC).replace(tzinfo=None)
    loser.superseded_by_id = w_old.id
    await db_session.commit()

    w_new = await _episodic(db_session, user, "新胜者", lane="inferred_extraction", day=3)
    candidate = _cand(user, "新胜者", lane="inferred_extraction", day=3)
    service = _resolver(db_session)
    await service.apply_live_decision(
        candidate=candidate,
        decision=_decision_accept(candidate, (loser.id,), (loser.source_lane,)),
        new_record=w_new,
    )
    await db_session.refresh(loser)
    assert loser.superseded_by_id == w_old.id  # 首链指针保留
    meta = (
        (await db_session.execute(select(ConflictResolutionRecord).where(ConflictResolutionRecord.user_id == user.id)))
        .scalar_one()
        .metadata_payload
    )
    assert meta.get("skipped_loser_ids") == [str(loser.id)]  # 审计记录跳过事实


def _decision_accept(candidate, loser_ids, loser_lanes):
    from app.services.conflict_resolver_service import ResolutionDecision

    return ResolutionDecision(
        action="accept",
        reason="candidate_overrides_lower_priority",
        winner_lane=candidate.source_lane,
        loser_record_ids=loser_ids,
        loser_lanes=loser_lanes,
        evidence_tokens=(candidate.evidence_token,),
        conflict_key=candidate.semantic_key,
    )


@pytest.mark.asyncio
async def test_f2_replay_is_idempotent_audit_epoch_event(db_session, outbox_tables):
    """重复投递同一冲突：二次 apply 为 no-op——不重复审计/epoch/事件。"""
    user = await _user(db_session)
    loser = await _episodic(db_session, user, "败者", lane="working_memory", day=1, confidence=0.4)
    candidate = _cand(user, "更强候选", lane="inferred_extraction", day=2)
    new_record = await _episodic(db_session, user, "更强候选", lane="inferred_extraction", day=2)
    service = _resolver(db_session)

    decision = service.resolve(candidate=candidate, existing_records=[loser])
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)
    epoch_after_first = await _epoch(db_session, user)
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)

    audits = (
        (
            await db_session.execute(
                select(ConflictResolutionRecord).where(
                    ConflictResolutionRecord.resolution_reason == "candidate_overrides_lower_priority"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1  # 幂等：不重复审计
    assert await _epoch(db_session, user) == epoch_after_first  # 不重复 bump
    events = await _invalidation_events(db_session)
    assert len(events) == 1  # 不重复事件


@pytest.mark.asyncio
async def test_f2_effective_supersede_bumps_epoch_and_writes_content_free_event(db_session, outbox_tables):
    """有效 supersede：epoch bump + memory.invalidated（M-07 同构），payload 不含记忆内容。"""
    user = await _user(db_session)
    loser = await _episodic(db_session, user, "败者内容不应出现在事件里", lane="working_memory", day=1, confidence=0.4)
    candidate = _cand(user, "更强候选", lane="inferred_extraction", day=2)
    new_record = await _episodic(db_session, user, "更强候选", lane="inferred_extraction", day=2)
    service = _resolver(db_session)

    decision = service.resolve(candidate=candidate, existing_records=[loser])
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)

    assert await _epoch(db_session, user) == 2  # 懒建首行 1→2
    events = await _invalidation_events(db_session)
    assert len(events) == 1
    payload = events[0]
    assert payload["action"] == "supersede"
    assert payload["memory_type"] == "episodic"
    assert payload["memory_ids"] == [str(loser.id)]
    assert payload["memory_epoch"] == 2
    assert payload["conflict_category"] == "TEMPORAL_CHANGE"
    # content-free 契约：事件 payload 不得携带记忆正文
    assert "败者内容" not in json.dumps(payload, ensure_ascii=False)
    assert "更强候选" not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_f2_accept_without_losers_records_audit_only_no_epoch(db_session, outbox_tables):
    """preserve-both / 无败者 accept：只落审计，不 bump epoch、不发 invalidation。"""
    user = await _user(db_session)
    global_record = await _episodic(db_session, user, "通常晚上学一小时", lane="inferred_extraction")
    candidate = _cand(user, "今天只有二十分钟", decay_policy="today")
    new_record = await _episodic(db_session, user, "今天只有二十分钟", decay_policy="today")
    service = _resolver(db_session)

    decision = service.resolve(candidate=candidate, existing_records=[global_record])
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)

    audits = (await db_session.execute(select(ConflictResolutionRecord))).scalars().all()
    assert len(audits) == 1
    assert audits[0].resolution_reason == "scope_difference_preserve_both"
    assert await _invalidation_events(db_session) == []
    assert await _epoch(db_session, user) == 1  # 无有效变更 → 无 bump（无行=基线1）


# ---------------------------------------------------------------------------
# 5. F4：用户仲裁入口补齐 epoch 契约 + SUPERSEDED 语义对称 + 幂等
# ---------------------------------------------------------------------------


async def _surface_one_conflict(db_session, user) -> UnresolvedConflict:
    existing = await _episodic(db_session, user, "右侧旧说法", lane="inferred_extraction")
    candidate = _cand(user, "左侧新说法")
    service = _resolver(db_session)
    decision = service.resolve(candidate=candidate, existing_records=[existing])
    assert decision.action == "surface_to_user"
    await service.apply_live_decision(candidate=candidate, decision=decision)
    return (
        await db_session.execute(select(UnresolvedConflict).where(UnresolvedConflict.user_id == user.id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_f4_arbitration_supersedes_loser_with_winner_pointer(db_session, outbox_tables):
    """用户选边：败者得 superseded_by_id=winner（SUPERSEDED，不再裸 RETRACTED）。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    loser_id = unresolved.right_record_id
    service = _resolver(db_session)

    resolved = await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")
    assert resolved.selected_side == "left"
    loser = await EpisodicMemory.get_by_id(db_session, loser_id)
    assert loser.superseded_by_id is not None  # 指向物化胜者
    assert loser.retracted_at is not None


@pytest.mark.asyncio
async def test_f4_arbitration_bumps_epoch_and_emits_invalidation(db_session, outbox_tables):
    """用户仲裁是破坏性变更：epoch bump + memory.invalidated（第 5 入口补齐）。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    service = _resolver(db_session)

    await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")

    assert await _epoch(db_session, user) == 2
    events = await _invalidation_events(db_session)
    assert len(events) == 1
    payload = events[0]
    assert payload["reason_code"] == "user_arbitrated"
    assert payload["action"] == "user_arbitration"  # R2 F-9：payload action 值钉死
    assert payload["memory_type"] == "episodic"
    assert payload["selected_side"] == "left"
    assert payload["memory_ids"]  # 被撤下的败者 id


@pytest.mark.asyncio
async def test_f4_arbitration_replay_is_idempotent(db_session, outbox_tables):
    """重复仲裁同一冲突：no-op——状态已终态，不重复 epoch/事件/审计。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    service = _resolver(db_session)

    await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")
    epoch_first = await _epoch(db_session, user)
    audits_first = len((await db_session.execute(select(ConflictResolutionRecord))).scalars().all())

    resolved_again = await service.arbitrate_unresolved_conflict(
        user_id=user.id, conflict_id=unresolved.id, selection="left"
    )
    assert resolved_again is not None
    assert resolved_again.status == "resolved"
    assert await _epoch(db_session, user) == epoch_first
    assert len(await _invalidation_events(db_session)) == 1
    assert len((await db_session.execute(select(ConflictResolutionRecord))).scalars().all()) == audits_first


@pytest.mark.asyncio
async def test_f4_none_selection_retracts_both_without_supersede(db_session, outbox_tables):
    """用户两边都否：双侧 retract、无 supersede 指针、仍 bump epoch + 事件。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    right_id = unresolved.right_record_id
    service = _resolver(db_session)

    resolved = await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="none")
    assert resolved.selected_side == "none"
    right = await EpisodicMemory.get_by_id(db_session, right_id)
    assert right.retracted_at is not None
    assert right.superseded_by_id is None
    assert await _epoch(db_session, user) == 2
    events = await _invalidation_events(db_session)
    assert len(events) == 1 and events[0]["selected_side"] == "none"


# ---------------------------------------------------------------------------
# 6. F6：偏好 provenance 的机器/人类边界显式化
# ---------------------------------------------------------------------------


def test_f6_explicit_source_type_is_authoritative_over_inferred_refs():
    """显式 source_type 的写带 ai_inferred 证据 → EXPLICIT（不再误拦）。"""
    provenance = preference_write_provenance(
        source_type="user_state",
        evidence_refs=[{"type": "ai_inferred", "id": "ref-1"}],
    )
    assert provenance == "explicit"


def test_f6_chat_preference_user_words_are_explicit():
    """用户原话抽取（chat_preference）是显式写，即使引用了推断证据。"""
    provenance = preference_write_provenance(
        source_type="chat_preference",
        evidence_refs=[{"type": "ai_inferred", "id": "ref-1"}],
    )
    assert provenance == "explicit"


def test_f6_ai_inferred_source_type_still_inferred():
    assert preference_write_provenance(source_type="ai_inferred", evidence_refs=[]) == "inferred"


def test_f6_refs_only_still_inferred_and_unknown_source_stays_refs_decided():
    assert preference_write_provenance(source_type=None, evidence_refs=[{"type": "ai_inferred"}]) == "inferred"
    # 未知/机器类 source_type（如 behavior/system）不自动获得显式权威——仍由证据决定
    assert preference_write_provenance(source_type="behavior", evidence_refs=[{"type": "ai_inferred"}]) == "inferred"
    assert preference_write_provenance(source_type="behavior", evidence_refs=[]) == "explicit"


def test_f6_guard_regression_inferred_still_cannot_supersede_explicit():
    from app.services.memory_epistemic_contract import inferred_may_supersede

    assert inferred_may_supersede("explicit", "inferred") is False
    assert inferred_may_supersede("explicit", "explicit") is True
    assert inferred_may_supersede("inferred", "inferred") is True


# ---------------------------------------------------------------------------
# 7. F7：守卫跳过 / 仲裁结局的计数指标
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f7_epistemic_guard_skip_is_metric_counted(db_session, monkeypatch):
    """推断档 winner 试图压显式档 loser：守卫跳过必须有计数指标（不再只有日志）。"""
    from app.core.business_metrics import MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL, snapshot_metric

    user = await _user(db_session)
    explicit_record = await _episodic(
        db_session, user, "用户直采事实", lane="direct_capture", source_type="user_registered", day=1
    )
    # 构造一个 resolver 算术不会产出、但 apply 端必须防御的决策：推断 winner 压显式 loser
    candidate = _cand(user, "越权推断", lane="inferred_extraction", day=3)
    new_record = await _episodic(db_session, user, "越权推断", lane="inferred_extraction", day=3)
    service = _resolver(db_session)

    before = snapshot_metric(MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL).get(
        "winner_lane=inferred_extraction,loser_lane=direct_capture", 0.0
    )
    await service.apply_live_decision(
        candidate=candidate,
        decision=_decision_accept(candidate, (explicit_record.id,), (explicit_record.source_lane,)),
        new_record=new_record,
    )
    after = snapshot_metric(MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL).get(
        "winner_lane=inferred_extraction,loser_lane=direct_capture", 0.0
    )
    assert after > before
    await db_session.refresh(explicit_record)
    assert explicit_record.retracted_at is None  # 守卫实际拦住了


@pytest.mark.asyncio
async def test_f7_resolution_outcome_metric_counted(db_session):
    from app.core.business_metrics import MEMORY_CONFLICT_RESOLUTIONS_TOTAL, snapshot_metric

    user = await _user(db_session)
    loser = await _episodic(db_session, user, "败者", lane="working_memory", day=1, confidence=0.4)
    candidate = _cand(user, "更强候选", lane="inferred_extraction", day=2)
    service = _resolver(db_session)

    key = "action=accept,category=TEMPORAL_CHANGE"
    before = snapshot_metric(MEMORY_CONFLICT_RESOLUTIONS_TOTAL).get(key, 0.0)
    decision = service.resolve(candidate=candidate, existing_records=[loser])
    new_record = await _episodic(db_session, user, "更强候选", lane="inferred_extraction", day=2)
    await service.apply_live_decision(candidate=candidate, decision=decision, new_record=new_record)
    after = snapshot_metric(MEMORY_CONFLICT_RESOLUTIONS_TOTAL).get(key, 0.0)
    assert after > before


# ---------------------------------------------------------------------------
# 8. 集成证据：经生产入口 write_candidate_to_l1 的端到端仲裁接线
# （lane → ConflictResolverService.resolve → apply_live_decision → 失效管道 →
#   event_outbox，全程真实 sqlite 会话；note: lane 自身的同 key 去重只看
#   inferred lane 行，故跨 lane 冲突才走仲裁——这正是生产真实形态）
# ---------------------------------------------------------------------------


def _lane_candidate(text: str, semantic_key: str, *, day: int = 2, decay: str = "30d", conf: float = 0.8):
    from app.services.memory_inferred_write_lane import InferredEpisodicCandidate

    return InferredEpisodicCandidate(
        candidate_text=text,
        subject_type="commitment",
        confidence=conf,
        evidence_token=f"lane-{uuid4().hex[:8]}",
        decay_policy=decay,
        source_lane="inferred_extraction",
        semantic_key=semantic_key,
        evidence_refs=[{"type": "chat_turn", "id": f"turn-{uuid4().hex[:6]}"}],
        occurred_at=_t(day),
        due_at=None,
        mentioned_entity_hash=None,
        mentioned_entity_owner_user_id=None,
    )


@pytest.mark.asyncio
async def test_integration_lane_supersedes_cross_lane_loser_e2e(db_session, outbox_tables):
    """端到端·accept：既有 working_memory 旧记录 → inferred 候选经 lane 写入 →
    败者 superseded + epoch bump + memory.invalidated + resolution 审计一条链全通。"""
    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

    user = await _user(db_session)
    loser = await _episodic(
        db_session,
        user,
        "工作记忆里的旧计划",
        lane="working_memory",
        day=1,
        confidence=0.4,
        semantic_key="sk:e2e-accept",
    )
    lane = MemoryInferredWriteLaneService(db_session)
    winner = await lane.write_candidate_to_l1(
        user_id=user.id,
        session_id=uuid4(),
        candidate=_lane_candidate("新推断计划", "sk:e2e-accept", day=2),
        force_write=True,
        bypass_min_confidence=True,
    )
    assert winner is not None and winner.source_lane == "inferred_extraction"

    await db_session.refresh(loser)
    assert loser.retracted_at is not None
    assert loser.superseded_by_id == winner.id  # supersede 链经生产入口真实落库
    assert await _epoch(db_session, user) == 2
    events = await _invalidation_events(db_session)
    assert len(events) == 1
    assert events[0]["action"] == "supersede"
    assert events[0]["memory_ids"] == [str(loser.id)]
    audit = (
        await db_session.execute(select(ConflictResolutionRecord).where(ConflictResolutionRecord.user_id == user.id))
    ).scalar_one()
    assert audit.resolution_reason == "candidate_overrides_lower_priority"
    assert audit.metadata_payload["conflict_category"] == "TEMPORAL_CHANGE"
    assert audit.winner_record_id == winner.id


@pytest.mark.asyncio
async def test_integration_lane_blocked_by_stronger_cross_lane_fact(db_session, outbox_tables):
    """端到端·reject：既有 user_confirmed 事实 → inferred 候选被仲裁拒绝 →
    不落 inferred 记录、不 bump epoch、不发事件，但留拒绝审计。"""
    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

    user = await _user(db_session)
    fact = await _episodic(
        db_session, user, "用户已确认的安排", lane="user_confirmed", day=1, confidence=0.3, semantic_key="sk:e2e-reject"
    )
    lane = MemoryInferredWriteLaneService(db_session)
    rejected = await lane.write_candidate_to_l1(
        user_id=user.id,
        session_id=uuid4(),
        candidate=_lane_candidate("与用户确认相悖的推断", "sk:e2e-reject", day=3, conf=0.99),
        force_write=True,
        bypass_min_confidence=True,
    )
    assert rejected is None
    inferred_rows = (
        (
            await db_session.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user.id,
                    EpisodicMemory.source_lane == "inferred_extraction",
                )
            )
        )
        .scalars()
        .all()
    )
    assert inferred_rows == []  # 候选未落库（被仲裁拒绝）
    await db_session.refresh(fact)
    assert fact.retracted_at is None and fact.superseded_by_id is None  # 事实未被触碰
    assert await _epoch(db_session, user) == 1  # 无破坏性变更 → 无 bump
    assert await _invalidation_events(db_session) == []
    audit = (
        await db_session.execute(select(ConflictResolutionRecord).where(ConflictResolutionRecord.user_id == user.id))
    ).scalar_one()
    assert audit.resolution_reason == "higher_priority_existing"
    assert audit.metadata_payload["conflict_category"] == "INFERENCE_CONTRADICTION"


@pytest.mark.asyncio
async def test_integration_lane_preserve_both_across_time_scopes(db_session, outbox_tables):
    """端到端·preserve-both：bounded 既有记录 vs today-only 候选 → 两条都活、
    无 supersede/epoch/事件，resolution 审计记录 SCOPE_DIFFERENCE。"""
    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

    user = await _user(db_session)
    bounded = await _episodic(
        db_session,
        user,
        "本周内要交的实验报告",
        lane="direct_capture",
        source_type="chat_turn",
        day=1,
        due_at=datetime(2026, 9, 10),
        semantic_key="sk:e2e-scope",
    )
    lane = MemoryInferredWriteLaneService(db_session)
    written = await lane.write_candidate_to_l1(
        user_id=user.id,
        session_id=uuid4(),
        candidate=_lane_candidate("今天只有二十分钟", "sk:e2e-scope", day=2, decay="today"),
        force_write=True,
        bypass_min_confidence=True,
    )
    assert written is not None
    await db_session.refresh(bounded)
    assert bounded.retracted_at is None and bounded.superseded_by_id is None  # 两者共存
    assert await _epoch(db_session, user) == 1  # 无破坏性变更
    assert await _invalidation_events(db_session) == []
    audit = (
        await db_session.execute(select(ConflictResolutionRecord).where(ConflictResolutionRecord.user_id == user.id))
    ).scalar_one()
    assert audit.resolution_reason == "scope_difference_preserve_both"
    assert audit.metadata_payload["coexisting_record_ids"] == [str(bounded.id)]


# ---------------------------------------------------------------------------
# 9. R2 返修回归（REVIEW_RECEIPT_2 F-1/F-2/F-5/F-9）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2_f1_third_same_key_row_does_not_silent_drop_user_answer(db_session, outbox_tables):
    """R2 F-1 探针回归：第三条同 semantic_key active 推断行存在（preserve-both
    共存的常态产物）时，用户仲裁选 left 必须落库选中侧——lane 机器写守卫
    （duplicate/限流/禁用）不得吞掉用户答案；败者不得裸 RETRACTED。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    loser_id = unresolved.right_record_id
    # 第三条同 key active 推断行：旧实现下物化经 lane 被 _is_duplicate 拒掉
    third = await _episodic(db_session, user, "今天的临时安排", decay_policy="today", semantic_key="sk:test")
    assert third.retracted_at is None

    service = _resolver(db_session)
    resolved = await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")
    assert resolved.selected_side == "left"

    winner = (
        await db_session.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user.id,
                EpisodicMemory.summary == "左侧新说法",
                EpisodicMemory.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    loser = await EpisodicMemory.get_by_id(db_session, loser_id)
    await db_session.refresh(loser)
    assert loser.retracted_at is not None
    assert loser.superseded_by_id == winner.id  # SUPERSEDED 对称——不是裸 RETRACTED
    assert await _epoch(db_session, user) == 2
    events = await _invalidation_events(db_session)
    assert len(events) == 1 and events[0]["memory_ids"] == [str(loser_id)]
    audit = (
        await db_session.execute(
            select(ConflictResolutionRecord).where(
                ConflictResolutionRecord.user_id == user.id,
                ConflictResolutionRecord.resolution_reason == "user_arbitrated",
            )
        )
    ).scalar_one()
    assert audit.winner_record_id == winner.id  # 审计揭示真实胜者（旧实现为 None）
    # 第三行（范围不同）不受本次仲裁牵连
    await db_session.refresh(third)
    assert third.retracted_at is None and third.superseded_by_id is None


@pytest.mark.asyncio
async def test_r2_f1_materialization_failure_keeps_conflict_pending(db_session, outbox_tables, monkeypatch):
    """R2 F-1 失败序：物化失败 → 冲突保持 pending_user、败者不被毁、
    无 epoch/事件/审计，响亮失败（不静默 resolved）。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    loser_id = unresolved.right_record_id
    service = _resolver(db_session)

    async def _fail_materialize(payload, *, user_id):
        return None

    monkeypatch.setattr(service, "_materialize_side", _fail_materialize)

    with pytest.raises(ValueError, match="materialization failed"):
        await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")

    fresh = (
        await db_session.execute(select(UnresolvedConflict).where(UnresolvedConflict.id == unresolved.id))
    ).scalar_one()
    await db_session.refresh(fresh)
    assert fresh.status == "pending_user"  # 未被静默 resolved——用户可重试
    loser = await EpisodicMemory.get_by_id(db_session, loser_id)
    await db_session.refresh(loser)
    assert loser.retracted_at is None  # 败者未先毁
    assert await _invalidation_events(db_session) == []
    # surface 阶段的审计行合法存在；断言仲裁路径零新增（reason=user_arbitrated 无行）
    assert (
        await db_session.execute(
            select(ConflictResolutionRecord).where(ConflictResolutionRecord.resolution_reason == "user_arbitrated")
        )
    ).scalars().all() == []
    assert await _epoch(db_session, user) == 1


@pytest.mark.asyncio
async def test_r2_f2_midflight_status_change_converges_as_processed(db_session, outbox_tables, monkeypatch):
    """R2 F-2 复查路径：物化提交后、终态阶段前，冲突已被并发请求处理
    （入口行锁被内部提交释放）→ 本调用按已处理收敛：不毁败者、不 bump
    epoch、不写事件/审计。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    loser_id = unresolved.right_record_id
    service = _resolver(db_session)

    original_stash = service._stash_materialized_id

    async def _stash_then_concurrently_resolve(conflict, payload_key, record_id):
        await original_stash(conflict, payload_key, record_id)
        # 模拟并发对手：在物化提交后、本调用终态阶段前完成整场仲裁
        conflict.status = "resolved"
        conflict.selected_side = "right"
        conflict.resolved_at = datetime.now(UTC).replace(tzinfo=None)
        await db_session.commit()

    monkeypatch.setattr(service, "_stash_materialized_id", _stash_then_concurrently_resolve)

    result = await service.arbitrate_unresolved_conflict(user_id=user.id, conflict_id=unresolved.id, selection="left")
    assert result is not None
    assert result.status == "resolved"
    assert result.selected_side == "right"  # 以并发对手的结果为准，不覆盖
    # 本调用收敛为 no-op：不追加任何效果（surface 审计合法存在，仲裁审计零新增）
    assert await _invalidation_events(db_session) == []
    assert (
        await db_session.execute(
            select(ConflictResolutionRecord).where(ConflictResolutionRecord.resolution_reason == "user_arbitrated")
        )
    ).scalars().all() == []
    assert await _epoch(db_session, user) == 1
    loser = await EpisodicMemory.get_by_id(db_session, loser_id)
    await db_session.refresh(loser)
    assert loser.retracted_at is None  # 本调用未进入破坏性阶段


@pytest.mark.asyncio
async def test_r2_f5_right_selection_cleans_stashed_left_remnant(db_session, outbox_tables):
    """R2 F-5：中断的 left 尝试已物化并暂存（冲突仍 pending）→ 用户改选
    right → 暂存残留按败者清算（supersede 指向 right 胜者），不再双活。"""
    user = await _user(db_session)
    unresolved = await _surface_one_conflict(db_session, user)
    # 模拟中断的 left 尝试：物化记录存在、锚点已暂存、终态未落
    left_remnant = await _episodic(db_session, user, "左侧新说法", semantic_key="sk:test")
    conflict_row = (
        await db_session.execute(select(UnresolvedConflict).where(UnresolvedConflict.id == unresolved.id))
    ).scalar_one()
    payload = dict(conflict_row.left_payload)
    payload["materialized_record_id"] = str(left_remnant.id)
    conflict_row.left_payload = payload
    await db_session.commit()

    service = _resolver(db_session)
    resolved = await service.arbitrate_unresolved_conflict(
        user_id=user.id, conflict_id=conflict_row.id, selection="right"
    )
    assert resolved.selected_side == "right"
    await db_session.refresh(left_remnant)
    assert left_remnant.retracted_at is not None  # 残留被清算
    assert left_remnant.superseded_by_id == conflict_row.right_record_id  # 指向 right 胜者
    assert await _epoch(db_session, user) == 2  # 清算是有效破坏性变更
    events = await _invalidation_events(db_session)
    assert len(events) == 1 and str(left_remnant.id) in events[0]["memory_ids"]
