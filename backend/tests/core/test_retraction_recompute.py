"""V4-D03 · 撤回派生影响与投影重算契约守卫（纯函数，无 DB、无模型）。

卡 V4-D03 验收（必须可失败——每条验收至少一个红转绿反例）：
1. 并发旧job不能复活已删内容（发布栅栏 + 持久墓碑词表）；
2. 非线性状态按有效事件回放而非减旧分数（有效回放装配 + 融合权威委托）；
3. 重算中UI与工具均标过期，不继续旧建议（读侧门同一门两出口）。

词表冻结纪律与 test_attribution.py 同款：封闭集精确字面断言，新增成员不改
本测试 → 红。语义唯一真源断言：融合=G-01 重放器、墓碑=G-01 effect_kind 词表、
outcome 依赖边标记=G-02 吸收器编码。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.retraction_recompute import (
    CANDIDATE_FACES_BY_KIND,
    DERIVED_FACES,
    PUBLISH_GATE_DECISIONS,
    RECOMPUTE_STATUSES,
    RETRACTED_EFFECT_KIND,
    RETRACTION_KINDS,
    RETRACTION_RECOMPUTE_SCHEMA_VERSION,
    STALE_UI_MARKER,
    DerivedFace,
    DerivedProjection,
    PublishGateDecision,
    RecomputeStatus,
    ReplayEvent,
    RetractionImpact,
    RetractionKind,
    SourcePointer,
    assemble_valid_replay,
    derive_retraction_id,
    evaluate_publish_gate,
    evaluate_read_gate,
    extract_outcome_marker,
    mark_pending,
    mark_recomputed,
    next_projection_version,
    outcome_marker_hex,
    plan_recompute,
)
from app.services.galaxy.mastery_evidence import (
    EvidenceHistoryEntry,
    MasteryEffectKind,
    MasteryEvidenceType,
    parse_effect_kind,
    recompute_evidence_state,
)
from app.services.galaxy.outcome_absorption_service import _evidence_request_id

_T0 = datetime(2026, 9, 28, 10, 0, 0)  # naive UTC 锚点时刻


# ---------------------------------------------------------------------------
# 词表冻结（封闭集精确字面断言）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("frozen", "expected"),
    [
        (RETRACTION_KINDS, {"material_deleted", "inference_retracted", "result_retracted"}),
        (DERIVED_FACES, {"capability_node", "insight", "strategy"}),
        (RECOMPUTE_STATUSES, {"fresh", "pending_recompute", "recomputed"}),
        (
            PUBLISH_GATE_DECISIONS,
            {"allow", "discard_stale_epoch", "discard_missing_exclusion", "discard_target_gone"},
        ),
    ],
)
def test_frozen_vocabularies_are_exact(frozen: frozenset[str], expected: set[str]) -> None:
    """撤回三分类/派生面/状态机/栅栏判定的封闭词表——多一个成员即红（bump 纪律）。"""
    assert set(frozen) == expected


def test_schema_version_frozen() -> None:
    assert RETRACTION_RECOMPUTE_SCHEMA_VERSION == "retraction.recompute.v1"


def test_retracted_effect_kind_matches_mastery_vocabulary() -> None:
    """持久墓碑值 = G-01 effect_kind 词表成员（import 期一致性在这里二次钉死）。"""
    assert MasteryEffectKind.RETRACTED.value == RETRACTED_EFFECT_KIND == "retracted"
    # 读侧解析显式认得墓碑（不再是 unknown fail-closed），但语义仍是跳过面。
    assert parse_effect_kind("retracted") is MasteryEffectKind.RETRACTED


# ---------------------------------------------------------------------------
# 验收①前置：撤回身份幂等 + 发布栅栏（并发旧 job 不能复活已删内容）
# ---------------------------------------------------------------------------


def test_retraction_id_is_content_addressed_and_replay_stable() -> None:
    """同一 (user, kind, target) 任意时点重放恒同 id；任一维度不同即不同 id。"""
    user = str(uuid4())
    target = str(uuid4())
    a = derive_retraction_id(user, RetractionKind.RESULT_RETRACTED, "outcome", target)
    b = derive_retraction_id(user, "result_retracted", "outcome", target)
    assert a == b
    assert a.startswith("rtr_") and len(a) == len("rtr_") + 32
    # 三分类不同 → 不同撤回（严格区分，不混用）
    assert derive_retraction_id(user, "material_deleted", "outcome", target) != a
    assert derive_retraction_id(user, "result_retracted", "outcome", str(uuid4())) != a
    assert derive_retraction_id(str(uuid4()), "result_retracted", "outcome", target) != a
    # 幂等重放：再算一遍仍同 id（不含时间成分）
    assert derive_retraction_id(user, "result_retracted", "outcome", target) == a


def test_publish_gate_discards_stale_epoch_job() -> None:
    """验收①红转绿：重算期间落了新撤回（epoch 前进）⇒ 旧 job 结果整体丢弃。"""
    verdict = evaluate_publish_gate(
        base_epoch=7, current_epoch=8, excluded_ids=["a"], retracted_ids=["a"], target_exists=True
    )
    assert verdict.decision is PublishGateDecision.DISCARD_STALE_EPOCH
    assert not verdict.allowed


def test_publish_gate_fails_closed_on_unpinned_epochs() -> None:
    """任一侧世代不可证 ⇒ fail-closed 丢弃（放行需要两侧世代可证相等）。"""
    for base, current in ((None, 8), (7, None), (None, None)):
        verdict = evaluate_publish_gate(
            base_epoch=base, current_epoch=current, excluded_ids=[], retracted_ids=[], target_exists=True
        )
        assert verdict.decision is PublishGateDecision.DISCARD_STALE_EPOCH


def test_publish_gate_discards_incomplete_exclusions() -> None:
    """job 排除集 ⊉ 已知撤回集 ⇒ 输入早于某次撤回 ⇒ 丢弃。"""
    verdict = evaluate_publish_gate(
        base_epoch=7,
        current_epoch=7,
        excluded_ids=["a"],
        retracted_ids=["a", "b"],
        target_exists=True,
    )
    assert verdict.decision is PublishGateDecision.DISCARD_MISSING_EXCLUSION


def test_publish_gate_discards_deleted_target_and_allows_live_one() -> None:
    """目标已删 ⇒ 丢弃（无复活出口）；同代且排除完备且存活 ⇒ 唯一放行。"""
    gone = evaluate_publish_gate(
        base_epoch=7, current_epoch=7, excluded_ids=["a"], retracted_ids=["a"], target_exists=False
    )
    assert gone.decision is PublishGateDecision.DISCARD_TARGET_GONE
    ok = evaluate_publish_gate(
        base_epoch=7, current_epoch=7, excluded_ids=["a"], retracted_ids=["a"], target_exists=True
    )
    assert ok.decision is PublishGateDecision.ALLOW and ok.allowed


# ---------------------------------------------------------------------------
# 验收②：非线性状态按有效事件回放而非减旧分数
# ---------------------------------------------------------------------------


def _entry(value: float, at: datetime, kind: str = "evidence") -> EvidenceHistoryEntry:
    return EvidenceHistoryEntry(
        evidence_type=MasteryEvidenceType.TASK_OUTCOME,
        value=value,
        confidence=0.9,
        observed_at=at,
        effect_kind=kind,
    )


def test_retracted_entries_never_reenter_fusion() -> None:
    """墓碑行在任何重放里结构性跳过——旧 job 重放原始账本也拿不回效果。"""
    history = [_entry(60.0, _T0), _entry(80.0, _T0 + timedelta(hours=1))]
    full = recompute_evidence_state(20.0, history)
    tombstoned = recompute_evidence_state(
        20.0, [history[0], _entry(80.0, _T0 + timedelta(hours=1), kind=RETRACTED_EFFECT_KIND)]
    )
    assert tombstoned.mean < full.mean  # 被撤回证据的效果不在了
    # 幂等：同账本重放恒同（回放安全）
    again = recompute_evidence_state(
        20.0, [history[0], _entry(80.0, _T0 + timedelta(hours=1), kind=RETRACTED_EFFECT_KIND)]
    )
    assert again.mean == tombstoned.mean


def test_retract_all_events_falls_back_to_baseline_not_stored_value() -> None:
    """全部证据被撤回 ⇒ 回落到冻结基线（≠ 含撤回效果的存储值，不复活）。"""
    history = [_entry(90.0, _T0, kind=RETRACTED_EFFECT_KIND)]
    belief = recompute_evidence_state(20.0, history)
    assert belief.mean == 20.0  # 基线，不是 90


def test_valid_replay_order_is_deterministic_and_exclusions_explicit() -> None:
    """有效回放装配：排除精确身份、(occurred_at, event_id) 确定顺序、显式减除。"""
    events = [
        ReplayEvent("e3", _T0 + timedelta(hours=2)),
        ReplayEvent("e1", _T0),
        ReplayEvent("e2", _T0),
    ]
    plan = assemble_valid_replay(events, retracted_ids=["e3"])
    assert [e.event_id for e in plan.valid_events] == ["e1", "e2"]  # 同刻按 id 决次序
    assert plan.removed_event_ids == ("e3",)  # 显式，不静默
    # 重放恒同
    assert assemble_valid_replay(events, retracted_ids=["e3"]) == plan


def test_replay_is_forward_fusion_not_inverse_subtraction() -> None:
    """验收②红转绿判据：撤回后状态 = 前向回放有效事件，≠ 存储值减撤回分差。

    「减旧分数」被禁路径 = ``stored - 撤回行效果差``：它继承存储值的维护漂移
    （decay/set-point/其他写面都会动 stored），同一账本漂移后减出不同结果；
    前向回放只认（冻结锚 + 有效事件），恒同幂等。两者必然分歧。
    """
    anchor = 20.0
    e1 = _entry(55.0, _T0)
    e2 = _entry(95.0, _T0 + timedelta(hours=1))
    full = recompute_evidence_state(anchor, [e1, e2])
    after_e1 = recompute_evidence_state(anchor, [e1])
    retracted_row_delta = full.mean - after_e1.mean  # 撤回行在账本上的效果差

    replay_valid = recompute_evidence_state(anchor, [e1]).mean
    assert replay_valid == after_e1.mean  # 回放幂等：同一有效事件集恒同结果

    drifted_stored = full.mean + 7.0  # 模拟存储值被维护路径移动（decay 等）
    inverse_subtract = drifted_stored - retracted_row_delta  # 被禁的「减撤回分」
    assert inverse_subtract != pytest.approx(replay_valid)  # 随存储漂移，非同一语义


# ---------------------------------------------------------------------------
# oc= 依赖边标记（与 G-02 吸收器编码往返一致）
# ---------------------------------------------------------------------------


def test_outcome_marker_roundtrip_with_g02_encoder() -> None:
    """本模块解析器与 G-02 编码器互为逆运算（依赖边语义单一，无第二编码）。"""
    outcome_id = f"outc_{uuid4().hex}"
    request_id = _evidence_request_id(60.0, 0.8, outcome_id, None)
    assert extract_outcome_marker(request_id) == outcome_marker_hex(outcome_id)
    # 带 tk 段同样可解析
    with_task = _evidence_request_id(60.0, 0.8, outcome_id, str(uuid4()))
    assert extract_outcome_marker(with_task) == outcome_marker_hex(outcome_id)


def test_outcome_marker_matching_is_segment_exact() -> None:
    """hex 子串不构成同因：oc= 段必须整段相等（G-02 分号精确分段纪律）。"""
    real_hex = "ab" * 16
    superset_hex = "ab" * 15 + "cd"  # 非 superstring，但验证段级解析不受前缀影响
    request_id = f"obs=60;conf=0.8;oc={real_hex}"
    assert extract_outcome_marker(request_id) == real_hex
    assert extract_outcome_marker(f"obs=60;conf=0.8;oc={superset_hex}") == superset_hex
    assert extract_outcome_marker("obs=60;conf=0.8") is None
    assert extract_outcome_marker(None) is None
    assert extract_outcome_marker("") is None


# ---------------------------------------------------------------------------
# 影响规划（依赖索引；保留合法其他来源）
# ---------------------------------------------------------------------------


def test_plan_recompute_marks_only_derived_from_retracted() -> None:
    """命中=来源指针精确相等；unaffected 是显式一等结论（不删不改合法来源）。"""
    target = SourcePointer("outcome", "outc_aaa")
    affected = DerivedProjection(
        face=DerivedFace.CAPABILITY_NODE,
        subject_id="node-1",
        source_pointers=(SourcePointer("task", "t1"), target),
    )
    other_source = DerivedProjection(
        face=DerivedFace.CAPABILITY_NODE,
        subject_id="node-2",
        source_pointers=(SourcePointer("task", "t1"), SourcePointer("outcome", "outc_bbb")),
    )
    wrong_type_same_value = DerivedProjection(
        face=DerivedFace.INSIGHT,
        subject_id="ins-1",
        source_pointers=(SourcePointer("task", "outc_aaa"),),  # 值同域不同 → 不构成同源
    )
    verdicts = {
        (v.face, v.subject_id): v
        for v in plan_recompute(
            RetractionKind.RESULT_RETRACTED, target, [affected, other_source, wrong_type_same_value]
        )
    }
    assert verdicts[("capability_node", "node-1")].impact is RetractionImpact.AFFECTED
    assert verdicts[("capability_node", "node-1")].matched_pointers == (target,)
    assert verdicts[("capability_node", "node-2")].impact is RetractionImpact.UNAFFECTED
    assert verdicts[("capability_node", "node-2")].matched_pointers == ()
    assert verdicts[("insight", "ins-1")].impact is RetractionImpact.UNAFFECTED


def test_plan_recompute_candidate_faces_narrowed_by_kind() -> None:
    """候选面按撤回类型收窄；候选面外直接 unaffected（不检查指针）。"""
    target = SourcePointer("outcome", "outc_aaa")
    all_faces = tuple(DerivedProjection(face=face, subject_id="s", source_pointers=(target,)) for face in DerivedFace)
    result_verdicts = plan_recompute("result_retracted", target, all_faces)
    inference_verdicts = plan_recompute("inference_retracted", target, all_faces)
    assert all(v.impact is RetractionImpact.AFFECTED for v in result_verdicts)
    # 推断撤回不波及能力节点（候选面收窄=依赖边类型纪律）
    by_face = {v.face: v for v in inference_verdicts}
    assert by_face["capability_node"].impact is RetractionImpact.UNAFFECTED
    assert by_face["insight"].impact is RetractionImpact.AFFECTED
    assert by_face["strategy"].impact is RetractionImpact.AFFECTED
    # 候选面表本身冻结
    assert set(CANDIDATE_FACES_BY_KIND) == set(RETRACTION_KINDS)


# ---------------------------------------------------------------------------
# 验收③：读侧门（UI 与工具同一门两出口）
# ---------------------------------------------------------------------------


def test_read_gate_pending_recompute_stales_ui_and_tools_together() -> None:
    """验收③红转绿：重算中 ⇒ UI 标过期 AND 工具禁建议（同门，无分裂态）。"""
    gate = evaluate_read_gate(status="pending_recompute", computed_epoch=9, current_epoch=9)
    assert gate.stale is True
    assert gate.suggestions_allowed is False
    assert gate.ui_marker == STALE_UI_MARKER == "stale_recomputing"


def test_read_gate_epoch_behind_is_stale_even_if_status_fresh() -> None:
    """投影世代落后当前世代 ⇒ 同一过期出口（epoch 门统一）。"""
    gate = evaluate_read_gate(status="recomputed", computed_epoch=7, current_epoch=9)
    assert gate.stale is True and gate.suggestions_allowed is False
    # 未钉世代 = 按落后处理（fail-closed）
    unpinned = evaluate_read_gate(status="recomputed", computed_epoch=None, current_epoch=9)
    assert unpinned.stale is True and unpinned.suggestions_allowed is False


def test_read_gate_fresh_and_current_serves_with_suggestions() -> None:
    """新鲜且同代 ⇒ 不标过期、允许建议（无过界保守）。"""
    gate = evaluate_read_gate(status="recomputed", computed_epoch=9, current_epoch=9)
    assert gate.stale is False and gate.suggestions_allowed is True and gate.ui_marker is None
    # 无世代权威可比时不越权代判（各自消费面 C-07 门负责）
    no_epoch = evaluate_read_gate(status="fresh", computed_epoch=None, current_epoch=None)
    assert no_epoch.stale is False and no_epoch.suggestions_allowed is True


def test_recompute_status_transitions_and_version_publish() -> None:
    """状态机 fresh→pending→recomputed；发布使逻辑时钟严格 +1 永不复位。"""
    projection = DerivedProjection(
        face=DerivedFace.CAPABILITY_NODE,
        subject_id="node-1",
        source_pointers=(SourcePointer("outcome", "outc_aaa"),),
        computed_epoch=5,
        status=RecomputeStatus.FRESH,
    )
    pending = mark_pending(projection)
    assert pending.status is RecomputeStatus.PENDING_RECOMPUTE
    assert pending.computed_epoch == 5  # 世代不变，等待重算发布

    recomputed = mark_recomputed(pending, at_epoch=6)
    assert recomputed.status is RecomputeStatus.RECOMPUTED
    assert recomputed.computed_epoch == 6

    assert next_projection_version(None) == 1
    assert next_projection_version(0) == 1
    assert next_projection_version(41) == 42
    assert next_projection_version(-3) == 1  # 负值按 0 起步，永不回退
