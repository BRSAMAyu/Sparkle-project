"""A-02 · Intervention Policy Engine V1 测试（scenario simulator + 通道纪律）。

覆盖面（卡面 acceptance ②：至少 30 基础 scenario 可输出合法决策——本文件
消费 45 条 fixture 场景，38 基线 + 7 对抗）：
1. **场景仿真**：``tests/aurora/fixtures/intervention_policy_scenarios.json``
   全量 parametrize——每条断言 selected（恒封闭目录成员）/ why（封闭 reason
   码，有序精确）/ exclusion_reasons（子集）/ no_action_reason（封闭词表）/
   feasible 包含与排除 / resolved mode / semantic_eligible；
2. **词表冻结**：INTERVENTION_POLICY_REASONS / LAYERS 精确集 + sha256 双钉；
3. **确定性与纯函数性**：同输入同输出；dict 与 factors 输入等价；无 IO；
4. **韧性**：脏输入（None/非映射/脏串/脏枚举）确定性归一，永不 raise；
   inert 地板（任意因子下 no_action/abstain 恒可行）；
5. **构造门（P3-7 预留）**：build_decision_contract 非法组合 → (None,
   violations) 显式拒绝，绝不静默产出非法契约；合法组合 → validate()==()；
6. **P3-8 钉死**：执行面干预缺分配 mode → R4 确定性剔除（脏 allocation 同归
   None）；
7. **LLM 参数化通道（默认关，mock 测，真实 LLM 0 次）**：默认不调用；开启后
   只能在 feasible 内选（S2 越界拒收）；熔断/限频/超时降级规则缺省。

哈希种子纪律（A-01 P2-1 教训）：全部集合断言经 sorted/子集语义，任意
PYTHONHASHSEED 下结果一致（fixture 期望均为排序无关比较）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from app.aurora.intervention_policy import (
    INTERVENTION_POLICY_LAYERS,
    INTERVENTION_POLICY_REASONS,
    INTERVENTION_POLICY_VERSION,
    InterventionPolicyEngine,
    InterventionPolicyEvaluation,
    InterventionPolicyFactors,
    build_decision_contract,
    evaluate_intervention_policy,
)
from app.core.aurora_decision import AURORA_NO_ACTION_REASONS

_FIXTURE = Path(__file__).parent.parent / "aurora" / "fixtures" / "intervention_policy_scenarios.json"
_SCENARIOS = json.loads(_FIXTURE.read_text(encoding="utf-8"))["scenarios"]


def _reasons_for(evaluation: InterventionPolicyEvaluation, target: str) -> set[str]:
    return {reason for name, reason in evaluation.exclusions if name == target}


# ---------------------------------------------------------------------------
# 1. 场景仿真（45 条：38 基线 S 系列 + 7 对抗 A 系列）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[s["id"] for s in _SCENARIOS])
def test_scenario_outputs_legal_decision(scenario: dict) -> None:
    factors = scenario["factors"]
    expect = scenario["expect"]
    evaluation = evaluate_intervention_policy(factors)

    # selected 恒为封闭目录成员（无字符串自由动作）
    assert evaluation.selected in INTERVENTION_CATALOG, (
        f"{scenario['id']}: selected {evaluation.selected!r} 不在封闭目录"
    )
    assert evaluation.selected == expect["selected"], (
        f"{scenario['id']}: selected {evaluation.selected!r} != {expect['selected']!r}"
    )
    # why：封闭 reason 码，有序精确
    assert list(evaluation.why) == list(expect["why"]), (
        f"{scenario['id']}: why {evaluation.why} != {tuple(expect['why'])}"
    )
    assert set(evaluation.why) <= INTERVENTION_POLICY_REASONS
    # exclusion_reasons：子集断言（每目标至少含期望码）
    for target, reason in (expect.get("exclusion_reasons") or {}).items():
        assert reason in _reasons_for(evaluation, target), (
            f"{scenario['id']}: {target} 期望剔除码 {reason}，实得 {sorted(_reasons_for(evaluation, target))}"
        )
    # inert 选中必带封闭 no_action_reason；actionable 必带 mode 镜像
    if expect.get("no_action_reason") is not None:
        assert evaluation.selected in {"no_action", "abstain"}
        assert evaluation.no_action_reason == expect["no_action_reason"]
        assert evaluation.no_action_reason in AURORA_NO_ACTION_REASONS
        assert evaluation.resolved_execution_mode is None
    if "resolved_execution_mode" in expect:
        assert evaluation.resolved_execution_mode == expect["resolved_execution_mode"], (
            f"{scenario['id']}: mode {evaluation.resolved_execution_mode!r}"
        )
    # feasible 包含/排除
    for name in expect.get("feasible_contains", []):
        assert name in evaluation.feasible_interventions, f"{scenario['id']}: {name} 应可行"
    for name in expect.get("feasible_not_contains", []):
        assert name not in evaluation.feasible_interventions, f"{scenario['id']}: {name} 不应可行"
    if "semantic_eligible" in expect:
        assert evaluation.semantic_eligible is expect["semantic_eligible"], scenario["id"]
    # policy version 与目录指纹随行（卡面 Work 3：可审计）
    assert evaluation.policy_version == INTERVENTION_POLICY_VERSION
    assert evaluation.catalog_fingerprint


def test_scenario_count_meets_acceptance() -> None:
    """卡面 acceptance ②：至少 30 基础 scenario。"""
    base = [s for s in _SCENARIOS if s["id"].startswith("S")]
    adversarial = [s for s in _SCENARIOS if s["id"].startswith("A")]
    assert len(base) >= 30
    assert len(adversarial) >= 5  # 对抗面（非法组合/权限不足/上下文缺失）
    assert len(_SCENARIOS) >= 35


def test_every_scenario_decision_is_contractible_or_deterministic() -> None:
    """每条场景都可投影为合法 AuroraDecisionContract（integration 证据：
    no_action 族直接构造；clarify 场景显式补 question；其余 actionable 由
    engine 的 resolved mode 支撑）。"""
    user_id = uuid4()
    for scenario in _SCENARIOS:
        evaluation = evaluate_intervention_policy(scenario["factors"])
        kwargs: dict = {"cognition_tier": "l2_intervention"}
        if evaluation.selected == "clarify":
            kwargs["clarifying_question"] = "你现在最想推进哪一部分？"
        contract, violations = build_decision_contract(evaluation, user_id, **kwargs)
        assert contract is not None and violations == (), (
            f"{scenario['id']}: 契约构造失败 {violations}"
        )


# ---------------------------------------------------------------------------
# 2. 词表冻结（精确集 + sha256 双钉）
# ---------------------------------------------------------------------------


def test_policy_reasons_vocabulary_frozen() -> None:
    expected = {
        "R0.nominee_out_of_catalog",
        "R1.capability_missing",
        "R2.permission_missing",
        "R3.task_context_missing",
        "R4.allocation_mode_missing",
        "R5.allocation_mode_conflict",
        "R6.quiet_hours_suppression",
        "R7.cooldown_active",
        "R8.materiality_below_threshold",
        "R9.proactive_budget_exhausted",
        "D1.first_legal_nominee",
        "D2.no_legal_nominee_no_action",
        "X1.explicit_request_bypassed_gate",
        "S1.semantic_refined",
        "S2.semantic_outside_feasible_rejected",
        "E1.degraded_to_rule_default",
    }
    assert set(INTERVENTION_POLICY_REASONS) == expected
    digest = hashlib.sha256(json.dumps(sorted(INTERVENTION_POLICY_REASONS)).encode()).hexdigest()[:16]
    assert digest == "9264ba28d6af0f64"


def test_policy_layers_vocabulary_frozen() -> None:
    assert set(INTERVENTION_POLICY_LAYERS) == {"rule", "semantic", "semantic_fallback", "error_degraded"}


# ---------------------------------------------------------------------------
# 3. 确定性与纯函数性
# ---------------------------------------------------------------------------


def test_deterministic_same_input_same_output() -> None:
    factors = {
        "capabilities": ["task_write", "chat"],
        "permissions": ["plan_adjust"],
        "nominated": ["rescope", "pause"],
        "has_task_context": True,
    }
    first = evaluate_intervention_policy(factors)
    second = evaluate_intervention_policy(factors)
    assert first.to_dict() == second.to_dict()


def test_factors_and_mapping_inputs_equivalent() -> None:
    mapping = {"capabilities": ["chat"], "nominated": ["clarify"]}
    via_factors = evaluate_intervention_policy(InterventionPolicyFactors.coerce(mapping))
    via_mapping = evaluate_intervention_policy(mapping)
    assert via_factors.to_dict() == via_mapping.to_dict()


# ---------------------------------------------------------------------------
# 4. 韧性（脏输入确定性归一；inert 地板）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dirty",
    [
        None,
        42,
        "rescope",
        [],
        {"capabilities": "not-a-list"},
        {"nominated": [None, 42, {"obj": 1}]},
        {"capabilities": ["chat"], "nominated": "CLARIFY", "allocation_mode": "AUTO"},
        {"quiet_hours": "yes", "has_task_context": "true"},
    ],
)
def test_dirty_inputs_never_raise(dirty) -> None:
    evaluation = evaluate_intervention_policy(dirty)
    assert evaluation.selected in INTERVENTION_CATALOG
    assert set(evaluation.why) <= INTERVENTION_POLICY_REASONS


def test_strict_bool_coercion_documented() -> None:
    """布尔因子严格化：字符串 "true"/"yes" 归 False（确定性脏输入契约，
    与 X-02 宽松解析不同——本引擎因子面更窄，fixture 全用真布尔）。"""
    evaluation = evaluate_intervention_policy(
        {"capabilities": ["llm_generate"], "nominated": ["practice"], "has_task_context": "true"}
    )
    assert "R3.task_context_missing" in _reasons_for(evaluation, "practice")


def test_inert_floor_always_feasible() -> None:
    """地板性质：任意因子（含冷却指向 inert、全缺省）下 inert 出口恒可行。"""
    for cooldown in [None, "no_action", "abstain", "rescope"]:
        evaluation = evaluate_intervention_policy({"cooldown_target": cooldown})
        assert "no_action" in evaluation.feasible_interventions
        assert "abstain" in evaluation.feasible_interventions


# ---------------------------------------------------------------------------
# 5. 构造门（P3-7 预留）：非法组合显式拒绝，合法组合 validate==()
# ---------------------------------------------------------------------------


def test_build_contract_valid_actionable() -> None:
    evaluation = evaluate_intervention_policy(
        {"capabilities": ["task_write"], "permissions": ["plan_adjust"], "nominated": ["rescope"], "has_task_context": True}
    )
    contract, violations = build_decision_contract(
        evaluation, uuid4(), cognition_tier="l2_intervention", evidence_refs=("signal://task_granularity_fit",)
    )
    assert contract is not None
    assert violations == ()
    assert contract.intervention_type == "rescope"
    assert contract.execution_mode is not None and contract.execution_mode.value == "hybrid"
    # policy version + 选择理由进契约 annotations（卡面 Work 3）
    assert contract.annotations["policy_version"] == INTERVENTION_POLICY_VERSION
    assert contract.annotations["policy_why"] == list(evaluation.why)


def test_build_contract_clarify_requires_question() -> None:
    evaluation = evaluate_intervention_policy({"capabilities": ["chat"], "nominated": ["clarify"]})
    contract, violations = build_decision_contract(evaluation, uuid4(), cognition_tier="l1_light")
    assert contract is None
    assert any("clarifying_question" in v for v in violations)
    # 补 question 后可构造
    contract2, violations2 = build_decision_contract(
        evaluation, uuid4(), cognition_tier="l1_light", clarifying_question="先确认目标分数？"
    )
    assert contract2 is not None and violations2 == ()
    assert contract2.clarifying_question == "先确认目标分数？"


def test_build_contract_rejects_out_of_vocabulary_inputs() -> None:
    evaluation = evaluate_intervention_policy({})
    # tier 词表外
    contract, violations = build_decision_contract(evaluation, uuid4(), cognition_tier="l9_magic")
    assert contract is None and violations
    # governance 词表外
    contract, violations = build_decision_contract(evaluation, uuid4(), cognition_tier="l0_rules", governance_mode="off")
    assert contract is None and violations
    # evidence ref scheme 外（裸 token）
    contract, violations = build_decision_contract(
        evaluation, uuid4(), cognition_tier="l0_rules", evidence_refs=("aurora_route",)
    )
    assert contract is None and any("scheme" in v for v in violations)
    # selected 词表外（对抗构造）
    hacked = InterventionPolicyEvaluation(
        selected="mega_rescope",
        feasible_interventions=(),
        exclusions=(),
        why=(),
        resolved_execution_mode="agent",
        no_action_reason=None,
    )
    contract, violations = build_decision_contract(hacked, uuid4(), cognition_tier="l0_rules")
    assert contract is None and violations


# ---------------------------------------------------------------------------
# 6. P3-8 钉死：执行面干预缺分配 mode → 确定性 R4，绝不静默放行
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("intervention", ["delegate", "execute", "co_execute"])
def test_execution_family_requires_allocation_mode(intervention: str) -> None:
    base = {
        "capabilities": ["tool_execution", "chat", "llm_generate"],
        "permissions": ["task_execute"],
        "nominated": [intervention],
        "has_task_context": True,
    }
    # 缺分配 → R4
    evaluation = evaluate_intervention_policy(base)
    assert evaluation.selected != intervention
    assert "R4.allocation_mode_missing" in _reasons_for(evaluation, intervention)
    # 脏分配（归 None）→ 同 R4
    dirty = {**base, "allocation_mode": "AUTO"}
    evaluation_dirty = evaluate_intervention_policy(dirty)
    assert "R4.allocation_mode_missing" in _reasons_for(evaluation_dirty, intervention)
    # 分配在且匹配 → 可选且 mode 镜像分配
    modes = {"delegate": "agent", "execute": "agent", "co_execute": "hybrid"}
    evaluation_ok = evaluate_intervention_policy({**base, "allocation_mode": modes[intervention]})
    assert evaluation_ok.selected == intervention
    assert evaluation_ok.resolved_execution_mode == modes[intervention]


# ---------------------------------------------------------------------------
# 7. LLM 参数化通道（默认关；mock 测；真实 LLM 0 次）
# ---------------------------------------------------------------------------


class _MockLLM:
    def __init__(self, payload=None, latency: float = 0.0, raise_exc: Exception | None = None):
        self.payload = payload
        self.latency = latency
        self.raise_exc = raise_exc
        self.calls: list[str] = []

    async def __call__(self, prompt: str):
        self.calls.append(prompt)
        if self.latency:
            await asyncio.sleep(self.latency)
        if self.raise_exc:
            raise self.raise_exc
        return self.payload


_OPEN_FACTORS = {  # 无提名 + 全量可用 → semantic_eligible
    "capabilities": ["chat", "llm_generate", "memory_read", "task_write", "scheduler", "peer_network", "tool_execution"],
    "permissions": ["memory_read", "plan_adjust", "task_execute", "model_write", "peer_contact", "proactive_contact"],
    "nominated": [],
    "has_task_context": True,
    "allocation_mode": "hybrid",
}


def test_semantic_channel_default_off() -> None:
    """通道默认关：即便注入 LLM 也不被调用（本卡真实 LLM 0 次的机制保证）。"""
    mock = _MockLLM({"intervention": "reflect", "rationale": "test"})
    engine = InterventionPolicyEngine(semantic_llm=mock)  # semantic_enabled 缺省 False
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert mock.calls == []
    assert evaluation.layer == "rule"
    assert evaluation.selected == "no_action"


def test_semantic_channel_not_called_when_nominee_legal() -> None:
    """规则层已有合法提名（选择不开放）→ 即便开启也不调用 LLM。"""
    mock = _MockLLM({"intervention": "pause", "rationale": "test"})
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    factors = {**_OPEN_FACTORS, "nominated": ["rescope"]}
    evaluation = asyncio.run(engine.evaluate(factors))
    assert mock.calls == []
    assert evaluation.selected == "rescope"


def test_semantic_refine_within_feasible() -> None:
    mock = _MockLLM({"intervention": "reflect", "rationale": "开放选择下反思收益最大", "clarifying_question": "x"})
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert len(mock.calls) == 1
    assert evaluation.selected == "reflect"
    assert evaluation.layer == "semantic"
    assert "S1.semantic_refined" in evaluation.why
    assert evaluation.resolved_execution_mode == "hybrid"
    # 非 clarify 的 question 提议被确定性丢弃
    assert evaluation.clarifying_question is None
    # 契约构造（P3-7）：语义层产物同样过构造门
    contract, violations = build_decision_contract(evaluation, uuid4(), cognition_tier="l3_full_core")
    assert contract is not None and violations == ()
    assert contract.annotations["policy_layer"] == "semantic"


def test_semantic_refine_clarify_carries_question() -> None:
    mock = _MockLLM(
        {"intervention": "clarify", "rationale": "r", "clarifying_question": "这周的目标是多少分？"}
    )
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert evaluation.selected == "clarify"
    assert evaluation.clarifying_question == "这周的目标是多少分？"
    # 参数化经构造门直达契约（无需调用方再补）
    contract, violations = build_decision_contract(evaluation, uuid4(), cognition_tier="l2_intervention")
    assert contract is not None and violations == ()
    assert contract.clarifying_question == "这周的目标是多少分？"


def test_semantic_outside_feasible_rejected() -> None:
    """LLM 越界（提名词表内但被守卫剔除的 delegate——hybrid 分配下 R5）→
    S2 拒收保规则缺省；S2 不计熔断失败（X-02 同款：正常拒绝路径）。"""
    InterventionPolicyEngine._reset_breaker()
    mock = _MockLLM({"intervention": "delegate", "rationale": "r"})
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert evaluation.selected == "no_action"
    assert evaluation.layer == "semantic_fallback"
    assert "S2.semantic_outside_feasible_rejected" in evaluation.why
    assert "R5.allocation_mode_conflict" in _reasons_for(evaluation, "delegate")
    assert type(engine)._semantic_failures == 0


def test_semantic_out_of_catalog_rejected() -> None:
    """LLM 提目录外串 → 同 S2 拒收（字符串自由动作双保险：规则层 R0 + 语义层 S2）。"""
    mock = _MockLLM({"intervention": "mega_rescope", "rationale": "r"})
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert evaluation.selected == "no_action"
    assert "S2.semantic_outside_feasible_rejected" in evaluation.why


def test_semantic_failure_degrades_to_rule_default() -> None:
    InterventionPolicyEngine._reset_breaker()
    mock = _MockLLM(None, raise_exc=RuntimeError("llm down"))
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert evaluation.selected == "no_action"
    assert evaluation.layer == "rule"
    assert type(engine)._semantic_failures == 1


def test_semantic_timeout_degrades() -> None:
    InterventionPolicyEngine._reset_breaker()
    mock = _MockLLM({"intervention": "reflect"}, latency=5.0)
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True, semantic_timeout_seconds=0.05)
    evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert evaluation.selected == "no_action"
    assert evaluation.layer == "rule"


def test_semantic_breaker_opens_after_threshold() -> None:
    InterventionPolicyEngine._reset_breaker()
    mock = _MockLLM(None, raise_exc=RuntimeError("down"))
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True)
    for _ in range(3):
        evaluation = asyncio.run(engine.evaluate(_OPEN_FACTORS))
        assert evaluation.layer == "rule"
    assert type(engine)._semantic_open_until > 0.0
    calls_after_open = len(mock.calls)
    # 熔断打开：不再调用
    asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert len(mock.calls) == calls_after_open


def test_semantic_rate_limited() -> None:
    InterventionPolicyEngine._reset_breaker()
    mock = _MockLLM({"intervention": "reflect", "rationale": "r"})
    engine = InterventionPolicyEngine(semantic_llm=mock, semantic_enabled=True, semantic_max_per_minute=1)
    first = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert first.selected == "reflect"
    # 窗口内第二次：限频降级（规则缺省），不再调用
    second = asyncio.run(engine.evaluate(_OPEN_FACTORS))
    assert len(mock.calls) == 1
    assert second.selected == "no_action"
    assert second.layer == "rule"
