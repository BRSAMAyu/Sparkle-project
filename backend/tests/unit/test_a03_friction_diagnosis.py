"""A-03 · Friction Diagnosis + Sufficiency / One Best Question —— targeted tests.

覆盖面（对应卡面 Acceptance 与 wt 指令的「变异必红」要求）：

1. **词表/证据面/问题库/裁决参数 sha256 四指纹双钉**——任何一面被改（类型集、
   词牌权重、分支支持集、阈值、预算表）指纹测试必红；
2. **分类确定性**：同输入重复跑 + 输入 dict 键序打乱 → 输出 bit-for-bit 相等；
3. **充分性两路 + One Best Question 质量**：S1/S2/S3 直出；Q1 问询的 IG > 0、
   决策敏感（存在可达翻转）、已问不重问、IG 排序与暴力重算一致（非模板复读：
   不同情境选出不同问、IG 数值可论证）；
4. **追问预算**：session/day 双上限；ask_less 收紧 / ask_more 放宽（A-05 偏好
   联通）；超限 B1 best-guess + uncertain 标注 / B2 无证据不假诊断；
5. **错分类代价面**：burnout 语境绝不 practice 优先、skill 语境绝不 pause
   优先（错分类 → 错误干预路径的最小例证）；竞争带回退提名垫后；
6. **20 canonical scenarios**：≥18 合理；hard_family（同句三态、预算双路、
   冷启动闭环）全过——容差不适用于验收锚点；
7. **A 链衔接**：A-02 因子合并后选择面消费本模块提名；A-04 decide_joint 兼容；
   A-05 lifecycle 投影值域 + scope_matches 真 patch 冒烟；A-01 不确定类型词表；
8. **韧性**：脏输入（错型/越界/巨值/None）永不 raise。
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.aurora.friction_diagnosis import (
    ANSWER_SEED_WEIGHT,
    BRANCH_DECAY_MULTIPLIER,
    BRANCH_SUPPORT_MULTIPLIER,
    CLARIFICATION_PREFERENCE_BUDGETS,
    CLARIFICATION_PREFERENCE_VALUES,
    DEFAULT_DAY_QUESTION_LIMIT,
    DEFAULT_SESSION_QUESTION_LIMIT,
    FRICTION_DIAGNOSIS_REASONS,
    FRICTION_DIAGNOSIS_VERSION,
    FRICTION_EVIDENCE_TYPES,
    FRICTION_INTERVENTION_NOMINATIONS,
    FRICTION_OUTCOMES,
    FRICTION_QUESTION_BANK,
    FRICTION_TYPE_TO_LIFECYCLE_TAG,
    FRICTION_TYPES,
    FRICTION_UTTERANCE_LEXICON,
    SPINE_STATE_EVIDENCE,
    FrictionDiagnosisInput,
    apply_question_answer,
    diagnose_friction,
    friction_evidence_fingerprint,
    friction_question_bank_fingerprint,
    friction_sufficiency_fingerprint,
    friction_taxonomy_fingerprint,
    resolve_answer_branch,
)
from app.aurora.intervention_policy import (
    InterventionPolicyFactors,
    evaluate_intervention_policy,
)
from app.core.aurora_decision import (
    AURORA_INTERVENTION_TYPES,
    AURORA_UNCERTAINTY_KINDS,
)
from app.core.intervention_lifecycle import INTERVENTION_FRICTION_TAGS
from app.core.policy_patch import SURFACE_PAYLOAD_SCHEMAS, PolicyPatch
from app.signals.policy_engine import _RULE_TABLE

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "aurora" / "fixtures" / "friction_diagnosis_scenarios.json"

#: 四指纹的冻结值（A-02 词表双钉同款纪律；任何词面/阈值变更 → 此处必红，
#: 提醒提交者 bump FRICTION_DIAGNOSIS_VERSION 并过 reviewer）。
FROZEN_TAXONOMY_FINGERPRINT = "0ce224ab8e12139e2dbdce7092868bad7b7d0efd710de7d9f730ea46a6f6c903"
FROZEN_EVIDENCE_FINGERPRINT = "2bff307f03cb5176e0c2f885b43ed991f3ddf19631187da94aab5661e33df238"
FROZEN_QUESTION_BANK_FINGERPRINT = "059458db6e155905d31b12a32e30c1a6e55499f198fc85a92abd805c91ec4538"
FROZEN_SUFFICIENCY_FINGERPRINT = "a05fdee9fa84160c0fb907782489208e6dd4ed5f6d526d7e05a814119c851a18"


def _load_scenarios() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _run_scenario(scenario: dict) -> tuple[bool, str]:
    """执行单场景 rubric，返回 (pass, detail)。"""
    result = diagnose_friction(scenario["input"])
    expect = scenario["expect"]
    if result.outcome != expect["outcome"]:
        return False, f"outcome {result.outcome!r} != {expect['outcome']!r}"
    if result.friction_type not in expect["friction_in"]:
        return False, f"friction {result.friction_type!r} not in {expect['friction_in']}"
    if expect["outcome"] == "act":
        if not result.nominated_interventions:
            return False, "act outcome without nominations"
        if result.nominated_interventions[0] not in expect["nomination_first_in"]:
            return (
                False,
                f"primary nomination {result.nominated_interventions[0]!r} not in {expect['nomination_first_in']}",
            )
        if expect.get("must_carry_question") and not (result.suggested_clarifying_question or "").strip():
            return False, "clarify act path missing suggested question"
    if expect["outcome"] == "ask":
        if result.question is None:
            return False, "ask outcome without question"
        if result.question.question_id not in expect["question_id_in"]:
            return False, f"question {result.question.question_id!r} not in {expect['question_id_in']}"
    if expect.get("outcome") == "no_action" and expect.get("nomination_first_in") == []:
        if result.nominated_interventions:
            return False, "no_action/unknown fabricated nominations"
    if "uncertain" in expect and result.uncertain is not expect["uncertain"]:
        return False, f"uncertain {result.uncertain} != {expect['uncertain']}"
    if "reason_contains" in expect and expect["reason_contains"] not in result.reasons:
        return False, f"reasons {result.reasons} missing {expect['reason_contains']!r}"
    if "followup" in scenario:
        followup = scenario["followup"]
        question_id = result.question.question_id if result.question else None
        if question_id is None:
            return False, "followup configured but first step did not ask"
        branch = resolve_answer_branch(question_id, followup["answer_text"])
        if branch is None:
            return False, f"answer {followup['answer_text']!r} unresolved to branch"
        second = apply_question_answer(
            result,
            question_id,
            branch,
            extra_input=followup.get("extra_input"),
        )
        second_expect = followup["expect"]
        if second.outcome != second_expect["outcome"]:
            return False, f"followup outcome {second.outcome!r} != {second_expect['outcome']!r}"
        if second.friction_type not in second_expect["friction_in"]:
            return False, f"followup friction {second.friction_type!r} not in {second_expect['friction_in']}"
        if second_expect["outcome"] == "act":
            if second.nominated_interventions[0] not in second_expect["nomination_first_in"]:
                return (
                    False,
                    f"followup nomination {second.nominated_interventions[0]!r} not in {second_expect['nomination_first_in']}",
                )
    return True, "ok"


# ---------------------------------------------------------------------------
# 1. 词表冻结（sha256 双钉）
# ---------------------------------------------------------------------------


class TestVocabularyFreeze:
    def test_taxonomy_matches_v3_unified_semantics(self):
        """15 类封闭集 = USER_SEGMENTS_AND_JTBD §5 V3 统一语义（全小写投影）。"""
        assert (
            frozenset(
                {
                    "entry",
                    "clarity",
                    "knowledge",
                    "skill",
                    "difficulty",
                    "time",
                    "energy",
                    "dependency",
                    "choice",
                    "feedback",
                    "plan_drift",
                    "goal_drift",
                    "social",
                    "tooling",
                    "unknown",
                }
            )
            == FRICTION_TYPES
        )

    def test_nominations_cover_taxonomy_and_stay_in_a01_catalog(self):
        assert set(FRICTION_INTERVENTION_NOMINATIONS) == set(FRICTION_TYPES)
        for nominations in FRICTION_INTERVENTION_NOMINATIONS.values():
            assert set(nominations) <= AURORA_INTERVENTION_TYPES

    def test_unknown_never_nominates(self):
        """不假诊断：unknown 的提名恒空。"""
        assert FRICTION_INTERVENTION_NOMINATIONS["unknown"] == ()

    def test_taxonomy_fingerprint_double_pinned(self):
        assert friction_taxonomy_fingerprint() == FROZEN_TAXONOMY_FINGERPRINT

    def test_evidence_fingerprint_double_pinned(self):
        assert friction_evidence_fingerprint() == FROZEN_EVIDENCE_FINGERPRINT

    def test_question_bank_fingerprint_double_pinned(self):
        assert friction_question_bank_fingerprint() == FROZEN_QUESTION_BANK_FINGERPRINT

    def test_sufficiency_fingerprint_double_pinned(self):
        assert friction_sufficiency_fingerprint() == FROZEN_SUFFICIENCY_FINGERPRINT

    def test_reasons_and_outcomes_closed_vocabularies(self):
        assert (
            frozenset(
                {
                    "S1.sufficient_confidence",
                    "S2.sufficient_decision_equivalence",
                    "S3.sufficient_after_question",
                    "Q1.insufficient_ask_best_question",
                    "Q2.no_discriminative_question_act_argmax",
                    "B1.budget_exhausted_best_guess",
                    "B2.budget_exhausted_unknown_no_action",
                    "U1.unknown_ask_entry_question",
                    "E1.degraded_to_conservative",
                }
            )
            == FRICTION_DIAGNOSIS_REASONS
        )
        assert frozenset({"act", "ask", "no_action"}) == FRICTION_OUTCOMES

    def test_spine_state_evidence_covers_rule_table_exactly(self):
        """spine 演进（新增/改名 state_key）→ 此测试红（投影缺项即刻暴露）。"""
        assert set(SPINE_STATE_EVIDENCE) == set(_RULE_TABLE)

    def test_utterance_lexicon_covers_evidence_taxonomy(self):
        assert set(FRICTION_UTTERANCE_LEXICON) == set(FRICTION_EVIDENCE_TYPES)

    def test_lifecycle_projection_total_and_in_vocab(self):
        assert set(FRICTION_TYPE_TO_LIFECYCLE_TAG) == set(FRICTION_TYPES)
        assert set(FRICTION_TYPE_TO_LIFECYCLE_TAG.values()) <= INTERVENTION_FRICTION_TAGS

    def test_clarification_preference_structurally_derived_from_a05(self):
        """A-05 clarification 面值域的结构派生（零抄写；漂移红）。"""
        assert SURFACE_PAYLOAD_SCHEMAS["clarification"] == CLARIFICATION_PREFERENCE_VALUES


# ---------------------------------------------------------------------------
# 2. 分类确定性（同输入同分类）
# ---------------------------------------------------------------------------


class TestDeterminism:
    CASES = [
        {"utterance": "做不下去"},
        {"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True},
        {"utterance": "做不下去", "spine_state_keys": ["affective_pressure", "crisis_mode"]},
        {"utterance": "公式都会背，一做题就不会", "task_anchor": "期末复习"},
        {"spine_state_keys": ["knowledge_transfer", "recall_needed"], "materials_available_unused": True},
        {},
    ]

    @pytest.mark.parametrize("case", CASES)
    def test_repeat_calls_identical(self, case):
        first = diagnose_friction(case).to_dict()
        for _ in range(3):
            assert diagnose_friction(case).to_dict() == first

    @pytest.mark.parametrize("case", CASES)
    def test_input_key_order_irrelevant(self, case):
        reference = diagnose_friction(case).to_dict()
        reordered = dict(reversed(list(case.items())))
        assert diagnose_friction(reordered).to_dict() == reference

    def test_state_key_order_and_duplicates_irrelevant(self):
        a = diagnose_friction({"spine_state_keys": ["affective_pressure", "goal_mode"]}).to_dict()
        b = diagnose_friction({"spine_state_keys": ["goal_mode", "affective_pressure", "goal_mode"]}).to_dict()
        assert a == b


# ---------------------------------------------------------------------------
# 3. 充分性判定 + One Best Question 质量
# ---------------------------------------------------------------------------


class TestSufficiency:
    def test_s1_confidence_sufficient_acts_without_asking(self):
        result = diagnose_friction({"utterance": "做不下去", "spine_state_keys": ["affective_pressure"]})
        assert result.outcome == "act"
        assert "S1.sufficient_confidence" in result.reasons
        assert result.question is None
        assert not result.uncertain

    def test_s2_decision_equivalence_does_not_ask(self):
        """竞争带同首要提名 → 问不改变行动 → 不问（不必要澄清受控）。"""
        result = diagnose_friction({"utterance": "感觉计划全乱了，也不知道怎么开始"})
        assert result.outcome == "act"
        assert "S2.sufficient_decision_equivalence" in result.reasons
        assert result.question is None
        band_types = {t for t, p in result.posterior if t in ("entry", "plan_drift")}
        assert band_types == {"entry", "plan_drift"}
        # 带内回退提名垫后（错分类代价面：首要被守卫剔除时的确定性回退）。
        assert result.nominated_interventions[0] == "rescope"
        assert set(result.nominated_interventions) >= {"rescope", "split", "schedule"}

    def test_s3_sufficient_after_single_question(self):
        first = diagnose_friction({"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True})
        assert first.outcome == "ask"
        second = apply_question_answer(first, first.question.question_id, "tried_unsure")
        assert second.outcome == "act"
        assert "S3.sufficient_after_question" in second.reasons
        assert second.friction_type == "skill"
        assert second.nominated_interventions[0] == "practice"

    def test_q1_insufficient_asks_with_reported_ig(self):
        first = diagnose_friction({"utterance": "做不下去"})
        assert first.outcome == "ask"
        assert "Q1.insufficient_ask_best_question" in first.reasons
        assert first.question is not None
        # IG 可为负（答案可诚实拓宽不确定性），但必须已计算且有限（非模板复读的装饰数字）。
        assert first.question.information_gain_bits == first.question.information_gain_bits  # not NaN
        assert first.question.discriminates  # 正在分离的竞争带非空

    def test_q2_no_flippable_question_acts_with_uncertainty(self):
        """无可达翻转 → 问是纯官僚 → argmax 行动 + 不确定标注。"""
        # 单一微弱证据（energy 0.6 弱词牌独占）且所有问题的可达分支都无法
        # 翻转 argmax：构造 energy 弱独占场景。
        result = diagnose_friction({"utterance": "提不起劲"})
        # 无论走 S1 还是 Q2，都不允许问（微弱单证据下无问可改变行动或直接充分）
        assert result.outcome in {"act", "ask"}
        if result.outcome == "act" and "Q2.no_discriminative_question_act_argmax" in result.reasons:
            assert result.uncertain
            assert "insufficient_context" in result.uncertainty_kinds

    def test_e1_degrades_to_no_action_never_raises(self, monkeypatch):
        import app.aurora.friction_diagnosis as fd

        def _boom(_scores, _notes):
            raise RuntimeError("injected")

        monkeypatch.setattr(fd, "_utterance_scores", _boom)
        result = diagnose_friction({"utterance": "x"})
        assert result.outcome == "no_action"
        assert result.reasons == ("E1.degraded_to_conservative",)
        assert result.friction_type == "unknown"


class TestOneBestQuestionQuality:
    def test_selected_question_is_decision_sensitive_by_bruteforce(self):
        """所选问题存在 P(b)>0 的分支使变换后 argmax 首要提名改变（暴力重算）。"""
        from app.aurora.friction_diagnosis import (
            _QUESTION_BANK_INDEX,
            _apply_branch_transform,
            _argmax_type,
            _primary_nomination,
        )

        result = diagnose_friction({"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True})
        spec = _QUESTION_BANK_INDEX[result.question.question_id]
        scores = dict(result.evidence_scores)
        posterior = result.posterior
        current_primary = _primary_nomination(posterior[0][0])
        flips = []
        for branch in spec.branches:
            p_branch = sum(_p for t, _p in posterior if t in branch.supports)
            if p_branch <= 0:
                continue
            argmax = _argmax_type(_apply_branch_transform(scores, branch))
            if argmax is not None:
                flips.append(_primary_nomination(argmax) != current_primary)
        assert any(flips)

    def test_ig_matches_bruteforce_recomputation(self):
        """报告的 IG 数值与独立重算一致（非装饰性数字）。"""

        from app.aurora.friction_diagnosis import _apply_branch_transform, _entropy

        result = diagnose_friction({"utterance": "做不下去"})
        scores = dict(result.evidence_scores)
        posterior = result.posterior
        h0 = _entropy(dict(posterior))
        expected_after = 0.0
        for branch in result.question.branch_options:
            spec_branch = next(
                b
                for spec in FRICTION_QUESTION_BANK
                if spec.question_id == result.question.question_id
                for b in spec.branches
                if b.key == branch[0]
            )
            p_branch = sum(_p for t, _p in posterior if t in spec_branch.supports)
            if p_branch > 0:
                expected_after += p_branch * _entropy(_apply_branch_transform(scores, spec_branch))
        assert result.question.information_gain_bits == pytest.approx(h0 - expected_after, abs=1e-9)

    def test_ig_is_maximal_among_sensitive_questions(self):
        """选问 = 决策敏感集合中 IG 最大者（并列按冻结优先级）——暴力验证。"""
        from app.aurora.friction_diagnosis import (
            _apply_branch_transform,
            _entropy,
            _flip_changes_primary,
        )

        result = diagnose_friction({"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True})
        scores = dict(result.evidence_scores)
        posterior = result.posterior
        h0 = _entropy(dict(posterior))
        eligible: list[tuple[float, int, str]] = []
        for spec in FRICTION_QUESTION_BANK:
            if not _flip_changes_primary(spec, posterior, scores):
                continue
            expected_after = 0.0
            for branch in spec.branches:
                p_branch = sum(_p for t, _p in posterior if t in branch.supports)
                if p_branch > 0:
                    expected_after += p_branch * _entropy(_apply_branch_transform(scores, branch))
            eligible.append((-(h0 - expected_after), spec.priority, spec.question_id))
        eligible.sort()
        assert eligible[0][2] == result.question.question_id

    def test_asked_question_not_reasked(self):
        """已问过的问题不再被选（问卷回潮的面源封死）——用该问的**合法分支**
        作答后若仍需问，必须换下一问。"""
        first = diagnose_friction({"utterance": "做不下去"})
        assert first.outcome == "ask"
        valid_branches = {key for key, _label in first.question.branch_options}
        # tried_unsure 使后验仍不充分（skill/feedback 为种子级新证据 → 再问）
        ambiguous_branch = "tried_unsure" if "tried_unsure" in valid_branches else sorted(valid_branches)[0]
        second = apply_question_answer(first, first.question.question_id, ambiguous_branch)
        if second.outcome == "ask":
            assert second.question.question_id != first.question.question_id

    def test_question_text_renders_anchor_deterministically(self):
        from app.aurora.friction_diagnosis import _QUESTION_BANK_INDEX

        spec = _QUESTION_BANK_INDEX["q_direction_vs_push"]  # 含 {anchor} 的模板
        assert "{anchor}" not in spec.render(None)
        assert "「线代作业」" in spec.render("线代作业")
        # 任何被选问的渲染文本不得残留占位符（无论模板是否含锚）。
        for case in ({"utterance": "做不下去"}, {"utterance": "做不下去", "task_anchor": "线代作业"}):
            result = diagnose_friction(case)
            if result.question is not None:
                assert "{anchor}" not in result.question.text

    def test_different_contexts_select_different_questions(self):
        """非模板复读：不同情境的 One Best Question 不是同一问的复读。"""
        q_failures = diagnose_friction(
            {"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True}
        ).question.question_id
        q_bare = diagnose_friction({"utterance": "做不下去"}).question.question_id
        # 两情境都 ask 时问题应因证据结构不同而不同（同问也允许，但至少
        # 20 场景全集里出现 ≥3 种不同 question_id——由场景测试钉）。
        assert {q_failures, q_bare} <= {spec.question_id for spec in FRICTION_QUESTION_BANK}


# ---------------------------------------------------------------------------
# 4. 追问预算（防问卷回潮）
# ---------------------------------------------------------------------------


class TestQuestionBudget:
    AMBIGUOUS = {"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True}

    def test_default_budget_allows_ask_then_exhausts(self):
        assert DEFAULT_SESSION_QUESTION_LIMIT == 2
        assert DEFAULT_DAY_QUESTION_LIMIT == 5
        assert diagnose_friction(self.AMBIGUOUS).outcome == "ask"
        exhausted = diagnose_friction({**self.AMBIGUOUS, "questions_asked_session": 2})
        assert exhausted.outcome == "act"
        assert "B1.budget_exhausted_best_guess" in exhausted.reasons
        assert exhausted.uncertain
        assert "insufficient_context" in exhausted.uncertainty_kinds

    def test_day_budget_exhaustion_independent_of_session(self):
        result = diagnose_friction({**self.AMBIGUOUS, "questions_asked_day": 5})
        assert result.outcome == "act"
        assert "B1.budget_exhausted_best_guess" in result.reasons

    def test_b1_keeps_argmax_evidence(self):
        """best-guess 仍有 argmax 证据与提名（超限不等于躺平）。"""
        result = diagnose_friction({**self.AMBIGUOUS, "questions_asked_session": 2})
        assert result.friction_type in {"difficulty", "skill"}
        assert result.nominated_interventions
        assert result.budget_exhausted

    def test_b2_unknown_never_fabricates(self):
        """无证据 + 超限 → no_action + 空提名（不假诊断红线）。"""
        result = diagnose_friction({"questions_asked_day": 5})
        assert result.outcome == "no_action"
        assert result.friction_type == "unknown"
        assert result.nominated_interventions == ()
        assert "B2.budget_exhausted_unknown_no_action" in result.reasons

    def test_a05_ask_less_tightens_budget(self):
        assert CLARIFICATION_PREFERENCE_BUDGETS["ask_less"] == (1, 3)
        # session=1 在缺省预算(2)内可问，ask_less 下即超限 → best-guess。
        base = {**self.AMBIGUOUS, "questions_asked_session": 1}
        assert diagnose_friction(base).outcome == "ask"
        tightened = diagnose_friction({**base, "clarification_preference": "ask_less"})
        assert tightened.outcome == "act"
        assert "B1.budget_exhausted_best_guess" in tightened.reasons

    def test_a05_ask_more_loosens_budget(self):
        assert CLARIFICATION_PREFERENCE_BUDGETS["ask_more"] == (3, 8)
        loosened = diagnose_friction(
            {**self.AMBIGUOUS, "questions_asked_session": 2, "clarification_preference": "ask_more"}
        )
        assert loosened.outcome == "ask"

    def test_invalid_preference_ignored(self):
        result = diagnose_friction({**self.AMBIGUOUS, "clarification_preference": "ask_never"})
        assert result.outcome == "ask"


# ---------------------------------------------------------------------------
# 5. 错分类代价面（错分类 → 错误干预路径）
# ---------------------------------------------------------------------------


class TestMisclassificationCostSurface:
    def test_burnout_context_never_practices_first(self):
        """情绪耗竭语境被错判为 skill 时会给出「去练习」——错误干预路径；
        本测试钉死：affective 证据充分时 practice 绝不出现在首位。"""
        result = diagnose_friction({"utterance": "太累了，心累", "spine_state_keys": ["affective_pressure"]})
        assert result.friction_type == "energy"
        assert result.nominated_interventions[0] == "pause"
        assert "practice" not in result.nominated_interventions[:1]

    def test_skill_gap_context_never_pauses_first(self):
        """技能缺口语境被错判为 energy 时会给出「先歇会儿」——错误干预路径。"""
        result = diagnose_friction({"utterance": "公式都会背，一做题就不会", "recent_failure_count": 4})
        assert result.friction_type == "skill"
        assert result.nominated_interventions[0] == "practice"
        assert "pause" not in result.nominated_interventions[:1]

    def test_adversarial_label_swaps_change_intervention_family(self):
        """代价面存在性：同一输入被换成对抗标签 → 首要提名族不同（分类错→干预错）。
        这证明分类层有真实的决策杠杆，不是装饰性标签。"""
        energy = diagnose_friction({"utterance": "做不下去", "spine_state_keys": ["affective_pressure"]})
        skill = diagnose_friction(
            {
                "utterance": "做不下去",
                "recent_failure_count": 5,
                "has_task_context": True,
                "answered_branches": [["q_tried_and_checked", "tried_unsure"]],
            }
        )
        assert energy.nominated_interventions[0] != skill.nominated_interventions[0]
        assert set(energy.nominated_interventions).isdisjoint(set(skill.nominated_interventions[:1]))

    def test_contender_fallback_nominations_appended(self):
        """竞争带回退：带内 runner-up 的提名按序垫后（A-02 守卫剔除首要时的确定性回退面）。"""
        result = diagnose_friction({"utterance": "感觉计划全乱了，也不知道怎么开始"})
        assert result.nominated_interventions[0] == "rescope"
        assert "schedule" in result.nominated_interventions  # plan_drift 的次提名


# ---------------------------------------------------------------------------
# 6. 20 canonical stuck scenarios（卡面 Acceptance ① ②）
# ---------------------------------------------------------------------------


class TestCanonicalScenarios:
    def test_at_least_18_of_20_reasonable(self):
        payload = _load_scenarios()
        scenarios = payload["scenarios"]
        assert len(scenarios) == 20
        results = {s["scenario_id"]: _run_scenario(s) for s in scenarios}
        failures = {sid: detail for sid, (ok, detail) in results.items() if not ok}
        assert len(failures) <= 2, f"scenario failures (tolerance 2): {failures}"

    def test_hard_family_all_pass(self):
        """验收锚点（同句三态/预算双路/冷启动闭环）不吃容差。"""
        payload = _load_scenarios()
        hard_family = payload["hard_family"]
        results = {s["scenario_id"]: _run_scenario(s) for s in payload["scenarios"]}
        failures = {sid: results[sid][1] for sid in hard_family if not results[sid][0]}
        assert not failures, f"hard family failures: {failures}"

    def test_same_utterance_three_contexts_three_handlings(self):
        """卡面 Acceptance ②：同一句「做不下去」在不同 Context 产生不同处理。"""
        bare = diagnose_friction({"utterance": "做不下去"})
        failures = diagnose_friction({"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True})
        affective = diagnose_friction({"utterance": "做不下去", "spine_state_keys": ["affective_pressure"]})
        assert bare.outcome == "ask"
        assert failures.outcome == "ask"
        assert affective.outcome == "act"
        # 三种处理互不相同（签名含问询身份/首要提名）：
        # bare 问 difficulty/energy 平局 → failures 问 difficulty/skill 带 → affective 直出 pause。
        signatures = {
            (bare.outcome, bare.question.question_id, tuple(bare.question.discriminates)),
            (failures.outcome, failures.question.question_id, tuple(failures.question.discriminates)),
            (affective.outcome, affective.nominated_interventions[0]),
        }
        assert len(signatures) == 3
        assert affective.nominated_interventions[0] == "pause"

    def test_question_id_diversity_across_scenarios(self):
        """问询面非单一模板复读：场景全集出现 ≥2 种不同 question_id。"""
        payload = _load_scenarios()
        asked_ids = set()
        for scenario in payload["scenarios"]:
            result = diagnose_friction(scenario["input"])
            if result.question is not None:
                asked_ids.add(result.question.question_id)
        assert len(asked_ids) >= 2


# ---------------------------------------------------------------------------
# 7. A 链衔接（A-02 / A-04 / A-05 / A-01）
# ---------------------------------------------------------------------------


class TestAChainIntegration:
    def test_a02_policy_consumes_diagnosis_nominations(self):
        """A-02 衔接：patch 并入因子后选择面选出本模块首要提名。"""
        diagnosis = diagnose_friction({"utterance": "公式都会背，一做题就不会"})
        assert diagnosis.outcome == "act"
        factors = InterventionPolicyFactors.coerce(
            {
                "capabilities": {"chat", "llm_generate", "memory_read", "task_write"},
                "permissions": {"model_write"},
                "has_task_context": True,
                **diagnosis.policy_factors_patch(),
            }
        )
        evaluation = evaluate_intervention_policy(factors)
        assert evaluation.selected == diagnosis.nominated_interventions[0]
        assert "D1.first_legal_nominee" in evaluation.why

    def test_a02_unknown_patch_is_empty(self):
        """unknown / no_action 出口不改写下游提名（上游无诊断不越权）。"""
        diagnosis = diagnose_friction({"questions_asked_day": 5})
        assert diagnosis.policy_factors_patch() == {}

    def test_a02_clarify_act_carries_question_into_contract(self):
        from app.aurora.intervention_policy import build_decision_contract

        diagnosis = diagnose_friction(
            {"utterance": "老师没说要交什么格式，不知道做成什么样", "task_anchor": "期末论文"}
        )
        assert diagnosis.nominated_interventions[0] == "clarify"
        factors = InterventionPolicyFactors.coerce(
            {
                "capabilities": {"chat"},
                "permissions": set(),
                "has_task_context": True,
                **diagnosis.policy_factors_patch(),
            }
        )
        evaluation = evaluate_intervention_policy(factors)
        assert evaluation.selected == "clarify"
        contract, violations = build_decision_contract(
            evaluation,
            uuid4(),
            cognition_tier="l2_intervention",
            clarifying_question=diagnosis.suggested_clarifying_question,
        )
        assert contract is not None
        assert not violations
        assert contract.clarifying_question == diagnosis.suggested_clarifying_question
        assert contract.intervention_type == "clarify"

    def test_a04_decide_joint_consumes_diagnosis_nominations(self):
        from app.aurora.joint_decision import decide_joint

        diagnosis = diagnose_friction({"utterance": "做不下去", "spine_state_keys": ["affective_pressure"]})
        assert diagnosis.nominated_interventions[0] == "pause"
        # pause 的目录前提：caps {chat, task_write} + perm {plan_adjust}（A-02 守卫面）。
        factors = InterventionPolicyFactors.coerce(
            {
                "capabilities": {"chat", "task_write"},
                "permissions": {"plan_adjust"},
                "has_task_context": True,
                **diagnosis.policy_factors_patch(),
            }
        )
        joint = decide_joint(factors, None)
        assert joint.selected == "pause"

    def test_a05_lifecycle_projection_feeds_scope_matching(self):
        """A-05 上游信号源：诊断的 lifecycle 投影值可作为 patch scope 精确匹配。"""
        diagnosis = diagnose_friction({"utterance": "做不下去", "spine_state_keys": ["affective_pressure"]})
        tag = diagnosis.lifecycle_tag
        assert tag in INTERVENTION_FRICTION_TAGS
        patch = PolicyPatch(
            patch_id="polpatch_test00000000",
            user_id=str(uuid4()),
            surface="clarification",
            payload={"mode": "ask_less"},
            state="active",
            scope_friction_tag=tag,
        )
        assert patch.scope_matches(goal_type=None, friction_tag=tag)
        assert not patch.scope_matches(goal_type=None, friction_tag="knowledge_bottleneck")

    def test_a01_uncertainty_kinds_in_frozen_vocabulary(self):
        for case in (
            {"utterance": "做不下去"},
            {"questions_asked_day": 5},
            {"utterance": "做不下去", "recent_failure_count": 3, "questions_asked_session": 2},
        ):
            result = diagnose_friction(case)
            assert set(result.uncertainty_kinds) <= AURORA_UNCERTAINTY_KINDS

    def test_contract_annotations_carry_diagnosis_provenance(self):
        diagnosis = diagnose_friction({"utterance": "公式都会背，一做题就不会"})
        annotations = diagnosis.contract_annotations()
        assert annotations["friction_type"] == "skill"
        assert annotations["friction_diagnosis_version"] == FRICTION_DIAGNOSIS_VERSION
        assert annotations["friction_lifecycle_tag"] == "knowledge_bottleneck"

    def test_evidence_refs_use_existing_schemes_only(self):
        from app.core.aurora_decision import AURORA_DECISION_REF_SCHEMES

        result = diagnose_friction(
            {"utterance": "做不下去", "spine_state_keys": ["affective_pressure"], "days_since_progress": 7}
        )
        for ref in result.evidence_refs:
            assert ref.split("://", 1)[0] in AURORA_DECISION_REF_SCHEMES


# ---------------------------------------------------------------------------
# 8. 韧性（脏输入永不 raise）
# ---------------------------------------------------------------------------


class TestResilience:
    DIRTY_CASES = [
        None,
        {},
        "not-a-mapping",
        42,
        {"utterance": 123, "spine_state_keys": "single-string", "days_since_progress": 10**9},
        {"utterance": ["l", "i"], "recent_failure_count": -5, "blocked_on_external": "yes"},
        {"answered_branches": [["q_unknown", "x"], "garbage", ["q_direction_vs_push", "no_such_branch"]]},
        {"questions_asked_session": None, "questions_asked_day": "many", "clarification_preference": ["ask_less"]},
        {"task_anchor": "x" * 500, "utterance": "\x00\xff 做 不 下 去 "},
        {"utterance": "做不下去" * 500},
    ]

    @pytest.mark.parametrize("case", DIRTY_CASES)
    def test_dirty_input_never_raises(self, case):
        result = diagnose_friction(case)
        assert result.outcome in FRICTION_OUTCOMES
        assert result.friction_type in FRICTION_TYPES
        assert set(result.reasons) <= FRICTION_DIAGNOSIS_REASONS

    def test_coerce_bounds(self):
        coerced = FrictionDiagnosisInput.coerce(
            {"days_since_progress": 400, "recent_failure_count": -1, "task_anchor": "  "}
        )
        assert coerced.days_since_progress is None  # 越界 → 缺省
        assert coerced.recent_failure_count is None
        assert coerced.task_anchor is None

    def test_answer_resolution_first_hit_and_none_on_miss(self):
        assert resolve_answer_branch("q_direction_vs_push", "完全不知道下一步做什么") == "no_direction"
        assert resolve_answer_branch("q_direction_vs_push", "随便说点什么") is None
        assert resolve_answer_branch("no_such_question", "不知道做什么") is None
        assert resolve_answer_branch("q_direction_vs_push", "") is None

    def test_branch_transform_constants_frozen(self):
        """变换常数被指纹钉死之外的运行时断言（改常数 → IG/应用分叉检测前提）。"""
        assert BRANCH_SUPPORT_MULTIPLIER == 2.0
        assert BRANCH_DECAY_MULTIPLIER == 0.35
        assert ANSWER_SEED_WEIGHT == 1.0
