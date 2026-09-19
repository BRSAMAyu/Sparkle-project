"""A-04 · Aurora 联合决策行为测试（aurora_joint_decision.v1）。

测试面（卡面 Acceptance + 任务书设计要求逐项落测）：

1. **场景仿真**（``tests/aurora/fixtures/joint_decision_scenarios.json``，12 条）：
   CE canonical 三元组（学习/创作/工具——卡面 Work 2）、P paired cases、
   A 对抗（high-risk auto=0 / 荒谬提名 / 脏分配）、S 抑制门与系统面镜像。
2. **交叉边界穷举**（卡面 Acceptance 1「paired cases 不出现 intervention
   合理但执行权错误」）：全部 8 个步绑定干预 × 三种真实 X-02 分配
   （human/agent/hybrid 由真实任务因子驱动）× 两入口——任何入选的
   (intervention, mode) 对必落在 ``JOINT_STEP_BOUND_DELIVERY_MODES`` 内。
3. **high-risk auto=0**（卡面 Acceptance 2）：高危任务 × 全部步绑定提名
   ——出口 mode 永不为 agent，且 requires_human_approval 随分配镜像。
4. **联合约束层纯函数**（J 码逐个：J2/J3/J4/J5——J1 由场景与穷举覆盖）。
5. **D3/D4 对抗裁决**：两系统结论冲突的确定性落锤 + 完整归因
   （exclusions 携带分配 why）+ D4 守卫恒同（再分配被原可行集界定、
   交付因子不动守卫输入维度）。
6. **契约构造门 P3-8**：步绑定缺 allocation_decision_id 必违规、镜像
   mode 与分配 mode 不一致必违规、allocation 缺 mode 不静默（读侧对偶）。
7. **统一读门 P3-7 + shadow 治理门**：validate 门机制化；shadow 决策
   只记录不作用（专门违规码）。
8. **P3-4 发生键纪律**：occurrence_id 每次发生唯一；decision_id 内容
   寻址（同内容同号）。
9. **韧性契约**：脏输入 fuzz 恒不 raise；内部异常降级 E1。
10. **语义层**（mock LLM，真实 LLM 0 次）：默认关；开启后只能在联合
    可行集内选（越界 S2 拒收）；语义提升后 why 不携带过期的 D2/D3
    裁决码；熔断/限频/超时/异常 LLM 降级规则缺省。
11. **事件可观测**：decision.recorded 复用名 + shared-fields 契约形状。

哈希种子纪律：全部集合断言经 sorted/子集语义（任意 PYTHONHASHSEED 一致）。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from app.aurora.joint_decision import (
    JOINT_DECISION_VERSION,
    JOINT_REASONS,
    JOINT_STEP_BOUND_DELIVERY_MODES,
    JointDecisionEngine,
    allocation_decision_ref,
    build_joint_contract,
    build_joint_decision_event_metadata,
    decide_joint,
    decide_joint_two_step,
    derive_delivery_factors,
    enforce_allocation_consistency,
    read_decision_contract,
)
from app.core.aurora_decision import AURORA_NO_ACTION_REASONS
from app.services.action_allocation_policy import (
    AllocationFactors,
    decide_allocation,
)

_FIXTURE = Path(__file__).parent.parent / "aurora" / "fixtures" / "joint_decision_scenarios.json"
_SCENARIOS = json.loads(_FIXTURE.read_text(encoding="utf-8"))["scenarios"]


def _allocation_like(override: dict[str, Any]) -> SimpleNamespace:
    """构造分配事实的最小形状（J2/脏分配路径用——非重算 X-02）。"""
    return SimpleNamespace(
        mode=override.get("mode"),
        feasible_modes=tuple(override.get("feasible_modes", ())),
        why=tuple(override.get("why", ("X0.test",))),
        annotations=override.get("annotations", {}),
        layer="rule",
        confidence=0.5,
        requires_human_approval=False,
        requires_user_authored_evidence=False,
        recommended_cognitive_ownership=None,
    )


def _run_scenario(scenario: dict[str, Any]):
    """按场景 entry 语义执行：two_step / one_step(+override|task 派生分配)。"""
    factors = scenario["intervention_factors"]
    entry = scenario.get("entry", "one_step")
    if entry == "two_step":
        return decide_joint_two_step(factors, scenario.get("task_factors"))
    if scenario.get("allocation_override"):
        return decide_joint(factors, _allocation_like(scenario["allocation_override"]))
    allocation = decide_allocation(AllocationFactors.coerce(scenario.get("task_factors") or {}))
    return decide_joint(factors, allocation)


# ---------------------------------------------------------------------------
# 1. 场景仿真（fixture 12 条）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[s["id"] for s in _SCENARIOS])
def test_scenario_outputs_legal_joint_decision(scenario: dict) -> None:
    expect = scenario["expect"]
    joint = _run_scenario(scenario)

    # selected 恒为封闭目录成员；why 恒为封闭 JOINT_REASONS 码（有序精确）
    assert joint.selected in INTERVENTION_CATALOG
    assert joint.selected == expect["selected"], (
        f"{scenario['id']}: selected {joint.selected!r} != {expect['selected']!r}"
    )
    assert list(joint.why) == list(expect["why"]), (
        f"{scenario['id']}: why {joint.why} != {tuple(expect['why'])}"
    )
    assert set(joint.why) <= JOINT_REASONS
    assert joint.mode == expect["mode"], f"{scenario['id']}: mode {joint.mode!r}"

    if expect.get("no_action_reason") is not None:
        assert joint.selected in {"no_action", "abstain"}
        assert joint.policy_evaluation.no_action_reason == expect["no_action_reason"]
        assert joint.policy_evaluation.no_action_reason in AURORA_NO_ACTION_REASONS

    for target, reason in expect.get("exclusions_subset", []):
        got = {(e.target, e.reason) for e in joint.exclusions}
        assert (target, reason) in got, (
            f"{scenario['id']}: 期望联合排除 ({target}, {reason})，实得 {sorted(got)}"
        )
    if expect.get("exclusions") == []:
        assert joint.exclusions == (), f"{scenario['id']}: 联合排除应为空"

    for target, reason in expect.get("policy_exclusion_subset", []):
        got = {(d["target"], d["reason"]) for d in joint.annotations.get("policy_exclusions", [])}
        assert (target, reason) in got, (
            f"{scenario['id']}: 期望 policy 排除 ({target}, {reason})，实得 {sorted(got)}"
        )

    if "task_allocation_mode" in expect:
        task_mode = joint.task_allocation.mode if joint.task_allocation is not None else None
        assert task_mode == expect["task_allocation_mode"], f"{scenario['id']}: task alloc {task_mode!r}"
    if "allocation_mode" in expect:
        assert joint.allocation is not None and joint.allocation.mode == expect["allocation_mode"]
    if "cognitive_ownership" in expect:
        assert joint.cognitive_ownership == expect["cognitive_ownership"]
    if "requires_user_authored_evidence" in expect:
        assert joint.requires_user_authored_evidence == expect["requires_user_authored_evidence"]
    if "requires_human_approval" in expect:
        assert joint.requires_human_approval == expect["requires_human_approval"]
    if "reallocated" in expect:
        assert ("D4.delivery_reallocation_applied" in joint.why) == expect["reallocated"]
    if "allocation_ref" in expect:
        assert joint.allocation_ref == expect["allocation_ref"], (
            f"{scenario['id']}: allocation_ref {joint.allocation_ref!r}"
        )
    if "allocation_why_subset" in expect:
        assert joint.allocation is not None
        assert set(expect["allocation_why_subset"]) <= set(joint.annotations.get("allocation_why", ()))


def test_canonical_trio_families_present() -> None:
    """卡面 Work 2：学习/创作/工具 canonical 三元组必须在 fixture 中注册。"""
    families = {s["family"] for s in _SCENARIOS}
    assert {"canonical_learning", "canonical_creation", "canonical_tooling"} <= families


# ---------------------------------------------------------------------------
# 2. 交叉边界穷举（Acceptance 1：paired cases 不出现执行权错误）
# ---------------------------------------------------------------------------


def _task_for_mode(mode: str) -> dict[str, Any]:
    """真实任务因子驱动 X-02 产出指定 mode（分配由真核心算出，非手造）。"""
    if mode == "human":
        return {
            "task_ref": f"task://cross-{mode}",
            "learning_goal": True,
            "cognitive_ownership": "user_core",
            "tool_advantage": "low",
            "task_summary": "学习核心任务",
        }
    if mode == "agent":
        return {
            "task_ref": f"task://cross-{mode}",
            "explicit_intent": "delegate",
            "cognitive_ownership": "delegated",
            "tool_advantage": "high",
            "risk_class": "low",
            "task_summary": "机械委派任务",
        }
    return {
        "task_ref": f"task://cross-{mode}",
        "cognitive_ownership": "shared",
        "tool_advantage": "medium",
        "task_summary": "人机协作任务",
    }


@pytest.mark.parametrize("task_mode", ["human", "agent", "hybrid"])
@pytest.mark.parametrize("intervention", sorted(JOINT_STEP_BOUND_DELIVERY_MODES))
def test_cross_boundary_step_bound_delivery_invariant(intervention: str, task_mode: str) -> None:
    """8 步绑定干预 × 3 分配 × 两入口：入选对的 mode 必落交付允许集内。"""
    task = _task_for_mode(task_mode)
    allocation = decide_allocation(AllocationFactors.coerce(task))
    assert allocation.mode == task_mode  # 测试前提：因子族确实驱动该 mode

    factors = {
        "nominated": (intervention,),
        "capabilities": frozenset(
            INTERVENTION_CATALOG[intervention].capability_requirements
        ),
        "permissions": frozenset(INTERVENTION_CATALOG[intervention].permission_requirements),
        "has_task_context": True,
        "materiality_sufficient": True,
    }
    allowed = JOINT_STEP_BOUND_DELIVERY_MODES[intervention]

    for joint in (
        decide_joint(factors, allocation),
        decide_joint_two_step(factors, task),
    ):
        if joint.selected == intervention:
            assert joint.mode in allowed, (
                f"{intervention} × {task_mode}: 入选 mode {joint.mode!r} 不在交付集 {sorted(allowed)}"
            )
            assert joint.mode == joint.allocation.mode  # 镜像恒等于分配事实
        else:
            assert joint.selected == "no_action"
            assert joint.mode is None


def test_cross_boundary_exhaustive_no_illegal_pair_in_feasible_set() -> None:
    """联合可行集本身不含非法对：任何分配下产出的 joint_feasible_pairs
    中步绑定成员的 mode 必落交付集（选择前的硬边界，非仅终选校验）。"""
    for task_mode in ("human", "agent", "hybrid"):
        task = _task_for_mode(task_mode)
        joint = decide_joint_two_step(
            {
                "nominated": ("practice", "review", "rescope"),
                "capabilities": frozenset({"chat", "llm_generate", "task_write"}),
                "permissions": frozenset({"plan_adjust"}),
                "has_task_context": True,
                "materiality_sufficient": True,
            },
            task,
        )
        for name, mode in joint.joint_feasible_pairs:
            if name in JOINT_STEP_BOUND_DELIVERY_MODES:
                assert mode in JOINT_STEP_BOUND_DELIVERY_MODES[name], (
                    f"{task_mode}: 可行集含非法对 ({name}, {mode})"
                )


# ---------------------------------------------------------------------------
# 3. high-risk auto=0（Acceptance 2）
# ---------------------------------------------------------------------------


_HIGH_RISK_TASK = {
    "task_ref": "task://hi-cross",
    "risk_class": "high",
    "reversible": False,
    "cognitive_ownership": "delegated",
    "tool_advantage": "high",
    "task_summary": "高危不可逆操作",
}


@pytest.mark.parametrize("intervention", sorted(JOINT_STEP_BOUND_DELIVERY_MODES))
def test_high_risk_never_auto(intervention: str) -> None:
    """高危任务 × 任意步绑定提名：联合出口 mode 永不为 agent（auto=0）。"""
    factors = {
        "nominated": (intervention,),
        "capabilities": frozenset(
            INTERVENTION_CATALOG[intervention].capability_requirements
        ),
        "permissions": frozenset(INTERVENTION_CATALOG[intervention].permission_requirements),
        "has_task_context": True,
        "materiality_sufficient": True,
    }
    for joint in (
        decide_joint(factors, decide_allocation(AllocationFactors.coerce(_HIGH_RISK_TASK))),
        decide_joint_two_step(factors, _HIGH_RISK_TASK),
    ):
        assert joint.mode != "agent", f"{intervention}: high-risk 出现 agent/auto"
        if joint.selected == intervention:
            # 若入选：必须落在交付集内且携带 human approval 要求（R1 镜像）
            assert joint.mode in JOINT_STEP_BOUND_DELIVERY_MODES[intervention]
            assert joint.requires_human_approval is True
        else:
            assert joint.selected == "no_action"


def test_high_risk_allocation_facts() -> None:
    """高危任务的 X-02 事实：feasible 不含 agent + approval=True（联合出口
    auto=0 的上游保证——联合层不再放行被守卫排除的 mode）。"""
    allocation = decide_allocation(AllocationFactors.coerce(_HIGH_RISK_TASK))
    assert "agent" not in allocation.feasible_modes
    assert allocation.requires_human_approval is True


# ---------------------------------------------------------------------------
# 4. 联合约束层纯函数（J 码逐个）
# ---------------------------------------------------------------------------


def _pair_reasons(intervention: str, mode: Any, allocation: Any = None) -> tuple[str, ...]:
    from app.aurora.joint_decision import _pair_guard_reasons

    return _pair_guard_reasons(intervention, mode, allocation)


def test_j3_inert_must_not_carry_mode() -> None:
    assert "J3.inert_must_not_carry_mode" in _pair_reasons("no_action", "agent")
    assert _pair_reasons("no_action", None) == ()


def test_j5_requires_allocation_unbacked() -> None:
    for name in ("delegate", "execute", "co_execute"):
        assert INTERVENTION_CATALOG[name].requires_allocation
        assert "J5.requires_allocation_unbacked" in _pair_reasons(name, None)


def test_j2_mode_outside_allocation_feasible() -> None:
    dirty = _allocation_like({"mode": "agent", "feasible_modes": ["human", "hybrid"]})
    assert "J2.mode_outside_allocation_feasible" in _pair_reasons("review", "agent", dirty)


def test_j4_learning_guard_agent_pair_excluded() -> None:
    """J4：学习守卫生效 × agent 交付——X-02 语义层改 mode 或手工脏分配的
    联合面确定性排除（防代写是联合不变式；真实 X-02 决策恒不产此对，
    此处按脏路径构造——纯函数契约）。"""
    guarded = _allocation_like(
        {"mode": "agent", "feasible_modes": ["agent"], "annotations": {"learning_guard": True}}
    )
    assert "J4.learning_deskilling_pair" in _pair_reasons("review", "agent", guarded)
    # 同分配无学习守卫 → 不触发 J4（review 允许 agent 交付）
    clean = _allocation_like({"mode": "agent", "feasible_modes": ["agent"]})
    assert "J4.learning_deskilling_pair" not in _pair_reasons("review", "agent", clean)


def test_j1_delivery_table_pairs() -> None:
    for name, allowed in JOINT_STEP_BOUND_DELIVERY_MODES.items():
        for mode in ("human", "agent", "hybrid"):
            reasons = _pair_reasons(name, mode, None)
            assert ("J1.delivery_mode_incompatible" in reasons) == (mode not in allowed)


# ---------------------------------------------------------------------------
# 5. D3/D4 对抗裁决与守卫恒同
# ---------------------------------------------------------------------------


_LEARNING_TASK = {
    "task_ref": "task://adv-001",
    "learning_goal": True,
    "cognitive_ownership": "user_core",
    "tool_advantage": "low",
    "task_summary": "对抗：学习任务 practice 冲突",
}
_PRACTICE_FACTORS = {
    "nominated": ("practice",),
    "capabilities": frozenset({"chat", "llm_generate"}),
    "permissions": frozenset(),
    "has_task_context": True,
    "materiality_sufficient": True,
}


def test_d3_conflict_attribution_complete() -> None:
    """一步冲突：分配事实优先 + 归因完整（哪个提名被哪个 J 码排除、
    背后 allocation why 是什么）。"""
    allocation = decide_allocation(AllocationFactors.coerce(_LEARNING_TASK))
    joint = decide_joint(_PRACTICE_FACTORS, allocation)
    assert joint.selected == "no_action"
    assert "D3.conflict_allocation_precedence" in joint.why
    exclusion = next(e for e in joint.exclusions if e.target == "practice")
    assert exclusion.reason == "J1.delivery_mode_incompatible"
    assert exclusion.allocation_mode == "human"
    assert "G1.learning_guard_no_agent" in exclusion.allocation_why  # X-02 归因随行


def test_d4_rescue_bounded_by_original_feasible_set() -> None:
    """D4 守卫恒同机制化：再分配 mode 必 ∈ 原分配可行集 ∩ 交付集；
    task_allocation 对照保留。"""
    joint = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
    assert joint.selected == "practice"
    assert joint.mode == "hybrid"
    assert joint.task_allocation is not None
    original_feasible = set(joint.task_allocation.feasible_modes)
    assert joint.mode in original_feasible  # 未越守卫界
    assert joint.mode in JOINT_STEP_BOUND_DELIVERY_MODES["practice"]
    assert joint.allocation is not joint.task_allocation  # 交付分配是新判定


def test_derive_delivery_factors_preserves_guard_inputs() -> None:
    """交付锚定投影只动选择层维度：学习/风险/隐私/具身/置信/显式意图/
    偏好原样保留（守卫输入不变 → 守卫结论恒同）。"""
    task = AllocationFactors.coerce(
        {
            "task_ref": "task://derive-001",
            "learning_goal": True,
            "risk_class": "medium",
            "reversible": False,
            "explicit_intent": "self",
            "embodiment_required": True,
            "privacy": "sensitive",
            "confidence": 0.3,
            "user_preference": "prefer_human",
            "task_summary": "守卫因子保留检查",
        }
    )
    delivered = derive_delivery_factors(task, "practice")
    assert delivered.learning_goal is task.learning_goal
    assert delivered.risk_class == task.risk_class
    assert delivered.reversible is task.reversible
    assert delivered.explicit_intent == task.explicit_intent
    assert delivered.embodiment_required is task.embodiment_required
    assert delivered.privacy == task.privacy
    assert delivered.confidence == task.confidence
    assert delivered.user_preference == task.user_preference
    assert delivered.task_ref == task.task_ref
    # 改变的只有选择层：practice 族 llm_generate → 工具优势 high
    assert delivered.tool_advantage == "high"


def test_d4_rescue_never_escapes_original_feasible_set() -> None:
    """D4 守卫恒同（负例）：分配可行集本身不含交付 mode（privacy
    restricted → feasible 仅 human）时，再分配**不得**越界救回——交付
    重判给出的 hybrid 不在原可行集内，弃用，维持 D3。越界即守卫因子
    被污染（如隐私守卫被绕过），联合面是最后一道闸。"""
    restricted_task = {
        "task_ref": "task://pv-001",
        "privacy": "restricted",
        "learning_goal": True,
        "cognitive_ownership": "user_core",
        "tool_advantage": "low",
        "task_summary": "隐私受限学习任务",
    }
    allocation = decide_allocation(AllocationFactors.coerce(restricted_task))
    assert allocation.feasible_modes == ("human",)  # 测试前提：可行集仅 human
    joint = decide_joint_two_step(_PRACTICE_FACTORS, restricted_task)
    assert joint.selected == "no_action"
    assert "D4.delivery_reallocation_applied" not in joint.why
    assert "D3.conflict_allocation_precedence" in joint.why
    assert joint.mode is None


def test_d4_belt_rejects_polluted_delivery_allocation() -> None:
    """D4 第二道皮带（机制测试）：即使上游分配器被污染（返回越出原可行集
    的交付分配——真实 X-02 因 derive 保留全部守卫因子而结构性不可能），
    联合层仍以「再分配 mode ∈ 原可行集 ∩ 交付集」硬界拒绝救回。经
    ``decide_allocation_fn`` 注入通道测（生产签名公开参数）。"""
    from app.services.action_allocation_policy import AllocationDecision

    restricted_task = {
        "task_ref": "task://pv-002",
        "privacy": "restricted",
        "learning_goal": True,
        "cognitive_ownership": "user_core",
        "tool_advantage": "low",
        "task_summary": "隐私受限学习任务（皮带测试）",
    }

    def _polluted_allocator(factors):
        # 首调（任务步）返回真实 X-02 判定；交付步（第二次）返回越出原
        # 可行集的 hybrid——模拟守卫因子被污染的上游。
        nonlocal calls
        calls += 1
        if calls == 1:
            return decide_allocation(factors)
        return AllocationDecision(
            mode="hybrid",
            why=("X0.polluted",),
            confidence=0.5,
            layer="rule",
            feasible_modes=("human", "hybrid"),
        )

    calls = 0
    joint = decide_joint_two_step(_PRACTICE_FACTORS, restricted_task, decide_allocation_fn=_polluted_allocator)
    assert joint.selected == "no_action"
    assert "D4.delivery_reallocation_applied" not in joint.why  # 越界救回被皮带拒绝
    assert "D3.conflict_allocation_precedence" in joint.why


def test_d4_rescue_deterministic_and_reproducible() -> None:
    """对抗裁决确定性：同输入两跑同结论（裁决序是纯函数）。"""
    first = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
    second = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
    assert (first.selected, first.mode, first.why) == (second.selected, second.mode, second.why)


# ---------------------------------------------------------------------------
# 6. 契约构造门（P3-8）
# ---------------------------------------------------------------------------


def _delegate_joint():
    task = {
        "task_ref": "task://contract-001",
        "explicit_intent": "delegate",
        "cognitive_ownership": "delegated",
        "tool_advantage": "high",
        "risk_class": "low",
        "task_summary": "契约构造基准",
    }
    allocation = decide_allocation(AllocationFactors.coerce(task))
    factors = {
        "nominated": ("delegate",),
        "capabilities": frozenset({"chat", "tool_execution"}),
        "permissions": frozenset({"task_execute"}),
        "has_task_context": True,
        "materiality_sufficient": True,
    }
    return decide_joint(factors, allocation), task


def test_build_contract_requires_allocation_id_for_step_bound() -> None:
    joint, _ = _delegate_joint()
    contract, violations = build_joint_contract(
        joint, uuid4(), cognition_tier="l2_intervention"
    )
    assert contract is None
    assert any("allocation_decision_id" in v and "P3-8" in v for v in violations)


def test_build_contract_backfills_allocation_ref() -> None:
    joint, task = _delegate_joint()
    alloc_id = joint.allocation.decision_id(AllocationFactors.coerce(task))
    contract, violations = build_joint_contract(
        joint, uuid4(), cognition_tier="l2_intervention", allocation_decision_id=alloc_id
    )
    assert contract is not None and violations == ()
    assert contract.allocation_ref == allocation_decision_ref(alloc_id)
    assert contract.allocation_ref.startswith("decision://alloc_")
    assert contract.execution_mode is not None and contract.execution_mode.value == "agent"
    assert contract.validate() == ()
    assert contract.annotations["joint_decision_version"] == JOINT_DECISION_VERSION
    assert contract.annotations["occurrence_id"] == joint.occurrence_id


def test_enforce_allocation_consistency_hard_rules() -> None:
    """P3-8 硬化：ref 已指向分配时缺 mode 不静默；镜像不一致违规；
    学习守卫 × agent 违规；无 ref 的纯对话域决策不受影响。"""
    joint, task = _delegate_joint()
    alloc_id = joint.allocation.decision_id(AllocationFactors.coerce(task))
    contract, _ = build_joint_contract(
        joint, uuid4(), cognition_tier="l2_intervention", allocation_decision_id=alloc_id
    )
    # 正常：一致 → 无违规
    assert enforce_allocation_consistency(contract, joint.allocation) == ()
    # 缺 mode 的分配（P3-8：不再静默放行）
    no_mode = replace(joint.allocation, mode=None) if hasattr(joint.allocation, "mode") else None
    if no_mode is not None:
        violations = enforce_allocation_consistency(contract, no_mode)
        assert any("without a mode" in v and "P3-8" in v for v in violations)
    # mode 不一致
    mismatch = _allocation_like({"mode": "human", "feasible_modes": ["human"], "annotations": {}})
    violations = enforce_allocation_consistency(contract, mismatch)
    assert any("!= allocation mode" in v for v in violations)
    # 学习守卫 × agent 镜像（J4 读侧对偶）
    guarded = _allocation_like(
        {"mode": "agent", "feasible_modes": ["agent"], "annotations": {"learning_guard": True}}
    )
    violations = enforce_allocation_consistency(contract, guarded)
    assert any("anti-deskilling" in v for v in violations)


def test_enforce_consistency_no_ref_is_noop_for_conversation_domain() -> None:
    factors = {
        "nominated": ("clarify",),
        "capabilities": frozenset({"chat"}),
        "permissions": frozenset(),
        "materiality_sufficient": True,
    }
    joint = decide_joint(factors, None)
    contract, violations = build_joint_contract(
        joint, uuid4(), cognition_tier="l1_light", clarifying_question="现在最想先做哪一步？"
    )
    assert contract is not None and violations == ()
    assert contract.allocation_ref is None  # A-01 边界：纯对话域不携带
    assert enforce_allocation_consistency(contract, object()) == ()


# ---------------------------------------------------------------------------
# 7. 统一读门（P3-7 + shadow 治理门）
# ---------------------------------------------------------------------------


def _live_payload() -> dict[str, Any]:
    joint, task = _delegate_joint()
    alloc_id = joint.allocation.decision_id(AllocationFactors.coerce(task))
    contract, _ = build_joint_contract(
        joint, uuid4(), cognition_tier="l2_intervention", allocation_decision_id=alloc_id
    )
    payload = contract.to_dict()
    return payload


def test_read_gate_accepts_live_valid_contract() -> None:
    payload = _live_payload()
    contract, violations = read_decision_contract(payload)
    assert contract is not None and violations == ()
    assert contract.governance_mode == "live"


def test_read_gate_rejects_non_mapping_and_broken_payload() -> None:
    assert read_decision_contract(None)[0] is None
    assert read_decision_contract("not-a-dict")[0] is None
    broken = _live_payload()
    broken["intervention_type"] = "not_in_vocab"
    contract, violations = read_decision_contract(broken)
    assert contract is None and violations


def test_read_gate_shadow_never_applies() -> None:
    """shadow 治理门：shadow 决策只记录对比、不得作用于用户可见行为——
    读门以专门违规码拒收（可与「数据坏」区分观测）。"""
    payload = _live_payload()
    payload["governance_mode"] = "shadow"
    contract, violations = read_decision_contract(payload)
    assert contract is None
    assert any("recorded but never applied" in v for v in violations)


def test_read_gate_allocation_consistency_with_payload() -> None:
    """读门 + allocation 载荷：镜像不一致在读侧被拦（P3-8 读侧）。"""
    payload = _live_payload()
    mismatched = {"mode": "human", "annotations": {"learning_guard": False}}
    contract, violations = read_decision_contract(payload, allocation_payload=mismatched)
    assert contract is None
    assert any("!= allocation mode" in v for v in violations)
    # 一致载荷 → 通过
    payload2 = _live_payload()
    matched = {"mode": payload2["execution_mode"], "annotations": {"learning_guard": False}}
    contract, violations = read_decision_contract(payload2, allocation_payload=matched)
    assert contract is not None and violations == ()


# ---------------------------------------------------------------------------
# 8. P3-4 发生键纪律（occurrence_id 唯一 / decision_id 内容寻址）
# ---------------------------------------------------------------------------


def test_occurrence_id_unique_per_decision() -> None:
    joint1 = decide_joint(_PRACTICE_FACTORS, decide_allocation(AllocationFactors.coerce(_LEARNING_TASK)))
    joint2 = decide_joint(_PRACTICE_FACTORS, decide_allocation(AllocationFactors.coerce(_LEARNING_TASK)))
    assert joint1.occurrence_id != joint2.occurrence_id  # 发生键唯一
    # 内容决策同构（裁决确定性）
    assert (joint1.selected, joint1.mode, joint1.why) == (joint2.selected, joint2.mode, joint2.why)


def test_decision_id_content_addressed_across_occurrences() -> None:
    """decision_id 是内容锚：同内容跨 occurrence 复用同号（P3-4 by design）；
    occurrence_id 是发生键：恒不同。"""
    user = uuid4()
    delegate_factors = {
        "nominated": ("delegate",),
        "capabilities": frozenset({"chat", "tool_execution"}),
        "permissions": frozenset({"task_execute"}),
        "has_task_context": True,
        "materiality_sufficient": True,
    }
    joint1, task = _delegate_joint()
    joint2 = decide_joint(delegate_factors, joint1.allocation)
    alloc_id = joint1.allocation.decision_id(AllocationFactors.coerce(task))
    c1, _ = build_joint_contract(joint1, user, cognition_tier="l2_intervention", allocation_decision_id=alloc_id)
    c2, _ = build_joint_contract(joint2, user, cognition_tier="l2_intervention", allocation_decision_id=alloc_id)
    # 两次发生（occurrence 不同）同内容 → 同 decision_id（内容寻址）
    assert c1.annotations["occurrence_id"] != c2.annotations["occurrence_id"]
    assert c1.decision_id_or_compute() == c2.decision_id_or_compute()


def test_event_metadata_carries_occurrence_key() -> None:
    """事件可观测（M-07/X-05 同构）：shared-fields 契约 + 决策记录本体经
    extra 携带（扁平并入 metadata）；occurrence_id 发生键随行。"""
    joint = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
    user = uuid4()
    metadata = build_joint_decision_event_metadata(user_id=user, joint=joint)
    # shared-fields 契约（X-02 同款五字段）
    for field in ("event_id", "user_id", "schema_version", "source", "service", "occurred_at"):
        assert field in metadata, f"缺少 shared field {field}"
    assert metadata["service"] == "aurora_joint_decision"
    # 决策记录本体（extra 扁平并入）：schema 版本 + 发生键
    assert metadata["joint_decision"]["schema_version"] == JOINT_DECISION_VERSION
    assert metadata["occurrence_id"] == joint.occurrence_id
    assert metadata["joint_decision"]["selected"] == "practice"
    assert "decision_id" not in metadata  # 无契约时不携带
    # 契约在场时 decision_id（内容锚）随行
    delivery_factors = derive_delivery_factors(_LEARNING_TASK, "practice")
    contract, violations = build_joint_contract(
        joint,
        user,
        cognition_tier="l2_intervention",
        allocation_decision_id=joint.allocation.decision_id(delivery_factors),
    )
    assert contract is not None and violations == ()
    metadata2 = build_joint_decision_event_metadata(user_id=user, joint=joint, contract=contract)
    assert metadata2["decision_id"] == contract.decision_id_or_compute()


# ---------------------------------------------------------------------------
# 9. 韧性契约（脏输入 fuzz / NEVER raises / E1 降级）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dirty_factors,dirty_allocation",
    [
        (None, None),
        ({}, {}),
        ("garbage", 42),
        ({"nominated": ("coexecute", "connect"), "capabilities": "not-a-set"}, None),
        ({"nominated": ("practice",), "capabilities": frozenset({"chat"}), "has_task_context": "yes"}, None),
        ({"quiet_hours": 1, "materiality_sufficient": []}, {"mode": "AUTO", "feasible_modes": "nope"}),
    ],
)
def test_never_raises_on_dirty_inputs(dirty_factors, dirty_allocation) -> None:
    joint = decide_joint(dirty_factors, dirty_allocation)
    assert joint.selected in INTERVENTION_CATALOG
    assert joint.selected in {"no_action", "abstain"} or joint.mode is not None
    two_step = decide_joint_two_step(dirty_factors, dirty_factors)
    assert two_step.selected in INTERVENTION_CATALOG


def test_internal_error_degrades_to_e1() -> None:
    """属性访问即炸的因子对象 → E1 降级 no_action（韧性契约）。"""

    class _Evil:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    joint = decide_joint(_Evil(), _Evil())
    assert joint.selected == "no_action"
    assert joint.why == ("E1.degraded_to_rule_default",)
    assert joint.layer == "error_degraded"


def test_deterministic_same_inputs_same_outputs() -> None:
    for _ in range(3):
        joint = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
        assert (joint.selected, joint.mode, joint.why) == ("practice", "hybrid", joint.why)


# ---------------------------------------------------------------------------
# 10. 语义层（mock LLM；真实 LLM 0 次；默认关）
# ---------------------------------------------------------------------------


def _eligible_rule_decision(task: dict[str, Any] | None = None):
    """构造 semantic_eligible 的规则层决策：空提名（开放选择面——规则层
    无确定性序可依，D2 落 no_action 地板，但可行集含 actionable 成员）。"""
    factors = {
        "nominated": (),  # 开放选择：无人提名 → 规则层 no_action，语义层开放
        "capabilities": frozenset({"chat", "llm_generate", "task_write"}),
        "permissions": frozenset({"plan_adjust"}),
        "has_task_context": True,
        "materiality_sufficient": True,
    }
    if task is None:
        task = {
            "task_ref": "task://sem-001",
            "cognitive_ownership": "shared",
            "tool_advantage": "medium",
            "task_summary": "语义层基准任务",
        }
    joint = decide_joint(factors, decide_allocation(AllocationFactors.coerce(task)))
    return factors, task, joint


class TestSemanticLayer:
    def teardown_method(self):
        JointDecisionEngine._reset_breaker()

    def test_settings_default_pins_semantic_off(self):
        # P3-1（R2 回执）：构造器默认已有钉，settings 级默认也必须钉死——
        # 翻 True 属部署级语义通道开启，不允许静默发生。
        from app.config.settings import Settings

        assert Settings.model_fields["SPARKLE_JOINT_SEMANTIC_ENABLED"].default is False

    @pytest.mark.asyncio
    async def test_default_off_never_calls_llm(self):
        calls = []

        async def llm(prompt):
            calls.append(prompt)
            return {"intervention": "rescope"}

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=False)
        factors, task, rule = _eligible_rule_decision()
        result = await engine.evaluate(factors, decide_allocation(AllocationFactors.coerce(task)))
        assert calls == []  # 默认关：注入了 LLM 也不调用
        assert result == rule or (result.selected, result.mode) == (rule.selected, rule.mode)

    @pytest.mark.asyncio
    async def test_semantic_acceptance_within_joint_legal_set(self):
        """开启后 LLM 只能在联合可行集内选；提升后 why 不携带过期的
        D2/D3 裁决码（它们描述的是规则层 no_action 结局），layer=semantic。"""

        async def llm(prompt):
            return {"intervention": "clarify"}  # 系统面成员（联合可行集内）

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True, semantic_timeout_seconds=1.0)
        factors, task, rule = _eligible_rule_decision()
        assert rule.semantic_eligible is True
        result = await engine.evaluate(factors, decide_allocation(AllocationFactors.coerce(task)))
        assert result.selected == "clarify"
        assert result.layer == "semantic"
        assert "D2.no_legal_joint_nominee_no_action" not in result.why  # 过期裁决码已剥离
        assert "D3.conflict_allocation_precedence" not in result.why
        assert "D1.first_legal_joint_nominee" in result.why
        legal = {name for name, _ in rule.joint_feasible_pairs}
        assert "clarify" in legal
        assert result.annotations["semantic_proposed"] == "clarify"

    @pytest.mark.asyncio
    async def test_semantic_outside_joint_legal_rejected_s2(self):
        """LLM 越联合可行集 → S2 拒收（A-02 词表），规则缺省保留；
        不计熔断（越界是正常拒绝路径）。用学习分配使 practice 落在
        **policy-可行但联合-不可行**（J1）——证明联合集比 A-02 可行集更紧。"""

        async def llm(prompt):
            return {"intervention": "practice"}

        learning_task = {
            "task_ref": "task://sem-002",
            "learning_goal": True,
            "cognitive_ownership": "user_core",
            "tool_advantage": "low",
            "task_summary": "学习核心任务",
        }
        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True, semantic_timeout_seconds=1.0)
        factors, task, rule = _eligible_rule_decision(learning_task)
        # 前提：practice 在 A-02 policy 可行集内、但被 J1 排除在联合可行集外
        assert "practice" in rule.policy_evaluation.feasible_interventions
        assert "practice" not in {name for name, _ in rule.joint_feasible_pairs}
        result = await engine.evaluate(factors, decide_allocation(AllocationFactors.coerce(task)))
        assert result.selected == rule.selected == "no_action"
        assert result.layer == "semantic_fallback"
        assert "S2.semantic_outside_feasible_rejected" in result.policy_evaluation.why
        assert JointDecisionEngine._semantic_failures == 0  # S2 不计熔断

    @pytest.mark.asyncio
    async def test_semantic_timeout_degrades_and_counts_breaker(self):
        async def llm(prompt):
            await asyncio.sleep(10)

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True, semantic_timeout_seconds=0.01)
        factors, task, rule = _eligible_rule_decision()
        result = await engine.evaluate(factors, decide_allocation(AllocationFactors.coerce(task)))
        assert (result.selected, result.why) == (rule.selected, rule.why)  # 规则缺省保留
        assert JointDecisionEngine._semantic_failures == 1

    @pytest.mark.asyncio
    async def test_semantic_breaker_opens_after_three_failures(self):
        async def llm(prompt):
            raise RuntimeError("llm down")

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True, semantic_timeout_seconds=1.0)
        factors, task, _ = _eligible_rule_decision()
        allocation = decide_allocation(AllocationFactors.coerce(task))
        for _ in range(3):
            await engine.evaluate(factors, allocation)
        assert JointDecisionEngine._semantic_open_until > 0  # 熔断开
        calls = []

        async def recovering(prompt):
            calls.append(prompt)
            return {"intervention": "clarify"}

        engine._semantic_llm = recovering
        result = await engine.evaluate(factors, allocation)
        assert calls == []  # 熔断期内不再触达
        assert result.selected == "no_action"

    @pytest.mark.asyncio
    async def test_rate_limit_keeps_rule_default(self):
        async def llm(prompt):
            return {"intervention": "clarify"}

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True, semantic_max_per_minute=1, semantic_timeout_seconds=1.0)
        factors, task, _ = _eligible_rule_decision()
        allocation = decide_allocation(AllocationFactors.coerce(task))
        first = await engine.evaluate(factors, allocation)
        assert first.selected == "clarify"  # 第一次通过
        # 人为打满窗口（不动熔断状态）→ 限频 → 规则缺省
        JointDecisionEngine._semantic_calls_this_window = 99
        JointDecisionEngine._semantic_failures = 0
        second = await engine.evaluate(factors, allocation)
        assert second.selected == "no_action"

    @pytest.mark.asyncio
    async def test_not_eligible_never_touched(self):
        """规则层非开放选择（直接选中）→ 语义层不介入。"""
        calls = []

        async def llm(prompt):
            calls.append(prompt)
            return {"intervention": "clarify"}

        engine = JointDecisionEngine(semantic_llm=llm, semantic_enabled=True)
        joint, task = _delegate_joint()
        result = await engine.evaluate(
            {
                "nominated": ("delegate",),
                "capabilities": frozenset({"chat", "tool_execution"}),
                "permissions": frozenset({"task_execute"}),
                "has_task_context": True,
                "materiality_sufficient": True,
            },
            decide_allocation(AllocationFactors.coerce(task)),
        )
        assert calls == []
        assert result.selected == "delegate"


# ---------------------------------------------------------------------------
# 11. to_dict 审计同构（M-07/X-05 形状）
# ---------------------------------------------------------------------------


def test_to_dict_audit_shape() -> None:
    joint = decide_joint_two_step(_PRACTICE_FACTORS, _LEARNING_TASK)
    record = joint.to_dict()
    assert record["schema_version"] == JOINT_DECISION_VERSION
    assert record["occurrence_id"] == joint.occurrence_id
    assert record["intervention_policy_version"]  # A-02 版本随行
    assert record["allocation_policy_version"]  # X-02 版本随行
    assert isinstance(record["exclusions"], list)
    assert record["layer"] in {"rule", "semantic", "semantic_fallback", "error_degraded"}
    # 双系统归因随行（冲突如何落锤可审计）
    assert "allocation_why" in record["annotations"]
    assert "policy_why" in record["annotations"]
