"""X-02 blind scenario eval —— 60+ 场景盲评基准（验收①的固化守卫）。

口径：**规则层独跑**（语义层默认关闭；decide_allocation 纯函数）。fixture
targets 标注自 HUMAN_AGENT_HYBRID.md 原则；rubric 盲跑只见 factors。
阈值守卫：整体准确率 ≥ 0.90；high-risk auto-agent = 0；学习类 agent = 0。
词表/规则演进任何回退即红。复现：`pytest tests/unit/test_action_allocation_eval.py -q`。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.action_allocation_policy import AllocationFactors, decide_allocation

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "action_allocation_eval_v1.json"

#: 学习型类别（agent 必须为 0）。
LEARNING_CATEGORIES = {
    "learning_writing",
    "learning_practice",
    "explicit_delegate_learning",
}


def _load():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return payload["scenarios"]


def _run(scenarios):
    results = []
    for scenario in scenarios:
        factors = AllocationFactors.coerce(scenario["factors"])
        decision = decide_allocation(factors)
        results.append((scenario, decision, decision.mode == scenario["target"]))
    return results


def test_eval_set_has_at_least_60_scenarios():
    scenarios = _load()
    assert len(scenarios) >= 60, f"blind eval set must have >=60 scenarios, got {len(scenarios)}"
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids)), "duplicate scenario ids"


def test_eval_covers_all_eight_allocation_dimensions():
    """八维分配因子每一维至少在一个场景中取判别值（覆盖完整性）。"""
    scenarios = _load()
    seen_dimensions = set()
    for scenario in scenarios:
        factors = scenario["factors"]
        for key in factors:
            seen_dimensions.add(key)
    for dimension in (
        "cognitive_ownership",
        "tool_advantage",
        "risk_class",
        "embodiment_required",
        "privacy",
        "confidence",
        "time_pressure",
        "explicit_intent",
        "user_preference",
    ):
        assert dimension in seen_dimensions, f"dimension {dimension} not covered by eval set"


def test_eval_overall_accuracy_at_least_90_percent():
    results = _run(_load())
    hits = sum(1 for _, _, ok in results if ok)
    accuracy = hits / len(results)
    misses = [(s["id"], s["category"], d.mode, s["target"]) for s, d, ok in results if not ok]
    assert accuracy >= 0.90, f"blind accuracy {accuracy:.4f} < 0.90; misses={misses}"


def test_high_risk_auto_agent_is_zero():
    """验收①硬断言：high-risk 场景 auto-agent = 0。"""
    results = _run(_load())
    high_risk = [(s, d) for s, d, _ in results if s["category"] == "high_risk"]
    assert len(high_risk) >= 5
    agents = [s["id"] for s, d in high_risk if d.mode == "agent"]
    assert agents == [], f"high-risk auto-agent must be 0, got {agents}"
    assert all(d.requires_human_approval for _, d in high_risk), "high-risk must require human approval"


def test_learning_categories_agent_is_zero():
    results = _run(_load())
    learning = [(s, d) for s, d, _ in results if s["category"] in LEARNING_CATEGORIES]
    assert len(learning) >= 10
    agents = [s["id"] for s, d in learning if d.mode == "agent"]
    assert agents == [], f"learning tasks must never get agent mode, got {agents}"


def test_eval_mode_distribution_is_balanced():
    """三类都有足量代表（防退化：rubric 不能只会输出一个 mode）。"""
    results = _run(_load())
    counts = {"human": 0, "agent": 0, "hybrid": 0}
    for _, d, _ in results:
        counts[d.mode] += 1
    assert counts["agent"] >= 8, counts
    assert counts["hybrid"] >= 8, counts
    assert counts["human"] >= 8, counts


def test_structural_invariants_hold_on_every_scenario():
    """不变式（按因子动态判定，不依赖类别标签）：

    - 学习守卫生效（LEARNING/TRAINING/REFLECTION/user_core/learning_goal）→ mode != agent；
    - privacy=restricted → mode == human（agent 连准备面都无权限）；
    - embodiment_required → mode != agent；
    - high/critical 或 medium+不可逆 → mode != agent 且 requires_human_approval；
    - privacy=sensitive → mode != agent。
    """
    from app.services.action_allocation_policy import _high_risk, _learning_guard_active

    for scenario in _load():
        factors = AllocationFactors.coerce(scenario["factors"])
        decision = decide_allocation(factors)
        sid = scenario["id"]
        if _learning_guard_active(factors):
            assert decision.mode != "agent", f"{sid}: learning guard violated"
        if factors.privacy == "restricted":
            assert decision.mode == "human", f"{sid}: restricted privacy must force human"
        if factors.embodiment_required is True:
            assert decision.mode != "agent", f"{sid}: embodiment violated"
        if factors.privacy == "sensitive":
            assert decision.mode != "agent", f"{sid}: sensitive privacy must block agent"
        if _high_risk(factors):
            assert decision.mode != "agent", f"{sid}: high-risk auto-agent"
            assert decision.requires_human_approval is True, f"{sid}: high-risk must require approval"


def test_eval_is_deterministic():
    scenarios = _load()
    first = [d.mode for _, d, _ in _run(scenarios)]
    second = [d.mode for _, d, _ in _run(scenarios)]
    assert first == second
