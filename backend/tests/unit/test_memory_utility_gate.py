"""V4-I02 · optional-history utility gate —— unit tests.

Covers (card acceptance, v4/04_tasks/cards/V4-I02.md):
- 冻结锚：``FROZEN_OUTCOME_WEIGHTS`` 与 B03 ``frozen_utility.json`` 逐项对表
  （v4/evidence/V4-B03/frozen_utility.json → utility_frozen.weights）；
- FIX52：异类型失败不拉向 skill/difficulty（cross-type 失败硬拒）+ 同类型失败
  仍可在同类型/有效时间内影响候选（penalized but selectable）；
- required-memory 场景有召回；全部拒用不能过门（passed=False + precision N/A）；
- 选择集 ⊆ 输入集（无复活路径）+ 确定性 + TopK/成本/confirmed/stale 序。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.services.memory_utility_gate import (
    DEFAULT_TOP_K,
    FROZEN_OUTCOME_WEIGHTS,
    REQUIRED_MEMORY_MARKERS,
    UtilityFeatures,
    apply_history_utility_gate,
    derive_current_type_anchors,
    evaluate_history_utility,
    extract_utility_features,
    required_memory_query,
    score_candidate,
)

NOW = datetime(2026, 9, 28, 12, 0, 0)
_REPO = Path(__file__).resolve().parents[3]
_FROZEN = _REPO / "v4" / "evidence" / "V4-B03" / "frozen_utility.json"


# ---------------------------------------------------------------------------
# 冻结锚
# ---------------------------------------------------------------------------


def test_frozen_outcome_weights_match_b03_freeze():
    """冻结锚：与 B03 frozen_utility.json 的 utility_frozen.weights 逐项一致。"""
    assert _FROZEN.exists(), f"missing B03 freeze file: {_FROZEN}"
    frozen = json.loads(_FROZEN.read_text(encoding="utf-8"))
    assert frozen["frozen_by"] == "V4-B03"
    assert frozen["utility_frozen"]["weights"] == FROZEN_OUTCOME_WEIGHTS


# ---------------------------------------------------------------------------
# 特征派生
# ---------------------------------------------------------------------------


def _episodic_item(**overrides) -> SimpleNamespace:
    base = {
        "id": "ep-good-1",
        "summary": "上次数学练习解决了计算顺序问题",
        "source_lane": "direct_capture",
        "occurred_at": NOW - timedelta(days=2),
        "created_at": NOW - timedelta(days=2),
        "resolved_at": NOW - timedelta(days=1),
        "due_at": None,
        "correction_count": 0,
        "tags": ["task_type:math_practice"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_extract_features_resolved_vs_failed_commitment():
    resolved = extract_utility_features(_episodic_item(), now=NOW)
    assert resolved.resolved is True
    assert resolved.failed is False
    assert resolved.user_confirmed is True
    assert resolved.type_anchors == frozenset({"math_practice"})

    # 承诺到期未解决 = failed；未到期 = censored（不算失败）。
    overdue = extract_utility_features(
        _episodic_item(
            id="ep-late",
            resolved_at=None,
            due_at=NOW - timedelta(days=3),
            summary="单词背诵任务没完成",
            tags=["task_type:vocab_memorization"],
        ),
        now=NOW,
    )
    assert overdue.resolved is False
    assert overdue.failed is True

    pending = extract_utility_features(
        _episodic_item(id="ep-pending", resolved_at=None, due_at=NOW + timedelta(days=3)),
        now=NOW,
    )
    assert pending.resolved is False
    assert pending.failed is False  # censored ≠ negative

    plain = extract_utility_features(
        _episodic_item(id="ep-plain", resolved_at=None, due_at=None),
        now=NOW,
    )
    assert plain.failed is False  # 无承诺无解决 → 无 outcome 信号


def test_extract_features_marker_tags_and_inferred_lane():
    inferred = extract_utility_features(
        _episodic_item(id="ep-inf", source_lane="inferred_extraction", tags=[]),
        now=NOW,
    )
    assert inferred.user_confirmed is False

    marked = extract_utility_features(
        _episodic_item(
            id="ep-marked",
            tags=["wrong_followed_decision", "question", "control_intrusion"],
        ),
        now=NOW,
    )
    assert marked.wrong_followed is True
    assert marked.question is True
    assert marked.control_intrusion is True


def test_required_memory_query_markers():
    assert required_memory_query("帮我回顾上次的错题") is True
    assert required_memory_query("今天天气怎么样") is False
    assert required_memory_query("") is False
    assert required_memory_query(None) is False
    # 词表封闭性：全部 marker 可枚举（防散落定义）。
    assert "上次" in REQUIRED_MEMORY_MARKERS and "记得" in REQUIRED_MEMORY_MARKERS


# ---------------------------------------------------------------------------
# FIX52：异类型失败不拉向 skill/difficulty
# ---------------------------------------------------------------------------

_QUERY_MATH = "帮我安排今天的数学练习"
_MATH_ANCHORS = frozenset({"math_practice"})


def test_fix52_cross_type_failure_is_hard_rejected():
    """异类型失败（vocab 失败经验 × math 查询）不得入选——负迁移硬拒。"""
    cross_failure = UtilityFeatures(
        item_id="ep-vocab-fail",
        content="单词背诵任务连续失败，用户不适合记忆类任务",
        failed=True,
        type_anchors=frozenset({"vocab_memorization"}),
    )
    result = evaluate_history_utility(
        [cross_failure],
        query_text=_QUERY_MATH,
        current_type_anchors=_MATH_ANCHORS,
    )
    assert result.selected_ids == frozenset()
    decision = result.decisions[0]
    assert decision.selected is False
    assert "negative_transfer_cross_type" in decision.reasons
    assert result.passed is True  # 非 required-memory 场景，空选择≠recall miss


def test_fix52_same_type_failure_still_informs_within_type():
    """同类型失败不硬拒：惩罚后仍可在同类型影响候选（旧失败只在同类型生效）。

    保守性来自冻结 unresolved 权重（-1.0）：只有高相关（query 项几乎全被候选
    覆盖）+ 用户确认的同类型失败才拉回阈上——低相关失败一律压到阈下。
    """
    same_failure = UtilityFeatures(
        item_id="ep-math-fail",
        content="数学练习上次在分数运算上失败了",
        failed=True,
        type_anchors=frozenset({"math_practice"}),
        user_confirmed=True,
    )
    low_relevance_score, _ = score_candidate(same_failure, query_terms={"复习", "计划"})
    assert low_relevance_score < 0.0  # 低相关失败 → 阈下
    score, reasons = score_candidate(same_failure, query_terms={"数", "学", "练", "习", "上", "次", "失", "败"})
    assert score >= 0.0  # 高相关同类型失败 → 惩罚后仍可入选（合法影响）
    assert "outcome:unresolved_episode" in reasons
    result = evaluate_history_utility(
        [same_failure],
        query_text="上次数学练习失败回顾",
        current_type_anchors=_MATH_ANCHORS,
    )
    decision = result.decisions[0]
    assert decision.selected is True
    assert "outcome:unresolved_episode" in decision.reasons


def test_fix52_failure_without_type_anchor_not_hard_rejected():
    """无类型锚的失败经验：不硬拒（无法判定异类型），靠冻结 unresolved 权重压分。"""
    untyped_failure = UtilityFeatures(
        item_id="ep-untyped-fail",
        content="完全无关领域的失败记录",
        failed=True,
        type_anchors=frozenset(),
    )
    result = evaluate_history_utility(
        [untyped_failure],
        query_text=_QUERY_MATH,
        current_type_anchors=_MATH_ANCHORS,
    )
    decision = result.decisions[0]
    assert decision.selected is False
    assert "negative_transfer_cross_type" not in decision.reasons
    assert "utility_low_score" in decision.reasons


# ---------------------------------------------------------------------------
# 验收②：required-memory 有召回；全部拒用不能过门
# ---------------------------------------------------------------------------


def test_required_memory_with_good_history_recalls():
    good = UtilityFeatures(
        item_id="ep-good",
        content="上次数学练习解决了运算顺序问题",
        resolved=True,
        type_anchors=frozenset({"math_practice"}),
    )
    bad = UtilityFeatures(
        item_id="ep-bad",
        content="单词任务失败记录",
        failed=True,
        type_anchors=frozenset({"vocab_memorization"}),
    )
    result = evaluate_history_utility(
        [good, bad],
        query_text="继续上次的数学练习",
        current_type_anchors=_MATH_ANCHORS,
    )
    assert "ep-good" in result.selected_ids
    assert "ep-bad" not in result.selected_ids
    assert result.required_memory_detected is True
    assert result.required_memory_recall is True
    assert result.passed is True


def test_required_memory_all_rejected_fails_the_gate():
    """全部拒用不能过门：required-memory 场景空选择 = recall miss + precision N/A。"""
    bad = UtilityFeatures(
        item_id="ep-bad",
        content="无关失败记录",
        failed=True,
        type_anchors=frozenset({"vocab_memorization"}),
    )
    result = evaluate_history_utility(
        [bad],
        query_text="继续上次的数学练习",
        current_type_anchors=_MATH_ANCHORS,
    )
    assert result.selected_ids == frozenset()
    assert result.required_memory_detected is True
    assert result.required_memory_recall is False
    assert result.passed is False
    payload = result.to_metric_payload()
    assert payload["verdict"] == "required_memory_recall_miss"
    # 分母策略：precision N/A（None），不是 0% 更不是 100%。
    assert payload["precision"] is None


def test_non_required_all_rejected_reports_verdict_but_not_recall_miss():
    plain = UtilityFeatures(item_id="ep-x", content="一条普通记录")
    result = evaluate_history_utility([plain], query_text="今天安排什么")
    assert result.selected_ids == frozenset()
    assert result.required_memory_detected is False
    assert result.required_memory_recall is None
    assert result.passed is True  # 非必需场景允许空选择（宁可省掉不确定历史）
    assert result.to_metric_payload()["verdict"] == "all_rejected"


# ---------------------------------------------------------------------------
# 边界与序
# ---------------------------------------------------------------------------


def _many_good(n: int) -> list[UtilityFeatures]:
    return [
        UtilityFeatures(
            item_id=f"ep-{index:02d}",
            content=f"数学练习记录 {index} 上次解决了问题",
            resolved=True,
            type_anchors=frozenset({"math_practice"}),
        )
        for index in range(n)
    ]


def test_selection_is_subset_of_input_never_resurrects():
    """选择集 ⊆ 输入集：门无任何把未输入候选加回的路径（验收③同源）。"""
    candidates = _many_good(3)
    result = evaluate_history_utility(candidates, query_text="数学")
    input_ids = {features.item_id for features in candidates}
    assert result.selected_ids <= input_ids
    assert {decision.item_id for decision in result.decisions} == input_ids


def test_top_k_budget_caps_selection():
    result = evaluate_history_utility(_many_good(10), query_text="数学", top_k=DEFAULT_TOP_K)
    assert result.selected_count == DEFAULT_TOP_K == 6
    capped = [decision for decision in result.decisions if "top_k_cap" in decision.reasons]
    assert len(capped) == 10 - DEFAULT_TOP_K


def test_deterministic_ordering_and_tiebreak():
    a = UtilityFeatures(item_id="ep-a", content="数学练习一次", resolved=True)
    b = UtilityFeatures(item_id="ep-b", content="数学练习一次", resolved=True)
    first = evaluate_history_utility([a, b], query_text="数学")
    second = evaluate_history_utility([b, a], query_text="数学")
    assert first.selected_ids == second.selected_ids == {"ep-a", "ep-b"}
    scores_first = {decision.item_id: decision.score for decision in first.decisions}
    scores_second = {decision.item_id: decision.score for decision in second.decisions}
    assert scores_first == scores_second


def test_confirmed_and_resolved_outrank_inferred_neutral():
    confirmed = UtilityFeatures(item_id="ep-conf", content="数学练习记录", resolved=True, user_confirmed=True)
    inferred = UtilityFeatures(item_id="ep-inf", content="数学练习记录", resolved=False, user_confirmed=False)
    result = evaluate_history_utility([confirmed, inferred], query_text="数学")
    scores = {decision.item_id: decision.score for decision in result.decisions}
    assert scores["ep-conf"] > scores["ep-inf"]


def test_token_cost_penalizes_longer_content():
    short = UtilityFeatures(item_id="ep-short", content="数学记录", resolved=True)
    long = UtilityFeatures(
        item_id="ep-long",
        content="数学记录" + "冗余细节" * 200,
        resolved=True,
    )
    result = evaluate_history_utility([short, long], query_text="数学")
    scores = {decision.item_id: decision.score for decision in result.decisions}
    assert scores["ep-short"] > scores["ep-long"]


def test_stale_penalty_grows_beyond_free_window():
    fresh = extract_utility_features(
        _episodic_item(id="ep-fresh", resolved_at=None, occurred_at=NOW - timedelta(days=5)),
        now=NOW,  # FIX-585c：漏传 now 会走真实 datetime.now() 回退，age 随墙钟增长，
        #           追平 stale 侧 90d 满罚后 fresh_score==stale_score（爆点 2026-12-22）
    )
    stale = extract_utility_features(
        _episodic_item(id="ep-stale", resolved_at=None, occurred_at=NOW - timedelta(days=120)),
        now=NOW,
    )
    terms = {"数学"}
    fresh_score, _ = score_candidate(fresh, query_terms=terms)
    stale_score, stale_reasons = score_candidate(stale, query_terms=terms)
    assert fresh_score > stale_score
    assert any(reason.startswith("stale_penalty:") for reason in stale_reasons)


def test_conflict_penalty_from_correction_count():
    corrected = UtilityFeatures(item_id="ep-c2", content="数学记录", resolved=True, correction_count=2)
    clean = UtilityFeatures(item_id="ep-c0", content="数学记录", resolved=True, correction_count=0)
    result = evaluate_history_utility([corrected, clean], query_text="数学")
    scores = {decision.item_id: decision.score for decision in result.decisions}
    assert scores["ep-c0"] > scores["ep-c2"]


# ---------------------------------------------------------------------------
# context_pack 接线适配面
# ---------------------------------------------------------------------------


class _Entry:
    def __init__(self, item: SimpleNamespace) -> None:
        self.item = item
        self.score = 1.0


def test_apply_history_utility_gate_metadata_only_payload():
    """metadata-only：payload 无候选正文回灌（metadata 可进 prompt 面）。"""
    good = _episodic_item()
    bad = _episodic_item(
        id="ep-vocab-fail",
        summary="单词背诵任务失败，不适合记忆任务",
        resolved_at=None,
        due_at=NOW - timedelta(days=1),
        tags=["task_type:vocab_memorization"],
    )
    kept, metadata = apply_history_utility_gate(
        [_Entry(good), _Entry(bad)],
        query_text=_QUERY_MATH,
        now=NOW,
        current_type_anchors=_MATH_ANCHORS,
    )
    assert [entry.item.id for entry in kept] == [good.id]
    assert metadata["applied"] is True
    assert metadata["passed"] is True
    assert metadata["selected_count"] == 1
    serialized = json.dumps(metadata, ensure_ascii=False)
    assert "单词背诵任务失败" not in serialized  # 正文不回灌
    assert "negative_transfer_cross_type" in serialized


def test_apply_history_utility_gate_reports_recall_miss_for_bypass():
    bad = _episodic_item(
        id="ep-vocab-fail",
        summary="单词背诵任务失败",
        resolved_at=None,
        due_at=NOW - timedelta(days=1),
        tags=["task_type:vocab_memorization"],
    )
    kept, metadata = apply_history_utility_gate(
        [_Entry(bad)],
        query_text="继续上次的数学练习",
        now=NOW,
        current_type_anchors=_MATH_ANCHORS,
    )
    assert kept == []
    assert metadata["passed"] is False
    assert metadata["required_memory_recall"] is False


# ---------------------------------------------------------------------------
# 集成面类型锚派生（一审 R1 整改）
# ---------------------------------------------------------------------------


def test_derive_current_type_anchors_from_plan_and_route():
    """plan_type + task by_type + route_intent 全部入锚，统一 strip+lower 口径
    （对齐候选侧 ``task_type:*`` tag 的 ``_type_anchors_from_tags``）。"""
    plan_context = {
        "plan_type": "Sprint",
        "task_summary": {"by_type": {"LEARNING": {"total": 2}, "TRAINING": {"total": 1}}},
    }
    anchors = derive_current_type_anchors(plan_context, route_intent="Learn", intent="chat")
    assert anchors == frozenset({"sprint", "learning", "training", "learn"})


def test_derive_current_type_anchors_falls_back_to_route_then_intent():
    assert derive_current_type_anchors(None, route_intent="error_diagnosis", intent="chat") == frozenset(
        {"error_diagnosis"}
    )
    assert derive_current_type_anchors({}, route_intent=None, intent="chat") == frozenset({"chat"})


def test_derive_current_type_anchors_empty_when_no_structured_declaration():
    """无任何结构化类型声明 → 空集（调用方必须记 anchors_unavailable，不静默）。"""
    assert derive_current_type_anchors(None) == frozenset()
    assert derive_current_type_anchors({}) == frozenset()
    assert derive_current_type_anchors({"plan_type": None, "task_summary": {"by_type": {}}}, route_intent="  ") == (
        frozenset()
    )


def test_derive_current_type_anchors_ignores_malformed_shapes():
    """畸形形状（非 dict 的 task_summary / None 值）健壮跳过，只收可用声明。"""
    anchors = derive_current_type_anchors(
        {"plan_type": "growth", "task_summary": "bad", "by_type": "also_bad"},
        route_intent=None,
        intent=None,
    )
    assert anchors == frozenset({"growth"})


def test_apply_history_utility_gate_records_anchor_availability():
    """metadata 如实登记实际参与判定的当次锚；空锚 → anchors_unavailable=True
    （硬门未触发的真相落 metadata，不许静默）。"""
    item = _episodic_item(id="ep-neutral", resolved_at=None, due_at=None)

    kept_with, meta_with = apply_history_utility_gate(
        [_Entry(item)],
        query_text=_QUERY_MATH,
        now=NOW,
        current_type_anchors=_MATH_ANCHORS,
    )
    assert meta_with["current_type_anchors"] == ["math_practice"]
    assert meta_with["anchors_unavailable"] is False
    assert kept_with

    _, meta_without = apply_history_utility_gate(
        [_Entry(item)],
        query_text=_QUERY_MATH,
        now=NOW,
    )
    assert meta_without["current_type_anchors"] == []
    assert meta_without["anchors_unavailable"] is True


def test_relevance_is_bounded_and_lexical():
    """相关性 ∈ [0,1]，词法确定性：query 项全覆盖 → 1，零覆盖 → 0。"""
    full = UtilityFeatures(item_id="ep-full", content="数学练习相关的内容")
    none = UtilityFeatures(item_id="ep-none", content="完全无关的内容")
    terms = frozenset({"数", "学", "练", "习"})
    full_score, _ = score_candidate(full, query_terms=terms)
    none_score, _ = score_candidate(none, query_terms=terms)
    assert full_score > none_score  # 覆盖差进入分数
