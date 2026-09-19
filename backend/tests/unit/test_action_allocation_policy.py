"""X-02 Action Allocation Policy —— 决策核心/语义层/决策记录 全量契约测试。

覆盖：
- 封闭词表双冻结（精确集 + sha256）；
- 规则层：guard（R1/R4/R5/R6/G1）× 选择层（X1/X2/U1-U4/D1-D6）× 修饰层（T1/T2）；
- 韧性契约：任何输入不 raise，脏值归一，异常降级 E1；
- ownership 推荐：永不落 X-01 F5 矛盾集；
- 与 X-01 ActionPlanContract 的组合面（validate / merge）；
- 决策记录 + event_registry 接线（allocation.decision_recorded）；
- 语义层：feasible set 边界强制、熔断、限频、超时、禁用默认。
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from app.core.event_registry import EVENT_REGISTRY
from app.models.execution_intent import ExecutionMode
from app.models.task import CognitiveOwnership
from app.services.action_allocation_policy import (
    ALLOCATION_EVENT_NAME,
    ALLOCATION_LAYERS,
    ALLOCATION_REASONS,
    OFFER_VERDICT_REASONS,
    USER_AUTHORED_EVIDENCE_KINDS,
    ActionAllocationPolicy,
    AllocationDecision,
    AllocationFactors,
    build_allocation_event_metadata,
    decide_allocation,
    merge_into_action_plan,
    validate_action_plan_allocation,
)

# sha256 of "|".join(sorted(ALLOCATION_REASONS)) captured at X-02 freeze.
_FROZEN_REASONS_SHA256 = "c4fc32a943f11718ac8e3d1b19d4734dbc623dfd821e5534df31f58a407f6ffd"


def F(**kw) -> AllocationFactors:
    """快捷构造：默认全 None（灰区基底），按用例覆盖。"""
    return AllocationFactors.coerce(kw)


# ---------------------------------------------------------------------------
# 1. 封闭词表冻结
# ---------------------------------------------------------------------------


def test_reason_vocabulary_is_frozen_exact_set():
    expected = {
        "R1.high_risk_requires_human_approval",
        "R4.embodiment_required",
        "R5.privacy_restricted",
        "R5.privacy_sensitive_no_auto_agent",
        "R6.low_system_confidence",
        "X1.explicit_self_request",
        "X2.explicit_delegate_request",
        "X2.delegate_downgraded_by_guard",
        "U1.user_preference_agent",
        "U2.user_preference_human",
        "U3.user_preference_mixed",
        "U4.user_preference_partially_honored",
        "D1.ownership_user_core",
        "D2.ownership_shared_hybrid",
        "D3.ownership_delegated_agent",
        "D4.delegated_advantage_unverified",
        "D5.tool_advantage_low_human",
        "D6.gray_zone_default_hybrid",
        "R0.insufficient_factors",
        "T1.time_pressure_favors_agent",
        "T2.agent_slower_or_costlier",
        "G1.learning_guard_no_agent",
        "G2.learning_evidence_user_authored",
        "S1.semantic_refined",
        "S2.semantic_outside_feasible_rejected",
        "E1.degraded_to_rule_default",
    }
    assert expected == ALLOCATION_REASONS


def test_reason_vocabulary_is_frozen_by_hash():
    digest = hashlib.sha256("|".join(sorted(ALLOCATION_REASONS)).encode()).hexdigest()
    assert digest == _FROZEN_REASONS_SHA256, (
        f"reason vocabulary changed ({len(ALLOCATION_REASONS)} codes); if intentional, "
        "update _FROZEN_REASONS_SHA256 deliberately and bump ALLOCATION_POLICY_VERSION"
    )


def test_offer_verdict_reasons_frozen():
    """R2 返修（F1）：+2 个 R5 拒收码，ALLOCATION_POLICY_VERSION 已 bump v1.1。"""
    assert (
        frozenset(
            {
                "OK.content_generation_allowed",
                "OK.hybrid_preparation_allowed",
                "G3.complete_answer_rejected_for_learning",
                "G4.draft_rejected_user_core",
                "R1.autonomous_execution_needs_approval",
                "R5.restricted_agent_supply_forbidden",
                "R5.sensitive_autonomous_supply_forbidden",
                "E2.unknown_offer_kind",
            }
        )
        == OFFER_VERDICT_REASONS
    )


def test_mode_vocabulary_reuses_execution_intent():
    """mode 词表唯一协议 = ExecutionMode（不新造第二套枚举）。"""
    decision = decide_allocation(F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low"))
    assert isinstance(decision.execution_mode, ExecutionMode)


# ---------------------------------------------------------------------------
# 2. Guard 层（硬规则）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("risk", ["high", "critical"], ids=["high", "critical"])
def test_high_risk_never_agent(risk):
    """验收①核心：high-risk 场景 auto-agent = 0（硬规则，偏好/意图都翻不动）。"""
    factors = F(
        cognitive_ownership="delegated",
        tool_advantage="high",
        risk_class=risk,
        reversible=False,
        explicit_intent="delegate",
        user_preference="prefer_agent",
    )
    decision = decide_allocation(factors)
    assert decision.mode != "agent"
    assert "agent" not in decision.feasible_modes
    assert decision.requires_human_approval is True
    assert "R1.high_risk_requires_human_approval" in decision.why
    assert "X2.delegate_downgraded_by_guard" in decision.why


def test_medium_risk_irreversible_treated_as_high():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="medium", reversible=False)
    )
    assert decision.mode != "agent"
    assert decision.requires_human_approval is True


def test_medium_risk_reversible_allows_agent():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="medium", reversible=True)
    )
    assert decision.mode == "agent"


def test_embodiment_blocks_agent():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", embodiment_required=True)
    )
    assert decision.mode != "agent"
    assert "R4.embodiment_required" in decision.why


def test_privacy_restricted_forces_human():
    decision = decide_allocation(
        F(
            cognitive_ownership="delegated",
            tool_advantage="high",
            risk_class="low",
            privacy="restricted",
            explicit_intent="delegate",
        )
    )
    assert decision.mode == "human"
    assert decision.feasible_modes == ("human",)
    assert "R5.privacy_restricted" in decision.why


def test_privacy_sensitive_blocks_agent_only():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", privacy="sensitive")
    )
    assert decision.mode == "hybrid"
    assert "R5.privacy_sensitive_no_auto_agent" in decision.why


def test_low_system_confidence_blocks_agent():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", confidence=0.2)
    )
    assert decision.mode != "agent"
    assert "R6.low_system_confidence" in decision.why


# ---------------------------------------------------------------------------
# 3. 选择层
# ---------------------------------------------------------------------------


def test_explicit_self_request_human():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", explicit_intent="self")
    )
    assert decision.mode == "human"
    assert "X1.explicit_self_request" in decision.why
    assert decision.confidence == pytest.approx(0.9)


def test_explicit_delegate_low_risk_agent():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", explicit_intent="delegate")
    )
    assert decision.mode == "agent"
    assert "X2.explicit_delegate_request" in decision.why
    assert "X2.delegate_downgraded_by_guard" not in decision.why


def test_user_preference_agent_honored_when_feasible():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", user_preference="prefer_agent")
    )
    assert decision.mode == "agent"
    assert "U1.user_preference_agent" in decision.why


def test_user_preference_agent_on_learning_partially_honored():
    decision = decide_allocation(
        F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high", user_preference="prefer_agent")
    )
    assert decision.mode == "hybrid"
    assert "U4.user_preference_partially_honored" in decision.why


def test_user_preference_human():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="high", user_preference="prefer_human")
    )
    assert decision.mode == "human"
    assert "U2.user_preference_human" in decision.why


def test_user_preference_mixed():
    decision = decide_allocation(F(cognitive_ownership="shared", tool_advantage="high", user_preference="prefer_mixed"))
    assert decision.mode == "hybrid"
    assert "U3.user_preference_mixed" in decision.why


def test_default_user_core_with_tool_support_hybrid():
    decision = decide_allocation(F(cognitive_ownership="user_core", tool_advantage="high", risk_class="low"))
    assert decision.mode == "hybrid"
    assert "D1.ownership_user_core" in decision.why


def test_default_user_core_without_tool_support_human():
    decision = decide_allocation(F(cognitive_ownership="user_core", tool_advantage="none", risk_class="low"))
    assert decision.mode == "human"
    assert "D1.ownership_user_core" in decision.why


def test_default_shared_hybrid():
    decision = decide_allocation(F(cognitive_ownership="shared", tool_advantage="medium"))
    assert decision.mode == "hybrid"
    assert "D2.ownership_shared_hybrid" in decision.why


def test_default_delegated_high_advantage_agent():
    decision = decide_allocation(F(cognitive_ownership="delegated", tool_advantage="high", risk_class="low"))
    assert decision.mode == "agent"
    assert "D3.ownership_delegated_agent" in decision.why


def test_default_delegated_low_advantage_human():
    decision = decide_allocation(F(cognitive_ownership="delegated", tool_advantage="low", risk_class="low"))
    assert decision.mode == "human"
    assert "D5.tool_advantage_low_human" in decision.why


def test_default_delegated_unverified_advantage_hybrid():
    decision = decide_allocation(F(cognitive_ownership="delegated", tool_advantage=None, risk_class="low"))
    assert decision.mode == "hybrid"
    assert "D4.delegated_advantage_unverified" in decision.why


def test_gray_zone_defaults_hybrid_and_semantic_eligible():
    decision = decide_allocation(F(task_type="PLANNING", task_summary="准备小组作业分工", tool_advantage="high"))
    assert decision.mode == "hybrid"
    assert "D6.gray_zone_default_hybrid" in decision.why
    assert decision.annotations["semantic_eligible"] is True
    assert decision.confidence == pytest.approx(0.45)


def test_insufficient_factors_conservative():
    decision = decide_allocation(F())
    assert decision.mode == "hybrid"
    assert "R0.insufficient_factors" in decision.why
    assert decision.confidence == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# 4. 修饰层
# ---------------------------------------------------------------------------


def test_time_pressure_upgrades_unverified_delegated_to_agent():
    """T1 真实路径：D4（delegated + 优势未确证 → hybrid）+ urgent + 已知足够 → agent。"""
    decision = decide_allocation(
        F(
            cognitive_ownership="delegated",
            tool_advantage=None,
            risk_class="low",
            time_pressure="urgent",
            confidence=0.7,
        )
    )
    assert decision.mode == "agent"
    assert "D4.delegated_advantage_unverified" in decision.why
    assert "T1.time_pressure_favors_agent" in decision.why


def test_time_pressure_t1_blocked_by_low_confidence():
    """置信不足时 T1 不放行（红旗优先于速度）。"""
    decision = decide_allocation(
        F(
            cognitive_ownership="delegated",
            tool_advantage=None,
            risk_class="low",
            time_pressure="urgent",
            confidence=0.3,
        )
    )
    assert decision.mode != "agent"
    assert "T1.time_pressure_favors_agent" not in decision.why


def test_time_pressure_never_flips_shared_hybrid():
    """shared（用户核心决策）的 hybrid 不被紧急度翻成 agent——速度不凌驾用户决策角色。"""
    decision = decide_allocation(
        F(cognitive_ownership="shared", tool_advantage="high", risk_class="low", time_pressure="urgent")
    )
    assert decision.mode == "hybrid"
    assert "T1.time_pressure_favors_agent" not in decision.why


def test_time_pressure_never_overrides_learning_guard():
    decision = decide_allocation(
        F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high", time_pressure="urgent")
    )
    assert decision.mode != "agent"


def test_t2_preference_agent_with_low_advantage_downgraded():
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="low", risk_class="low", user_preference="prefer_agent")
    )
    assert decision.mode == "hybrid"
    assert "T2.agent_slower_or_costlier" in decision.why


def test_t1_applies_only_to_default_tier():
    """显式 self 意图不被时间压力翻盘。"""
    decision = decide_allocation(
        F(
            cognitive_ownership="delegated",
            tool_advantage="high",
            risk_class="low",
            explicit_intent="self",
            time_pressure="urgent",
        )
    )
    assert decision.mode == "human"


# ---------------------------------------------------------------------------
# 5. 韧性契约 + 防御归一
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"cognitive_ownership": "bogus", "risk_class": 123, "confidence": "not-a-number"},
        {"tool_advantage": "HIGH", "privacy": " Restricted "},
        {"explicit_intent": "DELEGATE", "reversible": "yes"},
    ],
    ids=["none", "empty", "garbage-values", "case-normalization", "string-bools"],
)
def test_decide_never_raises_on_any_input(raw):
    decision = decide_allocation(raw)
    assert isinstance(decision, AllocationDecision)
    assert decision.mode in {"human", "agent", "hybrid"}
    assert set(decision.why) <= ALLOCATION_REASONS


def test_coerce_normalizes_case_and_rejects_unknown():
    factors = AllocationFactors.coerce(
        {
            "tool_advantage": "HIGH",
            "privacy": " Restricted ",
            "cognitive_ownership": "USER_CORE",
            "risk_class": "nah",
            "confidence": 1.5,
        }
    )
    assert factors.tool_advantage == "high"
    assert factors.privacy == "restricted"
    assert factors.cognitive_ownership == "user_core"
    assert factors.risk_class is None  # 未知值 → None（未知，不是非法崩溃）
    assert factors.confidence is None  # 越界 → None


def test_coerce_bare_task_id_wrapped_in_ref_scheme():
    factors = AllocationFactors.coerce({"task_ref": "abc-123"})
    assert factors.task_ref == "task://abc-123"


def test_all_reason_codes_are_in_closed_vocabulary():
    """抽干：代表性因子网格（~6 万组合）上所有产出 why 必在封闭集内。

    R2 返修（F2/F5）：同一 62,208 组合网格同时断言——
    - F5 矛盾集零命中（(mode, recommended_ownership) 永不落三对矛盾）；
    - ``semantic_eligible ⇒ not learning_guard``（语义层入口与学习守卫的结构
      不变式，显式化为回归断言）。
    """
    factor_matrix = [F()] + [
        F(
            cognitive_ownership=co,
            tool_advantage=ta,
            risk_class=rc,
            privacy=pv,
            explicit_intent=ei,
            user_preference=up,
            time_pressure=tp,
            learning_goal=lg,
            embodiment_required=em,
            reversible=rv,
            confidence=cf,
            task_type=tt,
        )
        for co in ("user_core", "shared", "delegated", None)
        for ta in ("high", "low", None)
        for rc in ("low", "high", None)
        for pv in ("public", "restricted", None)
        for ei in ("delegate", "self", None)
        for up in ("prefer_agent", "prefer_human", None)
        for tp in ("urgent", None)
        for lg in (True, None)
        for em in (True, None)
        for rv in (False, None)
        for cf in (0.2, None)
        for tt in ("LEARNING", None)
    ]
    seen: set[str] = set()
    for factors in factor_matrix:
        decision = decide_allocation(factors)
        assert decision.mode in decision.feasible_modes or decision.layer == "error_degraded"
        pair = (decision.mode, decision.recommended_cognitive_ownership)
        assert pair not in F5_CONTRADICTIONS, f"{pair} lands in X-01 F5 contradiction set (factors={factors})"
        if decision.annotations.get("semantic_eligible"):
            assert not decision.annotations.get(
                "learning_guard"
            ), f"semantic_eligible must imply no learning guard (factors={factors})"
        seen.update(decision.why)
    assert seen <= ALLOCATION_REASONS


def test_determinism_same_input_same_output():
    factors = F(cognitive_ownership="shared", tool_advantage="high", risk_class="medium", reversible=True)
    d1, d2 = decide_allocation(factors), decide_allocation(factors)
    assert d1 == d2
    assert d1.decision_id(factors) == d2.decision_id(factors)


# ---------------------------------------------------------------------------
# 6. ownership 推荐：X-01 F5 矛盾集零命中
# ---------------------------------------------------------------------------


F5_CONTRADICTIONS = {("agent", "user_core"), ("hybrid", "delegated"), ("human", "shared")}


def test_recommended_ownership_never_lands_in_f5_contradiction_set():
    factor_matrix = [
        F(
            cognitive_ownership=co,
            tool_advantage=ta,
            risk_class=rc,
            task_type=tt,
            explicit_intent=ei,
            user_preference=up,
        )
        for co in ("user_core", "shared", "delegated", None)
        for ta in ("high", "medium", "low", None)
        for rc in ("low", "medium", "high", None)
        for tt in ("LEARNING", "PLANNING", None)
        for ei in ("delegate", "self", None)
        for up in ("prefer_agent", "prefer_human", None)
    ]
    for factors in factor_matrix:
        decision = decide_allocation(factors)
        assert decision.recommended_cognitive_ownership is not None
        pair = (decision.mode, decision.recommended_cognitive_ownership)
        assert pair not in F5_CONTRADICTIONS, f"{pair} is an X-01 F5 contradiction (factors={factors})"


def test_hybrid_recommended_evidence_kinds_are_user_authored_subset():
    decision = decide_allocation(F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high"))
    assert decision.mode == "hybrid"
    assert set(decision.recommended_evidence_kinds) <= set(USER_AUTHORED_EVIDENCE_KINDS)


# ---------------------------------------------------------------------------
# 7. 与 X-01 ActionPlanContract 的组合面
# ---------------------------------------------------------------------------


def _plan(**kw):
    from app.core.action_plan import ActionPlanContract, CompletionEvidenceSpec, SmallestUsefulStep

    defaults: dict = {
        "desired_outcome": "掌握滑动窗口原理并完成习题",
        "smallest_useful_step": SmallestUsefulStep(
            description="完成 3.2 节例题", useful_because=("builds_capability",)
        ),
        "completion_evidence": (CompletionEvidenceSpec(evidence_kind="quiz_result"),),
        "execution_mode": ExecutionMode.HYBRID,
        "cognitive_ownership": CognitiveOwnership.USER_CORE,
        "risk_class": None,
    }
    defaults.update(kw)
    return ActionPlanContract(**defaults)


def test_validate_rejects_agent_mode_learning_plan():
    plan = _plan(execution_mode=ExecutionMode.AGENT)
    factors = F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high")
    violations = validate_action_plan_allocation(plan, factors)
    assert any("learning guard" in v for v in violations)


def test_validate_rejects_f5_contradictions():
    factors = F(cognitive_ownership="user_core", tool_advantage="high")
    violations = validate_action_plan_allocation(
        _plan(execution_mode=ExecutionMode.AGENT, cognitive_ownership=CognitiveOwnership.USER_CORE), factors
    )
    assert any("definitional contradiction" in v for v in violations)


def test_merge_corrects_agent_learning_plan_to_hybrid():
    plan = _plan(execution_mode=ExecutionMode.AGENT, cognitive_ownership=CognitiveOwnership.DELEGATED)
    factors = F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high", risk_class="low")
    corrected, decision = merge_into_action_plan(plan, factors)
    assert corrected.execution_mode == ExecutionMode.HYBRID
    assert corrected.cognitive_ownership == CognitiveOwnership.USER_CORE
    assert decision.mode == "hybrid"
    # 改写后必须通过校验（构造性自洽）
    assert validate_action_plan_allocation(corrected, factors) == ()


def test_merge_passes_valid_plan_through():
    plan = _plan()
    factors = F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high", risk_class="low")
    corrected, decision = merge_into_action_plan(plan, factors)
    assert corrected == plan
    assert decision.mode == "hybrid"


# ---------------------------------------------------------------------------
# 8. 决策记录 + event_registry 接线
# ---------------------------------------------------------------------------


def test_allocation_event_name_is_registered():
    entry = EVENT_REGISTRY[ALLOCATION_EVENT_NAME]
    assert entry.stage.value == "decision"
    assert entry.aggregate_type == "allocation_decision"


def test_build_allocation_event_metadata_shape():
    from app.core.event_registry import read_event_metadata

    factors = F(
        task_type="LEARNING",
        cognitive_ownership="user_core",
        tool_advantage="high",
        task_ref=f"task://{'1' * 8}-{'2' * 4}-{'3' * 4}-{'4' * 4}-{'5' * 12}",
    )
    decision = decide_allocation(factors)
    metadata = build_allocation_event_metadata(
        user_id="11111111-11111111-11111111-11111111",
        aggregate_id="22222222-22222222-22222222-22222222",
        decision=decision,
        factors=factors,
        sequence_number=7,
    )
    view = read_event_metadata(metadata)
    assert view.is_v3_envelope
    assert view.user_id == "11111111-1111-1111-1111-111111111111"
    assert view.correlation["task_id"] == f"{'1' * 8}-{'2' * 4}-{'3' * 4}-{'4' * 4}-{'5' * 12}"
    assert metadata["allocation_decision"]["mode"] == decision.mode
    assert metadata["allocation_decision"]["schema_version"] == "allocation.v1.1"
    assert metadata["decision_id"].startswith("alloc_")


def test_decision_record_dict_is_jsonable_and_complete():
    factors = F(cognitive_ownership="shared", tool_advantage="high")
    decision = decide_allocation(factors)
    record = decision.to_dict()
    assert record["schema_version"] == "allocation.v1.1"
    assert set(record) == {
        "schema_version",
        "mode",
        "why",
        "confidence",
        "layer",
        "feasible_modes",
        "requires_human_approval",
        "requires_user_authored_evidence",
        "recommended_evidence_kinds",
        "recommended_cognitive_ownership",
    }
    import json

    json.dumps(record)  # 必须可序列化（供 outbox payload）


# ---------------------------------------------------------------------------
# 9. 语义层（fake LLM）
# ---------------------------------------------------------------------------

GRAY_FACTORS = F(task_type="PLANNING", task_summary="准备下周小组展示的分工与排期", tool_advantage="high")


@pytest.mark.asyncio
async def test_semantic_disabled_by_default(monkeypatch):
    """语义层默认关：灰区也只走规则默认。"""
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", False, raising=False)
    policy = ActionAllocationPolicy(semantic_llm=lambda prompt: _should_not_be_called())  # noqa: E731
    decision = await policy.evaluate(GRAY_FACTORS)
    assert decision.layer == "rule"
    assert decision.mode == "hybrid"


async def _should_not_be_called():
    raise AssertionError("semantic LLM must not be called when disabled")


@pytest.mark.asyncio
async def test_semantic_refinement_within_feasible_set(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        return {"mode": "agent", "confidence": 0.7, "reason": "mechanical prep"}

    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(GRAY_FACTORS)
    # gray factors: task_type=PLANNING + tool high → 无 guard → agent feasible
    assert decision.layer == "semantic"
    assert decision.mode == "agent"
    assert "S1.semantic_refined" in decision.why
    assert decision.confidence == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_semantic_outside_feasible_is_rejected(monkeypatch):
    """LLM 越界（feasible 外）→ S2 拒收，保规则默认（代码强制边界）。"""
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        return {"mode": "agent", "confidence": 0.9, "reason": ""}

    factors = F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high")
    # 学习守卫生效 → agent 不可行；但 learning 场景非 semantic_eligible——
    # 用 privacy restricted 构造 eligible+受限：privacy restricted 排除 agent/hybrid
    factors = F(task_summary="整理我的私人日记", tool_advantage="high", privacy="restricted")
    # privacy=restricted → feasible={human}；ownership 未知 → D6 灰区（eligible），
    # 规则默认在 feasible 内取 human；LLM 的 agent 提议必须被拒。
    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(factors)
    assert decision.mode == "human"  # LLM 的 agent 提议被拒
    assert "S2.semantic_outside_feasible_rejected" in decision.why
    assert decision.layer == "semantic_fallback"


@pytest.mark.asyncio
async def test_semantic_failure_degrades_to_rule_default(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        raise RuntimeError("llm down")

    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(GRAY_FACTORS)
    assert decision.layer == "rule"
    assert decision.mode == "hybrid"


@pytest.mark.asyncio
async def test_semantic_bad_payload_counts_as_failure(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        return "garbage not json"

    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(GRAY_FACTORS)
    assert decision.layer == "rule"
    assert ActionAllocationPolicy._semantic_failures == 1


@pytest.mark.asyncio
async def test_semantic_breaker_opens_after_threshold(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        raise RuntimeError("down")

    policy = ActionAllocationPolicy(semantic_llm=llm)
    for _ in range(3):
        await policy.evaluate(GRAY_FACTORS)
    assert ActionAllocationPolicy._semantic_open_until > 0
    # 熔断打开后不再调用 LLM（第 4 次直接降级，failures 不再增长）
    failures = ActionAllocationPolicy._semantic_failures
    await policy.evaluate(GRAY_FACTORS)
    assert ActionAllocationPolicy._semantic_failures == failures
    ActionAllocationPolicy._reset_breaker()


@pytest.mark.asyncio
async def test_semantic_rate_cap(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_MAX_PER_MINUTE", 1, raising=False)
    ActionAllocationPolicy._reset_breaker()
    calls = []

    async def llm(prompt):
        calls.append(prompt)
        return {"mode": "hybrid", "confidence": 0.6}

    policy = ActionAllocationPolicy(semantic_llm=llm)
    await policy.evaluate(GRAY_FACTORS)
    await policy.evaluate(GRAY_FACTORS)
    assert len(calls) == 1  # 第 2 次被限频
    ActionAllocationPolicy._reset_breaker()


@pytest.mark.asyncio
async def test_semantic_never_clears_guard_flags(monkeypatch):
    """语义精化不能清除 R1 审批要求（flags 来自 guard 层，非 mode 派生）。"""
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        return {"mode": "hybrid", "confidence": 0.8}

    factors = F(task_summary="代发一封给导师的邮件", tool_advantage="high", risk_class="high", reversible=False)
    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(factors)
    assert decision.requires_human_approval is True
    # risk high + tool high → tier: D6 gray? cognitive_ownership None → D6 hybrid
    if decision.layer == "semantic":
        assert decision.requires_human_approval is True  # 仍不可清除
        assert decision.confidence <= 0.75  # 语义置信封顶


@pytest.mark.asyncio
async def test_evaluate_never_raises(monkeypatch):
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        raise RuntimeError("boom")

    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate({"garbage": object()})
    assert decision.mode in {"human", "agent", "hybrid"}


@pytest.mark.asyncio
async def test_vet_offer_wrapper_counts_rejections():
    ActionAllocationPolicy._reset_breaker()
    policy = ActionAllocationPolicy()
    verdict = await policy.vet_offer("complete_answer", F(task_type="LEARNING"))
    assert verdict.allowed is False


def test_layer_values_closed():
    assert frozenset({"rule", "semantic", "semantic_fallback", "error_degraded"}) == ALLOCATION_LAYERS


# ---------------------------------------------------------------------------
# 10. R2 返修（REVIEW_RECEIPT_2 §8）：F3/F5/F6.1/F6.2/F6.5 固化测试
# ---------------------------------------------------------------------------


def test_explicit_delegate_exempts_t2_cost_check():
    """R2 F3 固化：当轮显式委托豁免 T2 成本检查——用户主权 > 系统成本启发。

    对照：同一「无工具优势」因子下，持久偏好 prefer_agent 仍被 T2 降级 hybrid。
    硬规则不受豁免影响（feasible set 照常剔除）。
    """
    decision = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="none", risk_class="low", explicit_intent="delegate")
    )
    assert decision.mode == "agent"
    assert "X2.explicit_delegate_request" in decision.why
    assert "T2.agent_slower_or_costlier" not in decision.why
    # 对照组：稳态偏好无此豁免（T2 对冲偏好撞上坏适配）
    pref = decide_allocation(
        F(cognitive_ownership="delegated", tool_advantage="none", risk_class="low", user_preference="prefer_agent")
    )
    assert pref.mode == "hybrid"
    assert "T2.agent_slower_or_costlier" in pref.why
    # 豁免不含硬规则：高风险下显式委托仍翻不出 agent
    risky = decide_allocation(
        F(
            cognitive_ownership="delegated",
            tool_advantage="none",
            risk_class="high",
            reversible=False,
            explicit_intent="delegate",
        )
    )
    assert risky.mode != "agent"
    assert "X2.delegate_downgraded_by_guard" in risky.why


@pytest.mark.asyncio
async def test_semantic_agent_proposal_under_high_risk_rejected(monkeypatch):
    """R2 F6.2：high-risk 灰区 + LLM 提议 agent → S2 拒收 + 审批旗标保留。

    此前 S2 边界只有 1 个测试拦截（M3 变异仅 1 failed）；本用例把
    「guard 剔除 agent × 语义层试图翻回 agent」写成显式对抗场景。
    """
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm(prompt):
        return {"mode": "agent", "confidence": 0.9, "reason": "看起来是机械步骤"}

    factors = F(task_summary="批量改写期末成绩单并群发全班", tool_advantage=None, risk_class="high", reversible=False)
    policy = ActionAllocationPolicy(semantic_llm=llm)
    decision = await policy.evaluate(factors)
    assert "agent" not in decision.feasible_modes
    assert decision.mode != "agent"
    assert "S2.semantic_outside_feasible_rejected" in decision.why
    assert decision.layer == "semantic_fallback"
    assert decision.requires_human_approval is True  # R1 旗标不被语义层清除


@pytest.mark.asyncio
async def test_semantic_refine_recomputes_g2_evidence_flags(monkeypatch):
    """R2 F5 加固：精化改 mode 后 G2 旗标按 (learning, mode) 重算。

    当前选择层结构上保证 semantic_eligible ⇒ not learning_guard（62K 网格断言），
    本测试人为构造「learning_guard=True 且语义层介入」的决策，防御未来放开
    灰区时旗标沿用旧 mode：
    - hybrid(带 G2) → 精化到 human：G2 清除（human 模式用户亲手做，无证据要求）；
    - human(无 G2) → 精化到 hybrid：G2 补上（学习 × hybrid 必须带 user-authored
      证据——防代写的危险方向）。
    """
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()

    async def llm_human(prompt):
        return {"mode": "human", "confidence": 0.6}

    async def llm_hybrid(prompt):
        return {"mode": "hybrid", "confidence": 0.6}

    factors = F(task_type="LEARNING", cognitive_ownership="user_core", tool_advantage="high", risk_class="low")
    base = decide_allocation(factors)
    assert base.mode == "hybrid"
    assert base.requires_user_authored_evidence is True
    forced_eligible = replace(base, annotations={**base.annotations, "semantic_eligible": True})

    policy = ActionAllocationPolicy(semantic_llm=llm_human)
    refined = await policy._semantic_refine(factors, forced_eligible)
    assert refined is not None and refined.mode == "human"
    assert refined.requires_user_authored_evidence is False
    assert refined.recommended_evidence_kinds == ()
    assert "G2.learning_evidence_user_authored" not in refined.why

    stripped = replace(
        base,
        mode="human",
        why=tuple(r for r in base.why if r != "G2.learning_evidence_user_authored"),
        requires_user_authored_evidence=False,
        recommended_evidence_kinds=(),
        annotations={**base.annotations, "semantic_eligible": True},
    )
    policy2 = ActionAllocationPolicy(semantic_llm=llm_hybrid)
    refined2 = await policy2._semantic_refine(factors, stripped)
    assert refined2 is not None and refined2.mode == "hybrid"
    assert refined2.requires_user_authored_evidence is True
    assert refined2.recommended_evidence_kinds == USER_AUTHORED_EVIDENCE_KINDS
    assert "G2.learning_evidence_user_authored" in refined2.why


def test_merge_with_foreign_plan_object_passes_through():
    """R2 F6.1：非 ActionPlanContract 对象（属性不匹配）不炸 replace——
    isinstance 防御先于属性访问/改写，原样返还 + 决策照常返回。"""
    ActionAllocationPolicy._reset_breaker()

    class Foreign:
        execution_mode = "agent"
        cognitive_ownership = "user_core"

    foreign = Foreign()
    corrected, decision = merge_into_action_plan(foreign, F(cognitive_ownership="shared", tool_advantage="high"))
    assert corrected is foreign
    assert decision.mode in {"human", "agent", "hybrid"}


@pytest.mark.asyncio
async def test_breaker_uses_injected_clock(monkeypatch):
    """R2 F6.5：熔断开启时刻用可注入 now_fn（不再直呼 time.monotonic），
    测试可离线断言 open_until 的精确值。"""
    monkeypatch.setattr("app.config.settings.SPARKLE_ALLOCATION_SEMANTIC_ENABLED", True, raising=False)
    ActionAllocationPolicy._reset_breaker()
    fake_now = 1234.5

    async def llm(prompt):
        raise RuntimeError("down")

    policy = ActionAllocationPolicy(semantic_llm=llm, now_fn=lambda: fake_now)
    for _ in range(3):
        await policy.evaluate(GRAY_FACTORS)
    assert ActionAllocationPolicy._semantic_open_until == pytest.approx(
        fake_now + ActionAllocationPolicy.SEMANTIC_BREAKER_COOLDOWN_SECONDS
    )
    ActionAllocationPolicy._reset_breaker()
