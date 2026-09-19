"""M-06 · Experience Memory 契约守卫（纯函数层，无 IO）。

钉死四条产品红线（卡 M-06 + 记忆流设计）：
1. **字段集/词表冻结**：记录/投影/检索结果 payload 的键集、召回桶名、
   截断原因码逐字冻结（任何变更须 bump ``EXPERIENCE_MEMORY_SCHEMA_VERSION``）；
2. **无因果断言字段**（验收 ③）：``scan_output_for_causal_assertions`` 对
   全量序列化输出干净；注入「effectiveness」字段或 ``causal_claim=True``
   变异必红；
3. **无 outcome 不标 effective**（验收 ② 的纯函数面）：方向判定谓词只读
   观察子集——删失/unknown/exposure 计数进不了 evidence_count / 方向 /
   档位（censored 计数变异注入方向谓词必红）；
4. **失败等价保留**：负向观察与正向同权进 evidence_count 与档位；混合
   记录同时进两个方向桶；无证据记录保留在 ``no_outcome_evidence`` 桶。

另钉：record_id 确定性、截断档位降级阶梯、情境匹配保守性（unknown/
unattributed 不匹配显式约束）、排序确定性、M-03 预筛候选鸭子类型契约
（record_kind=episodic / derive_status=active / classify=EXPERIENCE）。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.experience_memory import (
    BUCKET_NO_OUTCOME_EVIDENCE,
    CAUSAL_GUARD_KEY,
    DIRECTION_NEGATIVE,
    DIRECTION_POSITIVE,
    EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS,
    EXPERIENCE_FEEDBACK_KEYS,
    EXPERIENCE_MEMORY_SCHEMA_VERSION,
    EXPERIENCE_OUTCOME_FACE_KEYS,
    EXPERIENCE_PROJECTION_PAYLOAD_KEYS,
    EXPERIENCE_RECALL_BUCKETS,
    EXPERIENCE_RECORD_PAYLOAD_KEYS,
    EXPERIENCE_RECORD_TYPE,
    SUMMARY_TRUNCATION_REASON,
    ExperienceContextQuery,
    ExperienceMemoryRecord,
    derive_experience_record_id,
    downgrade_evidence_tier,
    project_slice,
    project_summary,
    rank_experience_records,
    scan_output_for_causal_assertions,
    signature_matches_query,
    split_by_evidence_direction,
)
from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_ACCUMULATED,
    EVIDENCE_TIER_INSUFFICIENT,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_SINGLE,
    AssociationSummary,
    SituationSignature,
    SliceSummary,
)

_T0 = datetime(2026, 9, 19, 10, 0, 0)


def _record(**overrides) -> ExperienceMemoryRecord:
    """最小合法经验记录（默认：2 正 1 负观察，repeated 档）。"""
    defaults: dict = {
        "record_id": "expmem_" + "a" * 16,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "signature": SituationSignature(
            intervention_type="rescope",
            goal_type="exam",
            friction_tag="cognitive_overload",
            execution_mode="hybrid",
        ),
        "n_exposed": 3,
        "n_accepted": 2,
        "n_started": 1,
        "observed_with_positive": 2,
        "observed_with_negative": 1,
        "evidence_strength": EVIDENCE_TIER_REPEATED,
        "claim": "该用户在相似情境下 3 次观察到该帮助与结果共同出现（重复观察，相关性证据，非因果结论）。",
        "scope": ("user", "11111111-1111-1111-1111-111111111111"),
        "generated_at": _T0,
    }
    defaults.update(overrides)
    return ExperienceMemoryRecord(**defaults)


def _slice(**overrides) -> SliceSummary:
    defaults: dict = {
        "signature": SituationSignature(
            intervention_type="rescope",
            goal_type="exam",
            friction_tag="cognitive_overload",
            execution_mode="hybrid",
        ),
        "n_exposed": 3,
        "n_accepted": 2,
        "n_started": 1,
        "n_positive": 2,
        "n_negative": 1,
        "evidence_strength": EVIDENCE_TIER_REPEATED,
        "claim": "该用户在相似情境下 3 次观察到该帮助与结果共同出现（重复观察，相关性证据，非因果结论）。",
    }
    defaults.update(overrides)
    return SliceSummary(**defaults)


# ---------------------------------------------------------------------------
# 1. 字段集 / 词表冻结
# ---------------------------------------------------------------------------


class TestFrozenVocabularies:
    def test_record_payload_keys_frozen(self):
        record = _record()
        assert tuple(record.to_dict().keys()) == EXPERIENCE_RECORD_PAYLOAD_KEYS

    def test_outcome_face_keys_frozen(self):
        assert tuple(_record().outcome_face.keys()) == EXPERIENCE_OUTCOME_FACE_KEYS
        assert tuple(_record().feedback.keys()) == EXPERIENCE_FEEDBACK_KEYS

    def test_projection_payload_keys_frozen(self):
        summary = AssociationSummary(
            scope=("user", "11111111-1111-1111-1111-111111111111"),
            generated_at=_T0,
            since=None,
            until=None,
            watermark="wm_test",
            slices=(_slice(),),
        )
        assert tuple(project_summary(summary).to_dict().keys()) == EXPERIENCE_PROJECTION_PAYLOAD_KEYS

    def test_recall_bucket_vocabulary_frozen(self):
        assert EXPERIENCE_RECALL_BUCKETS == (
            "observed_with_positive",
            "observed_with_negative",
            "no_outcome_evidence",
        )

    def test_truncation_reason_code_frozen(self):
        assert SUMMARY_TRUNCATION_REASON == "d05_summary_cap_exceeded"

    def test_schema_version_shape(self):
        assert EXPERIENCE_MEMORY_SCHEMA_VERSION == "experience_memory.m06.v1"
        assert EXPERIENCE_RECORD_TYPE == "EXPERIENCE"


# ---------------------------------------------------------------------------
# 2. 无因果断言（验收 ③ 机制化；变异必红）
# ---------------------------------------------------------------------------


class TestNoCausalAssertionGuard:
    def test_full_serialization_clean(self):
        summary = AssociationSummary(
            scope=("user", "11111111-1111-1111-1111-111111111111"),
            generated_at=_T0,
            since=None,
            until=None,
            watermark="wm_test",
            slices=(
                _slice(),
                _slice(
                    signature=SituationSignature("reframe", "exam", "cognitive_overload", "agent"),
                    n_positive=0,
                    n_negative=0,
                    evidence_strength=EVIDENCE_TIER_INSUFFICIENT,
                    claim="该用户尚无足够的观察样本，不能判断该帮助与此情境下结果的关联。",
                ),
            ),
        )
        violations = scan_output_for_causal_assertions(project_summary(summary, truncated=True).to_dict())
        assert violations == []

    def test_mutation_effectiveness_field_is_caught(self):
        payload = _record().to_dict()
        payload["effectiveness"] = 0.8  # 变异：注入效果断言字段
        assert any("forbidden field name" in v for v in scan_output_for_causal_assertions(payload))

    def test_mutation_causal_claim_true_is_caught(self):
        payload = _record().to_dict()
        payload[CAUSAL_GUARD_KEY] = True  # 变异：因果断言翻转
        violations = scan_output_for_causal_assertions(payload)
        assert any("causal_claim must be False" in v for v in violations)

    def test_mutation_forbidden_claim_term_is_caught(self):
        payload = _record().to_dict()
        payload["claim"] = "该干预导致了成功（证明了有效率）"  # 变异：因果文案
        violations = scan_output_for_causal_assertions(payload)
        assert len(violations) >= 3  # 导致 + 成功率/有效率/证明了 族至少命中多个

    def test_mutation_nested_forbidden_field_is_caught(self):
        payload = {"result": {"records": [{"works_because": True}]}}  # 深层嵌套
        assert any("forbidden field name" in v for v in scan_output_for_causal_assertions(payload))

    def test_record_serialization_always_carries_false_causal_guard(self):
        assert _record().to_dict()[CAUSAL_GUARD_KEY] is False


# ---------------------------------------------------------------------------
# 3. 无 outcome 不标 effective（验收 ② 纯函数面；变异必红）
# ---------------------------------------------------------------------------


class TestNoOutcomeNeverMarked:
    def test_censored_only_record_has_no_evidence(self):
        record = _record(
            observed_with_positive=0,
            observed_with_negative=0,
            censored_not_yet_due=4,
            censored_window_closed=2,
            censored_user_churned=1,
            n_unknown_status=3,
            n_exposed=10,
            evidence_strength=EVIDENCE_TIER_INSUFFICIENT,
        )
        assert record.evidence_count == 0
        assert record.has_outcome_evidence is False
        assert record.has_positive_association_evidence is False
        assert record.has_negative_association_evidence is False

    def test_mutation_censored_counting_as_evidence_is_caught(self):
        """变异面：把删失计入 evidence_count / 方向谓词 → 本测试族必红。

        （运行变异验证时把 evidence_count 改为
        ``observed_with_positive + observed_with_negative + censored_*`` 之和，
        test_censored_only_record_has_no_evidence 的 evidence_count==0 断言
        与分桶测试的桶归属断言都会失败。）
        """
        record = _record(observed_with_positive=0, observed_with_negative=0, censored_not_yet_due=5)
        buckets = split_by_evidence_direction([record])
        assert buckets[DIRECTION_POSITIVE] == ()
        assert buckets[DIRECTION_NEGATIVE] == ()
        assert buckets[BUCKET_NO_OUTCOME_EVIDENCE] == (record,)

    def test_unknown_status_preserved_but_not_evidence(self):
        """验收 ④ 纯函数面：unknown 保留在 outcome 面，不进证据。"""
        record = _record(observed_with_positive=0, observed_with_negative=0, n_unknown_status=7)
        payload = record.to_dict()
        assert payload["outcome"]["unknown"] == 7
        assert payload["evidence_count"] == 0
        assert record.has_outcome_evidence is False

    def test_strength_never_upgraded_by_censoring(self):
        """档位只由观察数决定（D-05 语义投影）：大量删失不推高档位。"""
        record = _record(
            observed_with_positive=1,
            observed_with_negative=0,
            censored_window_closed=50,
            evidence_strength=EVIDENCE_TIER_SINGLE,
        )
        assert record.evidence_strength == EVIDENCE_TIER_SINGLE
        assert record.evidence_count == 1

    def test_mixed_direction_record_enters_both_buckets(self):
        record = _record()  # 2 正 1 负
        buckets = split_by_evidence_direction([record])
        assert record in buckets[DIRECTION_POSITIVE]
        assert record in buckets[DIRECTION_NEGATIVE]
        assert record not in buckets[BUCKET_NO_OUTCOME_EVIDENCE]

    def test_negative_evidence_equal_to_positive(self):
        """失败等价保留：同观察数的正/负记录同档位、同 evidence_count。"""
        positive = _record(observed_with_positive=3, observed_with_negative=0)
        negative = _record(
            observed_with_positive=0,
            observed_with_negative=3,
            signature=SituationSignature("reframe", "exam", "cognitive_overload", "hybrid"),
        )
        assert positive.evidence_count == negative.evidence_count
        assert positive.evidence_strength == negative.evidence_strength


# ---------------------------------------------------------------------------
# 4. 投影映射（D-05 载体 → 记录，零语义改写）
# ---------------------------------------------------------------------------


class TestProjectionMapping:
    def test_slice_fields_projected_verbatim(self):
        record = project_slice(
            _slice(
                n_exposed=5,
                n_accepted=3,
                n_started=2,
                n_positive=2,
                n_negative=1,
                n_censored_not_yet_due=1,
                n_censored_window_closed=1,
                n_censored_user_churned=1,
                n_unknown=1,
            ),
            scope=("user", "u1"),
            user_id="u1",
            since=None,
            until=None,
            generated_at=_T0,
            truncated=False,
        )
        assert record.n_exposed == 5
        assert record.feedback == {"accepted": 3, "started": 2}
        assert record.observed_with_positive == 2
        assert record.observed_with_negative == 1
        assert record.censored_not_yet_due == 1
        assert record.censored_window_closed == 1
        assert record.censored_user_churned == 1
        assert record.n_unknown_status == 1
        assert record.evidence_count == 3
        assert record.evidence_strength == EVIDENCE_TIER_REPEATED
        assert record.completeness_adjusted_strength == EVIDENCE_TIER_REPEATED

    def test_truncation_downgrades_adjusted_strength_only(self):
        record = project_slice(
            _slice(),
            scope=("user", "u1"),
            user_id="u1",
            since=None,
            until=None,
            generated_at=_T0,
            truncated=True,
        )
        assert record.evidence_strength == EVIDENCE_TIER_REPEATED  # D-05 原值保留
        assert record.completeness_adjusted_strength == EVIDENCE_TIER_SINGLE  # 降一级
        assert record.to_dict()["truncated"] is True

    def test_downgrade_ladder(self):
        assert downgrade_evidence_tier(EVIDENCE_TIER_ACCUMULATED) == EVIDENCE_TIER_REPEATED
        assert downgrade_evidence_tier(EVIDENCE_TIER_REPEATED) == EVIDENCE_TIER_SINGLE
        assert downgrade_evidence_tier(EVIDENCE_TIER_SINGLE) == EVIDENCE_TIER_INSUFFICIENT
        assert downgrade_evidence_tier(EVIDENCE_TIER_INSUFFICIENT) == EVIDENCE_TIER_INSUFFICIENT
        assert downgrade_evidence_tier("garbage_tier") == EVIDENCE_TIER_INSUFFICIENT

    def test_projection_carries_truncation_face(self):
        summary = AssociationSummary(
            scope=("user", "u1"),
            generated_at=_T0,
            since=None,
            until=None,
            watermark="wm_test",
            slices=(_slice(),),
        )
        projection = project_summary(summary, truncated=True)
        assert projection.truncated is True
        assert projection.truncation_reason == SUMMARY_TRUNCATION_REASON
        assert all(record.truncated for record in projection.records)

    def test_global_scope_user_id_none(self):
        summary = AssociationSummary(
            scope=("global",),
            generated_at=_T0,
            since=None,
            until=None,
            watermark="wm_test",
            slices=(_slice(),),
        )
        projection = project_summary(summary)
        assert projection.user_id is None
        assert projection.records[0].user_id is None


# ---------------------------------------------------------------------------
# 5. record_id 确定性（幂等投影；消费方可安全去重）
# ---------------------------------------------------------------------------


class TestRecordIdDeterminism:
    def test_same_inputs_same_id(self):
        signature = _record().signature
        first = derive_experience_record_id(scope=("user", "u1"), signature=signature, since=None, until=None)
        second = derive_experience_record_id(scope=("user", "u1"), signature=signature, since=None, until=None)
        assert first == second and first.startswith("expmem_")

    def test_different_scope_or_window_different_id(self):
        signature = _record().signature
        base = derive_experience_record_id(scope=("user", "u1"), signature=signature, since=None, until=None)
        other_user = derive_experience_record_id(scope=("user", "u2"), signature=signature, since=None, until=None)
        other_window = derive_experience_record_id(scope=("user", "u1"), signature=signature, since=_T0, until=None)
        other_signature = derive_experience_record_id(
            scope=("user", "u1"),
            signature=SituationSignature("reframe", "exam", "cognitive_overload", "hybrid"),
            since=None,
            until=None,
        )
        assert len({base, other_user, other_window, other_signature}) == 4


# ---------------------------------------------------------------------------
# 6. 情境匹配与排序（检索确定性）
# ---------------------------------------------------------------------------


class TestMatchingAndRanking:
    def test_unconstrained_dimensions_pass(self):
        assert signature_matches_query({}, _record().signature) is True

    def test_constrained_dimensions_exact_match(self):
        signature = _record().signature
        assert signature_matches_query({"goal_type": "exam"}, signature) is True
        assert signature_matches_query({"goal_type": "project"}, signature) is False
        assert (
            signature_matches_query(
                {"goal_type": "exam", "friction_tag": "cognitive_overload", "execution_mode": "hybrid"},
                signature,
            )
            is True
        )

    def test_unknown_values_never_match_explicit_constraint(self):
        """保守匹配：unknown/unattributed 不猜（不匹配任何显式约束）。"""
        unknown_sig = SituationSignature("rescope", "unknown", "unattributed", "unattributed")
        assert signature_matches_query({"goal_type": "exam"}, unknown_sig) is False
        assert signature_matches_query({"friction_tag": "cognitive_overload"}, unknown_sig) is False

    def test_intervention_type_narrows_answer_axis(self):
        signature = _record().signature
        assert signature_matches_query({"intervention_type": "rescope"}, signature) is True
        assert signature_matches_query({"intervention_type": "reframe"}, signature) is False

    def test_ranking_deterministic(self):
        low = _record(record_id="expmem_low", observed_with_positive=1, observed_with_negative=0)
        high = _record(record_id="expmem_high", observed_with_positive=2, observed_with_negative=2)
        tie_a = _record(record_id="expmem_a", observed_with_positive=1, observed_with_negative=0)
        tie_b = _record(
            record_id="expmem_b",
            observed_with_positive=1,
            observed_with_negative=0,
            signature=SituationSignature("zzz_last", "exam", "cognitive_overload", "hybrid"),
        )
        ranked = rank_experience_records([low, high, tie_b, tie_a])
        assert [r.record_id for r in ranked] == ["expmem_high", "expmem_low", "expmem_a", "expmem_b"]

    def test_query_constraints_reflect_only_set_dimensions(self):
        query = ExperienceContextQuery(
            user_id="11111111-1111-1111-1111-111111111111",
            goal_type="exam",
            friction_tag=None,
        )
        assert query.constraints() == {"goal_type": "exam"}


# ---------------------------------------------------------------------------
# 7. M-03 预筛候选鸭子类型契约（接线不变量）
# ---------------------------------------------------------------------------


class TestPrefilterDuckTyping:
    def test_record_is_episodic_kind_active_experiENCE_class(self):
        from app.services.memory_epistemic_contract import classify_episodic_class, derive_status
        from app.services.memory_retrieval_prefilter import record_kind

        record = _record()
        assert record_kind(record) == "episodic"  # summary + occurred_at 嗅探
        assert derive_status(record, now=_T0) == "active"  # 无生命周期列 → active
        assert (
            classify_episodic_class(
                record.source_lane, explicit_class=record.epistemic_class, source_type=record.source_type
            )
            == "EXPERIENCE"
        )  # 显式 EXPERIENCE → 非 HYPOTHESIS（inferred 门不误伤）

    def test_prefilter_candidates_accepts_record_with_matching_context(self):
        from app.services.memory_retrieval_prefilter import RetrievalContext, prefilter_candidates

        record = _record()
        ctx = RetrievalContext(
            user_id=str(record.user_id),
            purpose="llm_context",
            now=_T0,
        )
        result = prefilter_candidates([record], ctx)
        assert result.allowed == [record]

    def test_prefilter_candidates_cuts_wrong_user(self):
        from app.services.memory_retrieval_prefilter import RetrievalContext, prefilter_candidates

        record = _record()
        ctx = RetrievalContext(user_id="22222222-2222-2222-2222-222222222222", purpose="llm_context", now=_T0)
        result = prefilter_candidates([record], ctx)
        assert result.allowed == []
        assert result.rejections[0].reason == "user:wrong_user"


# ---------------------------------------------------------------------------
# 8. 检索结果序列化（形状冻结 + 干净面）
# ---------------------------------------------------------------------------


class TestContextResultShape:
    def test_result_payload_keys_frozen_and_clean(self):
        record = _record()
        from app.core.experience_memory import ExperienceContextResult

        result = ExperienceContextResult(
            schema_version=EXPERIENCE_MEMORY_SCHEMA_VERSION,
            query=ExperienceContextQuery(user_id=str(record.user_id)),
            observed_with_positive=(record,),
        )
        payload = result.to_dict()
        assert tuple(payload.keys()) == EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS
        assert scan_output_for_causal_assertions(payload) == []
        assert payload["degraded_confidence"]["truncated"] is False

    def test_degraded_confidence_face_when_truncated(self):
        from app.core.experience_memory import ExperienceContextResult

        result = ExperienceContextResult(
            schema_version=EXPERIENCE_MEMORY_SCHEMA_VERSION,
            query=ExperienceContextQuery(user_id="u1"),
            truncated=True,
            truncation_reason=SUMMARY_TRUNCATION_REASON,
        )
        face = result.to_dict()["degraded_confidence"]
        assert face["truncated"] is True
        assert face["reason"] == SUMMARY_TRUNCATION_REASON
        assert "completeness_adjusted_strength" in face["note"]


@pytest.mark.parametrize(
    "tier",
    [EVIDENCE_TIER_INSUFFICIENT, EVIDENCE_TIER_SINGLE, EVIDENCE_TIER_REPEATED, EVIDENCE_TIER_ACCUMULATED],
)
def test_every_tier_claim_stays_clean(tier):
    """全档位 claim 模板（D-05 产出）过 M-06 无因果扫描。"""
    from app.core.intervention_lifecycle import association_claim

    claim = association_claim(tier, n_observed=6, n_positive=4, n_negative=2, scope_label="该用户")
    record = _record(claim=claim, evidence_strength=tier)
    assert scan_output_for_causal_assertions(record.to_dict()) == []
