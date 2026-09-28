"""V4-D01 · experience_event.v1 契约守卫（冻结词表 / E1–E4 不变量 / 投影全函数）。

契约真源：v4/evidence/V4-B05/contract_receipt_min.md §3（B05 DONE_REVIEWED）。
词表扩展 = 契约变更：本文件对全部封闭集做精确字面冻结（D-05/C-01 同款纪律），
新增成员不改本测试 → 红。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.action_command import ACTION_ERROR_CODES
from app.core.experience_event import (
    COMMIT_STATE_VOCABULARY,
    ERROR_STATE_VOCABULARY,
    EXPERIENCE_EVENT_KINDS,
    EXPERIENCE_EVENT_SCHEMA_VERSION,
    EXPERIENCE_RECEIPT_REF_SCHEMES,
    PRESENTATION_MODALITY_VOCABULARY,
    RECEIPT_REF_REQUIRED_KINDS,
    SUBJECT_TYPE_VOCABULARY,
    SUCCESS_PRESENTATION_KINDS,
    ExperienceCommitState,
    ExperienceErrorState,
    ExperienceEvent,
    ExperienceEventKind,
    ExperienceEventValidationError,
    ExperiencePresentation,
    ExperienceProjectionRefused,
    ExperienceSubject,
    derive_dedupe_key,
    derive_experience_event_id,
    project_error_state,
    project_terminal_reason,
)

_T0 = datetime(2026, 9, 28, 12, 0, 0)


def _subject(**overrides) -> ExperienceSubject:
    values = {"type": "intervention", "id": "11111111-2222-3333-4444-555555555555", "version_token": "cv1"}
    values.update(overrides)
    return ExperienceSubject(**values)


def _presentation(**overrides) -> ExperiencePresentation:
    values = {"modalities": ("visual",), "copy_key": "intervention.rendered"}
    values.update(overrides)
    return ExperiencePresentation(**values)


def _project(**overrides) -> ExperienceEvent:
    values = {
        "kind": ExperienceEventKind.STATE_CONFIRMED.value,
        "commit_state": ExperienceCommitState.COMMITTED.value,
        "receipt_ref": "intervention_lifecycle://aurora_" + "a" * 32,
        "subject": _subject(),
        "presentation": _presentation(),
        "issued_at": _T0,
        "expires_at": None,
    }
    values.update(overrides)
    return ExperienceEvent.project(**values)


# ---------------------------------------------------------------------------
# 封闭词表（精确字面冻结）
# ---------------------------------------------------------------------------


class TestFrozenVocabularies:
    def test_kind_vocabulary_is_the_contract_seven(self):
        assert frozenset(
            {
                "state_confirmed",
                "state_syncing",
                "correction_applied",
                "calibration_notice",
                "resume_available",
                "progress_delta",
                "terminal_failed",
            }
        ) == EXPERIENCE_EVENT_KINDS

    def test_commit_state_vocabulary(self):
        assert frozenset({"committed", "error"}) == COMMIT_STATE_VOCABULARY

    def test_error_state_vocabulary_is_five_values(self):
        assert frozenset(
            {"version_conflict", "unauthorized", "not_pending", "expired", "not_found"}
        ) == ERROR_STATE_VOCABULARY

    def test_subject_type_vocabulary(self):
        assert frozenset({"task", "goal", "run", "intervention", "memory", "plan"}) == SUBJECT_TYPE_VOCABULARY

    def test_modality_vocabulary(self):
        assert frozenset({"visual", "audio", "haptic"}) == PRESENTATION_MODALITY_VOCABULARY

    def test_receipt_ref_schemes_are_the_contract_six(self):
        assert frozenset(
            {"action_command", "run", "outcome", "intervention_lifecycle", "calibration_receipt", "context_selection"}
        ) == EXPERIENCE_RECEIPT_REF_SCHEMES

    def test_receipt_required_kinds(self):
        assert frozenset(
            {"state_confirmed", "progress_delta", "correction_applied", "calibration_notice"}
        ) == RECEIPT_REF_REQUIRED_KINDS
        assert frozenset({"state_confirmed"}) == SUCCESS_PRESENTATION_KINDS


# ---------------------------------------------------------------------------
# 幂等键（内容寻址；重放身份稳定）
# ---------------------------------------------------------------------------


class TestIdempotencyKeys:
    def test_dedupe_key_matches_contract_formula(self):
        import hashlib

        ref = "intervention_lifecycle://aurora_" + "a" * 32
        expected = hashlib.sha256(f"{ref}state_confirmedcv1".encode()).hexdigest()
        assert derive_dedupe_key(receipt_ref=ref, kind="state_confirmed", version_token="cv1") == expected

    def test_event_id_is_deterministic_and_time_independent(self):
        event_a = _project(issued_at=_T0)
        event_b = _project(issued_at=datetime(2030, 1, 1, 0, 0, 0))
        assert event_a.event_id == event_b.event_id, "replay at any time must yield the same event identity"
        assert event_a.dedupe_key == event_b.dedupe_key
        assert event_a.event_id.startswith("eev_") and len(event_a.event_id) == 4 + 32

    def test_event_id_derives_from_dedupe_key(self):
        dedupe = derive_dedupe_key(receipt_ref=None, kind="resume_available", version_token="v9")
        assert derive_experience_event_id(dedupe) == derive_experience_event_id(dedupe)
        assert derive_experience_event_id(dedupe).startswith("eev_")


# ---------------------------------------------------------------------------
# 不变量 E1 / E2 / I2 / E4
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_e1_state_confirmed_requires_committed_and_receipt(self):
        event = _project()
        assert event.commit_state == "committed"
        assert event.receipt_ref is not None

    def test_e1_state_confirmed_with_error_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="E1"):
            _project(
                commit_state=ExperienceCommitState.ERROR.value,
                error_state=ExperienceErrorState.EXPIRED.value,
            )

    def test_e1_state_confirmed_without_receipt_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="I2|receipt_ref"):
            _project(receipt_ref=None)

    def test_e2_error_requires_error_state(self):
        event = _project(
            kind=ExperienceEventKind.TERMINAL_FAILED.value,
            commit_state=ExperienceCommitState.ERROR.value,
            error_state=ExperienceErrorState.VERSION_CONFLICT.value,
        )
        assert event.error_state == "version_conflict"

    def test_e2_error_without_error_state_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="E2"):
            _project(kind=ExperienceEventKind.TERMINAL_FAILED.value, commit_state=ExperienceCommitState.ERROR.value)

    def test_e2_committed_with_error_state_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="E2"):
            _project(error_state=ExperienceErrorState.NOT_FOUND.value)

    def test_i2_receipt_required_kind_without_receipt_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="I2|receipt_ref"):
            _project(kind=ExperienceEventKind.PROGRESS_DELTA.value, receipt_ref=None)

    def test_e4_fabricated_ref_scheme_rejected(self):
        with pytest.raises(ExperienceEventValidationError, match="scheme"):
            _project(receipt_ref="model_free_text://whatever")

    def test_closed_vocabulary_violations_rejected(self):
        with pytest.raises(ExperienceEventValidationError):
            _project(kind="rendered")  # 词表外 kind（同义新成员必须走契约 bump）
        with pytest.raises(ExperienceEventValidationError):
            _project(commit_state="maybe")
        with pytest.raises(ExperienceEventValidationError):
            _project(subject=_subject(type="server"))
        with pytest.raises(ExperienceEventValidationError):
            _project(presentation=_presentation(modalities=("smell",)))
        with pytest.raises(ExperienceEventValidationError):
            _project(presentation=_presentation(copy_key="free form text from a model"))

    def test_empty_modalities_are_legal_but_copy_key_discipline_holds(self):
        event = _project(presentation=_presentation(modalities=()))
        assert event.presentation.modalities == ()
        assert event.presentation.copy_key == "intervention.rendered"

    def test_subject_requires_version_token(self):
        with pytest.raises(ExperienceEventValidationError):
            _subject(version_token="")


# ---------------------------------------------------------------------------
# E3/I1 结构面：事件无权限语义字段
# ---------------------------------------------------------------------------


class TestNoPermissionSemantics:
    def test_serialized_key_set_is_frozen_and_permission_free(self):
        event = _project()
        payload = event.to_dict()
        assert set(payload) == {
            "schema_version",
            "event_id",
            "kind",
            "receipt_ref",
            "commit_state",
            "error_state",
            "subject",
            "presentation",
            "dedupe_key",
            "issued_at",
            "expires_at",
        }
        blob = repr(payload)
        for forbidden in ("permission", "role", "token_scope", "can_write", "grants"):
            assert forbidden not in blob, f"experience_event must never carry {forbidden} semantics"

    def test_subject_payload_is_three_keys(self):
        assert set(_subject().to_dict()) == {"type", "id", "version_token"}


# ---------------------------------------------------------------------------
# 投影全函数（契约 §6：commit_state 唯一真源 = X-03）
# ---------------------------------------------------------------------------


class TestProjectionFunctions:
    def test_terminal_reason_committed(self):
        assert project_terminal_reason("committed") == (ExperienceCommitState.COMMITTED, None)

    def test_terminal_reason_expired(self):
        assert project_terminal_reason("expired") == (ExperienceCommitState.ERROR, ExperienceErrorState.EXPIRED)

    def test_terminal_reason_user_decisions_skip_no_event(self):
        assert project_terminal_reason("user_cancelled") is None
        assert project_terminal_reason("user_rejected") is None

    def test_terminal_reason_unknown_is_fail_loud(self):
        with pytest.raises(ExperienceProjectionRefused):
            project_terminal_reason("mysteriously_finished")

    def test_error_state_mapping_is_one_to_one_with_action_codes(self):
        assert project_error_state(ACTION_ERROR_CODES["VERSION_CONFLICT"]) is ExperienceErrorState.VERSION_CONFLICT
        assert project_error_state(ACTION_ERROR_CODES["UNAUTHORIZED"]) is ExperienceErrorState.UNAUTHORIZED
        assert project_error_state(ACTION_ERROR_CODES["NOT_PENDING"]) is ExperienceErrorState.NOT_PENDING
        assert project_error_state(ACTION_ERROR_CODES["EXPIRED"]) is ExperienceErrorState.EXPIRED
        assert project_error_state(ACTION_ERROR_CODES["NOT_FOUND"]) is ExperienceErrorState.NOT_FOUND
        assert len(ACTION_ERROR_CODES) == 6, "source vocabulary drift must surface here"

    def test_invalid_command_is_fail_loud_never_silently_mapped(self):
        with pytest.raises(ExperienceProjectionRefused, match="ACTION_INVALID_COMMAND"):
            project_error_state("ACTION_INVALID_COMMAND")

    def test_unknown_error_code_is_fail_loud(self):
        with pytest.raises(ExperienceProjectionRefused):
            project_error_state("ACTION_SOMETHING_ELSE")

    def test_schema_version_constant(self):
        assert EXPERIENCE_EVENT_SCHEMA_VERSION == "experience_event.v1"
        assert _project().schema_version == "experience_event.v1"
