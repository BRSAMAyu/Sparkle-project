"""V4-I05 · 经验策略影子验证与有界启用 —— 纯契约层测试（可失败；一正一反）。

验收对照（卡面，全部可失败）：
1. **不新增任意 prompt/code 字段，不越六表面权限**：
   - 正例：合法六面 patch → 策略卡构造成功（payload 原样、封闭校验过）；
   - 反例（可失败）：surface=``prompt``/``code``/任意第七面 → ValueError（V1）；
     payload 夹带未知键 / 词表外值 → ValueError（V2/V3）——「prompt/code」
     没有合法 surface 名，结构上进不了策略层。
2. **缺失结果 censored；重复摘要不累积为多源证据**：
   - 正例：censored-only 观察面 → ``censored_insufficient_evidence``（显式不
     结论，既非收益也非失败）；重复引用折叠（3 份重复 = 1 条证据；折叠计数
     审计可见）；评估版本对折叠集内容寻址；
   - 反例（可失败）：朴素按出现次数计证据会让 3 份重复把 single_observation
     顶成 repeated（绕过确认门自动激活）——本测试钉死「naive 计数过 repeated
     线」这一事实 + 折叠后唯一计数不过线（修复面）。
3. **撤回源后相关策略失效；无收益策略不静默启用**：
   - 正例：撤回目标命中策略源（精确 SourcePointer 身份）→ AFFECTED；prefer
     正向 > 负向 → benefit_observed；
   - 反例（可失败）：其他来源（身份不同/跨域同值不同域）→ UNAFFECTED；
     负向反超/平手 → no_benefit；censored-only ≠ no_benefit（缺失结果不能当
     失败计）；human_required_step 情境 → 门出（I07 掌握门不绕过）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.experience_memory import scan_output_for_causal_assertions
from app.core.experience_strategy import (
    BENEFIT_CENSORED_INSUFFICIENT,
    BENEFIT_DIRECTIONS,
    BENEFIT_INSUFFICIENT_EVIDENCE,
    BENEFIT_NO_BENEFIT,
    BENEFIT_OBSERVED,
    BENEFIT_VERDICTS,
    DO_NOT_APPLY_KEYS,
    EVALUATION_VERSION_EMPTY,
    EXPERIENCE_STRATEGY_VERSION,
    GATE_REASONS,
    STRATEGY_ALLOWED_SURFACES,
    STRATEGY_CARD_PAYLOAD_KEYS,
    STRATEGY_MODE_LIVE,
    STRATEGY_MODE_OFF,
    STRATEGY_MODE_SHADOW,
    STRATEGY_MODES,
    ExperienceStrategyCard,
    ObservationFace,
    PreconditionOutcome,
    apply_live_bounds,
    benefit_verdict,
    compare_shadow_arms,
    derive_comparison_id,
    derive_strategy_id,
    evaluation_version,
    fold_evidence_refs,
    observation_face_from_records,
    precondition_verdict,
    project_treatment_arm,
    resolve_strategy_mode,
    source_pointer_of_ref,
    strategy_card_for_patch,
    strategy_withdrawal_plan,
)
from app.core.intervention_lifecycle import association_evidence_tier
from app.core.policy_patch import POLICY_PATCH_SURFACES, PolicyPatch
from app.core.retraction_recompute import (
    RetractionImpact,
    RetractionKind,
    SourcePointer,
)

_T0 = datetime(2026, 9, 20, 10, 0, 0)
_MEMORY_REF = "memory://experience/expmem_0123456789abcdef"
_MEMORY_REF_2 = "memory://experience/expmem_fedcba9876543210"
_DECISION_REF = "decision://aurora_" + "a" * 32


# ---------------------------------------------------------------------------
# 鸭子类型假记录（M-06 记录面：方向计数 + 删失计数 + record_id）
# ---------------------------------------------------------------------------


class _FakeRecord:
    def __init__(
        self,
        record_id: str,
        *,
        positive: int = 0,
        negative: int = 0,
        censored: int = 0,
        unknown: int = 0,
        intervention: str = "practice",
    ):
        self.record_id = record_id
        self.observed_with_positive = positive
        self.observed_with_negative = negative
        self.censored_not_yet_due = censored
        self.censored_window_closed = 0
        self.censored_user_churned = 0
        self.n_unknown_status = unknown
        self.intervention = intervention
        self.execution_mode = "hybrid"

    @property
    def has_positive_association_evidence(self) -> bool:
        return self.observed_with_positive > 0

    @property
    def has_negative_association_evidence(self) -> bool:
        return self.observed_with_negative > 0


def _patch(
    *,
    surface: str = "intervention_preference",
    payload: dict | None = None,
    refs: tuple[str, ...] = (_MEMORY_REF,),
    state: str = "active",
    scope_goal_type: str | None = "exam",
    scope_friction_tag: str | None = None,
    expires_at: datetime | None = None,
) -> PolicyPatch:
    return PolicyPatch(
        patch_id="polpatch_" + "0" * 32,
        user_id="u-1",
        surface=surface,
        payload=payload or {"intervention": "practice", "direction": "prefer"},
        state=state,
        scope_goal_type=scope_goal_type,
        scope_friction_tag=scope_friction_tag,
        evidence_refs=refs,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# 验收①：六表面权限封闭（正例 + 反例）
# ---------------------------------------------------------------------------


class TestSixSurfaceClosure:
    def test_six_surface_whitelist_is_exact_and_shared(self):
        """import 复用 A-05 六面同一对象（非复制）；恰好六面。"""
        assert STRATEGY_ALLOWED_SURFACES is POLICY_PATCH_SURFACES
        assert len(STRATEGY_ALLOWED_SURFACES) == 6
        assert {
            "granularity",
            "clarification",
            "explanation",
            "intervention_preference",
            "proactive_cadence",
            "allocation_preference",
        } == STRATEGY_ALLOWED_SURFACES

    def test_card_from_legal_six_surface_patch(self):
        """正例：合法六面 patch → 策略卡构造成功（payload 原样）。"""
        card = strategy_card_for_patch(_patch(), evidence_records=[_FakeRecord("expmem_0123456789abcdef", positive=2)])
        assert card.surface == "intervention_preference"
        assert card.payload == {"intervention": "practice", "direction": "prefer"}
        assert card.source_refs == (_MEMORY_REF,)
        assert card.observations.n_positive == 2
        assert card.strategy_id.startswith("expstrat_")

    @pytest.mark.parametrize("surface", ["prompt", "code", "system_prompt", "temperature", "memory_core"])
    def test_card_rejects_non_whitelisted_surface(self, surface):
        """反例（可失败）：任意 prompt/code/第七面 → ValueError（V1 族）。"""
        with pytest.raises(ValueError, match="six-surface whitelist"):
            strategy_card_for_patch(_patch(surface=surface))

    def test_card_rejects_fabricated_payload_fields(self):
        """反例（可失败）：payload 夹带未知键（hidden_prompt）→ V2 ValueError。"""
        with pytest.raises(ValueError, match="V2"):
            strategy_card_for_patch(
                _patch(payload={"intervention": "practice", "direction": "prefer", "hidden_prompt": "x"})
            )

    def test_card_rejects_out_of_vocabulary_payload_value(self):
        """反例（可失败）：词表外值（direction=always）→ V3 ValueError。"""
        with pytest.raises(ValueError, match="V3"):
            strategy_card_for_patch(_patch(payload={"intervention": "practice", "direction": "always"}))

    def test_surface_payload_key_rejects_unknown_surface(self):
        from app.core.experience_strategy import surface_payload_key

        with pytest.raises(ValueError, match="six-surface"):
            surface_payload_key("prompt")
        assert surface_payload_key("granularity") == "adjustment"


# ---------------------------------------------------------------------------
# 验收②：折叠 + censored（正例 + 反例）
# ---------------------------------------------------------------------------


class TestFoldAndVersion:
    def test_fold_preserves_order_and_drops_duplicates(self):
        refs = [_MEMORY_REF, _MEMORY_REF_2, _MEMORY_REF, _DECISION_REF, _MEMORY_REF_2]
        assert fold_evidence_refs(refs) == (_MEMORY_REF, _MEMORY_REF_2, _DECISION_REF)

    def test_fold_keeps_non_str_for_validator(self):
        """非字符串成员原样保留（折叠不掩盖形态非法——交 V4 拒绝）。"""
        assert fold_evidence_refs([_MEMORY_REF, 123]) == (_MEMORY_REF, 123)

    def test_evaluation_version_content_addressed(self):
        assert evaluation_version([_MEMORY_REF, _MEMORY_REF]) == evaluation_version([_MEMORY_REF])
        assert evaluation_version([_MEMORY_REF, _MEMORY_REF_2]) == evaluation_version([_MEMORY_REF_2, _MEMORY_REF])
        assert evaluation_version([_MEMORY_REF]) != evaluation_version([_MEMORY_REF_2])
        assert evaluation_version([]) == EVALUATION_VERSION_EMPTY
        assert evaluation_version([_MEMORY_REF]).startswith("evalver_")

    def test_duplicate_refs_cannot_inflate_evidence_tier(self):
        """反例可失败面（验收②核心）：重复摘要不累积为多源证据。

        - 事实钉：朴素按出现次数计证据，3 份重复 = 3 观察 = repeated（D-05
          档位函数既有语义——这正是折叠要堵的绕确认门通道）；
        - 修复面：折叠后唯一引用计数 = 1 = single_observation（需显式 confirm）；
        - 观察面如实记录折叠发生（duplicate_folded_count=2，审计可见）。
        """
        assert association_evidence_tier(3) == "repeated"  # naive 计数会过自动激活线
        assert association_evidence_tier(1) == "single_observation"  # 折叠后不过线
        face = observation_face_from_records(
            [_FakeRecord("expmem_0123456789abcdef", positive=1)],
            source_refs=[_MEMORY_REF, _MEMORY_REF, _MEMORY_REF],
        )
        assert face.n_refs_raw == 3 and face.n_refs_folded == 1
        assert face.duplicate_folded_count == 2
        assert face.evidence_count == 1  # 唯一记录的唯一观察——不因重复引用虚增


class TestCensoredDiscipline:
    def test_censored_only_is_explicit_no_conclusion(self):
        """缺失结果 censored：显式不结论——既非收益也非失败。"""
        face = observation_face_from_records([_FakeRecord("r1", censored=5, unknown=2)])
        assert face.evidence_count == 0
        assert face.censored_total == 5 and face.n_unknown == 2
        assert not face.has_direction_evidence
        assert benefit_verdict(face, required_direction="positive") == BENEFIT_CENSORED_INSUFFICIENT
        assert benefit_verdict(face, required_direction="positive") != BENEFIT_NO_BENEFIT
        assert benefit_verdict(face, required_direction="positive") != BENEFIT_OBSERVED

    def test_no_observation_at_all_is_insufficient_not_censored(self):
        face = ObservationFace()
        assert benefit_verdict(face, required_direction="negative") == BENEFIT_INSUFFICIENT_EVIDENCE

    def test_censored_counts_never_enter_direction(self):
        """删失计数永不产生方向证据（M-06 红线 1 消费侧同律）。"""
        face = observation_face_from_records(
            [_FakeRecord("r1", positive=0, negative=0, censored=99)],
            source_refs=[_MEMORY_REF],
        )
        assert not face.has_direction_evidence
        assert benefit_verdict(face, required_direction="positive") == BENEFIT_CENSORED_INSUFFICIENT

    def test_direction_evidence_ignores_censored_volume(self):
        """有方向证据时，删失体量不改变方向判定输入（正=1 负=0 + 删失 99 → 仍按 1>0）。"""
        face = observation_face_from_records([_FakeRecord("r1", positive=1, censored=99)])
        assert benefit_verdict(face, required_direction="positive") == BENEFIT_OBSERVED


# ---------------------------------------------------------------------------
# 验收③：收益判定（负向证据等权参与；无收益不静默启用）
# ---------------------------------------------------------------------------


class TestBenefitVerdict:
    @pytest.mark.parametrize(
        ("positive", "negative", "expected"),
        [
            (2, 1, BENEFIT_OBSERVED),
            (1, 1, BENEFIT_NO_BENEFIT),  # 平手 = 无收益（负向等权）
            (1, 2, BENEFIT_NO_BENEFIT),  # 负向反超
            (0, 2, BENEFIT_NO_BENEFIT),  # 纯负向
        ],
    )
    def test_prefer_requires_strict_positive_majority(self, positive, negative, expected):
        face = ObservationFace(n_positive=positive, n_negative=negative, n_records=1)
        assert benefit_verdict(face, required_direction="positive") == expected

    @pytest.mark.parametrize(
        ("positive", "negative", "expected"),
        [
            (1, 2, BENEFIT_OBSERVED),
            (1, 1, BENEFIT_NO_BENEFIT),
            (2, 1, BENEFIT_NO_BENEFIT),
        ],
    )
    def test_demote_requires_strict_negative_majority(self, positive, negative, expected):
        face = ObservationFace(n_positive=positive, n_negative=negative, n_records=1)
        assert benefit_verdict(face, required_direction="negative") == expected

    def test_verdict_vocabulary_frozen_and_direction_guarded(self):
        assert {
            BENEFIT_OBSERVED,
            BENEFIT_NO_BENEFIT,
            BENEFIT_INSUFFICIENT_EVIDENCE,
            BENEFIT_CENSORED_INSUFFICIENT,
        } == BENEFIT_VERDICTS
        assert {"positive", "negative"} == BENEFIT_DIRECTIONS
        with pytest.raises(ValueError, match="vocabulary"):
            benefit_verdict(ObservationFace(), required_direction="sideways")


# ---------------------------------------------------------------------------
# 模式解析（shadow 默认 / live 显式 / 未知 fail-closed off）
# ---------------------------------------------------------------------------


class TestModeResolution:
    def test_known_modes_round_trip(self):
        assert resolve_strategy_mode("off") == STRATEGY_MODE_OFF
        assert resolve_strategy_mode("shadow") == STRATEGY_MODE_SHADOW
        assert resolve_strategy_mode(" live ") == STRATEGY_MODE_LIVE
        assert {STRATEGY_MODE_OFF, STRATEGY_MODE_SHADOW, STRATEGY_MODE_LIVE} == STRATEGY_MODES

    @pytest.mark.parametrize("bad", ["", None, "Live!", "enabled", "LIVE;rm", 1])
    def test_unknown_mode_fails_closed_to_off(self, bad):
        """反例（可失败）：任何非字面 live 的值都放大不了权限（fail-closed off）。"""
        assert resolve_strategy_mode(bad) == STRATEGY_MODE_OFF


# ---------------------------------------------------------------------------
# 策略卡：确定性身份 / 冻结序列化 / 因果断言红线
# ---------------------------------------------------------------------------


class TestStrategyCard:
    def test_strategy_id_deterministic_and_sensitive(self):
        kw = {
            "patch_id": "polpatch_" + "0" * 32,
            "source_refs": [_MEMORY_REF],
            "valid_until": None,
            "scope_goal_type": "exam",
            "scope_friction_tag": None,
        }
        assert derive_strategy_id(**kw) == derive_strategy_id(**kw)
        assert derive_strategy_id(**{**kw, "source_refs": [_MEMORY_REF, _MEMORY_REF]}) == derive_strategy_id(**kw)
        assert derive_strategy_id(**{**kw, "scope_goal_type": "project"}) != derive_strategy_id(**kw)
        assert derive_strategy_id(**{**kw, "valid_until": _T0}) != derive_strategy_id(**kw)

    def test_card_to_dict_frozen_keys_and_causal_clean(self):
        card = strategy_card_for_patch(
            _patch(expires_at=_T0),
            evidence_records=[_FakeRecord("r1", positive=1, censored=3)],
        )
        payload = card.to_dict()
        assert tuple(payload.keys()) == STRATEGY_CARD_PAYLOAD_KEYS
        assert payload["schema_version"] == EXPERIENCE_STRATEGY_VERSION
        assert payload["valid_until"] == _T0.isoformat()
        assert scan_output_for_causal_assertions(payload) == []

    def test_card_rebuild_is_deterministic(self):
        """同一 (patch, 证据) 恒同卡（可随时确定性重建——零存储语义）。"""
        records = [_FakeRecord("r1", positive=2, negative=1)]
        assert strategy_card_for_patch(_patch(), evidence_records=records) == strategy_card_for_patch(
            _patch(), evidence_records=records
        )

    def test_do_not_apply_vocabulary_frozen(self):
        card = strategy_card_for_patch(_patch())
        assert set(card.do_not_apply_when) == DO_NOT_APPLY_KEYS
        assert {"human_required_step", "user_revoked", "cross_domain_transfer"} == DO_NOT_APPLY_KEYS


# ---------------------------------------------------------------------------
# 前置条件判定（fail-closed；do_not_apply 优先；I07 门不绕过）
# ---------------------------------------------------------------------------


class TestPreconditions:
    def _card(self, *, expires_at: datetime | None = None) -> ExperienceStrategyCard:
        return strategy_card_for_patch(_patch(expires_at=expires_at))

    def test_applicable_when_context_matches_scope(self):
        outcome = precondition_verdict(self._card(), {"goal_type": "exam"}, now=_T0)
        assert outcome.applicable is True and outcome.reasons == ()

    def test_missing_fact_fails_closed(self):
        """反例（可失败）：情境事实缺失 → 不启用（绝不猜）。"""
        outcome = precondition_verdict(self._card(), {}, now=_T0)
        assert outcome.applicable is False
        assert "missing_fact" in outcome.reasons

    def test_scope_mismatch_is_precondition_unmet(self):
        outcome = precondition_verdict(self._card(), {"goal_type": "project"}, now=_T0)
        assert outcome.applicable is False and "precondition_unmet" in outcome.reasons

    def test_human_required_step_blocks_enablement(self):
        """验收③联动（I07 门）：human_required_step 情境 → 门出，经验启用不绕掌握门。"""
        outcome = precondition_verdict(self._card(), {"goal_type": "exam", "human_required_step": True}, now=_T0)
        assert outcome.applicable is False
        assert "do_not_apply_human_required_step" in outcome.reasons

    def test_user_revoked_fact_blocks(self):
        outcome = precondition_verdict(self._card(), {"goal_type": "exam", "user_revoked": True}, now=_T0)
        assert outcome.applicable is False and "do_not_apply_user_revoked" in outcome.reasons

    def test_window_closed_blocks(self):
        expired = _T0 - timedelta(hours=1)
        outcome = precondition_verdict(self._card(expires_at=expired), {"goal_type": "exam"}, now=_T0)
        assert outcome.applicable is False and "window_closed" in outcome.reasons

    def test_gate_reasons_vocabulary_frozen(self):
        assert {
            "precondition_unmet",
            "missing_fact",
            "do_not_apply_human_required_step",
            "do_not_apply_user_revoked",
            "do_not_apply_cross_domain_transfer",
            "window_closed",
        } == GATE_REASONS

    def test_unknown_do_not_apply_key_rejected(self):
        """卡面词表外 do_not_apply 键 → 构造期即拒（策略卡冻结三键）。"""
        card = strategy_card_for_patch(_patch())
        object.__setattr__(card, "do_not_apply_when", ("mood_based_guess",))
        with pytest.raises(ValueError, match="vocabulary"):
            precondition_verdict(card, {}, now=_T0)


# ---------------------------------------------------------------------------
# 影子对照（两臂投影；treatment 臂经 A-05 单一权威）
# ---------------------------------------------------------------------------


class TestShadowComparison:
    def _prefer_card(self, *, record=None) -> ExperienceStrategyCard:
        records = [record] if record is not None else [_FakeRecord("expmem_0123456789abcdef", positive=2, negative=0)]
        return strategy_card_for_patch(_patch(), evidence_records=records)

    def test_two_arm_comparison_detects_change(self):
        card = self._prefer_card()
        allowed, gated = apply_live_bounds([card], {"goal_type": "exam"}, now=_T0)
        assert allowed and not gated
        treatment, allocation, proactive, explanation = project_treatment_arm(
            ("explain", "practice"),
            allowed,
            [_FakeRecord("expmem_0123456789abcdef", positive=2, negative=0)],
            goal_type="exam",
            now=_T0,
        )
        assert treatment[0] == "practice"  # prefer 生效：practice 升首
        assert allocation is None and explanation is None and dict(proactive) == {}
        comparison = compare_shadow_arms(
            derive_comparison_id(
                stage="unit",
                user_id="u-1",
                control_nominated=("explain", "practice"),
                treatment_nominated=treatment,
                strategy_ids=[card.strategy_id],
                evaluation_versions=[card.evaluation_version],
            ),
            stage="unit",
            control_nominated=("explain", "practice"),
            treatment_nominated=treatment,
            cards=[card],
            gate_outcomes=gated,
            benefit_verdicts=[(card.strategy_id, BENEFIT_OBSERVED)],
        )
        assert comparison.changed is True
        assert comparison.control_nominated == ("explain", "practice")
        assert comparison.treatment_nominated == treatment

    def test_comparison_id_deterministic_and_sensitive(self):
        kw = {
            "stage": "unit",
            "user_id": "u-1",
            "control_nominated": ("a", "b"),
            "treatment_nominated": ("b", "a"),
            "strategy_ids": ["expstrat_1"],
            "evaluation_versions": ["evalver_1"],
        }
        assert derive_comparison_id(**kw) == derive_comparison_id(**kw)
        assert derive_comparison_id(**{**kw, "treatment_nominated": ("a", "b")}) != derive_comparison_id(**kw)

    def test_comparison_to_dict_causal_clean(self):
        card = self._prefer_card()
        comparison = compare_shadow_arms(
            "expshadow_" + "0" * 16,
            stage="unit",
            control_nominated=("explain",),
            treatment_nominated=("explain",),
            cards=[card],
            gate_outcomes=(),
            benefit_verdicts=[(card.strategy_id, BENEFIT_NO_BENEFIT)],
        )
        payload = comparison.to_dict()
        assert payload["changed"] is False
        assert scan_output_for_causal_assertions(payload) == []

    def test_no_direction_evidence_patch_changes_nothing(self):
        """反例（可失败）：无方向证据的 patch 重排零变化（skipped G3 同律）。"""
        card = self._prefer_card(record=_FakeRecord("expmem_0123456789abcdef", positive=0, negative=0))
        treatment, _alloc, _proactive, _explanation = project_treatment_arm(
            ("explain", "practice"),
            [card],
            [],  # 无证据记录 → G3 skip，不凭空偏好
            goal_type="exam",
            now=_T0,
        )
        assert treatment == ("explain", "practice")

    def test_live_bounds_gates_card_out_with_reasons(self):
        card = self._prefer_card()
        allowed, gated = apply_live_bounds([card], {"goal_type": "exam", "human_required_step": True}, now=_T0)
        assert allowed == () and len(gated) == 1
        strategy_id, outcome = gated[0]
        assert strategy_id == card.strategy_id
        assert isinstance(outcome, PreconditionOutcome)
        assert "do_not_apply_human_required_step" in outcome.reasons

    def test_allocation_factor_flows_only_from_allowed_cards(self):
        """因子面只来自 allowed 集（门出 card 的偏好不投影——有界启用边界）。"""
        alloc_card = strategy_card_for_patch(
            _patch(
                surface="allocation_preference",
                payload={"preference": "prefer_agent"},
                refs=(_MEMORY_REF,),
                scope_goal_type=None,
            ),
            evidence_records=[_FakeRecord("r1", positive=1)],
        )
        # 情境无 human_required 门 → alloc card 通过 → 因子投影生效
        allowed, gated = apply_live_bounds([alloc_card], {}, now=_T0)
        assert allowed and not gated
        _treatment, allocation, _proactive, _explanation = project_treatment_arm(("practice",), allowed, [], now=_T0)
        assert allocation == "prefer_agent"
        # 同一 card + human_required_step 情境 → 门出 → 因子零投影（I07 门不绕过）
        allowed2, gated2 = apply_live_bounds([alloc_card], {"human_required_step": True}, now=_T0)
        assert allowed2 == () and len(gated2) == 1
        _treatment2, allocation2, _proactive2, _explanation2 = project_treatment_arm(
            ("practice",), allowed2, [], now=_T0
        )
        assert allocation2 is None


# ---------------------------------------------------------------------------
# 撤回传播（D03 strategy 面消费；精确身份匹配）
# ---------------------------------------------------------------------------


class TestWithdrawalPlan:
    def test_source_pointer_round_trip_and_rejects_garbage(self):
        pointer = source_pointer_of_ref(_MEMORY_REF)
        assert pointer is not None and pointer.identity() == ("expmem_record", "expmem_0123456789abcdef")
        pointer = source_pointer_of_ref(_DECISION_REF)
        assert pointer is not None and pointer.identity() == ("decision_evidence", "aurora_" + "a" * 32)
        assert source_pointer_of_ref("signal://crisis_mode") is None
        assert source_pointer_of_ref("memory://experience/expmem_zzz") is None

    def test_withdrawal_hits_affected_strategy(self):
        card = strategy_card_for_patch(_patch(refs=(_MEMORY_REF,)))
        verdicts = strategy_withdrawal_plan(
            RetractionKind.MATERIAL_DELETED, SourcePointer("expmem_record", "expmem_0123456789abcdef"), [card]
        )
        assert len(verdicts) == 1
        assert verdicts[0].impact == RetractionImpact.AFFECTED
        assert verdicts[0].subject_id == card.strategy_id
        assert verdicts[0].matched_pointers[0].identity() == ("expmem_record", "expmem_0123456789abcdef")

    def test_withdrawal_leaves_other_source_strategy_unaffected(self):
        """反例（可失败）：合法其他来源显式保留（不删不改）。"""
        card = strategy_card_for_patch(_patch(refs=(_MEMORY_REF,)))
        verdicts = strategy_withdrawal_plan(
            RetractionKind.MATERIAL_DELETED, SourcePointer("expmem_record", "expmem_fedcba9876543210"), [card]
        )
        assert verdicts[0].impact == RetractionImpact.UNAFFECTED
        assert verdicts[0].matched_pointers == ()

    def test_cross_domain_same_value_is_not_same_source(self):
        """跨域同值不构成同源（D-02 分域同律）：expmem id 装进 decision 域不命中。"""
        card = strategy_card_for_patch(_patch(refs=(_MEMORY_REF,)))
        verdicts = strategy_withdrawal_plan(
            RetractionKind.MATERIAL_DELETED, SourcePointer("decision_evidence", "expmem_0123456789abcdef"), [card]
        )
        assert verdicts[0].impact == RetractionImpact.UNAFFECTED

    def test_inference_retracted_candidates_include_strategy(self):
        card = strategy_card_for_patch(_patch(refs=(_DECISION_REF,)))
        verdicts = strategy_withdrawal_plan(
            RetractionKind.INFERENCE_RETRACTED, SourcePointer("decision_evidence", "aurora_" + "a" * 32), [card]
        )
        assert verdicts[0].impact == RetractionImpact.AFFECTED
