"""A-01 · AuroraDecisionContract 契约冻结测试（parity guard）。

冻结内容（任何变更都需要契约版本号 bump + 两位 reviewer）：
1. 三个契约 dataclass 的字段集（名称 + 顺序 + sha256 指纹）；
2. 全部封闭词表（intervention catalog / ref schemes / uncertainty kinds /
   cognition tiers / no-action reasons / governance modes / policy patch scopes）
   的精确集与 sha256 钉法；
3. 交叉字段规则（no_action ⇔ inert、clarify 必带 question、回执 ⊆ 证据、
   task:///decision:// 边界 ref scheme）；
4. to_dict/from_dict 往返 + JSON 安全 + 确定性 decision_id；
5. 与 C-01 / X-01 / X-02 的结构对齐（ref scheme 包含关系、ExecutionMode 复用）。

变异必红：改词表（增/删/改名）、改字段形状（增/删/换序）都会使本文件失败
（验证记录见 v3-output/A-01/REPORT.md 的变异实验节）。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES
from app.core.aurora_decision import (
    AURORA_COGNITION_TIERS,
    AURORA_DECISION_FIELDS,
    AURORA_DECISION_REF_SCHEMES,
    AURORA_DECISION_SCHEMA_VERSION,
    AURORA_GOVERNANCE_MODES,
    AURORA_INTERVENTION_TYPES,
    AURORA_NO_ACTION_REASONS,
    AURORA_POLICY_PATCH_SCOPES,
    AURORA_UNCERTAINTY_KINDS,
    DECISION_UNCERTAINTY_FIELDS,
    POLICY_PATCH_CANDIDATE_FIELDS,
    AuroraDecisionContract,
    DecisionUncertainty,
    PolicyPatchCandidate,
    aurora_decision_from_dict,
)
from app.models.execution_intent import ExecutionMode


def _field_names(cls) -> tuple[str, ...]:
    return tuple(field.name for field in dataclasses.fields(cls))


def _vocab_sha(vocab: frozenset[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(vocab), ensure_ascii=False).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Part A — 契约冻结（无 DB）
# ---------------------------------------------------------------------------


def test_contract_schema_version_frozen():
    assert AURORA_DECISION_SCHEMA_VERSION == "aurora_decision.v1"


def test_contract_field_sets_frozen():
    """字段集快照：名称、顺序、导出常量三者齐验，防任何静默漂移。"""
    assert _field_names(AuroraDecisionContract) == AURORA_DECISION_FIELDS
    assert _field_names(DecisionUncertainty) == DECISION_UNCERTAINTY_FIELDS
    assert _field_names(PolicyPatchCandidate) == POLICY_PATCH_CANDIDATE_FIELDS

    # 冻结指纹：三个 dataclass 的 (name, type) 序列 sha256（改字段形状必红）
    fingerprint = hashlib.sha256(
        json.dumps(
            [
                [cls.__name__, [[f.name, str(f.type)] for f in dataclasses.fields(cls)]]
                for cls in (AuroraDecisionContract, DecisionUncertainty, PolicyPatchCandidate)
            ],
            sort_keys=False,
        ).encode("utf-8")
    ).hexdigest()
    assert fingerprint == _DECLARED_FINGERPRINT


_DECLARED_DECISION_FIELDS = [
    ("user_id", "UUID"),
    ("intervention_type", "str"),
    ("rationale_summary", "str"),
    ("cognition_tier", "str"),
    ("execution_mode", "ExecutionMode | None"),
    ("schema_version", "str"),
    ("governance_mode", "str"),
    ("decision_id", "str | None"),
    ("trigger_point", "str | None"),
    ("input_context_hash", "str | None"),
    ("evidence_refs", "tuple[str, ...]"),
    ("uncertainties", "tuple[DecisionUncertainty, ...]"),
    ("clarifying_question", "str | None"),
    ("action_proposal_ref", "str | None"),
    ("allocation_ref", "str | None"),
    ("memory_use_receipts", "tuple[str, ...]"),
    ("policy_patch_candidate", "PolicyPatchCandidate | None"),
    ("no_action_reason", "str | None"),
    ("annotations", "Mapping[str, Any]"),
    ("created_at", "datetime | None"),
]
_DECLARED_UNCERTAINTY_FIELDS = [
    ("kind", "str"),
    ("note", "str"),
]
_DECLARED_PATCH_FIELDS = [
    ("scope", "str"),
    ("evidence_refs", "tuple[str, ...]"),
    ("confidence", "float"),
    ("expires_at", "datetime | None"),
    ("intervention_preference", "str | None"),
    ("user_confirmed", "bool"),
]
_DECLARED_FINGERPRINT = hashlib.sha256(
    json.dumps(
        [
            ["AuroraDecisionContract", [list(pair) for pair in _DECLARED_DECISION_FIELDS]],
            ["DecisionUncertainty", [list(pair) for pair in _DECLARED_UNCERTAINTY_FIELDS]],
            ["PolicyPatchCandidate", [list(pair) for pair in _DECLARED_PATCH_FIELDS]],
        ],
        sort_keys=False,
    ).encode("utf-8")
).hexdigest()


class TestVocabularyClosure:
    """封闭词表：精确集 + sha256 双钉（改词表必红）。"""

    def test_intervention_catalog_is_aurora_v3_section2(self):
        assert AURORA_INTERVENTION_TYPES == frozenset(
            {
                "clarify", "explain", "retrieve", "rescope", "split", "schedule",
                "practice", "review", "delegate", "execute", "co_execute",
                "reflect", "connect_peer", "pause", "remind", "abstain", "no_action",
            }
        )
        assert len(AURORA_INTERVENTION_TYPES) == 17

    def test_ref_schemes_align_with_x01_plus_signal_extension(self):
        """ref 语义对齐：X-01 的 11 scheme 原样包含（结构派生，非复制），
        Aurora 域只新增 signal://（spine StateRegister / L0 ActionableSignal）。"""
        assert ACTION_SOURCE_REF_SCHEMES <= AURORA_DECISION_REF_SCHEMES
        assert AURORA_DECISION_REF_SCHEMES - ACTION_SOURCE_REF_SCHEMES == {"signal"}

    def test_uncertainty_kinds_frozen(self):
        assert AURORA_UNCERTAINTY_KINDS == frozenset(
            {
                "insufficient_context",
                "stale_signal",
                "conflicting_evidence",
                "unverified_inference",
                "user_model_conflict",
                "policy_gap",
            }
        )

    def test_cognition_tiers_map_runtime_layers(self):
        assert AURORA_COGNITION_TIERS == frozenset(
            {"l0_rules", "l1_light", "l2_intervention", "l3_full_core", "l4_async", "rule_fallback"}
        )

    def test_no_action_reasons_frozen(self):
        assert AURORA_NO_ACTION_REASONS == frozenset(
            {
                "materiality_below_threshold",
                "quiet_hours",
                "cooldown_active",
                "focus_protected",
                "budget_exhausted",
                "no_matching_pattern",
                "no_active_states",
            }
        )

    def test_governance_modes_tri_state_off_is_absence(self):
        """三态：live/shadow 在词表内；off = 不构造实例（不是词表成员）。"""
        assert AURORA_GOVERNANCE_MODES == frozenset({"live", "shadow"})

    def test_policy_patch_scopes_whitelist(self):
        assert AURORA_POLICY_PATCH_SCOPES == frozenset(
            {
                "ux_intent",
                "aurora_presence",
                "capability_gate",
                "intervention_preference",
                "proactive_policy",
                "materiality_threshold",
            }
        )

    def test_vocab_sha256_pins(self):
        """sha256 钉法（对齐 M-01/X-02 冻结纪律）：改词表任意成员即红。"""
        assert _vocab_sha(AURORA_INTERVENTION_TYPES) == "8bcfb6f28c41cbf846cfd40a200e6d29742c2109f80e784e2c68a7d7a8876b9b"
        assert _vocab_sha(AURORA_DECISION_REF_SCHEMES) == "8e82cc6d56f3cce07f388274923bae2dee19cc2bdf0ac06eafc9f6e17e8b9383"
        assert _vocab_sha(AURORA_UNCERTAINTY_KINDS) == "58b38c937bd1dd0322c83fcdab200c53089b5baee4faf3cc134120d1eadc88a3"
        assert _vocab_sha(AURORA_COGNITION_TIERS) == "3d79ae5206e4769ffd5c9944551bf5ea97bf01cd2563c9e681aaf13a52fea362"
        assert _vocab_sha(AURORA_NO_ACTION_REASONS) == "9777cb6ea67ba4b7bf5cca3d9175fc199bd8a3643d5d19d933b443ca89b7d840"
        assert _vocab_sha(AURORA_GOVERNANCE_MODES) == "5ca20fb4471f83333e3bd6326b746b224c8ae9cdc77575d20559b7238de2312e"
        assert _vocab_sha(AURORA_POLICY_PATCH_SCOPES) == "f78699e9f61bba7cc10119129ab34c9340c687c71619442e67eb012cc96fb5f2"


def test_execution_mode_reuses_frozen_execution_intent_enum():
    """Aurora 不新造第二套 HUMAN/AGENT/HYBRID 枚举（X-01/X-02 同款纪律）。"""
    assert {member.value for member in ExecutionMode} == {"human", "agent", "hybrid"}


# ---------------------------------------------------------------------------
# Part B — 校验面（交叉字段规则）
# ---------------------------------------------------------------------------


def _actionable_contract() -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=uuid4(),
        intervention_type="rescope",
        rationale_summary="knowledge bottleneck detected — trigger worked example repair",
        cognition_tier="l2_intervention",
        execution_mode=ExecutionMode.HYBRID,
        trigger_point="l2_escalation",
        input_context_hash="0123abcd",
        evidence_refs=(
            "signal://knowledge_bottleneck",
            "signal://transfer_failure",
            "memory://episodic/00000000-0000-0000-0000-000000000001",
        ),
        memory_use_receipts=("memory://episodic/00000000-0000-0000-0000-000000000001",),
        uncertainties=(DecisionUncertainty(kind="unverified_inference", note="bottleneck claim not probed"),),
    )


class TestValidationRules:
    def test_legal_actionable_decision_validates(self):
        assert _actionable_contract().validate() == ()

    def test_legal_no_action_decision_validates(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="no_action",
            rationale_summary="no escalation pattern matched",
            cognition_tier="l2_intervention",
            no_action_reason="no_matching_pattern",
        )
        assert contract.validate() == ()

    def test_inert_intervention_requires_reason_and_forbids_mode(self):
        missing_reason = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="abstain",
            rationale_summary="x",
            cognition_tier="l1_light",
        )
        violations = missing_reason.validate()
        assert any("requires no_action_reason" in v for v in violations)

        with_mode = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="no_action",
            rationale_summary="x",
            cognition_tier="l1_light",
            no_action_reason="quiet_hours",
            execution_mode=ExecutionMode.HUMAN,
        )
        violations = with_mode.validate()
        assert any("must not carry execution_mode" in v for v in violations)

    def test_actionable_intervention_requires_mode_and_forbids_reason(self):
        no_mode = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="rescope",
            rationale_summary="x",
            cognition_tier="l2_intervention",
        )
        assert any("must carry execution_mode" in v for v in no_mode.validate())

        with_reason = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="rescope",
            rationale_summary="x",
            cognition_tier="l2_intervention",
            execution_mode=ExecutionMode.HYBRID,
            no_action_reason="quiet_hours",
        )
        assert any("only valid for no_action/abstain" in v for v in with_reason.validate())

    def test_clarify_requires_question(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="clarify",
            rationale_summary="x",
            cognition_tier="l1_light",
            execution_mode=ExecutionMode.HUMAN,
        )
        assert any("clarifying_question" in v for v in contract.validate())

    def test_memory_receipts_must_subset_evidence(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="explain",
            rationale_summary="x",
            cognition_tier="l1_light",
            execution_mode=ExecutionMode.HYBRID,
            evidence_refs=("signal://deadline_pressure",),
            memory_use_receipts=("memory://episodic/00000000-0000-0000-0000-000000000002",),
        )
        assert any("subset of evidence_refs" in v for v in contract.validate())

    def test_boundary_ref_schemes(self):
        base = dict(
            user_id=uuid4(),
            intervention_type="execute",
            rationale_summary="x",
            cognition_tier="l1_light",
            execution_mode=ExecutionMode.AGENT,
        )
        bad_action = AuroraDecisionContract(action_proposal_ref="goal://123", **base)
        assert any("task:// scheme" in v for v in bad_action.validate())
        bad_alloc = AuroraDecisionContract(allocation_ref="task://123", **base)
        assert any("decision:// scheme" in v for v in bad_alloc.validate())

    def test_unknown_ref_scheme_rejected(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="explain",
            rationale_summary="x",
            cognition_tier="l1_light",
            execution_mode=ExecutionMode.HYBRID,
            evidence_refs=("aurora_route",),  # 现存 runtime 的裸 token 形态，契约必须拒绝
        )
        assert any("unknown or missing scheme" in v for v in contract.validate())

    def test_policy_patch_candidate_surface_whitelist(self):
        off_whitelist = PolicyPatchCandidate(
            scope="model_weights",  # 非白名单 surface：拒绝
            evidence_refs=("signal://a",),
            confidence=0.6,
            expires_at=datetime(2026, 10, 1),
        )
        assert any("not in whitelist surface" in v for v in off_whitelist.validate())

        no_expiry = PolicyPatchCandidate(
            scope="intervention_preference",
            intervention_preference="practice",
            evidence_refs=("memory://episodic/00000000-0000-0000-0000-000000000001",),
            confidence=0.7,
            expires_at=None,
        )
        assert any("expires_at" in v for v in no_expiry.validate())

        legal = PolicyPatchCandidate(
            scope="intervention_preference",
            intervention_preference="practice",
            evidence_refs=("memory://episodic/00000000-0000-0000-0000-000000000001",),
            confidence=0.7,
            expires_at=datetime(2026, 10, 1) + timedelta(days=7),
            user_confirmed=True,
        )
        assert legal.validate() == ()


class TestDeterministicIdentity:
    def test_decision_id_deterministic_and_prefix(self):
        first = _actionable_contract()
        second = _actionable_contract()
        # 不同 user_id → 不同 id；同对象 → 稳定 id
        assert first.decision_id_or_compute() == first.decision_id_or_compute()
        assert first.decision_id_or_compute().startswith("aurora_")
        assert len(first.decision_id_or_compute()) == len("aurora_") + 32
        assert second.decision_id_or_compute() != first.decision_id_or_compute()

    def test_decision_id_ignores_created_at_and_annotations(self):
        import dataclasses as dc

        base = _actionable_contract()
        decorated = dc.replace(
            base,
            created_at=datetime(2026, 9, 19, 12, 0, 0),
            annotations={"pattern": "knowledge_crisis"},
        )
        assert decorated.decision_id_or_compute() == base.decision_id_or_compute()

    def test_shadow_and_live_same_decision_share_id(self):
        """shadow/live 可对比的锚点：同输入同结论 ⇒ 同 decision_id。"""
        import dataclasses as dc

        live = _actionable_contract()
        shadow = dc.replace(live, governance_mode="shadow")
        assert shadow.decision_id_or_compute() == live.decision_id_or_compute()
        assert shadow.validate() == ()

    def test_explicit_malformed_decision_id_rejected(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="no_action",
            rationale_summary="x",
            cognition_tier="l1_light",
            no_action_reason="quiet_hours",
            decision_id="not-a-valid-id",
        )
        assert any("decision_id malformed" in v for v in contract.validate())


class TestRoundTrip:
    def test_to_dict_json_safe_and_from_dict_roundtrip(self):
        contract = _actionable_contract()
        payload = contract.to_dict()
        json.dumps(payload, ensure_ascii=False)  # 不得 raise

        restored = aurora_decision_from_dict(payload)
        assert restored is not None
        assert restored.validate() == ()
        assert restored.decision_id_or_compute() == contract.decision_id_or_compute()
        assert restored.intervention_type == contract.intervention_type
        assert restored.execution_mode == contract.execution_mode
        assert restored.evidence_refs == contract.evidence_refs
        assert restored.memory_use_receipts == contract.memory_use_receipts
        assert dict(restored.annotations) == dict(contract.annotations)

    def test_from_dict_with_policy_patch_roundtrip(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="reflect",
            rationale_summary="strategy recalibration candidate",
            cognition_tier="l4_async",
            execution_mode=ExecutionMode.HYBRID,
            policy_patch_candidate=PolicyPatchCandidate(
                scope="intervention_preference",
                intervention_preference="practice",
                evidence_refs=("memory://episodic/00000000-0000-0000-0000-000000000003",),
                confidence=0.72,
                expires_at=datetime(2026, 10, 1, 8, 0, 0),
                user_confirmed=False,
            ),
        )
        assert contract.validate() == ()
        restored = aurora_decision_from_dict(contract.to_dict())
        assert restored is not None and restored.policy_patch_candidate is not None
        assert restored.policy_patch_candidate.scope == "intervention_preference"
        assert restored.validate() == ()

    def test_from_dict_dirty_payload_returns_none(self):
        assert aurora_decision_from_dict(None) is None
        assert aurora_decision_from_dict("garbage") is None
        assert aurora_decision_from_dict({"intervention_type": "rescope"}) is None  # 缺 user_id 等
        bad_version = _actionable_contract().to_dict()
        bad_version["schema_version"] = "aurora_decision.v9"
        restored = aurora_decision_from_dict(bad_version)
        assert restored is not None  # 能重构
        assert restored.validate() != ()  # 但版本门必须拦下


class TestX02Consistency:
    def test_consistent_with_allocation_mode_mismatch_detected(self):
        contract = AuroraDecisionContract(
            user_id=uuid4(),
            intervention_type="delegate",
            rationale_summary="mechanical step delegated",
            cognition_tier="l1_light",
            execution_mode=ExecutionMode.HYBRID,
            allocation_ref="decision://alloc_abcdef0123456789abcdef0123456789",
        )
        assert contract.validate() == ()

        class _FakeAllocation:
            mode = "agent"

        assert contract.consistent_with_allocation(_FakeAllocation()) != ()

        class _FakeAllocationHybrid:
            mode = "hybrid"

        assert contract.consistent_with_allocation(_FakeAllocationHybrid()) == ()

    def test_consistency_check_skipped_without_allocation_ref(self):
        contract = _actionable_contract()  # 无 allocation_ref
        assert contract.consistent_with_allocation(type("A", (), {"mode": "agent"})()) == ()


def test_annotations_frozen_readonly():
    """C-01 FIX-09/F3 同款：annotations 固化为只读视图，防下游突变观测面。"""
    contract = _actionable_contract()
    with pytest.raises(TypeError):
        contract.annotations["hack"] = 1  # type: ignore[index]
