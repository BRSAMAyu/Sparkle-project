"""A-05 · Bounded Policy Patches 契约冻结测试（六面白名单 + 状态机 + 版本语义）。

冻结面（任何变更需 bump POLICY_PATCH_SCHEMA_VERSION 并过两位 reviewer）：
1. **六面白名单精确集 + sha256 双钉**（本卡灵魂）：放开白名单（加任何
   surface——如 system_prompt/temperature/prompt_override）→ 精确集断言红 +
   sha256 红（变异守卫 ①）；
2. 生命周期状态/动作/迁移表精确集 + sha256 双钉（非法迁移 T6 拒绝）；
3. reason codes / provenance / payload schema 词表冻结；
4. fail-closed 语义：非法 surface/payload 键/payload 值/inert 干预/scope/
   provenance 全部返回非空 violations（fail-closed，无静默修正）；
5. 版本与缓存键：active 集变化 → 版本必变；patch_cache_key 并入版本；
6. evidence ref 形态封闭（memory://experience/expmem_*hex16 与
   decision://aurora_*hex32；A-01 既有 scheme 内零新名）。

哈希种子纪律（A-01 P2-1）：全部集合断言经 sorted 比较。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

import pytest

from app.core.aurora_decision import AURORA_DECISION_REF_SCHEMES
from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_ACCUMULATED,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_SINGLE,
)
from app.core.policy_patch import (
    AUTO_ACTIVATE_TIERS,
    INTENTION_DIRECTIONS,
    POLICY_PATCH_ACTIONS,
    POLICY_PATCH_EMPTY_VERSION,
    POLICY_PATCH_PROVENANCES,
    POLICY_PATCH_REASONS,
    POLICY_PATCH_STATES,
    POLICY_PATCH_SURFACES,
    POLICY_PATCH_TRANSITIONS,
    PolicyPatch,
    admit_decision,
    apply_transition,
    compute_policy_patch_version,
    derive_policy_patch_id,
    is_valid_evidence_ref,
    may_auto_activate,
    patch_cache_key,
    reorder_nominations,
    validate_patch_request,
)


def _sha(values) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _patch(**overrides) -> PolicyPatch:
    base = {
        "patch_id": "polpatch_" + "a" * 32,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "surface": "granularity",
        "payload": {"adjustment": "finer"},
        "state": "active",
        "activated_at": datetime(2026, 9, 19, 12, 0, 0),
    }
    return PolicyPatch(**{**base, **overrides})


# ---------------------------------------------------------------------------
# 1. 六面白名单精确集 + sha256 双钉（灵魂红线；变异守卫 ①）
# ---------------------------------------------------------------------------


class TestSurfaceWhitelistFrozen:
    def test_exactly_six_surfaces(self) -> None:
        assert sorted(POLICY_PATCH_SURFACES) == [
            "allocation_preference",
            "clarification",
            "explanation",
            "granularity",
            "intervention_preference",
            "proactive_cadence",
        ]

    def test_surface_whitelist_sha256_frozen(self) -> None:
        assert _sha(POLICY_PATCH_SURFACES) == _sha(
            {
                "granularity",
                "clarification",
                "explanation",
                "intervention_preference",
                "proactive_cadence",
                "allocation_preference",
            }
        )
        # 稳定指纹（改动集即改指纹——reviewer diff 点）
        assert hashlib.sha256("|".join(sorted(POLICY_PATCH_SURFACES)).encode()).hexdigest() == (
            hashlib.sha256(
                b"allocation_preference|clarification|explanation|granularity|"
                b"intervention_preference|proactive_cadence"
            ).hexdigest()
        )

    @pytest.mark.parametrize(
        "illegal_surface",
        ["system_prompt", "prompt", "temperature", "model_params", "code", "llm_config", "", None, 42, "Granularity"],
    )
    def test_non_whitelisted_surface_rejected_fail_closed(self, illegal_surface) -> None:
        """任何非白名单 surface → V1 拒绝（「改 prompt/代码/模型参数」没有合法面）。"""
        violations = validate_patch_request(
            surface=illegal_surface,
            payload={"adjustment": "finer"},
            evidence_refs=["memory://experience/expmem_0123456789abcdef"],
        )
        assert violations and violations[0].startswith("V1.surface_not_whitelisted")

    def test_legal_surfaces_all_pass_shape_validation(self) -> None:
        payloads = {
            "granularity": {"adjustment": "finer"},
            "clarification": {"mode": "ask_less"},
            "explanation": {"style": "examples_first"},
            "intervention_preference": {"intervention": "practice", "direction": "prefer"},
            "proactive_cadence": {"cadence": "minimal"},
            "allocation_preference": {"preference": "prefer_mixed"},
        }
        for surface, payload in payloads.items():
            assert (
                validate_patch_request(
                    surface=surface,
                    payload=payload,
                    evidence_refs=["memory://experience/expmem_0123456789abcdef"],
                )
                == ()
            ), (surface, payload)


# ---------------------------------------------------------------------------
# 2. payload 封闭（未知键 V2 / 词表外值 V3 / inert V6）
# ---------------------------------------------------------------------------


class TestPayloadClosedness:
    def test_unknown_payload_key_rejected(self) -> None:
        violations = validate_patch_request(
            surface="granularity",
            payload={"adjustment": "finer", "system_prompt_override": "be brief"},
            evidence_refs=["memory://experience/expmem_0123456789abcdef"],
        )
        assert any(v.startswith("V2.payload_field_unknown") for v in violations)

    def test_out_of_vocabulary_value_rejected(self) -> None:
        for surface, payload in [
            ("granularity", {"adjustment": "chunkier"}),
            ("clarification", {"mode": "never_ask"}),
            ("explanation", {"style": "poem"}),
            ("proactive_cadence", {"cadence": "off"}),
            ("allocation_preference", {"preference": "prefer_robot"}),
            ("intervention_preference", {"intervention": "teleport", "direction": "prefer"}),
        ]:
            violations = validate_patch_request(
                surface=surface, payload=payload, evidence_refs=["memory://experience/expmem_0123456789abcdef"]
            )
            assert any(v.startswith("V3.payload_value_out_of_vocabulary") for v in violations), surface

    def test_inert_intervention_not_patchable(self) -> None:
        for inert in ("no_action", "abstain"):
            violations = validate_patch_request(
                surface="intervention_preference",
                payload={"intervention": inert, "direction": "prefer"},
                evidence_refs=["memory://experience/expmem_0123456789abcdef"],
            )
            assert any(v.startswith("V6.inert_intervention_not_patchable") for v in violations)

    def test_intervention_preference_requires_direction(self) -> None:
        violations = validate_patch_request(
            surface="intervention_preference",
            payload={"intervention": "practice"},
            evidence_refs=["memory://experience/expmem_0123456789abcdef"],
        )
        assert any("missing required key 'direction'" in v for v in violations)
        assert {"prefer", "demote"} == INTENTION_DIRECTIONS

    def test_malformed_evidence_ref_rejected(self) -> None:
        for bad in ["", "memory://experience/xyz", "decision://not_a_decision", "http://evil", "prompt://override", 42]:
            violations = validate_patch_request(
                surface="granularity", payload={"adjustment": "finer"}, evidence_refs=[bad]
            )
            assert any(v.startswith("V4.evidence_ref_malformed") for v in violations), bad

    def test_scope_and_provenance_vocabularies(self) -> None:
        violations = validate_patch_request(
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["memory://experience/expmem_0123456789abcdef"],
            scope_goal_type="not_a_goal",
            scope_friction_tag="not_a_friction",
            provenance="attacker",
        )
        assert any(v.startswith("V5.scope_value_out_of_vocabulary") for v in violations)
        assert any(v.startswith("V7.provenance_not_whitelisted") for v in violations)
        assert {"l4_async_analysis", "decision_loop", "user_action"} == POLICY_PATCH_PROVENANCES


# ---------------------------------------------------------------------------
# 3. 生命周期状态机冻结（迁移表 + T6 非法迁移拒绝）
# ---------------------------------------------------------------------------


class TestLifecycleStateMachine:
    def test_states_frozen(self) -> None:
        assert sorted(POLICY_PATCH_STATES) == ["active", "candidate", "evidenced", "expired", "rejected", "revoked"]

    def test_actions_frozen(self) -> None:
        assert sorted(POLICY_PATCH_ACTIONS) == ["admit_evidence", "auto_activate", "confirm", "expire", "revoke"]

    def test_reasons_frozen_sha(self) -> None:
        expected = {
            "V1.surface_not_whitelisted",
            "V2.payload_field_unknown",
            "V3.payload_value_out_of_vocabulary",
            "V4.evidence_ref_malformed",
            "V5.scope_value_out_of_vocabulary",
            "V6.inert_intervention_not_patchable",
            "V7.provenance_not_whitelisted",
            "G1.no_resolved_evidence",
            "G2.evidence_tier_insufficient",
            "G3.evidence_direction_mismatch",
            "T1.evidence_admitted",
            "T2.auto_activated",
            "T3.user_confirmed_activated",
            "T4.revoked_by_user_correction",
            "T5.expired",
            "T6.illegal_transition",
        }
        assert expected == POLICY_PATCH_REASONS
        assert _sha(POLICY_PATCH_REASONS) == _sha(expected)

    def test_happy_path_transitions(self) -> None:
        now = datetime(2026, 9, 19, 10, 0, 0)
        outcome = apply_transition(state="candidate", action="admit_evidence", now=now, actor="evidence_gate")
        assert outcome.transitioned and outcome.new_state == "evidenced"
        outcome = apply_transition(state="evidenced", action="auto_activate", now=now, actor="evidence_gate")
        assert outcome.transitioned and outcome.new_state == "active"
        outcome = apply_transition(state="evidenced", action="confirm", now=now, actor="user")
        assert outcome.transitioned and outcome.new_state == "active"
        outcome = apply_transition(state="active", action="revoke", now=now, actor="user")
        assert outcome.transitioned and outcome.new_state == "revoked"
        outcome = apply_transition(state="active", action="expire", now=now, actor="system")
        assert outcome.transitioned and outcome.new_state == "expired"

    def test_illegal_transitions_rejected(self) -> None:
        now = datetime(2026, 9, 19, 10, 0, 0)
        # 终态不可迁出（复活需新 patch——M-01 supersede 哲学）
        for terminal in ("revoked", "expired", "rejected"):
            for action in POLICY_PATCH_ACTIONS:
                outcome = apply_transition(state=terminal, action=action, now=now, actor="user")
                assert not outcome.transitioned and outcome.reasons == ("T6.illegal_transition",)
        # candidate 不能直接激活（必须先过证据门）；active 不能再确认
        assert not apply_transition(state="candidate", action="confirm", now=now, actor="user").transitioned
        assert not apply_transition(state="active", action="confirm", now=now, actor="user").transitioned
        assert not apply_transition(state="candidate", action="expire", now=now, actor="system").transitioned
        # 未知状态/动作
        assert not apply_transition(state="zombie", action="revoke", now=now, actor="user").transitioned
        assert not apply_transition(state="active", action="resurrect", now=now, actor="user").transitioned
        # 迁移表与词表一致
        assert set(POLICY_PATCH_TRANSITIONS) <= POLICY_PATCH_ACTIONS
        for _action, table in POLICY_PATCH_TRANSITIONS.items():
            assert set(table) <= POLICY_PATCH_STATES
            assert set(table.values()) <= POLICY_PATCH_STATES

    def test_history_entry_carries_audit_fields(self) -> None:
        now = datetime(2026, 9, 19, 10, 0, 0)
        outcome = apply_transition(state="active", action="revoke", now=now, actor="user")
        assert outcome.history_entry is not None
        entry = dict(outcome.history_entry)
        assert entry["from"] == "active" and entry["to"] == "revoked"
        assert entry["reason"] == "T4.revoked_by_user_correction"
        assert entry["actor"] == "user" and entry["at"] == now.isoformat()


# ---------------------------------------------------------------------------
# 4. 证据门纯函数（档位/方向/计数）
# ---------------------------------------------------------------------------


class TestEvidenceGatePure:
    def test_gate_thresholds(self) -> None:
        # 无解析证据 → G1
        ok, reasons = admit_decision(resolved_ref_count=0, direction_satisfied=True, tier=EVIDENCE_TIER_REPEATED)
        assert not ok and reasons == ("G1.no_resolved_evidence",)
        # 方向不满足 → G3
        ok, reasons = admit_decision(resolved_ref_count=2, direction_satisfied=False, tier=EVIDENCE_TIER_REPEATED)
        assert not ok and reasons == ("G3.evidence_direction_mismatch",)
        # 档位不足 → G2
        from app.core.intervention_lifecycle import EVIDENCE_TIER_INSUFFICIENT

        ok, reasons = admit_decision(resolved_ref_count=1, direction_satisfied=True, tier=EVIDENCE_TIER_INSUFFICIENT)
        assert not ok and reasons == ("G2.evidence_tier_insufficient",)
        # 通过
        ok, reasons = admit_decision(resolved_ref_count=1, direction_satisfied=True, tier=EVIDENCE_TIER_SINGLE)
        assert ok and reasons == ()

    def test_auto_activate_tiers(self) -> None:
        assert {EVIDENCE_TIER_REPEATED, EVIDENCE_TIER_ACCUMULATED} == AUTO_ACTIVATE_TIERS
        assert may_auto_activate(EVIDENCE_TIER_SINGLE) is False  # single → confirm(若需)
        assert may_auto_activate(EVIDENCE_TIER_REPEATED) is True
        assert may_auto_activate(EVIDENCE_TIER_ACCUMULATED) is True

    def test_evidence_ref_schemes_stay_within_a01(self) -> None:
        """evidence ref scheme 落在 A-01 既有 scheme 内（零新名；可直接进契约）。"""
        for ref in ("memory://experience/expmem_0123456789abcdef", "decision://aurora_" + "f" * 32):
            assert is_valid_evidence_ref(ref)
            assert ref.split("://", 1)[0] in AURORA_DECISION_REF_SCHEMES


# ---------------------------------------------------------------------------
# 5. policy version 与缓存键（Work 3）
# ---------------------------------------------------------------------------


class TestVersionAndCacheKey:
    def test_empty_active_set_has_stable_version(self) -> None:
        assert compute_policy_patch_version([]) == POLICY_PATCH_EMPTY_VERSION
        # 非 active 状态不进版本
        assert compute_policy_patch_version([_patch(state="revoked")]) == POLICY_PATCH_EMPTY_VERSION
        assert compute_policy_patch_version([_patch(state="candidate")]) == POLICY_PATCH_EMPTY_VERSION

    def test_active_set_change_bumps_version(self) -> None:
        p1 = _patch()
        v1 = compute_policy_patch_version([p1])
        v2 = compute_policy_patch_version(
            [p1, _patch(surface="clarification", payload={"mode": "ask_less"}, patch_id="polpatch_" + "b" * 32)]
        )
        assert v1 != v2
        # 撤销（离开 active）→ 版本回到空集常量
        assert compute_policy_patch_version([_patch(state="revoked")]) != v1
        # 同集确定性
        assert compute_policy_patch_version([p1]) == v1

    def test_patch_cache_key_includes_version(self) -> None:
        k1 = patch_cache_key("a02:nominees:u1", "polpatch_abc")
        k2 = patch_cache_key("a02:nominees:u1", "polpatch_def")
        assert k1 != k2  # 版本 bump → 键变 → 缓存不命中
        assert k1 == "a02:nominees:u1|polpatch=polpatch_abc"

    def test_patch_id_content_addressed(self) -> None:
        a = derive_policy_patch_id(
            user_id="u1",
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["decision://aurora_" + "1" * 32],
        )
        b = derive_policy_patch_id(
            user_id="u1",
            surface="granularity",
            payload={"adjustment": "finer"},
            evidence_refs=["decision://aurora_" + "1" * 32],
        )
        c = derive_policy_patch_id(
            user_id="u1",
            surface="granularity",
            payload={"adjustment": "coarser"},
            evidence_refs=["decision://aurora_" + "1" * 32],
        )
        assert a == b and a != c and a.startswith("polpatch_") and len(a) == len("polpatch_") + 32


# ---------------------------------------------------------------------------
# 6. 生效判定与 scope 匹配（「同 scope」语义）
# ---------------------------------------------------------------------------


class TestEffectiveAndScope:
    def test_is_effective_read_time_gate(self) -> None:
        now = datetime(2026, 9, 19, 12, 0, 0)
        active = _patch()
        assert active.is_effective(now)
        expiring = _patch(expires_at=now + timedelta(hours=1))
        assert expiring.is_effective(now)
        assert not expiring.is_effective(now + timedelta(hours=2))  # 读时门
        assert not _patch(state="revoked").is_effective(now)
        assert not _patch(state="evidenced").is_effective(now)

    def test_scope_matches_constraints(self) -> None:
        patch = _patch(scope_goal_type="exam")
        assert patch.scope_matches(goal_type="exam", friction_tag=None)
        assert not patch.scope_matches(goal_type="coursework", friction_tag=None)
        assert not patch.scope_matches(goal_type=None, friction_tag=None)  # 已约束维度不放行缺失
        unconstrained = _patch()
        assert unconstrained.scope_matches(goal_type="exam", friction_tag="cognitive_overload")


# ---------------------------------------------------------------------------
# 7. 提名重排（纯函数：确定性 + 证据门槛 + 稳定序）
# ---------------------------------------------------------------------------


class _FakeRecord:
    """M-06 ExperienceMemoryRecord 的鸭子面（intervention/方向谓词/计数/id）。"""

    def __init__(self, *, record_id: str, intervention: str, positive: int, negative: int) -> None:
        self.record_id = record_id
        self.intervention = intervention
        self.observed_with_positive = positive
        self.observed_with_negative = negative

    @property
    def has_positive_association_evidence(self) -> bool:
        return self.observed_with_positive > 0

    @property
    def has_negative_association_evidence(self) -> bool:
        return self.observed_with_negative > 0

    @property
    def evidence_count(self) -> int:
        return self.observed_with_positive + self.observed_with_negative


class TestReorderNominations:
    def _prefer_patch(self, intervention: str, patch_letter: str) -> PolicyPatch:
        return _patch(
            patch_id="polpatch_" + patch_letter * 32,
            surface="intervention_preference",
            payload={"intervention": intervention, "direction": "prefer"},
        )

    def test_multiple_prefers_order_by_evidence_strength(self) -> None:
        """两条 prefer：证据多者占首位（insert(0) 序反转陷阱的钉死）。"""
        records = [
            _FakeRecord(record_id="expmem_" + "1" * 16, intervention="practice", positive=5, negative=0),
            _FakeRecord(record_id="expmem_" + "2" * 16, intervention="clarify", positive=1, negative=0),
        ]
        patches = [self._prefer_patch("practice", "a"), self._prefer_patch("clarify", "b")]
        outcome = reorder_nominations(
            ("explain", "clarify", "practice"), patches, now=datetime(2026, 9, 19), evidence_records=records
        )
        assert outcome.nominated[0] == "practice"  # 5 条证据 > 1 条
        assert outcome.nominated[1] == "clarify"
        assert outcome.nominated[2:] == ("explain",)

    def test_prefer_without_evidence_is_skipped_not_applied(self) -> None:
        """无方向证据的 patch 不改排序（skipped 归因；绝不凭空偏好）。"""
        records = [_FakeRecord(record_id="expmem_" + "3" * 16, intervention="practice", positive=0, negative=2)]
        patches = [self._prefer_patch("practice", "a")]  # prefer 但只有负向证据
        outcome = reorder_nominations(
            ("explain", "practice"), patches, now=datetime(2026, 9, 19), evidence_records=records
        )
        assert outcome.nominated == ("explain", "practice")
        assert outcome.skipped and outcome.skipped[0][1] == "G3.evidence_direction_mismatch"

    def test_demote_moves_to_tail_with_negative_evidence(self) -> None:
        records = [_FakeRecord(record_id="expmem_" + "4" * 16, intervention="clarify", positive=0, negative=3)]
        patch = _patch(
            surface="clarification",
            payload={"mode": "ask_less"},  # clarification 面 → demote clarify
        )
        outcome = reorder_nominations(
            ("clarify", "explain", "retrieve"), [patch], now=datetime(2026, 9, 19), evidence_records=records
        )
        assert outcome.nominated == ("explain", "retrieve", "clarify")
        assert outcome.moves[0].evidence_refs == ("memory://experience/expmem_" + "4" * 16,)

    def test_nontarget_nominations_keep_relative_order(self) -> None:
        records = [_FakeRecord(record_id="expmem_" + "5" * 16, intervention="split", positive=2, negative=0)]
        patch = _patch(surface="granularity", payload={"adjustment": "finer"})  # → prefer split
        outcome = reorder_nominations(
            ("explain", "review", "split", "retrieve"), [patch], now=datetime(2026, 9, 19), evidence_records=records
        )
        assert outcome.nominated == ("split", "explain", "review", "retrieve")  # 稳定重排

    def test_patch_never_injects_new_nominee(self) -> None:
        """提名权在 spine/L2/决策环——patch 只调序，不新增动作。"""
        records = [_FakeRecord(record_id="expmem_" + "6" * 16, intervention="practice", positive=2, negative=0)]
        patches = [self._prefer_patch("practice", "a")]
        outcome = reorder_nominations(("explain",), patches, now=datetime(2026, 9, 19), evidence_records=records)
        assert outcome.nominated == ("explain",)  # practice 不在提名序 → 不注入
        assert outcome.skipped and outcome.skipped[0][1] == "G1.no_resolved_evidence"
