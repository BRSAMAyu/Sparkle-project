"""V4-I03 复杂表达的受限语义选择器。

验收锚点（卡面，全部可失败）：
1. 多否定/时间约束/材料不足不靠单关键词误判——探针判定由多 token 结构单元
   承载，每形态一正一反反例 + 单关键词零判定力 + 去算子翻转检查；
2. 未知 ref / 目录外 tool 显式拒绝，不拼「已执行」话术——封闭拒绝码 + 冻结
   澄清文案（SUCCESS_TALK_MARKERS 扫描）+ 拒绝结局结构上不携带可执行声明；
3. 同输入规则臂/语义臂对照保留成本和失败——每臂判定、I10 口径成本
   （usage_source/sub_calls，unknown→None 不冒充）、失败形态全保留可审计。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config.settings import settings as settings_module
from app.core.aurora_decision import AURORA_DECISION_REF_SCHEMES, AURORA_INTERVENTION_TYPES
from app.models.execution_intent import ExecutionMode
from app.orchestration.semantic_selector import (
    COMPARISON_AGREEMENTS,
    CONFIDENCE_BANDS,
    MAX_SCHEMA_REPAIRS,
    SUCCESS_TALK_MARKERS,
    ZERO_MODEL_COST,
    ArmCost,
    ComplexExpressionProfile,
    ComplexForm,
    RefusalCode,
    RuleArmDecision,
    RuleArmDecisionKind,
    SelectionOutcome,
    SelectionRequest,
    SelectionVerdict,
    compare_arms,
    probe_complex_expression,
    rule_arm_decide,
    run_arm_comparison,
    run_selection,
    run_semantic_selector_shadow,
)

# ---------------------------------------------------------------------------
# 公共夹具
# ---------------------------------------------------------------------------

_ABSENT = object()

_FULL_WHITELIST = SelectionRequest(
    allowed_interventions=frozenset(
        {"clarify", "explain", "retrieve", "rescope", "split", "practice", "review", "pause", "remind", "no_action"}
    ),
    allowed_execution_modes=frozenset({mode.value for mode in ExecutionMode}),
    allowed_refs=frozenset({"task://t-1", "goal://g-1", "memory://episodic/m-1"}),
    allowed_tools=frozenset({"get_plan_state", "retrieve_user_material"}),
    allowed_candidate_ids=frozenset({"c-1", "c-2"}),
)


def _proposal(**overrides: object) -> dict:
    """合法基线提议；传 _ABSENT 删除键，传 None 保留显式空值。"""
    base: dict = {
        "selected_intervention_id": "clarify",
        "execution_mode": "agent",
        "used_ref_ids": ["task://t-1"],
        "confidence_band": "medium",
    }
    base.update(overrides)
    return {key: value for key, value in base.items() if value is not _ABSENT}


class _StubProposer:
    """语义臂 stub：按脚本响应；记录 repair_feedback 供断言。"""

    def __init__(self, responses: list, cost: ArmCost | None = None):
        self.responses = list(responses)
        self.cost = (
            cost
            if cost is not None
            else ArmCost(model_calls=1, prompt_tokens=100, completion_tokens=20, usage_source="measured")
        )
        self.calls = 0
        self.repair_feedbacks: list[tuple[str, ...]] = []

    async def propose(self, request: SelectionRequest, *, repair_feedback: tuple[str, ...] = ()):
        self.calls += 1
        self.repair_feedbacks.append(repair_feedback)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(proposal=item, cost=self.cost)


# ---------------------------------------------------------------------------
# 验收①：复杂表达探针——结构判定，不靠单关键词
# ---------------------------------------------------------------------------


class TestProbePositives:
    """每形态至少一个正例（形态判定 + 结构证据）。"""

    @pytest.mark.parametrize(
        "text,expected_form",
        [
            ("不是不感兴趣，是资料太多不知道先看哪份", ComplexForm.MULTI_NEGATION),
            ("我并不是没时间，只是想先整体规划", ComplexForm.MULTI_NEGATION),
            ("不能说没有进步", ComplexForm.MULTI_NEGATION),
            ("以后再说吧", ComplexForm.TIME_DEFERRAL),
            ("这个先不安排了", ComplexForm.TIME_DEFERRAL),
            ("还没复习完就要考试了", ComplexForm.DEADLINE_PRESSURE),
            ("还剩3天，来不及了", ComplexForm.DEADLINE_PRESSURE),
            ("现在没有材料", ComplexForm.MATERIAL_INSUFFICIENCY),
            ("资料还没准备好", ComplexForm.MATERIAL_INSUFFICIENCY),
            ("找不到复习资料", ComplexForm.MATERIAL_INSUFFICIENCY),
        ],
    )
    def test_positive_forms(self, text: str, expected_form: ComplexForm):
        profile = probe_complex_expression(text)
        assert profile.has_complex_expression, f"positive probe missed: {text}"
        assert profile.has_form(expected_form), f"wrong form for {text}: {profile.to_dict()}"
        for item in profile.evidence:
            assert item.pattern_id
            assert item.matched_span

    def test_multi_form_coexistence_and_priority(self):
        profile = probe_complex_expression("不是不想学，是真的没有材料")
        assert profile.has_form(ComplexForm.MULTI_NEGATION)
        assert profile.has_form(ComplexForm.MATERIAL_INSUFFICIENCY)
        # 规则臂优先级确定性：材料不足（澄清）压过多否定（升级）。
        decision = rule_arm_decide(profile)
        assert decision.kind is RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL
        assert decision.question


class TestProbeSingleKeywordNoFlip:
    """单关键词零判定力：任何单个 marker 独立出现不构成判定（可失败反例）。"""

    @pytest.mark.parametrize(
        "text",
        [
            "不",
            "没",
            "我不太确定",  # 单否定
            "我不知道，也不想知道",  # 同极性连续否定，不翻转
            "不是想学",  # 「不是」后接非否定谓词 = 单否定
            "以后",
            "再说一遍",  # 单「再说」无时间指称
            "以后每天背50个单词",  # 「以后」+计划 ≠ 搁置
            "还没",
            "还没开始",  # 进度缺口无临近后果
            "还有很多天",  # 无临期数字
            "他还没来，我先走了",  # 「还没…就」无强后续词，非临期
            "材料",
            "现在很忙",
        ],
    )
    def test_single_keywords_never_trigger(self, text: str):
        profile = probe_complex_expression(text)
        assert not profile.has_complex_expression, f"single keyword flipped decision: {text} -> {profile.to_dict()}"


class TestProbeOperatorRemovalFlips:
    """去任一结构算子即不触发：判定由结构承载，不由单关键词承载。"""

    @pytest.mark.parametrize(
        "with_operator,without_operator,expected_form",
        [
            # 多否定：拆掉第二个否定算子 → 单否定，不翻转。
            ("不是不想学", "不是想学", ComplexForm.MULTI_NEGATION),
            # 搁置：拆掉「再」→ 不构成「时间指称+再+处置」结构。
            ("以后再说", "以后说", ComplexForm.TIME_DEFERRAL),
            # 临期：拆掉强后续词 → 无临近后果。
            ("还没复习就要考试了", "还没复习完", ComplexForm.DEADLINE_PRESSURE),
            # 材料不足：拆掉否定算子 → 材料在场，非不足。
            ("现在没有材料", "现在有材料", ComplexForm.MATERIAL_INSUFFICIENCY),
        ],
    )
    def test_removal_kills_decision(self, with_operator: str, without_operator: str, expected_form: ComplexForm):
        assert probe_complex_expression(with_operator).has_form(expected_form)
        assert not probe_complex_expression(without_operator).has_form(expected_form)

    def test_mitigation_negates_material_blocking(self):
        """缓解词兜住缺口：材料不足不构成阻塞判定（可失败反例）。"""
        profile = probe_complex_expression("没有材料也不影响，我有笔记")
        assert not profile.has_form(ComplexForm.MATERIAL_INSUFFICIENCY)

    def test_empty_and_whitespace(self):
        assert not probe_complex_expression("").has_complex_expression
        assert not probe_complex_expression("   \n ").has_complex_expression


# ---------------------------------------------------------------------------
# 验收②：白名单构造 fail-loud + 未知 ref / 目录外 tool 显式拒绝
# ---------------------------------------------------------------------------


class TestWhitelistConstruction:
    def test_interventions_out_of_contract_vocab_fail_loud(self):
        with pytest.raises(ValueError, match="AURORA_INTERVENTION_TYPES"):
            SelectionRequest(allowed_interventions=frozenset({"made_up_intervention"}))

    def test_modes_out_of_execution_mode_fail_loud(self):
        with pytest.raises(ValueError, match="ExecutionMode"):
            SelectionRequest(allowed_execution_modes=frozenset({"teleport"}))

    def test_refs_out_of_closed_scheme_fail_loud(self):
        with pytest.raises(ValueError, match="AURORA_DECISION_REF_SCHEMES"):
            SelectionRequest(allowed_refs=frozenset({"unknown_scheme://x"}))

    def test_vocabularies_are_reused_not_copied(self):
        # 不造第二权威：干预词表/scheme 集直接来自契约常量。
        assert {"clarify", "rescope"} < AURORA_INTERVENTION_TYPES
        assert {"goal", "task"} < AURORA_DECISION_REF_SCHEMES


class TestUnknownRefAndToolRefusal:
    @pytest.mark.asyncio
    async def test_unknown_ref_refused_explicitly(self):
        proposer = _StubProposer([_proposal(used_ref_ids=["task://does-not-exist"])])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.UNKNOWN_REF
        assert any("task://does-not-exist" in violation for violation in outcome.violations)
        # 显式拒绝/澄清，绝无成功话术。
        text = outcome.render_refusal()
        assert "先不执行" in text
        for marker in SUCCESS_TALK_MARKERS:
            assert marker not in text
        # 未知 ref 不花修复调用（fail-loud）。
        assert proposer.calls == 1
        assert outcome.repairs_used == 0

    @pytest.mark.asyncio
    async def test_out_of_catalog_tool_refused_explicitly(self):
        proposer = _StubProposer([_proposal(tool="delete_all_tasks")])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.OUT_OF_CATALOG_TOOL
        assert any("delete_all_tasks" in violation for violation in outcome.violations)
        assert "先不执行" in outcome.render_refusal()

    @pytest.mark.asyncio
    async def test_ref_scheme_outside_closed_set_refused(self):
        proposer = _StubProposer([_proposal(used_ref_ids=["freeform://abc"])])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.UNKNOWN_REF
        assert any("ref_scheme_out_of_closed_set" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_unknown_intervention_refused(self):
        proposer = _StubProposer([_proposal(selected_intervention_id="ban_user")])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.UNKNOWN_INTERVENTION

    @pytest.mark.asyncio
    async def test_valid_vocab_but_not_in_whitelist_refused(self):
        # 契约词表成员（execute）但不在本次白名单 → 仍拒绝（白名单封闭）。
        proposer = _StubProposer([_proposal(selected_intervention_id="execute")])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.UNKNOWN_INTERVENTION
        assert any("intervention_not_in_allowed_set" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_invalid_execution_mode_refused(self):
        proposer = _StubProposer([_proposal(execution_mode="autonomous")])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.INVALID_EXECUTION_MODE

    def test_refused_outcome_structurally_carries_no_executable_claim(self):
        """拒绝结局结构上不携带可执行声明（「已执行」话术无处可拼）。"""
        refused = SelectionOutcome(verdict=SelectionVerdict.REFUSED, refusal_code=RefusalCode.UNKNOWN_REF)
        payload = refused.to_dict()
        assert payload["verdict"] == "refused"
        assert "selected_intervention_id" not in payload
        assert "execution_mode" not in payload
        assert "used_ref_ids" not in payload
        assert "tool" not in payload
        assert refused.selected_intervention_id is None
        assert refused.used_ref_ids == ()

    @pytest.mark.asyncio
    async def test_all_refusal_copies_free_of_success_talk(self):
        """全部拒绝码的冻结文案扫描：零成功话术（封闭词表逐一断言）。"""
        from app.orchestration.semantic_selector import _REFUSAL_COPY

        assert set(_REFUSAL_COPY) == set(RefusalCode)
        for code, text in _REFUSAL_COPY.items():
            assert text.strip(), code
            assert "先不执行" in text, code
            for marker in SUCCESS_TALK_MARKERS:
                assert marker not in text, f"{code} copy contains success talk: {marker}"


class TestSchemaValidationAndRepair:
    @pytest.mark.asyncio
    async def test_happy_path_selected(self):
        proposer = _StubProposer(
            [
                _proposal(
                    selected_intervention_id="rescope",
                    execution_mode="hybrid",
                    used_ref_ids=["goal://g-1", "task://t-1"],
                    tool="get_plan_state",
                    blocking_factors=[{"candidate_id": "c-1", "evidence_refs": ["memory://episodic/m-1"]}],
                    missing_decision_variable="目标截止日",
                    question="这次冲刺的截止日期是哪天？",
                    confidence_band="low",
                )
            ]
        )
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.SELECTED
        assert outcome.selected_intervention_id == "rescope"
        assert outcome.execution_mode == "hybrid"
        assert outcome.used_ref_ids == ("goal://g-1", "task://t-1")
        assert outcome.tool == "get_plan_state"
        assert outcome.blocking_factor_ids == ("c-1",)
        assert outcome.missing_decision_variable == "目标截止日"
        assert outcome.confidence_band == "low"
        assert outcome.failure_form == "none"

    @pytest.mark.asyncio
    async def test_schema_invalid_repaired_once_then_selected(self):
        bad = {"selected_intervention_id": "clarify", "execution_mode": "agent", "confidence_band": "extremely_sure"}
        proposer = _StubProposer([bad, _proposal()])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.SELECTED
        assert proposer.calls == 2
        assert outcome.repairs_used == MAX_SCHEMA_REPAIRS == 1
        # 修复轮携带违规反馈（可见修复，不是静默重试）。
        assert proposer.repair_feedbacks[1] and any("confidence_band" in item for item in proposer.repair_feedbacks[1])
        # 成本合并两次调用（I10 口径；来源一致保持 measured）。
        assert outcome.cost.model_calls == 2
        assert outcome.cost.prompt_tokens == 200
        assert outcome.cost.usage_source == "measured"

    @pytest.mark.asyncio
    async def test_schema_invalid_after_repair_refused(self):
        bad = {"selected_intervention_id": "clarify", "confidence_band": "nope"}
        proposer = _StubProposer([bad, bad])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.SCHEMA_INVALID_AFTER_REPAIR
        assert outcome.repairs_used == 1
        assert "先不执行" in outcome.render_refusal()

    @pytest.mark.asyncio
    async def test_unknown_keys_rejected(self):
        bad = _proposal(system_prompt_override="jailbreak")
        proposer = _StubProposer([bad, bad])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.SCHEMA_INVALID_AFTER_REPAIR
        assert any("unknown_key:system_prompt_override" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_missing_variable_requires_question(self):
        bad = _proposal(missing_decision_variable="目标截止日")
        proposer = _StubProposer([bad, bad])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.SCHEMA_INVALID_AFTER_REPAIR
        assert any("missing_variable_requires_question" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_inert_intervention_requires_null_mode(self):
        bad = _proposal(selected_intervention_id="no_action", execution_mode="agent")
        proposer = _StubProposer([bad, bad])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.SCHEMA_INVALID_AFTER_REPAIR
        assert any("inert_intervention_mode_must_be_null" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_inert_intervention_null_mode_selected(self):
        proposer = _StubProposer(
            [_proposal(selected_intervention_id="no_action", execution_mode=None, used_ref_ids=[])]
        )
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.SELECTED
        assert outcome.execution_mode is None

    @pytest.mark.asyncio
    async def test_abstain_with_closed_reason(self):
        proposer = _StubProposer(
            [
                _proposal(
                    selected_intervention_id=None,
                    execution_mode=None,
                    used_ref_ids=[],
                    abstain_reason="insufficient_context",
                    confidence_band="unknown",
                )
            ]
        )
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.ABSTAINED
        assert outcome.abstain_reason == "insufficient_context"
        assert outcome.failure_form == "abstained"

    @pytest.mark.asyncio
    async def test_abstain_reason_out_of_vocabulary_rejected(self):
        bad = _proposal(selected_intervention_id=None, execution_mode=None, abstain_reason="just_felt_like_it")
        proposer = _StubProposer([bad, bad])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.refusal_code is RefusalCode.SCHEMA_INVALID_AFTER_REPAIR
        assert any("abstain_reason_out_of_vocabulary" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_proposer_none_observable_degradation(self):
        outcome = await run_selection(_FULL_WHITELIST, None)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.PROPOSER_UNAVAILABLE
        assert outcome.cost == ZERO_MODEL_COST
        assert "先不执行" in outcome.render_refusal()

    @pytest.mark.asyncio
    async def test_proposer_exception_honest_cost_and_refusal(self):
        proposer = _StubProposer([RuntimeError("upstream 500")])
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.REFUSED
        assert outcome.refusal_code is RefusalCode.PROPOSER_UNAVAILABLE
        # 用量未知 → None 不冒充（I10 口径），不产生伪 0 实测。
        assert outcome.cost.usage_source is None
        assert outcome.cost.prompt_tokens is None
        assert any("proposer_exception" in violation for violation in outcome.violations)

    @pytest.mark.asyncio
    async def test_unknown_usage_reported_as_none_not_zero(self):
        """臂未上报用量 → cost None（unknown 不冒充），model_calls 仍如实。"""
        proposer = _StubProposer(
            [_proposal()],
            cost=ArmCost(model_calls=1, prompt_tokens=None, completion_tokens=None, usage_source=None),
        )
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.verdict is SelectionVerdict.SELECTED
        assert outcome.cost.model_calls == 1
        assert outcome.cost.usage_source is None
        assert outcome.cost.prompt_tokens is None

    @pytest.mark.asyncio
    async def test_sub_calls_slice_preserved(self):
        sub = [{"purpose": "repair", "prompt_tokens": 60, "completion_tokens": 10, "usage_source": "measured"}]
        proposer = _StubProposer(
            [_proposal()],
            cost=ArmCost(model_calls=1, prompt_tokens=60, completion_tokens=10, usage_source="measured", sub_calls=sub),
        )
        outcome = await run_selection(_FULL_WHITELIST, proposer)
        assert outcome.cost.sub_calls == tuple(sub)

    def test_confidence_bands_are_cautious_labels(self):
        assert {"high", "medium", "low", "unknown"} == CONFIDENCE_BANDS


# ---------------------------------------------------------------------------
# 验收③：同输入规则臂/语义臂对照——判定、成本、失败形态保留可审计
# ---------------------------------------------------------------------------


class TestArmComparison:
    @pytest.mark.asyncio
    async def test_comparison_record_keeps_both_arms_cost_and_failure(self):
        proposer = _StubProposer(
            [_proposal(selected_intervention_id="clarify", execution_mode="agent", used_ref_ids=[])]
        )
        record = await run_arm_comparison("现在没有材料，怎么开始复习？", _FULL_WHITELIST, proposer=proposer)

        payload = record.to_dict()
        # 可审计面：版本、输入指纹、双臂判定、双臂成本、失败形态全保留。
        assert payload["selector_version"]
        assert len(payload["input_text_sha256"]) == 64
        assert record.comparison_id.startswith("sscmp_") and len(record.comparison_id) == 6 + 32
        rule = payload["rule_arm"]
        semantic = payload["semantic_arm"]
        assert rule["decision"] == RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL.value
        assert rule["cost"] == {
            "model_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "usage_source": "measured",
            "sub_calls": [],
        }
        assert rule["failure_form"] == "none"
        assert semantic["verdict"] == "selected"
        assert semantic["selected_intervention_id"] == "clarify"
        assert semantic["cost"]["model_calls"] == 1
        assert semantic["cost"]["usage_source"] == "measured"
        assert semantic["failure_form"] == "none"
        assert record.agreement == "agree"
        assert record.agreement in COMPARISON_AGREEMENTS

    @pytest.mark.asyncio
    async def test_comparison_preserves_semantic_failure_form(self):
        proposer = _StubProposer([_proposal(tool="wipe_database")])
        record = await run_arm_comparison("以后再说吧", _FULL_WHITELIST, proposer=proposer)
        assert record.rule_arm.kind is RuleArmDecisionKind.DEFER_ACTION
        assert record.semantic_outcome.refusal_code is RefusalCode.OUT_OF_CATALOG_TOOL
        assert record.semantic_outcome.failure_form == "out_of_catalog_tool"
        assert record.agreement == "not_comparable"
        payload = record.to_dict()
        assert payload["semantic_arm"]["refusal_code"] == "out_of_catalog_tool"

    @pytest.mark.asyncio
    async def test_comparison_with_proposer_unavailable_records_failure(self):
        """生产影子形态：proposer 缺位 → 语义臂失败形态如实落账（零模型成本）。"""
        record = await run_arm_comparison("找不到复习资料", _FULL_WHITELIST, proposer=None)
        assert record.rule_arm.kind is RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL
        assert record.semantic_outcome.failure_form == "proposer_unavailable"
        assert record.semantic_outcome.cost == ZERO_MODEL_COST
        assert record.agreement == "not_comparable"

    @pytest.mark.asyncio
    async def test_comparison_deterministic_id_same_input(self):
        r1 = await run_arm_comparison("不是不想学", _FULL_WHITELIST, proposer=None)
        r2 = await run_arm_comparison("不是不想学", _FULL_WHITELIST, proposer=None)
        assert r1.comparison_id == r2.comparison_id
        assert r1.input_text_sha256 == r2.input_text_sha256

    @pytest.mark.asyncio
    async def test_audit_json_round_trip(self):
        import json

        record = await run_arm_comparison("还没复习完就要考试了", _FULL_WHITELIST, proposer=None)
        parsed = json.loads(record.to_audit_json())
        assert parsed["rule_arm"]["decision"] == RuleArmDecisionKind.RESCOPE_DEADLINE.value
        assert parsed["semantic_arm"]["failure_form"] == "proposer_unavailable"

    @pytest.mark.parametrize(
        "rule_kind,verdict,intervention,abstain,expected",
        [
            (RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL, SelectionVerdict.SELECTED, "clarify", None, "agree"),
            (RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL, SelectionVerdict.SELECTED, "pause", None, "disagree"),
            (
                RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL,
                SelectionVerdict.ABSTAINED,
                None,
                "insufficient_context",
                "agree",
            ),
            (RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL, SelectionVerdict.ABSTAINED, None, "policy_gap", "disagree"),
            (RuleArmDecisionKind.DEFER_ACTION, SelectionVerdict.SELECTED, "pause", None, "agree"),
            (RuleArmDecisionKind.RESCOPE_DEADLINE, SelectionVerdict.SELECTED, "split", None, "agree"),
            (RuleArmDecisionKind.SEMANTIC_ESCALATE, SelectionVerdict.REFUSED, None, None, "not_comparable"),
        ],
    )
    def test_compare_arms_mapping(self, rule_kind, verdict, intervention, abstain, expected):
        rule = RuleArmDecision(kind=rule_kind, profile=ComplexExpressionProfile(), question="")
        semantic = SelectionOutcome(verdict=verdict, selected_intervention_id=intervention, abstain_reason=abstain)
        assert compare_arms(rule, semantic) == expected

    def test_disagree_detected(self):
        rule = RuleArmDecision(kind=RuleArmDecisionKind.DEFER_ACTION, profile=ComplexExpressionProfile(), question="")
        semantic = SelectionOutcome(verdict=SelectionVerdict.SELECTED, selected_intervention_id="execute")
        assert compare_arms(rule, semantic) == "disagree"


# ---------------------------------------------------------------------------
# 行为开关与路由接线（shadow 永不改变路由；off 零行为）
# ---------------------------------------------------------------------------


class TestShadowMode:
    @pytest.mark.asyncio
    async def test_off_zero_behavior(self, monkeypatch):
        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "off")
        context_data: dict = {}
        result = await run_semantic_selector_shadow("以后再说吧", context_data)
        assert result is None
        assert "semantic_selector" not in context_data

    @pytest.mark.asyncio
    async def test_unknown_mode_fails_closed(self, monkeypatch):
        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "turbo")
        context_data: dict = {}
        result = await run_semantic_selector_shadow("以后再说吧", context_data)
        assert result is None
        assert "semantic_selector" not in context_data

    @pytest.mark.asyncio
    async def test_shadow_writes_record_without_routing_change(self, monkeypatch):
        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "shadow")
        context_data: dict = {}
        result = await run_semantic_selector_shadow("现在没有材料", context_data)
        assert result is not None
        assert context_data["semantic_selector"]["rule_arm"]["decision"] == "clarify_missing_material"
        assert context_data["semantic_selector_mode"] == "shadow"
        assert context_data["semantic_selector"]["semantic_arm"]["failure_form"] == "proposer_unavailable"

    @pytest.mark.asyncio
    async def test_router_node_shadow_keeps_routing_identical(self, monkeypatch):
        """影子对照在场：router_decision 与关闭时逐项一致（影子不裁决）。"""
        from app.agents.standard_workflow import router_node
        from app.orchestration.statechart_engine import WorkflowState

        constructed: list[int] = []

        class _FakeRouterNode:
            def __init__(self, *args, **kwargs):
                constructed.append(1)

            async def __call__(self, state):
                state.context_data["router_decision"] = "generation"
                state.context_data["router_confidence"] = 0.5
                return state

        monkeypatch.setattr("app.routing.router_node.RouterNode", _FakeRouterNode)

        def _state() -> WorkflowState:
            return WorkflowState(
                messages=[{"role": "user", "content": "还没复习完就要考试了，怎么办"}],
                context_data={"chat_mode": "standard"},
            )

        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "off")
        state_off = await router_node(_state())
        off_decision = state_off.context_data.get("router_decision")
        off_confidence = state_off.context_data.get("router_confidence")

        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "shadow")
        state_shadow = await router_node(_state())
        assert state_shadow.context_data.get("router_decision") == off_decision
        assert state_shadow.context_data.get("router_confidence") == off_confidence
        assert len(constructed) == 2
        # 影子记录在场但只是观测面。
        assert state_shadow.context_data["semantic_selector"]["rule_arm"]["decision"] == "rescope_deadline"
        assert state_off.context_data.get("semantic_selector") is None

    @pytest.mark.asyncio
    async def test_router_node_shadow_failure_never_breaks_routing(self, monkeypatch):
        """影子观测自身失败 → 路由继续（可观测降级，不阻塞主链）。"""
        from app.agents.standard_workflow import router_node
        from app.orchestration.statechart_engine import WorkflowState

        class _FakeRouterNode:
            def __init__(self, *args, **kwargs):
                pass

            async def __call__(self, state):
                state.context_data["router_decision"] = "generation"
                state.context_data["router_confidence"] = 0.5
                return state

        monkeypatch.setattr("app.routing.router_node.RouterNode", _FakeRouterNode)
        monkeypatch.setattr(settings_module, "SEMANTIC_SELECTOR_MODE", "shadow")

        async def _boom(*args, **kwargs):
            raise RuntimeError("shadow exploded")

        monkeypatch.setattr("app.orchestration.semantic_selector.run_semantic_selector_shadow", _boom)
        state = WorkflowState(
            messages=[{"role": "user", "content": "还剩3天考试"}],
            context_data={"chat_mode": "standard"},
        )
        new_state = await router_node(state)
        assert new_state.context_data.get("router_decision") == "generation"


# ---------------------------------------------------------------------------
# I09 词表不推翻回归：快路形态仍归 I09，本层零干扰
# ---------------------------------------------------------------------------


class TestFastLaneUntouched:
    def test_complex_expression_never_fast_lane(self):
        from app.orchestration.deterministic_lane import resolve_deterministic_lane

        for text in ("不是不想学", "以后再说吧", "现在没有材料", "还没复习完就要考试了"):
            assert resolve_deterministic_lane(text, {"chat_mode": "standard"}) is None

    def test_flag_defaults_off(self):
        assert settings_module.SEMANTIC_SELECTOR_MODE == "off"
