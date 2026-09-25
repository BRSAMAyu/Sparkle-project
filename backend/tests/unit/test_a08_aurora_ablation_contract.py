"""A-08 · 消融协议契约锁（pytest sqlite 内存口径）。

锁的不是数字（数字在 raw/summary 产物），是**协议与判据的结构性正确**：
消融臂能力面确实缺席、结果模型判据自洽、fixed 臂零引擎调用、经验回路的
真实服务链（D-05 漏斗 → A-05 证据门 → 重排）行为正确。产品代码零改动。
"""

from __future__ import annotations

import json

import pytest

from tests.aurora_ablation.engine import RESULT_RULES_VERSION, run_persona_arm
from tests.aurora_ablation.metrics import (
    METRICS_RULES_VERSION,
    UTILITY_WEIGHTS,
    extract_counterexamples,
    summarize_arm,
)
from tests.aurora_ablation.persona import (
    ARMS,
    EPISODE_SESSION_BUDGET,
    FIXED_TEMPLATE_INTERVENTION,
    PERSONAS,
    build_population,
    match_class,
    truthful_branch_key,
)

pytestmark = [pytest.mark.asyncio]


def _persona(persona_id: str):
    return next(p for p in PERSONAS if p.persona_id == persona_id)


# ---------------------------------------------------------------------------
# 1. 时间线/判据真源自洽（纯函数面）
# ---------------------------------------------------------------------------


def test_population_protocol_shape() -> None:
    """10 persona、四臂、每 persona ≥1 episode 且含对照会话（协议形状锁）。"""
    population = build_population()
    assert len(population) == 10
    assert ARMS == ("full", "no_memory", "no_experience", "fixed_policy")
    for spec in population:
        episodes = [e for e in spec.timeline if e.kind == "episode"]
        controls = [e for e in spec.timeline if e.kind == "control"]
        assert episodes, spec.persona_id
        assert controls, spec.persona_id
        assert spec.channel in ("chat", "journey")
        assert spec.explicitness in ("vague", "mixed", "explicit")
        assert spec.correction_propensity in ("none", "active")


def test_match_class_rule_score() -> None:
    """分派匹配规则分三值锁（primary/secondary/wrong）——allocation 判据真源。"""
    assert match_class("explain", "knowledge") == "primary"
    assert match_class("retrieve", "knowledge") == "secondary"
    assert match_class("practice", "knowledge") == "wrong"
    assert match_class(None, "knowledge") == "wrong"
    assert match_class("no_action", "knowledge") == "wrong"


def test_result_rules_frozen() -> None:
    """结果模型/指标权重版本钉死（口径漂移即红）。"""
    assert RESULT_RULES_VERSION == "aurora_ablation_result_rules.v1"
    assert METRICS_RULES_VERSION == "aurora_ablation_metrics.v1"
    assert EPISODE_SESSION_BUDGET == 3
    assert UTILITY_WEIGHTS["resolved_episode"] == 1.0
    assert UTILITY_WEIGHTS["unresolved_episode"] == -1.0


def test_truthful_answer_family_fallback_deterministic() -> None:
    """truthful 回答：真值在分支 → 直答；不在 → 同族最大支持分支（确定性）。"""
    # knowledge 恰在 q_direction_vs_push 的 cant_push 分支
    assert truthful_branch_key("q_direction_vs_push", "knowledge") == "cant_push"
    # clarity 不在 q_tried_and_checked 任何分支 → 同族（execution_friction）
    # 支持数最多的分支，确定性可复算
    first = truthful_branch_key("q_tried_and_checked", "clarity")
    second = truthful_branch_key("q_tried_and_checked", "clarity")
    assert first == second
    # clarity 属 execution_friction；tried_confident 分支共享该族支持数最多
    # （difficulty+plan_drift 均为 execution_friction）→ 确定性落此分支
    assert first == "tried_confident"


# ---------------------------------------------------------------------------
# 2. fixed-policy 臂：零引擎面、恒模板、无问句（结构锁）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ["fixed_policy"])
async def test_fixed_policy_arm_structure(arm: str) -> None:
    records = await run_persona_arm(_persona("p03_explicit_difficulty"), arm=arm)
    stuck = [r for r in records if r["kind"] == "stuck"]
    assert stuck
    for r in stuck:
        assert r["chat"] is None and r["journey"] is None
        assert r["decision_used"] == FIXED_TEMPLATE_INTERVENTION
        assert r["questions_this_session"] == 0
    summary = summarize_arm(records, arm=arm)
    assert summary["invariants"]["fixed_arm_zero_engine_calls"] is True
    # 模板 bot 对一切恒 explain → difficulty（主提名 split）错位必现
    assert any(r["match_class"] == "wrong" for r in stuck)


# ---------------------------------------------------------------------------
# 3. 消融臂能力面缺席（协议锁——消融必须真的消融）
# ---------------------------------------------------------------------------


async def test_no_memory_arm_correction_channel_absent() -> None:
    """no-memory：纠正通道缺席（纠正记忆不落库）+ 旅程事实面无失败痕迹。"""
    records = await run_persona_arm(_persona("p05_correction_loop"), arm="no_memory")
    stuck = [r for r in records if r["kind"] == "stuck"]
    assert stuck
    assert all(not r.get("correction") for r in stuck)
    summary = summarize_arm(records, arm="no_memory")
    assert summary["invariants"]["no_memory_zero_corrections"] is True


async def test_no_experience_arm_experience_faces_absent() -> None:
    """no-experience：spine 空 + patch 全无（chat 决策面无适应输入）。"""
    records = await run_persona_arm(_persona("p01_experience_reinforce"), arm="no_experience")
    stuck = [r for r in records if r["kind"] == "stuck"]
    for r in stuck:
        chat = r.get("chat") or {}
        assert not chat.get("patch_moves")
        assert not chat.get("applied_patch_ids")
        assert not chat.get("spine_keys_at_turn")
    summary = summarize_arm(records, arm="no_experience")
    assert summary["invariants"]["no_experience_zero_patches"] is True
    assert summary["invariants"]["no_experience_zero_spine"] is True


async def test_full_arm_experience_loop_builds_real_patch() -> None:
    """full：同型两段后存在真实 active patch（D-05 漏斗 → 证据门 → 激活）。"""
    records = await run_persona_arm(_persona("p01_experience_reinforce"), arm="full")
    stuck = [r for r in records if r["kind"] == "stuck"]
    resolved = [r for r in stuck if r.get("resolved_now")]
    assert resolved, "knowledge 显性段应可解决"
    admissions = [
        r.get("patch_admission") for r in stuck if r.get("patch_admission")
    ]
    assert admissions, "经验回路应产生 patch 准入记录"
    assert any((a or {}).get("state") in ("evidenced", "active") for a in admissions)
    # exposure 走真实服务：recorded=True 的行带 decision_id（aurora_ 前缀契约）
    exposures = [r["exposure"] for r in stuck if r.get("exposure")]
    assert exposures
    recorded = [e for e in exposures if e.get("recorded")]
    assert all(str(e["decision_id"]).startswith("aurora_") for e in recorded)


# ---------------------------------------------------------------------------
# 4. 结果模型自洽（raw 全量口径；mini 人口）
# ---------------------------------------------------------------------------


async def test_resolution_requires_match_and_budget() -> None:
    """解决必命中（primary/secondary）且预算≤3——结果模型判据结构性自洽。"""
    records = await run_persona_arm(_persona("p03_explicit_difficulty"), arm="full")
    ends = [r for r in records if r["kind"] == "episode_end"]
    assert ends
    for e in ends:
        assert e["resolved"] is True
        assert e["resolving_match_class"] in ("primary", "secondary")
        assert 1 <= e["sessions_used"] <= EPISODE_SESSION_BUDGET
    stuck = [r for r in records if r["kind"] == "stuck"]
    for r in stuck:
        assert r["attempt"] < EPISODE_SESSION_BUDGET


async def test_summary_metrics_recomputed_from_raw() -> None:
    """summary 全字段由 raw 程序化复算（--summarize-only 同路径的一致性锁）。"""
    all_records: list[dict] = []
    for arm in ("full", "fixed_policy"):
        all_records.extend(await run_persona_arm(_persona("p03_explicit_difficulty"), arm=arm))
    for arm in ("full", "fixed_policy"):
        records = [r for r in all_records if r["arm"] == arm]
        summary = summarize_arm(records, arm=arm)
        ends = [r for r in records if r["kind"] == "episode_end"]
        fails = [r for r in records if r["kind"] == "episode_fail"]
        assert summary["episodes_total"] == len(ends) + len(fails)
        assert summary["episodes_resolved"] == len(ends)
        if summary["episodes_total"]:
            expected = round(summary["episodes_resolved"] / summary["episodes_total"], 4)
            assert summary["stuck_accuracy"] == expected
        controls = [r for r in records if r["kind"] == "control"]
        intrusions = sum(1 for r in controls if r.get("control_intrusion"))
        assert summary["control_intrusions"] == intrusions


def test_counterexample_extraction_covers_burden_axes() -> None:
    """反例提取面完整（不剪）：B1 tie/纠正环/对照侵入/结构缺口/预算失败。"""
    assert set(extract_counterexamples([])) == {
        "b1_tie_acts",
        "correction_cycles",
        "control_intrusions",
        "chat_structural_no_action",
        "budget_failures",
    }


# ---------------------------------------------------------------------------
# 5. 全人口跑通的烟雾口径（协议在真实服务面上不炸；sqlite 隔离）
# ---------------------------------------------------------------------------


async def test_population_two_arms_end_to_end() -> None:
    """全人口 × 双臂端到端：记录齐、臂标签正确、summary 可产出。"""
    records: list[dict] = []
    for arm in ("full", "no_memory"):
        for spec in build_population():
            records.extend(await run_persona_arm(spec, arm=arm))
    for arm in ("full", "no_memory"):
        sub = [r for r in records if r["arm"] == arm]
        assert sub
        summary = summarize_arm(sub, arm=arm)
        assert summary["episodes_total"] == 20
        assert summary["invariants"]["budget_respected"] is True
        assert summary["invariants"]["resolution_requires_match"] is True
    if True:  # 双臂人口一致性（同一时间线在两臂出现）
        personas_by_arm = {
            arm: {r["persona"] for r in records if r["arm"] == arm} for arm in ("full", "no_memory")
        }
        assert personas_by_arm["full"] == personas_by_arm["no_memory"]


def test_spec_version_pin() -> None:
    """协议版本钉死（时间线/判据改动必须显式 bump）。"""
    from tests.aurora_ablation.persona import ABLATION_SPEC_VERSION

    assert ABLATION_SPEC_VERSION == "aurora_ablation_spec.v1"
    assert json.dumps(ARMS) == '["full", "no_memory", "no_experience", "fixed_policy"]'
