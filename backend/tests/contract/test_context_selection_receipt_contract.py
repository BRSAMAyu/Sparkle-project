"""V4-I06 · ``context_selection_receipt.v1`` 契约冻结测试（parity guard）。

冻结内容（任何变更都需要契约版本 bump + reviewer，B05 合同纪律节）：
1. schema 版本与 receipt_id 形态；
2. 四个封闭词表（selection_role / candidate status / reason_code / confidence_band）
   的**精确集合相等**；
3. ref scheme 复用不复制：与 ``ACTION_SOURCE_REF_SCHEMES``（action_plan.py）恒等；
4. 契约不变量 C1/C2（selected⇒reason_code=null；rejected/unavailable⇒必选且在词表；
   scheme 集合外违约；why_now 伪依据拒绝；basis_refs ⊆ selected）；
5. B05 §9 反例（机器可读集 counterexamples.json 相关项）不得漂移；
6. §8 双读：版本门外版本 → None+违例；旧生产者缺 candidates → 读侧 unknown；
   I1：字段面无权限语义字段；
7. M-03/M-05/C-08 reason → reason_code 映射表冻结。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES
from app.core.context_selection_receipt import (
    CANDIDATE_NOTE_MAX_LEN,
    CANDIDATE_STATUSES,
    CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
    RECEIPT_ID_PREFIX,
    REJECTION_REASON_CODES,
    SELECTION_ROLES,
    UNAVAILABLE_REASON_CODES,
    WHY_NOW_CONFIDENCE_BANDS,
    WHY_NOW_STATEMENT_MAX_LEN,
    ContextSelectionReceipt,
    ReceiptBudget,
    ReceiptCandidate,
    ReceiptInputVersions,
    ReceiptWhyNow,
    build_candidate,
    build_why_now,
    context_selection_receipt_from_payload,
    memory_ref,
    new_receipt_id,
    parse_ref_scheme,
    rejection_reason_code,
)


def _receipt(**overrides) -> ContextSelectionReceipt:
    base: dict = {
        "receipt_id": new_receipt_id(),
        "selection_role": "chat_context",
        "input_versions": ReceiptInputVersions(memory_epoch=1, selector_version="context_pack.v4-i06.v1"),
        "candidates": [
            ReceiptCandidate(ref="memory://episodic/a", status="selected", reason_code=None),
        ],
        "budget": ReceiptBudget(candidate_scan_limit=2, selected_max=1, clarifications_used=0),
    }
    base.update(overrides)
    return ContextSelectionReceipt(**base)


# ---------------------------------------------------------------------------
# 1. 版本与 ID 形态
# ---------------------------------------------------------------------------


def test_contract_schema_version_frozen():
    assert CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION == "context_selection_receipt.v1"


def test_receipt_id_shape():
    receipt_id = new_receipt_id()
    assert receipt_id.startswith(RECEIPT_ID_PREFIX)
    body = receipt_id[len(RECEIPT_ID_PREFIX) :]
    assert len(body) == 26  # ULID 宽度
    assert body.isalnum() and body == body.upper()
    assert new_receipt_id() != receipt_id  # 服务端生成唯一性（随机段）


# ---------------------------------------------------------------------------
# 2. 封闭词表（精确集合相等；扩展 = bump 版本过 reviewer）
# ---------------------------------------------------------------------------


def test_selection_roles_frozen():
    assert frozenset({"chat_context", "proposal_basis", "resume_view", "intervention_targeting"}) == SELECTION_ROLES


def test_candidate_statuses_frozen():
    assert frozenset({"selected", "rejected", "unavailable"}) == CANDIDATE_STATUSES


def test_rejection_reason_codes_frozen():
    assert (
        frozenset(
            {
                "out_of_scope_memory",
                "stale_epoch",
                "utility_gate_rejected",
                "conflicts_confirmed_preference",
                "permission_denied",
                "budget_exhausted",
                "duplicate",
                "expired",
            }
        )
        == REJECTION_REASON_CODES
    )


def test_confidence_bands_frozen():
    assert frozenset({"high", "medium", "low", "unknown"}) == WHY_NOW_CONFIDENCE_BANDS


def test_unavailable_reason_codes_subset():
    assert UNAVAILABLE_REASON_CODES <= REJECTION_REASON_CODES


# ---------------------------------------------------------------------------
# 3. ref scheme 复用不复制（B05 §1：ACTION_SOURCE_REF_SCHEMES 是唯一权威）
# ---------------------------------------------------------------------------


def test_ref_scheme_authority_is_action_plan_set():
    """receipt 不自造 scheme 集：封闭集判定直接消费 action_plan 权威。"""
    for scheme in (
        "memory",
        "plan",
        "task",
        "goal",
        "document",
        "profile",
        "user_state",
        "chat",
        "decision",
        "run",
        "subtask",
    ):
        assert scheme in ACTION_SOURCE_REF_SCHEMES
    assert parse_ref_scheme("memory://episodic/x") == "memory"
    assert parse_ref_scheme("astro://invented") not in ACTION_SOURCE_REF_SCHEMES
    assert parse_ref_scheme("no-scheme") is None


# ---------------------------------------------------------------------------
# 4. 契约不变量 C1/C2 + 反例
# ---------------------------------------------------------------------------


def test_c2_selected_requires_null_reason_code():
    receipt = _receipt(
        candidates=[ReceiptCandidate(ref="memory://episodic/a", status="selected", reason_code="duplicate")]
    )
    assert any("reason_code=null" in v for v in receipt.validate_contract())


def test_c2_non_selected_requires_reason_code():
    receipt = _receipt(candidates=[ReceiptCandidate(ref="memory://episodic/a", status="rejected", reason_code=None)])
    violations = receipt.validate_contract()
    assert any("requires reason_code" in v for v in violations)


def test_c2_reason_code_must_be_in_closed_vocabulary():
    receipt = _receipt(
        candidates=[ReceiptCandidate(ref="memory://episodic/a", status="rejected", reason_code="made_up_reason")]
    )
    assert any("made_up_reason" in v for v in receipt.validate_contract())


def test_c1_fabricated_ref_scheme_is_violation():
    """B05 §9 反例 fabricated_ref_scheme：scheme 集合外即契约违约。"""
    receipt = _receipt(candidates=[ReceiptCandidate(ref="astro://invented-id", status="selected", reason_code=None)])
    assert any("astro" in v for v in receipt.validate_contract())


def test_c1_duplicate_ref_is_violation():
    candidate = ReceiptCandidate(ref="memory://episodic/a", status="selected", reason_code=None)
    receipt = _receipt(candidates=[candidate, candidate.model_copy()])
    assert any("duplicated" in v for v in receipt.validate_contract())


def test_why_now_without_basis_is_rejected():
    """B05 §9 反例 why_now_without_basis：statement 非空 ⇒ basis_refs ≥1。"""
    receipt = _receipt(why_now=ReceiptWhyNow(statement="现在做最好", basis_refs=[], confidence_band="medium"))
    assert any("basis_refs" in v for v in receipt.validate_contract())


def test_why_now_basis_refs_must_be_selected():
    """C1 投影：why-now 依据必须真进本轮依据面（selected 集合），伪依据=违约。"""
    receipt = _receipt(
        candidates=[ReceiptCandidate(ref="memory://episodic/a", status="selected", reason_code=None)],
        why_now=ReceiptWhyNow(statement="s", basis_refs=["memory://episodic/not-selected"], confidence_band="low"),
    )
    assert any("not among selected" in v for v in receipt.validate_contract())


def test_why_now_confidence_band_closed():
    receipt = _receipt(why_now=ReceiptWhyNow(statement="s", basis_refs=["memory://episodic/a"], confidence_band="87%"))
    assert any("confidence_band" in v for v in receipt.validate_contract())


def test_why_now_statement_length_clamped():
    with pytest.raises(ValidationError):
        ReceiptWhyNow(statement="x" * (WHY_NOW_STATEMENT_MAX_LEN + 1), basis_refs=["memory://episodic/a"])


def test_why_now_builder_rejects_pseudo_basis():
    """build_why_now：无 selected 依据 → None+WARN（不构造伪依据 why-now）。"""
    assert build_why_now(statement="s", basis_refs=["memory://episodic/a"], selected_refs=[]) is None
    why = build_why_now(
        statement="s",
        basis_refs=["memory://episodic/a", "memory://episodic/b"],
        selected_refs=["memory://episodic/a"],
    )
    assert why is not None and why.basis_refs == ["memory://episodic/a"]


def test_empty_candidates_is_legal_selection_ran_without_candidates():
    """B05 §9 反例 empty_candidates_rendered_as_has_evidence 的结构面：
    空候选集合法（选择已运行但无合格候选），selected_refs 必须为空——
    呈现层据 selected_refs 空判定"不得声称引用了依据"。"""
    receipt = _receipt(candidates=[])
    assert receipt.validate_contract() == []
    assert receipt.selected_refs == []


def test_unknown_semantics_null_not_zero():
    """input_versions 各键 null=该权威未读取；不得以 0/'' 冒充已读（合同表）。
    selector_version 必选；其余允许显式 None。"""
    receipt = _receipt(
        input_versions=ReceiptInputVersions(
            memory_epoch=None,
            goal_version=None,
            task_version=None,
            policy_version=None,
            selector_version="context_pack.v4-i06.v1",
        )
    )
    assert receipt.validate_contract() == []
    with pytest.raises(ValidationError):
        ReceiptInputVersions(selector_version="")  # 必选版本串不得为空串冒充


def test_note_is_debug_only_bounded():
    note = "x" * (CANDIDATE_NOTE_MAX_LEN + 50)
    candidate = build_candidate(ref="memory://episodic/a", status="rejected", reason="ttl:expired", note=note)
    assert candidate.note is not None and len(candidate.note) == CANDIDATE_NOTE_MAX_LEN
    assert candidate.reason_code == "expired"


# ---------------------------------------------------------------------------
# 5. 字段面冻结（I1：无权限语义字段）
# ---------------------------------------------------------------------------


def test_payload_fields_frozen_no_permission_semantics():
    """I1 机器守卫：回执 payload 键集冻结且不含权限授予字段。"""
    payload = _receipt().to_payload()
    assert set(payload.keys()) == {
        "schema_version",
        "receipt_id",
        "selection_role",
        "decision_id",
        "input_versions",
        "candidates",
        "budget",
        "why_now",
    }
    forbidden = {"permission", "grant", "authorization", "scope_grant", "token"}
    assert not forbidden & set(payload.keys())


# ---------------------------------------------------------------------------
# 6. §8 双读：读侧门
# ---------------------------------------------------------------------------


def test_read_gate_unknown_version_returns_none():
    receipt, violations = context_selection_receipt_from_payload({"schema_version": "context_selection_receipt.v2"})
    assert receipt is None
    assert violations and "v2" in violations[0]


def test_read_gate_malformed_payload_returns_none():
    for bad in (None, [], "x", 42):
        receipt, violations = context_selection_receipt_from_payload(bad)
        assert receipt is None and violations


def test_read_gate_legacy_producer_missing_candidates_reads_unknown():
    """合同 §2：candidates 字段缺失 = 旧生产者 → 读侧按 unknown 处理（不炸、
    不得渲染为有/无依据任一），记 unknown 标记违例供遥测。"""
    payload = _receipt().to_payload()
    payload.pop("candidates")
    receipt, violations = context_selection_receipt_from_payload(payload)
    assert receipt is not None
    assert any("legacy producer" in v for v in violations)


def test_read_gate_roundtrip_preserves_contract_validity():
    payload = _receipt(
        why_now=ReceiptWhyNow(
            statement="距检查点还剩2天",
            basis_refs=["memory://episodic/a"],
            expires_at="2026-09-29T23:59:00+08:00",
            confidence_band="medium",
        )
    ).to_payload()
    receipt, violations = context_selection_receipt_from_payload(payload)
    assert receipt is not None and violations == []
    assert receipt.why_now is not None and receipt.why_now.confidence_band == "medium"
    assert receipt.selected_refs == ["memory://episodic/a"]


def test_memory_ref_format_resolvable():
    assert memory_ref("episodic", "uuid-1") == "memory://episodic/uuid-1"
    assert parse_ref_scheme(memory_ref("preference", "k")) == "memory"


# ---------------------------------------------------------------------------
# 7. reason → reason_code 映射表冻结（prefilter 面既有语义）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # M-03 维度（映射表判定序）
        ("user:wrong_user", "permission_denied"),
        ("status:expired", "expired"),
        ("status:revoked", "stale_epoch"),
        ("status:superseded", "stale_epoch"),
        ("status:archived", "stale_epoch"),
        ("ttl:expired", "expired"),
        ("ttl:today_only_expired", "expired"),
        ("ttl:not_yet_valid", "expired"),
        ("scope:mismatch", "out_of_scope_memory"),
        ("scope:unknown_level", "out_of_scope_memory"),
        ("purpose:blocked_source", "permission_denied"),
        ("purpose:memory_disabled", "permission_denied"),
        ("sensitivity:exceeded", "permission_denied"),
        # M-05 selfcheck 面
        ("selfcheck:duplicate_in_pack", "duplicate"),
        ("selfcheck:irrelevant_to_query", "utility_gate_rejected"),
        ("selfcheck:agreement_bias_risk", "utility_gate_rejected"),
        # C-08 漏斗面
        ("rank_cutoff", "budget_exhausted"),
        ("budget_truncated", "budget_exhausted"),
        ("selfcheck_internal", "utility_gate_rejected"),
        # 未知 reason → 封闭兜底（词表无 other；fallback 钉死 out_of_scope_memory）
        ("totally:unknown", "out_of_scope_memory"),
        ("", "out_of_scope_memory"),
    ],
)
def test_rejection_reason_mapping_frozen(raw: str, expected: str):
    assert rejection_reason_code(raw) == expected
    assert rejection_reason_code(raw) in REJECTION_REASON_CODES  # 函数即守卫
