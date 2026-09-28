"""V4-D05 · 洞察呈现契约层守卫（``insight.presentation.v1``，纯函数面）。

与卡验收逐条对应（全部一正一反、可失败）：
- 验收①「三例只有两例关联不能写因果提升 67%」：``exaggeration_gate`` 数值面
  （因果成效×百分比、部分关联子集上的百分比、M-06 因果断言扫描三通道）；
- 验收②「无数据不出充分理解；已删来源不复用」：``understanding_claim_gate``
  三态 + ``exclude_withdrawn_refs`` 精确身份排除（unaffected 不连坐）；
- 验收③「一条观察≤一个主建议，用户可拒绝且不扣奖励」：``build_suggestion_
  envelope`` 单主建议 fail-loud + ``user_can_reject``/``reject_penalty="none"``
  结构冻结；
- objective「回访能证明上次建议是否相关而非套模板」：``build_revisit_record``
  七态封闭词表 + ``revisit_evidence_integrity``（相关性必须引用真实链接身份）；
- D02-R1 C-3 消费方义务：``dedupe_outcome_samples`` 样本身份先行去重（重放
  不进样本量；attr_ 派生权威 = D02 ``derive_attribution_sample_id``）。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.attribution import derive_attribution_sample_id
from app.core.insight_presentation import (
    CAUSAL_EFFECT_TERMS,
    GATE_ALLOWED,
    GATE_REJECTED,
    PRESENTATION_SCHEMA_VERSION,
    REASON_CAUSAL_ASSERTION,
    REASON_CAUSAL_PERCENTAGE,
    REASON_INCOMPLETE_EVIDENCE,
    REASON_NO_DATA_NO_CLAIM,
    REASON_PARTIAL_LINKAGE_PERCENT,
    REJECT_PENALTY_NONE,
    RELEVANCE_ACTED_AWAITING_OUTCOME,
    RELEVANCE_AWAITING_USER,
    RELEVANCE_CENSORED_USER_CHURNED,
    RELEVANCE_CENSORED_WINDOW_CLOSED,
    RELEVANCE_NO_PRIOR,
    RELEVANCE_REJECTED_BY_USER,
    RELEVANCE_RELATED_OUTCOME,
    REVISIT_RELEVANCES,
    SampleDedup,
    SuggestionEnvelope,
    build_revisit_record,
    build_suggestion_envelope,
    dedupe_outcome_samples,
    exaggeration_gate,
    exclude_withdrawn_refs,
    find_understanding_overclaims,
    presentation_sample_id,
    revisit_evidence_integrity,
    understanding_claim_gate,
)
from app.core.intervention_lifecycle import (
    FORBIDDEN_CLAIM_TERMS,
    ObservationStatus,
)

_T0 = datetime(2026, 9, 20, 9, 0, 0)
_DID = "aurora_" + "ab12cd34" * 4  # aurora_<32hex> 合法形态


# ---------------------------------------------------------------------------
# 验收① 夸大表述门（反例钉：三例只有两例关联不能写因果提升 67%）
# ---------------------------------------------------------------------------


class TestExaggerationGate:
    def test_three_examples_two_linked_causal_percentage_rejected(self):
        """反例钉：三例两例关联 + 「提升67%」→ 拒绝（因果×百分比）。"""
        verdict = exaggeration_gate(
            {},
            n_linked=2,
            n_denominator=3,
            claim_texts=["关联后提升67%", "interventions improved results by 67%"],
        )
        assert verdict.allowed is False
        assert verdict.status == GATE_REJECTED
        assert REASON_CAUSAL_PERCENTAGE in verdict.reasons

    def test_three_examples_two_linked_causal_word_without_number_still_rejected(self):
        """「有效/提升」族不带数字同样是成效断言——相关面不写成效。"""
        verdict = exaggeration_gate({}, n_linked=2, n_denominator=3, claim_texts=["该干预在此情境下有效"])
        assert verdict.allowed is False
        assert REASON_CAUSAL_ASSERTION in verdict.reasons

    def test_partial_linkage_percentage_rejected_even_without_causal_word(self):
        """反例：纯百分比建立在部分关联子集（2/3）上——分母未随行即拒绝。"""
        verdict = exaggeration_gate({}, n_linked=2, n_denominator=3, claim_texts=["67% 的情况如此"])
        assert verdict.allowed is False
        assert REASON_PARTIAL_LINKAGE_PERCENT in verdict.reasons

    def test_full_linkage_descriptive_percentage_allowed_without_causal_terms(self):
        """正例：分母完整（3/3）且无因果措辞的描述性百分比——允许。"""
        verdict = exaggeration_gate({}, n_linked=3, n_denominator=3, claim_texts=["3 次观察均关联（100%）"])
        assert verdict.allowed is True
        assert verdict.status == GATE_ALLOWED
        assert verdict.reasons == ()

    def test_closed_template_claim_passes(self):
        """正例：D-05 封闭模板文案（相关性措辞、无百分比）恒过门。"""
        claim = "该用户在相似情境下 3 次观察到该帮助与结果共同出现（重复观察，相关性证据，非因果结论）。"
        verdict = exaggeration_gate(
            {"interpretation": {"causal": False}},
            n_linked=2,
            n_denominator=3,
            claim_texts=[claim],
        )
        assert verdict.allowed is True

    def test_m06_scanner_channel_fires_on_causal_claim_value(self):
        """M-06 单一权威通道：payload 内 causal_claim=True / 禁词字段被检出。"""
        verdict = exaggeration_gate(
            {"interpretation": {"causal_claim": True}},
            n_linked=3,
            n_denominator=3,
        )
        assert verdict.allowed is False
        assert REASON_CAUSAL_ASSERTION in verdict.reasons

    def test_d05_forbidden_terms_channel(self):
        """D-05 FORBIDDEN_CLAIM_TERMS 通道：导致/使得/成功率/证明/caused 族文本被拒。"""
        for text in ("干预导致放弃", "这使得进度加快", "成功率 90%", "证明了用户已掌握", "this caused improvement"):
            verdict = exaggeration_gate({}, n_linked=3, n_denominator=3, claim_texts=[text])
            assert verdict.allowed is False, text
            assert REASON_CAUSAL_ASSERTION in verdict.reasons

    def test_user_content_not_scanned_as_system_claim(self):
        """用户自述内容（goal 标题含「提高」）不是系统宣称——不进文本门。"""
        payload = {"fact": {"title": "提高英语口语"}, "interpretation": {"band": "in_progress"}}
        verdict = exaggeration_gate(payload, n_linked=1, n_denominator=2)
        assert verdict.allowed is True

    def test_zero_denominator_percentage_rejected(self):
        """分母为零时宣称百分比 = 假精确（按 partial-linkage 拒）。"""
        verdict = exaggeration_gate({}, n_linked=0, n_denominator=0, claim_texts=["50% 关联"])
        assert verdict.allowed is False
        assert REASON_PARTIAL_LINKAGE_PERCENT in verdict.reasons

    def test_causal_effect_term_vocabulary_is_closed_and_nonempty(self):
        """词表冻结：因果/成效族非空、去重、且与 D-05 禁词表互补（不改动冻结词表）。"""
        assert len(CAUSAL_EFFECT_TERMS) == len(set(CAUSAL_EFFECT_TERMS))
        assert "提升" in CAUSAL_EFFECT_TERMS and "有效" in CAUSAL_EFFECT_TERMS
        assert not set(CAUSAL_EFFECT_TERMS) & set(FORBIDDEN_CLAIM_TERMS)


# ---------------------------------------------------------------------------
# 验收②前半 理解宣称门（无数据不出「充分理解」）
# ---------------------------------------------------------------------------


class TestUnderstandingClaimGate:
    def test_no_data_never_claims(self):
        verdict = understanding_claim_gate(samples=0, missing=0, censored=0)
        assert verdict.allowed is False
        assert verdict.reasons == (REASON_NO_DATA_NO_CLAIM,)

    def test_missing_or_censored_blocks_full_understanding(self):
        for kwargs in ({"missing": 1, "censored": 0}, {"missing": 0, "censored": 2}):
            verdict = understanding_claim_gate(samples=5, **kwargs)
            assert verdict.allowed is False
            assert verdict.reasons == (REASON_INCOMPLETE_EVIDENCE,)

    def test_complete_data_allows_qualitative_only(self):
        verdict = understanding_claim_gate(samples=5, missing=0, censored=0)
        assert verdict.allowed is True
        assert verdict.reasons == ()

    def test_zero_samples_with_censored_is_still_no_claim(self):
        """只有删失没有观察 → 连「不结论」宣称都无数据支撑（no_data 优先）。"""
        verdict = understanding_claim_gate(samples=0, missing=0, censored=3)
        assert verdict.allowed is False
        assert verdict.reasons == (REASON_NO_DATA_NO_CLAIM,)

    def test_overclaim_scanner_finds_term_and_clean_payload_passes(self):
        hit = find_understanding_overclaims({"summary": "系统已充分理解你的学习习惯"})
        assert hit == ["summary"]
        clean = find_understanding_overclaims(
            {"summary": "窗口内 3 次观察到共同出现（相关性证据，非因果结论）", "band": "in_progress"}
        )
        assert clean == []

    def test_overclaim_vocabulary_frozen(self):
        from app.core.insight_presentation import UNDERSTANDING_OVERCLAIM_TERMS

        assert "充分理解" in UNDERSTANDING_OVERCLAIM_TERMS
        assert "fully understood" in UNDERSTANDING_OVERCLAIM_TERMS


# ---------------------------------------------------------------------------
# 验收③ 单主建议信封（≤1 主建议；可拒绝且零惩罚）
# ---------------------------------------------------------------------------


class TestSinglePrimarySuggestion:
    def test_single_candidate_envelope_has_reject_affordance_without_penalty(self):
        envelope = build_suggestion_envelope(
            observation_id="interventions_that_helped:rescope:context_switch",
            candidates=[{"action_key": "review_directives", "deep_link": "/learning/insights/directives"}],
        )
        assert isinstance(envelope, SuggestionEnvelope)
        assert envelope.user_can_reject is True
        assert envelope.reject_penalty == REJECT_PENALTY_NONE == "none"
        assert envelope.primary is not None

    def test_observation_without_candidate_has_no_fabricated_action(self):
        envelope = build_suggestion_envelope(observation_id="x", candidates=[])
        assert envelope.primary is None
        assert envelope.user_can_reject is True  # 拒绝 affordance 与主建议解耦

    def test_two_primary_candidates_fail_loud(self):
        with pytest.raises(ValueError, match="at most one"):
            build_suggestion_envelope(observation_id="x", candidates=[{"a": 1}, {"b": 2}])

    def test_reject_penalty_constant_frozen(self):
        assert REJECT_PENALTY_NONE == "none"


# ---------------------------------------------------------------------------
# D02-R1 C-3 样本去重（重放不进样本量）
# ---------------------------------------------------------------------------


class TestSampleDedupe:
    def test_replayed_deliveries_collapse_to_one_sample(self):
        dedup = dedupe_outcome_samples(decision_id=_DID, outcome_ids=["outc_a", "outc_a", "outc_a"])
        assert isinstance(dedup, SampleDedup)
        assert dedup.n_raw == 3
        assert dedup.n_unique == 1
        assert dedup.duplicates_dropped == 2
        assert len(dedup.unique_sample_ids) == 1

    def test_distinct_outcomes_are_distinct_samples(self):
        dedup = dedupe_outcome_samples(decision_id=_DID, outcome_ids=["outc_a", "outc_b"])
        assert dedup.n_unique == 2 and dedup.duplicates_dropped == 0

    def test_sample_id_matches_d02_authority_and_is_replay_stable(self):
        """身份派生单一权威：与 D02 derive_attribution_sample_id 恒同（重放恒同 id）。"""
        expected = derive_attribution_sample_id(domain="occurrence", anchor_id=_DID, outcome_id="outc_a")
        assert presentation_sample_id(decision_id=_DID, outcome_id="outc_a") == expected
        assert presentation_sample_id(decision_id=_DID, outcome_id="outc_a") == presentation_sample_id(
            decision_id=_DID, outcome_id="outc_a"
        )
        assert expected.startswith("attr_") and len(expected) == 37

    def test_empty_outcome_ref_is_not_a_sample(self):
        dedup = dedupe_outcome_samples(decision_id=_DID, outcome_ids=["", ""])
        assert dedup.n_raw == 0 and dedup.n_unique == 0

    def test_same_outcome_two_decisions_is_two_real_links(self):
        """不同 decision 链接同一 outcome = 两条真实链接（跨锚点不去重）。"""
        a = dedupe_outcome_samples(decision_id="aurora_" + "a" * 32, outcome_ids=["outc_a"])
        b = dedupe_outcome_samples(decision_id="aurora_" + "b" * 32, outcome_ids=["outc_a"])
        assert a.unique_sample_ids[0] != b.unique_sample_ids[0]


# ---------------------------------------------------------------------------
# 验收②后半 已删来源不复用（撤回/删除源排除；unaffected 保留）
# ---------------------------------------------------------------------------


class TestWithdrawnSourceExclusion:
    def test_withdrawn_ref_excluded_others_kept(self):
        filtered = exclude_withdrawn_refs(["task:1", "goal:2", "decision:aurora_x"], ["goal:2"])
        assert filtered.kept == ("task:1", "decision:aurora_x")
        assert filtered.excluded == ("goal:2",)
        assert filtered.has_valid_evidence is True

    def test_same_value_different_type_is_not_same_source(self):
        """I05 SourcePointer 同律：值同、类型不同不构成同源（不连坐）。"""
        filtered = exclude_withdrawn_refs(["task:1"], ["goal:1"])
        assert filtered.kept == ("task:1",) and filtered.excluded == ()

    def test_all_sources_withdrawn_means_no_valid_evidence(self):
        filtered = exclude_withdrawn_refs(["goal:1"], ["goal:1"])
        assert filtered.has_valid_evidence is False
        assert filtered.kept == ()

    def test_empty_withdrawal_set_is_identity(self):
        refs = ("a", "b")
        filtered = exclude_withdrawn_refs(refs, [])
        assert filtered.kept == refs and filtered.excluded == ()


# ---------------------------------------------------------------------------
# 回访记录（相关性由真实事件证明，非套模板）
# ---------------------------------------------------------------------------


def _revisit(**overrides):
    params: dict = {
        "decision_id": _DID,
        "intervention_type": "rescope",
        "friction_tag": "context_switch",
        "shown_at": _T0,
        "response": None,
        "outcome_ids": (),
        "observation_status": ObservationStatus.CENSORED_NOT_YET_DUE,
    }
    params.update(overrides)
    return build_revisit_record(**params)


class TestRevisitRecord:
    def test_no_prior_suggestion_when_no_exposure(self):
        record = build_revisit_record(
            decision_id="",
            intervention_type="",
            friction_tag="",
            shown_at=None,
            response=None,
            outcome_ids=(),
            observation_status=None,
        )
        assert record.relevance == RELEVANCE_NO_PRIOR
        assert record.proves_relevance is False
        assert record.sample_ids == ()
        assert revisit_evidence_integrity(record) is True

    def test_related_outcome_proven_by_deduped_sample_ids(self):
        record = _revisit(
            response="accepted",
            outcome_ids=["outc_1", "outc_1", "outc_2"],
            observation_status=ObservationStatus.OBSERVED,
        )
        assert record.relevance == RELEVANCE_RELATED_OUTCOME
        assert record.proves_relevance is True
        assert record.n_outcome_samples_raw == 3
        assert record.n_outcome_samples_unique == 2  # 重放投递不进样本量
        assert len(record.sample_ids) == 2
        assert revisit_evidence_integrity(record) is True

    def test_user_rejection_is_first_class_and_zero_penalty(self):
        """用户拒绝 = 相关性判定权在用户；即便随后有链接 outcome 也不改写；零惩罚随行。"""
        record = _revisit(response="rejected", outcome_ids=["outc_1"], observation_status=ObservationStatus.OBSERVED)
        assert record.relevance == RELEVANCE_REJECTED_BY_USER
        assert record.proves_relevance is False
        assert record.reward_consequence == "none"
        assert record.n_outcome_samples_unique == 1  # 计数仍如实随行
        assert revisit_evidence_integrity(record) is True

    def test_acted_without_outcome_awaits(self):
        record = _revisit(response="accepted", observation_status=ObservationStatus.CENSORED_NOT_YET_DUE)
        assert record.relevance == RELEVANCE_ACTED_AWAITING_OUTCOME
        assert record.proves_relevance is False

    def test_awaiting_user_when_no_response_window_open(self):
        record = _revisit(response=None, observation_status=ObservationStatus.CENSORED_NOT_YET_DUE)
        assert record.relevance == RELEVANCE_AWAITING_USER

    def test_window_closed_without_outcome_is_censored_not_failure(self):
        record = _revisit(response=None, observation_status=ObservationStatus.CENSORED_WINDOW_CLOSED)
        assert record.relevance == RELEVANCE_CENSORED_WINDOW_CLOSED
        assert record.proves_relevance is False
        record2 = _revisit(response="accepted", observation_status=ObservationStatus.CENSORED_WINDOW_CLOSED)
        assert record2.relevance == RELEVANCE_CENSORED_WINDOW_CLOSED  # 行动无果 ≠ 失败（显式不结论）

    def test_churned_user_is_censored_churned(self):
        record = _revisit(response=None, observation_status=ObservationStatus.CENSORED_USER_CHURNED)
        assert record.relevance == RELEVANCE_CENSORED_USER_CHURNED

    def test_relevance_vocabulary_is_closed(self):
        assert (
            frozenset(
                {
                    RELEVANCE_NO_PRIOR,
                    RELEVANCE_REJECTED_BY_USER,
                    RELEVANCE_RELATED_OUTCOME,
                    RELEVANCE_ACTED_AWAITING_OUTCOME,
                    RELEVANCE_AWAITING_USER,
                    RELEVANCE_CENSORED_WINDOW_CLOSED,
                    RELEVANCE_CENSORED_USER_CHURNED,
                }
            )
            == REVISIT_RELEVANCES
        )
        assert RELEVANCE_NO_PRIOR in REVISIT_RELEVANCES

    def test_related_claim_without_sample_ids_fails_integrity(self):
        """「非套模板」结构钉：宣称相关却不携带真实链接身份 → 完整性为假。"""
        record = _revisit(response="accepted", outcome_ids=[], observation_status=ObservationStatus.OBSERVED)
        forged = record.__class__(
            decision_id=record.decision_id,
            intervention_type=record.intervention_type,
            friction_tag=record.friction_tag,
            shown_at=record.shown_at,
            response=record.response,
            relevance=RELEVANCE_RELATED_OUTCOME,  # 谎称相关
            n_outcome_samples_raw=0,
            n_outcome_samples_unique=0,
            proves_relevance=True,  # 自封
        )
        assert revisit_evidence_integrity(forged) is False

    def test_no_prior_drops_fabricated_events(self):
        """无 exposure 时编造的响应是孤儿事件——构建期丢弃（D-05 孤儿拒收同律），
        归一化后的记录内部一致（完整性为真；不携带任何编造痕迹）。"""
        record = build_revisit_record(
            decision_id="",
            intervention_type="",
            friction_tag="",
            shown_at=None,
            response="accepted",  # 无 exposure 却有响应 = 编造
            outcome_ids=("outc_1",),
            observation_status=None,
        )
        assert record.relevance == RELEVANCE_NO_PRIOR
        assert record.response is None
        assert record.sample_ids == ()
        assert record.n_outcome_samples_raw == 0
        assert revisit_evidence_integrity(record) is True

    def test_different_histories_produce_different_records(self):
        """两条不同历史 → 结构化字段必然不同（模板复述不可能同构）。"""
        related = _revisit(response="accepted", outcome_ids=["outc_1"], observation_status=ObservationStatus.OBSERVED)
        rejected = _revisit(response="rejected", outcome_ids=[], observation_status=ObservationStatus.OBSERVED)
        assert related.to_dict() != rejected.to_dict()
        assert related.relevance != rejected.relevance
        assert related.sample_ids != rejected.sample_ids

    def test_shown_at_serialized_iso_and_schema_version_pinned(self):
        record = _revisit()
        as_dict = record.to_dict()
        assert as_dict["shown_at"] == _T0.isoformat()
        assert as_dict["schema_version"] == PRESENTATION_SCHEMA_VERSION
        assert as_dict["decision_id"] == _DID


# ---------------------------------------------------------------------------
# 版本与冻结面
# ---------------------------------------------------------------------------


def test_schema_version_pinned():
    assert PRESENTATION_SCHEMA_VERSION == "insight.presentation.v1"


def test_observation_status_vocabulary_shared_with_d05():
    """窗口/删失语义只消费 D-05 权威词表（零第二语义）。"""
    from app.core.insight_presentation import _status_value

    assert _status_value(ObservationStatus.CENSORED_NOT_YET_DUE) == "censored_not_yet_due"
    assert _status_value(None) is None
