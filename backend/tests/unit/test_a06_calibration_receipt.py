"""A-06 · Calibration Receipt 契约与纯函数测试（aurora_calibration_receipt.v1）。

冻结面：动作词表 / 呈现裁决 / 不确定标签 / 阈值参数（sha256 双钉）+ 门矩阵 +
CoT 守界（rationale 是组成摘要：绝不含内部 reason 码与决策环注释）。
"""

from __future__ import annotations

import hashlib
import json

import pytest

from app.core.aurora_decision import AURORA_UNCERTAINTY_KINDS
from app.aurora.calibration_receipt import (
    CALIBRATION_RECEIPT_ACTIONS,
    CALIBRATION_RECEIPT_VERSION,
    MAX_CALIBRATION_SURFACES_PER_DAY,
    MAX_REFERENCED_REFS,
    RECEIPT_ACTION_AUTHORITIES,
    RECEIPT_SURFACE_DECISIONS,
    RECEIPT_UNCERTAINTY_LABELS,
    UNCERTAIN_REFERENCE_CONFIDENCE,
    build_calibration_receipt,
    calibration_receipt_fingerprint,
    evaluate_receipt_surfacing,
    is_uncertain_reference,
    receipt_action_plan,
)

# ---------------------------------------------------------------------------
# 冻结面双钉
# ---------------------------------------------------------------------------


def test_action_vocabulary_exact() -> None:
    assert CALIBRATION_RECEIPT_ACTIONS == {"not_relevant", "wrong", "change_scope", "delete"}


def test_surface_decisions_exact() -> None:
    assert RECEIPT_SURFACE_DECISIONS == {"surfaced", "ambient", "hidden"}


def test_uncertainty_labels_cover_aurora_vocabulary_exactly() -> None:
    assert set(RECEIPT_UNCERTAINTY_LABELS) == set(AURORA_UNCERTAINTY_KINDS)
    assert all(label.strip() for label in RECEIPT_UNCERTAINTY_LABELS.values())


def test_every_action_declares_delegated_authority() -> None:
    assert set(RECEIPT_ACTION_AUTHORITIES) == set(CALIBRATION_RECEIPT_ACTIONS)
    for authority in RECEIPT_ACTION_AUTHORITIES.values():
        assert "MemoryService" in authority or "provenance" in authority or "memory." in authority


def test_fingerprint_stable() -> None:
    expected = hashlib.sha256(
        json.dumps(
            {
                "version": CALIBRATION_RECEIPT_VERSION,
                "actions": sorted(CALIBRATION_RECEIPT_ACTIONS),
                "authorities": dict(sorted(RECEIPT_ACTION_AUTHORITIES.items())),
                "surface_decisions": sorted(RECEIPT_SURFACE_DECISIONS),
                "uncertainty_labels": dict(sorted(RECEIPT_UNCERTAINTY_LABELS.items())),
                "uncertain_confidence": UNCERTAIN_REFERENCE_CONFIDENCE,
                "max_calibration_per_day": MAX_CALIBRATION_SURFACES_PER_DAY,
                "max_referenced_refs": MAX_REFERENCED_REFS,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert calibration_receipt_fingerprint() == expected


# ---------------------------------------------------------------------------
# 呈现门（触发有度）
# ---------------------------------------------------------------------------


def test_gate_hidden_without_references() -> None:
    decision, reason = evaluate_receipt_surfacing(referenced_total=0, uncertain_total=0, calibration_shown_today=0)
    assert (decision, reason) == ("hidden", "no_referenced_memory")


def test_gate_ambient_when_all_confident() -> None:
    decision, reason = evaluate_receipt_surfacing(referenced_total=2, uncertain_total=0, calibration_shown_today=0)
    assert decision == "ambient"
    assert reason == "all_confident_no_uncertainty"


def test_gate_surfaced_with_uncertainty_within_budget() -> None:
    decision, reason = evaluate_receipt_surfacing(
        referenced_total=2, uncertain_total=1, calibration_shown_today=MAX_CALIBRATION_SURFACES_PER_DAY - 1
    )
    assert (decision, reason) == ("surfaced", "uncertain_reference_within_budget")


def test_gate_downgrades_to_ambient_after_daily_budget() -> None:
    decision, reason = evaluate_receipt_surfacing(
        referenced_total=2, uncertain_total=1, calibration_shown_today=MAX_CALIBRATION_SURFACES_PER_DAY
    )
    assert (decision, reason) == ("ambient", "calibration_daily_budget_reached")


# ---------------------------------------------------------------------------
# 不确定引用判定（真实条目事实）
# ---------------------------------------------------------------------------


def test_uncertain_reference_by_low_confidence() -> None:
    assert is_uncertain_reference({"confidence": 0.4, "user_confirmed": True}) is True
    assert is_uncertain_reference({"confidence": 0.9, "user_confirmed": True}) is False


def test_uncertain_reference_by_unconfirmed_inference() -> None:
    assert is_uncertain_reference({"confidence": 0.95, "user_confirmed": False}) is True


def test_uncertain_reference_explicit_flag_wins() -> None:
    assert is_uncertain_reference({"uncertain": True, "confidence": 0.99, "user_confirmed": True}) is True
    assert is_uncertain_reference({"uncertain": False, "confidence": 0.3, "user_confirmed": False}) is False


# ---------------------------------------------------------------------------
# 回执装配
# ---------------------------------------------------------------------------


def _refs() -> list[dict]:
    return [
        {"id": "m1", "type": "episodic", "content": "先做样例", "confidence": 0.9, "user_confirmed": True},
        {"id": "m2", "type": "episodic", "content": "怕演算", "confidence": 0.4, "user_confirmed": False},
    ]


def test_build_receipt_composition_and_refs() -> None:
    receipt = build_calibration_receipt(
        response_id="resp1", referenced_memories=_refs(), knowledge_refs=["OS.pdf"]
    )
    assert receipt is not None
    assert receipt["receipt_type"] == "memory_reference_receipt"
    assert receipt["schema_version"] == CALIBRATION_RECEIPT_VERSION
    assert receipt["receipt_id"].startswith("calreceipt_")
    assert receipt["used_count"] == 2
    assert [ref["id"] for ref in receipt["referenced_memories"]] == ["m1", "m2"]
    assert receipt["referenced_memories"][1]["uncertain"] is True
    assert receipt["referenced_memories"][0]["uncertain"] is False
    assert sorted(receipt["referenced_memories"][0]["actions"]) == ["change_scope", "delete", "not_relevant", "wrong"]
    assert receipt["knowledge_refs"] == ["OS.pdf"]
    assert receipt["uncertainties"] == [
        {"kind": "unverified_inference", "label": RECEIPT_UNCERTAINTY_LABELS["unverified_inference"], "count": 1}
    ]
    assert receipt["surface"]["decision"] == "surfaced"
    assert receipt["surface"]["presentation"] == "calibration"


def test_build_receipt_deterministic_id() -> None:
    one = build_calibration_receipt(response_id="resp1", referenced_memories=_refs())
    two = build_calibration_receipt(response_id="resp1", referenced_memories=_refs())
    assert one is not None and two is not None
    assert one["receipt_id"] == two["receipt_id"]
    other = build_calibration_receipt(response_id="resp2", referenced_memories=_refs())
    assert other is not None
    assert other["receipt_id"] != one["receipt_id"]


def test_build_receipt_none_without_valid_refs() -> None:
    assert build_calibration_receipt(response_id="r", referenced_memories=[]) is None
    assert build_calibration_receipt(response_id="r", referenced_memories=[{"content": "no id"}]) is None


def test_build_receipt_cap_crefs_at_five() -> None:
    many = [{"id": f"m{i}", "confidence": 0.9, "user_confirmed": True} for i in range(8)]
    receipt = build_calibration_receipt(response_id="r", referenced_memories=many)
    assert receipt is not None
    assert receipt["used_count"] == MAX_REFERENCED_REFS


def test_build_receipt_ambient_for_confident_refs() -> None:
    receipt = build_calibration_receipt(
        response_id="r",
        referenced_memories=[{"id": "m1", "confidence": 0.9, "user_confirmed": True}],
    )
    assert receipt is not None
    assert receipt["surface"]["decision"] == "ambient"
    assert receipt["surface"]["presentation"] == "ambient"
    assert receipt["uncertainties"] == []
    # 纠偏动作在 ambient 档保持完整（门不弱化纠偏面）
    assert sorted(receipt["referenced_memories"][0]["actions"]) == [
        "change_scope",
        "delete",
        "not_relevant",
        "wrong",
    ]


# ---------------------------------------------------------------------------
# CoT 守界（产品红线）：rationale 是组成摘要，不是推理流
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["rationale_summary", "summary", "decision_reason"])
def test_rationale_fields_identical_composition_summary(field: str) -> None:
    receipt = build_calibration_receipt(response_id="r", referenced_memories=_refs(), knowledge_refs=["OS.pdf"])
    assert receipt is not None
    assert receipt[field] == receipt["rationale_summary"]


def test_rationale_contains_no_internal_reason_codes() -> None:
    receipt = build_calibration_receipt(response_id="r", referenced_memories=_refs())
    assert receipt is not None
    blob = json.dumps(receipt, ensure_ascii=False)
    for marker in (
        "policy_why",
        "joint_why",
        "allocation_why",
        "S1.sufficient",
        "S2.sufficient",
        "Q1.insufficient",
        "B1.budget",
        "R0.",
        "friction_reasons",
        "chain-of-thought",
    ):
        assert marker not in blob, f"internal reasoning marker leaked into receipt: {marker}"


def test_rationale_only_states_receipt_composition_facts() -> None:
    receipt = build_calibration_receipt(response_id="r", referenced_memories=_refs(), knowledge_refs=["OS.pdf"])
    assert receipt is not None
    rationale = receipt["rationale_summary"]
    assert "2 条你的记忆" in rationale
    assert "1 份参考材料" in rationale
    assert "1 条我还不太确定" in rationale
    # 不含任何对「为什么这样推理」的过程性陈述
    for process_word in ("推理", "因此我判断", "思考过程", "我认为因为"):
        assert process_word not in rationale


# ---------------------------------------------------------------------------
# 动作计划（路由面）
# ---------------------------------------------------------------------------


def test_action_plan_wrong_dual_mode() -> None:
    supersede = receipt_action_plan(action="wrong", corrected_content="其实是先看示例")
    assert supersede["mode"] == "supersede"
    lower = receipt_action_plan(action="wrong")
    assert lower["mode"] == "lower_confidence"


def test_action_plan_rejects_dirty_action() -> None:
    assert receipt_action_plan(action="") == {}
    assert receipt_action_plan(action="nuke_everything") == {}
    assert receipt_action_plan(action="DELETE') OR 1=1 --") == {}


def test_action_plan_all_four_actions_map_to_authority() -> None:
    for action in sorted(CALIBRATION_RECEIPT_ACTIONS):
        plan = receipt_action_plan(action=action)
        assert plan["action"] == action
        assert plan["authority"] == RECEIPT_ACTION_AUTHORITIES[action]
