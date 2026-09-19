"""D-02 · Outcome Ledger 契约冻结 + 「无法证明时不伪装 actual」守卫。

红→绿纪律：本文件先写先跑（RED = ModuleNotFoundError: app.core.outcome_ledger），
实现后全绿。守卫覆盖验收项：「无 evidence 的 complete → truth_class =
unknown/self_reported 而非 actual」。

对齐声明（勿漂移）：
- TruthClass 词表 = 卡面四值（actual/self_reported/estimated/unknown）+ B-02 台账
  demo 档合成（非「与 B-02 完全对齐」——B-02 另有 seed_namespace/pollution 等分类学）；
- evidence_kind 封闭枚举直接 import X-01 的 ``app.core.action_plan.EVIDENCE_KINDS``，
  本契约不造第二套 plan 侧枚举——五源映射表只做 kind → 信任档位 → 可解析 scheme →
  物化源 的正规化。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.core.action_plan import EVIDENCE_KINDS as X01_EVIDENCE_KINDS
from app.core.outcome_ledger import (
    ECHO_STUDY_RECORD_TYPES,
    EVIDENCE_KIND_REF_SCHEMES,
    EVIDENCE_KIND_SOURCE_MATERIALIZATION,
    EVIDENCE_TRUST_TIERS,
    FIVE_SOURCE_MAP,
    FOCUS_COVERAGE_MIN_MINUTES,
    FOCUS_COVERAGE_RATIO,
    EvidenceTrustTier,
    OutcomeSource,
    TruthClass,
    classify_task_completion,
    decode_cursor,
    derive_outcome_id,
    encode_cursor,
    outcome_key,
    required_focus_minutes,
)


def _evidence(kind: str, ref: str | None = None) -> dict:
    return {"evidence_kind": kind, "ref": ref, "description": None}


_TS = datetime(2026, 9, 19, 2, 0, 58, tzinfo=None)


class TestVocabularyFrozen:
    """词表冻结：改词表必须显式 bump 并过两位 reviewer。"""

    def test_truth_class_matches_b02_data_truth_vocabulary(self):
        assert {member.value for member in TruthClass} == {
            "actual",
            "self_reported",
            "estimated",
            "demo",
            "unknown",
        }

    def test_five_sources_frozen(self):
        assert {member.value for member in OutcomeSource} == {
            "task_completion",
            "study_record",
            "focus_session",
            "quiz_feedback",
            "behavioral",
        }

    def test_five_source_map_covers_exactly_the_five_sources(self):
        assert set(FIVE_SOURCE_MAP) == {member.value for member in OutcomeSource}

    def test_echo_study_record_types_frozen(self):
        """去重规则的 echo 面：这些 record_type 的 study_record 是完成管线的自动回声。"""
        assert frozenset({"task_complete"}) == ECHO_STUDY_RECORD_TYPES

    def test_evidence_trust_tiers_cover_all_x01_kinds(self):
        """X-01 evidence_kind 封闭枚举的每一 kind 都必须有信任档位（五源映射完整性）。"""
        assert set(EVIDENCE_TRUST_TIERS) == set(X01_EVIDENCE_KINDS)
        assert set(EVIDENCE_TRUST_TIERS.values()) == {"verifiable", "user", "system"}

    def test_evidence_trust_tiers_values_frozen(self):
        """R2 返修（P2-5，变异 M1）：逐 kind 钉死档位**值**——只断言键覆盖时，
        user_confirmation 被改成 verifiable 依然全绿（档位漂移无红灯）。"""
        assert dict(EVIDENCE_TRUST_TIERS) == {
            "artifact": EvidenceTrustTier.VERIFIABLE,
            "file": EvidenceTrustTier.VERIFIABLE,
            "code": EvidenceTrustTier.VERIFIABLE,
            "quiz_result": EvidenceTrustTier.VERIFIABLE,
            "system_event": EvidenceTrustTier.SYSTEM,
            "user_confirmation": EvidenceTrustTier.USER,
            "self_report": EvidenceTrustTier.USER,
        }

    def test_user_and_self_report_tiers_are_user_never_verifiable(self):
        """用户断言档位永不升 actual 的**档位值**守卫（M1 变异必红）。"""
        assert EVIDENCE_TRUST_TIERS["user_confirmation"] is EvidenceTrustTier.USER
        assert EVIDENCE_TRUST_TIERS["self_report"] is EvidenceTrustTier.USER

    def test_evidence_kind_ref_schemes_frozen(self):
        """R2 返修（P2-1）：kind↔scheme 配对白名单逐值冻结。

        v1 只有 artifact/file × document:// 可经声明 ref 验证；code 无解析器、
        quiz_result 走 quiz_feedback 物化面、system_event 走 focus/study 物化面
        ——它们对任何 scheme 都不升 actual。task://、subtask:// 不在白名单
        （指向的行本身也是用户主张，声明不构成证明）。
        """
        assert {kind: frozenset(schemes) for kind, schemes in EVIDENCE_KIND_REF_SCHEMES.items()} == {
            "artifact": frozenset({"document"}),
            "file": frozenset({"document"}),
            "code": frozenset(),
            "quiz_result": frozenset(),
            "system_event": frozenset(),
            "user_confirmation": frozenset(),
            "self_report": frozenset(),
        }

    def test_evidence_kind_materialization_covers_all_x01_kinds(self):
        assert set(EVIDENCE_KIND_SOURCE_MATERIALIZATION) == set(X01_EVIDENCE_KINDS)

    def test_task_completion_is_the_only_classified_source(self):
        """其余四源是服务器记录的行为观察（truth 默认 actual）；task_completion 是
        唯一需要逐条分级（可能 self_reported/unknown）的源——「完成 ≠ 点击」。"""
        classified = [name for name, spec in FIVE_SOURCE_MAP.items() if spec.truth_is_classified]
        assert classified == ["task_completion"]


class TestCompletionTruthGuard:
    """验收核心守卫：无法证明时不伪装 actual。"""

    def test_no_evidence_complete_is_self_reported_not_actual(self):
        """RED 主断言：无 declared evidence、无独立系统证据的 complete → self_reported。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=None,
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is TruthClass.SELF_REPORTED
        assert truth is not TruthClass.ACTUAL

    def test_broken_row_without_completed_at_is_unknown(self):
        truth = classify_task_completion(
            completed_at=None,
            declared_evidence=None,
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=None,
        )
        assert truth is TruthClass.UNKNOWN

    @pytest.mark.parametrize(
        "declared",
        [
            [_evidence("user_confirmation")],
            [_evidence("self_report")],
            [_evidence("user_confirmation"), _evidence("self_report")],
            [],  # V3 行声明了空证据列表 = 未证明
        ],
    )
    def test_user_tier_evidence_never_upgrades_to_actual(self, declared):
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=declared,
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is TruthClass.SELF_REPORTED

    @pytest.mark.parametrize("kind", ["artifact", "file", "code", "quiz_result"])
    def test_verifiable_kind_declared_but_unverified_is_not_actual(self, kind):
        """声明了可验证证据但 ref 无法解析/物化 → 不伪装 actual（退 self_reported）。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=[_evidence(kind, "document://00000000-0000-0000-0000-0000000000ff")],
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is not TruthClass.ACTUAL
        assert truth is TruthClass.SELF_REPORTED

    @pytest.mark.parametrize("kind", ["artifact", "file", "code", "quiz_result"])
    def test_verified_verifiable_kind_upgrades_to_actual(self, kind):
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=[_evidence(kind, "document://00000000-0000-0000-0000-0000000000aa")],
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset({kind}),
            actual_minutes=30,
        )
        assert truth is TruthClass.ACTUAL

    def test_quiz_materialized_upgrades_to_actual_even_without_declaration(self):
        """legacy 行（无 declared evidence）但 quiz 结果物化 → actual（独立可验证结果）。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=None,
            focus_minutes_covered=0,
            quiz_materialized=True,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is TruthClass.ACTUAL

    def test_system_event_declared_but_no_focus_coverage_is_not_actual(self):
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=[_evidence("system_event")],
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is TruthClass.SELF_REPORTED

    def test_focus_coverage_meeting_threshold_upgrades_to_actual(self):
        """独立系统证据（focus 计时行为）覆盖所需时长 → actual。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=None,
            focus_minutes_covered=required_focus_minutes(60),
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=60,
        )
        assert truth is TruthClass.ACTUAL

    def test_focus_coverage_below_threshold_is_not_actual(self):
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=None,
            focus_minutes_covered=required_focus_minutes(60) - 1,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=60,
        )
        assert truth is TruthClass.SELF_REPORTED

    def test_tiny_focus_cannot_upgrade_long_task(self):
        """1 分钟 focus 不能把 60 分钟任务伪装成 actual（覆盖率规则的意义）。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=None,
            focus_minutes_covered=1,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=60,
        )
        assert truth is not TruthClass.ACTUAL

    def test_dirty_declared_evidence_degrades_to_self_reported(self):
        """completion_evidence 脏数据（词表外 kind）→ 不 crash，不伪装 actual。"""
        truth = classify_task_completion(
            completed_at=_TS,
            declared_evidence=[{"evidence_kind": "trust_me_bro", "ref": None}],
            focus_minutes_covered=0,
            quiz_materialized=False,
            verified_evidence_kinds=frozenset(),
            actual_minutes=30,
        )
        assert truth is TruthClass.SELF_REPORTED

    def test_classification_never_returns_estimated_or_demo_for_completions(self):
        """确定性分级路径：task completion 分级永不出 estimated/demo（那是模型估计/
        demo cohort 的语义，属消费方标注，不属完成真相分级）。"""
        for focus in (0, 5, 10, 100):
            for quiz in (False, True):
                for verified in (frozenset(), frozenset({"artifact"})):
                    for declared in (None, [_evidence("user_confirmation")], [_evidence("code", "task://x")]):
                        truth = classify_task_completion(
                            completed_at=_TS,
                            declared_evidence=declared,
                            focus_minutes_covered=focus,
                            quiz_materialized=quiz,
                            verified_evidence_kinds=verified,
                            actual_minutes=45,
                        )
                        assert truth in (TruthClass.ACTUAL, TruthClass.SELF_REPORTED)


class TestFocusCoverageRule:
    def test_threshold_is_max_of_absolute_floor_and_ratio(self):
        assert required_focus_minutes(60) == max(FOCUS_COVERAGE_MIN_MINUTES, int(FOCUS_COVERAGE_RATIO * 60))
        assert required_focus_minutes(None) == FOCUS_COVERAGE_MIN_MINUTES
        assert required_focus_minutes(0) == FOCUS_COVERAGE_MIN_MINUTES

    def test_threshold_is_monotonic_in_actual_minutes(self):
        previous = -1
        for minutes in (0, 5, 10, 20, 40, 60, 120, 480):
            threshold = required_focus_minutes(minutes)
            assert threshold >= previous
            previous = threshold


class TestOutcomeIdentity:
    def test_derive_outcome_id_is_deterministic(self):
        task_id = uuid4()
        assert derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task_id) == (
            derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task_id)
        )

    def test_derive_outcome_id_separates_source_and_id(self):
        row_id = uuid4()
        assert derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=row_id) != (
            derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=row_id)
        )
        assert derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=row_id) != (
            derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=uuid4())
        )

    def test_derive_outcome_id_prefix_matches_event_id_style(self):
        value = derive_outcome_id(source=OutcomeSource.FOCUS_SESSION, source_id=uuid4())
        assert value.startswith("outc_") and len(value) == 5 + 32

    def test_outcome_key_is_readable_and_stable(self):
        row_id = uuid4()
        assert outcome_key(OutcomeSource.TASK_COMPLETION, row_id) == f"task_completion:{row_id}"

    def test_cursor_roundtrip(self):
        cursor = encode_cursor(_TS, "task_completion:x")
        assert decode_cursor(cursor) == (_TS, "task_completion:x")

    def test_decode_cursor_rejects_garbage(self):
        assert decode_cursor("not-a-cursor") is None
        assert decode_cursor("") is None
