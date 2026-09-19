"""D-05 · Intervention lifecycle 契约守卫（词表冻结 / 红线 / 删失语义 / 统计谦抑）。

覆盖面（对应卡 D-05 验收与 DATA_FLYWHEEL §5 禁令）：
- 生命周期六事件词表与 outcome 关联白名单**字面冻结**——把 chat reply 类源加进
  白名单的变异必红（灵魂红线：禁止用 chat reply 当 outcome）；
- 运行期硬拒绝门：即使未来白名单被污染，禁用字样（chat/reply/sentiment/…）
  仍被 ``is_whitelisted_outcome_source`` 拒收；
- censored/unknown 五态语义（未到期 ≠ 流失 ≠ 窗口关闭 ≠ 未知 ≠ 观察）；
- Wilson 区间 / 证据档位 / claim 禁词 / TruthClass 权重的谦抑语义；
- 幂等键派生（同输入同 id；非 A-01 decision_id 拒绝）；
- 切片词表结构派生完整性（spine/goal_type 权威全量覆盖）。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

import pytest

from app.core.intervention_lifecycle import (
    ACCUMULATED_TIER_MIN_OBSERVATIONS,
    DEFAULT_OBSERVATION_WINDOW_HOURS,
    EXECUTION_MODE_SLICES,
    FORBIDDEN_CLAIM_TERMS,
    FORBIDDEN_OUTCOME_SIGNAL_PATTERNS,
    GOAL_SLICE_TYPES,
    INTERVENTION_FRICTION_TAGS,
    LIFECYCLE_EVENT_TYPES,
    OUTCOME_ASSOCIATION_SOURCES,
    SPINE_STATE_KEY_TO_FRICTION,
    TRUTH_CLASS_ASSOCIATION_WEIGHTS,
    USER_RESPONSE_EVENT_TYPES,
    AssociationSummary,
    LifecycleEventType,
    ObservationStatus,
    SliceSummary,
    SituationSignature,
    association_claim,
    association_evidence_tier,
    clamp_observation_window_hours,
    derive_lifecycle_event_id,
    execution_mode_slice,
    friction_tag_from_state_key,
    goal_slice,
    is_exposable_intervention,
    is_whitelisted_outcome_source,
    linkage_keys,
    outcome_links_exposure,
    resolve_observation_status,
    truth_class_weight,
    wilson_interval,
)
from app.core.outcome_ledger import OutcomeSource, TruthClass
from app.signals.goal_type_adapter import GOAL_TYPE_PROFILES
from app.signals.policy_engine import _RULE_TABLE

_NOW = datetime(2026, 9, 19, 12, 0, 0)
_T0 = datetime(2026, 9, 19, 10, 0, 0)


def _vocab_sha(vocab) -> str:
    return hashlib.sha256("|".join(sorted(vocab)).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Part A — 词表冻结（变异必红）
# ---------------------------------------------------------------------------


class TestVocabularyFreeze:
    def test_lifecycle_event_types_frozen(self):
        """六段生命周期词表字面冻结（exposure/accept/edit/reject/start/outcome）。"""
        assert LIFECYCLE_EVENT_TYPES == {
            "exposed",
            "accepted",
            "edited",
            "rejected",
            "started",
            "outcome_observed",
        }

    def test_user_response_types_are_middle_funnel(self):
        assert USER_RESPONSE_EVENT_TYPES == {"accepted", "edited", "rejected", "started"}

    def test_outcome_association_sources_frozen_literal(self):
        """灵魂红线的第一层钉死：白名单是封闭字面集（D-02 五源的真子集）。

        变异「把 chat_reply / behavioral / sentiment 加进白名单」在本测试必红
        ——这正是卡面 Work 2 的红线机制化。
        """
        assert OUTCOME_ASSOCIATION_SOURCES == frozenset(
            {
                OutcomeSource.TASK_COMPLETION,
                OutcomeSource.STUDY_RECORD,
                OutcomeSource.FOCUS_SESSION,
                OutcomeSource.QUIZ_FEEDBACK,
            }
        )

    def test_behavioral_source_stays_out_of_whitelist(self):
        """behavioral 是 D-02 合法源但被 v1 有意排除（其写入方以 chat 信号
        分数作判定——正是红线排除的信号族）。把它加进关联白名单必红。"""
        assert OutcomeSource.BEHAVIORAL not in OUTCOME_ASSOCIATION_SOURCES

    def test_whitelist_is_strict_subset_of_d02_sources(self):
        assert OUTCOME_ASSOCIATION_SOURCES < set(OutcomeSource)

    def test_observation_status_enum_frozen(self):
        assert {status.value for status in ObservationStatus} == {
            "observed",
            "censored_not_yet_due",
            "censored_window_closed",
            "censored_user_churned",
            "unknown",
        }


class TestHardRejectionGate:
    """运行期硬拒绝门：禁用字样拦截（白名单被未来污染时的机制化下限）。"""

    @pytest.mark.parametrize(
        "polluted",
        [
            "chat_reply",
            "chat_reply_sentiment",
            "reply_score",
            "message_outcome",
            "sentiment_signal",
            "emotion_score",
            "self_eval_score",
            "model_score_outcome",
        ],
    )
    def test_chat_class_source_values_are_never_whitelisted(self, polluted):
        assert is_whitelisted_outcome_source(polluted) is False

    def test_every_forbidden_pattern_actually_blocks(self):
        """禁用字样表的每一条都在门内生效（防禁词表被掏空成空转）。"""
        for pattern in FORBIDDEN_OUTCOME_SIGNAL_PATTERNS:
            probe = f"{pattern}_outcome"  # 前缀拼接即含禁用字样
            assert is_whitelisted_outcome_source(probe) is False, pattern

    def test_real_whitelisted_sources_pass_gate(self):
        for source in OUTCOME_ASSOCIATION_SOURCES:
            assert is_whitelisted_outcome_source(source) is True

    def test_behavioral_and_non_members_rejected(self):
        assert is_whitelisted_outcome_source(OutcomeSource.BEHAVIORAL) is False
        assert is_whitelisted_outcome_source("nonsense") is False
        assert is_whitelisted_outcome_source(None) is False


# ---------------------------------------------------------------------------
# Part B — 切片词表（结构派生完整性，A-02 纪律）
# ---------------------------------------------------------------------------


class TestSliceVocabularies:
    def test_friction_projection_covers_spine_rule_table_exactly(self):
        """spine _RULE_TABLE key 集 == 投影 key 集（import 期断言的测试面镜像）。"""
        assert set(SPINE_STATE_KEY_TO_FRICTION) == set(_RULE_TABLE)

    def test_friction_families_frozen(self):
        assert INTERVENTION_FRICTION_TAGS == frozenset(
            {
                "execution_friction",
                "knowledge_bottleneck",
                "material_gap",
                "deadline_pressure",
                "overload_crisis",
                "cognitive_overload",
                "affective_pressure",
                "engagement_momentum",
                "recall_gap",
                "community_gap",
                "unattributed",
            }
        )

    def test_every_projection_value_is_declared_family(self):
        assert set(SPINE_STATE_KEY_TO_FRICTION.values()) <= INTERVENTION_FRICTION_TAGS - {"unattributed"}

    def test_goal_slice_matches_goal_type_adapter_authority(self):
        assert GOAL_SLICE_TYPES == frozenset(GOAL_TYPE_PROFILES) | {"unknown"}

    def test_execution_mode_slice_matches_a01_mirror(self):
        assert EXECUTION_MODE_SLICES == frozenset({"human", "agent", "hybrid", "unattributed"})

    def test_friction_tag_from_state_key(self):
        assert friction_tag_from_state_key("knowledge_transfer") == "knowledge_bottleneck"
        assert friction_tag_from_state_key("task_granularity_fit") == "execution_friction"
        assert friction_tag_from_state_key("community_cohort_pattern") == "community_gap"
        assert friction_tag_from_state_key("not_a_state_key") == "unattributed"
        assert friction_tag_from_state_key(None) == "unattributed"
        assert friction_tag_from_state_key("") == "unattributed"

    def test_goal_slice_values(self):
        assert goal_slice("exam") == "exam"
        assert goal_slice("  PROJECT ") == "project"
        assert goal_slice("weird") == "unknown"
        assert goal_slice(None) == "unknown"

    def test_execution_mode_slice_values(self):
        assert execution_mode_slice("human") == "human"
        assert execution_mode_slice("HYBRID") == "hybrid"
        assert execution_mode_slice("robot") == "unattributed"
        assert execution_mode_slice(None) == "unattributed"


# ---------------------------------------------------------------------------
# Part C — exposure 可行性 / 幂等键 / 关联键
# ---------------------------------------------------------------------------


class TestExposureEligibility:
    def test_actionable_live_intervention_is_exposable(self):
        ok, reason = is_exposable_intervention("rescope", "live")
        assert ok and reason == ""

    def test_inert_interventions_have_no_exposure(self):
        for inert in ("no_action", "abstain"):
            ok, _ = is_exposable_intervention(inert, "live")
            assert not ok

    def test_unknown_intervention_type_rejected(self):
        ok, _ = is_exposable_intervention("brainwash", "live")
        assert not ok

    def test_shadow_governance_never_exposed(self):
        """shadow 决策不得作用于用户可见行为 → exposure 事件在契约上不可能合法。"""
        ok, _ = is_exposable_intervention("rescope", "shadow")
        assert not ok


class TestIdempotencyKey:
    def test_id_format_and_determinism(self):
        decision = "aurora_" + "a" * 32
        first = derive_lifecycle_event_id(decision_id=decision, event_type="exposed")
        second = derive_lifecycle_event_id(decision_id=decision, event_type=LifecycleEventType.EXPOSED)
        assert first == second
        assert first.startswith("ilfe_") and len(first) == len("ilfe_") + 32

    def test_id_separates_event_type_and_subkey(self):
        decision = "aurora_" + "b" * 32
        ids = {
            derive_lifecycle_event_id(decision_id=decision, event_type="exposed"),
            derive_lifecycle_event_id(decision_id=decision, event_type="accepted"),
            derive_lifecycle_event_id(decision_id=decision, event_type="outcome_observed", dedupe_subkey="outc_1"),
            derive_lifecycle_event_id(decision_id=decision, event_type="outcome_observed", dedupe_subkey="outc_2"),
        }
        assert len(ids) == 4

    def test_rejects_non_aurora_decision_id(self):
        with pytest.raises(ValueError):
            derive_lifecycle_event_id(decision_id="decision://abc", event_type="exposed")
        with pytest.raises(ValueError):
            derive_lifecycle_event_id(decision_id="aurora_zzzz", event_type="exposed")


class TestLinkageKeys:
    def test_canonical_uuids_kept_dirty_dropped(self):
        task_id = "0f0e0d0c-0b0a-4909-8807-060504030201"
        keys = linkage_keys(task_id=task_id, plan_id="not-a-uuid", node_id=None)
        assert keys == {"task_id": task_id}

    def test_links_on_any_shared_key(self):
        exposure = linkage_keys(task_id="0f0e0d0c-0b0a-4909-8807-060504030201")
        assert outcome_links_exposure(exposure, {"task_id": "0f0e0d0c-0b0a-4909-8807-060504030201"})
        assert not outcome_links_exposure(exposure, {"task_id": "11111111-2222-4333-8444-555555555555"})
        assert not outcome_links_exposure(exposure, {"session_id": "0f0e0d0c-0b0a-4909-8807-060504030201"})
        assert not outcome_links_exposure({}, {"task_id": "0f0e0d0c-0b0a-4909-8807-060504030201"})
        assert not outcome_links_exposure(exposure, None)


# ---------------------------------------------------------------------------
# Part D — censored/unknown 语义（验收 ①）
# ---------------------------------------------------------------------------


class TestObservationStatus:
    def test_invalid_row_is_unknown(self):
        assert resolve_observation_status(
            exposed_at=None, window_hours=72, outcome_times=(), now=_NOW
        ) is ObservationStatus.UNKNOWN
        assert resolve_observation_status(
            exposed_at=_T0, window_hours=72, outcome_times=(), now=_NOW, exposure_valid=False
        ) is ObservationStatus.UNKNOWN

    def test_in_window_outcome_is_observed(self):
        status = resolve_observation_status(
            exposed_at=_T0,
            window_hours=72,
            outcome_times=(_T0 + timedelta(hours=2),),
            now=_NOW,
            user_last_active_at=_NOW,
        )
        assert status is ObservationStatus.OBSERVED

    def test_outcome_before_exposure_is_not_observed(self):
        status = resolve_observation_status(
            exposed_at=_T0,
            window_hours=72,
            outcome_times=(_T0 - timedelta(hours=1),),
            now=_NOW,
        )
        assert status is not ObservationStatus.OBSERVED

    def test_outcome_after_window_is_not_observed(self):
        status = resolve_observation_status(
            exposed_at=_T0,
            window_hours=72,
            outcome_times=(_T0 + timedelta(hours=73),),
            now=_NOW,
        )
        assert status is not ObservationStatus.OBSERVED

    def test_window_open_is_censored_not_yet_due(self):
        """未到期 ≠ 失败：绝不计入负向（生存分析纪律）。"""
        status = resolve_observation_status(
            exposed_at=_NOW - timedelta(hours=1),
            window_hours=72,
            outcome_times=(),
            now=_NOW,
        )
        assert status is ObservationStatus.CENSORED_NOT_YET_DUE

    def test_present_but_silent_is_window_closed(self):
        exposed = _NOW - timedelta(hours=100)  # 72h 窗已关
        status = resolve_observation_status(
            exposed_at=exposed,
            window_hours=72,
            outcome_times=(),
            now=_NOW,
            user_last_active_at=_NOW,  # 用户在窗口关后仍活跃 → 在场而未行动
        )
        assert status is ObservationStatus.CENSORED_WINDOW_CLOSED

    def test_departed_user_is_churned(self):
        exposed = _NOW - timedelta(hours=100)
        status = resolve_observation_status(
            exposed_at=exposed,
            window_hours=72,
            outcome_times=(),
            now=_NOW,
            user_last_active_at=exposed + timedelta(hours=10),  # 窗内已离开
        )
        assert status is ObservationStatus.CENSORED_USER_CHURNED

    def test_missing_activity_defaults_to_churned(self):
        exposed = _NOW - timedelta(hours=100)
        status = resolve_observation_status(
            exposed_at=exposed, window_hours=72, outcome_times=(), now=_NOW, user_last_active_at=None
        )
        assert status is ObservationStatus.CENSORED_USER_CHURNED


# ---------------------------------------------------------------------------
# Part E — 统计谦抑（Wilson / 档位 / claim 禁词 / TruthClass 权重）
# ---------------------------------------------------------------------------


class TestStatisticalHumility:
    def test_wilson_no_data_keeps_upper_bound_open(self):
        """无数据不得宣称 0%——上界必须 > 0。"""
        low, high = wilson_interval(0, 0)
        assert (low, high) == (0.0, 1.0)

    def test_wilson_known_value(self):
        # 8/10 正向：手工计算 Wilson 95% ≈ (0.4902, 0.9433)
        low, high = wilson_interval(8, 10)
        assert low == pytest.approx(0.4902, abs=1e-3)
        assert high == pytest.approx(0.9433, abs=1e-3)

    def test_wilson_bounds_ordered_and_clamped(self):
        for positives in (0, 3, 10):
            low, high = wilson_interval(positives, 10)
            assert 0.0 <= low <= high <= 1.0

    def test_evidence_tiers(self):
        assert association_evidence_tier(0) == "insufficient"
        assert association_evidence_tier(1) == "single_observation"
        assert association_evidence_tier(2) == "repeated"
        assert association_evidence_tier(ACCUMULATED_TIER_MIN_OBSERVATIONS - 1) == "repeated"
        assert association_evidence_tier(ACCUMULATED_TIER_MIN_OBSERVATIONS) == "accumulated"

    def test_claims_never_use_causal_or_success_language(self):
        """claim 文案对全部档位扫描禁词表（因果/成功宣称族必红）。"""
        for tier, n_observed in (
            ("insufficient", 0),
            ("single_observation", 1),
            ("repeated", 3),
            ("accumulated", ACCUMULATED_TIER_MIN_OBSERVATIONS),
        ):
            claim = association_claim(tier, n_observed=n_observed, n_positive=n_observed, n_negative=0)
            lowered = claim.lower()
            for term in FORBIDDEN_CLAIM_TERMS:
                assert term.lower() not in lowered, (tier, term, claim)

    def test_truth_class_weights_frozen(self):
        assert TRUTH_CLASS_ASSOCIATION_WEIGHTS == {
            TruthClass.ACTUAL: 1.0,
            TruthClass.SELF_REPORTED: 0.5,
            TruthClass.ESTIMATED: 0.25,
            TruthClass.DEMO: 0.0,
            TruthClass.UNKNOWN: 0.0,
        }

    def test_truth_class_weight_garbage_is_zero(self):
        assert truth_class_weight("garbage") == 0.0
        assert truth_class_weight(None) == 0.0

    def test_window_clamping(self):
        assert DEFAULT_OBSERVATION_WINDOW_HOURS == 72
        assert clamp_observation_window_hours(None) == 72
        assert clamp_observation_window_hours("junk") == 72
        assert clamp_observation_window_hours(0) == 1
        assert clamp_observation_window_hours(24 * 365) == 24 * 30
        assert clamp_observation_window_hours(48) == 48


# ---------------------------------------------------------------------------
# Part F — 摘要载体（M-06 消费面形状）
# ---------------------------------------------------------------------------


class TestSummaryCarriers:
    def _slice(self) -> SliceSummary:
        return SliceSummary(
            signature=SituationSignature(
                intervention_type="rescope",
                goal_type="exam",
                friction_tag="knowledge_bottleneck",
                execution_mode="hybrid",
            ),
            n_exposed=4,
            n_accepted=3,
            n_started=2,
            n_positive=2,
            n_negative=1,
            n_censored_not_yet_due=1,
            weighted_positive=1.5,
            weighted_total=2.0,
            positive_association_rate=2 / 3,
            rate_interval=(0.2, 0.9),
            weighted_positive_rate=0.75,
            evidence_strength="repeated",
            claim="x",
        )

    def test_causal_claim_always_false(self):
        assert self._slice().causal_claim is False

    def test_to_dict_shape(self):
        payload = self._slice().to_dict()
        assert payload["signature"] == {
            "intervention_type": "rescope",
            "goal_type": "exam",
            "friction_tag": "knowledge_bottleneck",
            "execution_mode": "hybrid",
        }
        assert payload["n_observed"] == 3
        # 删失面永不混进观察面
        assert payload["n_censored_not_yet_due"] == 1
        assert payload["causal_claim"] is False

    def test_association_summary_dict_shape(self):
        summary = AssociationSummary(
            scope=("user", "0f0e0d0c-0b0a-4909-8807-060504030201"),
            generated_at=_NOW,
            since=_T0,
            until=_NOW,
            watermark="wm_x",
            slices=(self._slice(),),
        )
        payload = summary.to_dict()
        assert payload["scope"] == ["user", "0f0e0d0c-0b0a-4909-8807-060504030201"]
        assert payload["n_exposures_total"] == 4
        assert payload["watermark"] == "wm_x"
        assert len(payload["slices"]) == 1
