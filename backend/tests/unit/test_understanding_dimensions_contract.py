"""D-03 · Understanding 五维契约测试：golden 冻结 + 公式单测 + 词表分区校验。

变异必红面：
- golden JSON sha256 冻结（改 fixture 或公式输出 → 红）；
- 冻结常数与公式行为钉死（改容忍度/单调方向 → 红）；
- 动作分区与 M-01 / M-08 写方词表的交集校验（词表漂移 → 红）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.understanding_dimensions import (
    ALL_DIMENSIONS,
    CORRECTNESS_NEGATIVE_ACTIONS,
    CORRECTNESS_TOLERANCE,
    FRESHNESS_LAG_TOLERANCE_DAYS,
    FRESHNESS_STATE_CHANGE_ACTIONS,
    MAX_LAG_DAYS,
    MIN_COVERAGE_SAMPLE,
    MIN_UTILITY_SAMPLE,
    SCOPE_FEEDBACK_ACTIONS,
    SCOPE_NEGATIVE_ACTIONS,
    SCOPE_TOLERANCE,
    UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION,
    UTILITY_DECISIVE_ACTIONS,
    DimensionStatus,
    band_of,
    compute_correctness,
    compute_coverage,
    compute_freshness,
    compute_scope_precision,
    compute_utility,
    summarize,
)
from app.services.understanding_dimensions_service import (
    WindowInputs,
    anchors_from_inputs,
    dimensions_from_inputs,
)

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "golden" / "understanding_dimensions_golden.json"

# sha256 of the golden file captured at D-03 freeze (2026-09-20). Any change to
# the fixture must be a deliberate re-freeze with dual review (D-01 style).
GOLDEN_SHA256 = "ee8c0384c5feb0a7ffcac283a20bc0051d9f083db4c2c8c4b704095daade6a3d"


@pytest.fixture(name="golden")
def _golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# golden 冻结
# ---------------------------------------------------------------------------


def test_golden_file_sha256_frozen():
    digest = hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest()
    assert digest == GOLDEN_SHA256, (
        "understanding_dimensions_golden.json changed without re-freeze; "
        "update GOLDEN_SHA256 deliberately (formula change needs reviewer sign-off)"
    )


def test_golden_schema_version_matches_contract(golden):
    assert golden["schema_version"] == UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION


def test_golden_coverage_ok_case(golden):
    case = golden["coverage"]["ok"]
    result = compute_coverage(
        context_scores=case["context_scores"],
        task_scores=case["task_scores"],
        missing_dimensions=case["missing_dimensions"],
    )
    expected = case["expected"]
    assert result.status.value == expected["status"]
    assert result.value == pytest.approx(expected["value"], abs=1e-4)
    assert result.samples == expected["samples"]
    assert result.detail["task_score_mean"] == pytest.approx(expected["task_score_mean"], abs=1e-4)
    assert result.detail["top_missing"] == expected["top_missing"]


def test_golden_coverage_unknown_case(golden):
    case = golden["coverage"]["unknown_below_min_sample"]
    result = compute_coverage(
        context_scores=case["context_scores"],
        task_scores=case["task_scores"],
        missing_dimensions=case["missing_dimensions"],
    )
    assert result.status is DimensionStatus.UNKNOWN
    assert result.value is None
    assert result.samples == case["expected"]["samples"]


@pytest.mark.parametrize(
    "case_key",
    ["ok_moderate", "unknown_no_usage", "zero_at_saturation"],
)
def test_golden_correctness_cases(golden, case_key):
    case = golden["correctness"][case_key]
    result = compute_correctness(
        usage_opportunities=case["usage_opportunities"],
        negative_corrections=case["negative_corrections"],
        unresolved_conflicts=case["unresolved_conflicts"],
    )
    expected = case["expected"]
    assert result.status.value == expected["status"]
    if expected["value"] is None:
        assert result.value is None
    else:
        assert result.value == pytest.approx(expected["value"], abs=1e-4)
    assert result.samples == expected["samples"]


@pytest.mark.parametrize("case_key", ["ok_half", "unknown_dark_channel"])
def test_golden_scope_cases(golden, case_key):
    case = golden["scope_precision"][case_key]
    result = compute_scope_precision(
        scope_feedback_total=case["scope_feedback_total"],
        scope_negative=case["scope_negative"],
    )
    expected = case["expected"]
    assert result.status.value == expected["status"]
    if expected["value"] is None:
        assert result.value is None
    else:
        assert result.value == pytest.approx(expected["value"], abs=1e-4)
    assert result.samples == expected["samples"]


@pytest.mark.parametrize("case_key", ["ok_two_thirds", "unknown_no_samples", "zero_on_clamped_stale"])
def test_golden_freshness_cases(golden, case_key):
    case = golden["freshness"][case_key]
    result = compute_freshness(lag_days_samples=case["lag_days_samples"])
    expected = case["expected"]
    assert result.status.value == expected["status"]
    if expected["value"] is None:
        assert result.value is None
    else:
        assert result.value == pytest.approx(expected["value"], abs=1e-4)
    assert result.samples == expected["samples"]


@pytest.mark.parametrize("case_key", ["ok_three_fifths", "unknown_below_min_decisive"])
def test_golden_utility_cases(golden, case_key):
    case = golden["utility"][case_key]
    result = compute_utility(
        accepted=case["accepted"],
        corrected=case["corrected"],
        denied=case["denied"],
    )
    expected = case["expected"]
    assert result.status.value == expected["status"]
    if expected["value"] is None:
        assert result.value is None
    else:
        assert result.value == pytest.approx(expected["value"], abs=1e-4)
    assert result.samples == expected["samples"]


def test_golden_window_inputs_composite(golden):
    case = golden["window_inputs_composite"]
    inputs = WindowInputs(**case["inputs"])
    values = dimensions_from_inputs(inputs)
    for dim_name, expected in case["expected_dimensions"].items():
        entry = values[dim_name]
        assert entry.status.value == expected["status"], dim_name
        assert entry.value == pytest.approx(expected["value"], abs=1e-4), dim_name
    anchors = anchors_from_inputs(inputs)
    anchor = anchors["coverage"]
    assert anchor["anchor_value"] == pytest.approx(case["expected_coverage_anchor"]["anchor_value"], abs=1e-4)
    assert anchor["anchor_samples"] == case["expected_coverage_anchor"]["anchor_samples"]


# ---------------------------------------------------------------------------
# 验收①：每一维有公式/数据源/边界；缺数据=unknown（变异必红：默认值冒充 → 红）
# ---------------------------------------------------------------------------


def test_every_dimension_has_provenance_or_unknown_reason():
    """有值必有 provenance；unknown 必有 unknown_reason —— 不存在无来源的值。"""
    cases = [
        compute_coverage(context_scores=[1.0] * MIN_COVERAGE_SAMPLE, task_scores=[], missing_dimensions=[]),
        compute_correctness(usage_opportunities=5, negative_corrections=0, unresolved_conflicts=0),
        compute_scope_precision(scope_feedback_total=5, scope_negative=0),
        compute_freshness(lag_days_samples=[1.0]),
        compute_utility(accepted=MIN_UTILITY_SAMPLE, corrected=0, denied=0),
        compute_coverage(context_scores=[1.0], task_scores=[], missing_dimensions=[]),
        compute_correctness(usage_opportunities=0, negative_corrections=0, unresolved_conflicts=0),
        compute_scope_precision(scope_feedback_total=0, scope_negative=0),
        compute_freshness(lag_days_samples=[]),
        compute_utility(accepted=0, corrected=0, denied=0),
    ]
    for entry in cases:
        if entry.status is DimensionStatus.OK:
            assert entry.provenance, entry
            assert entry.value is not None
        else:
            assert entry.value is None, entry  # unknown 永不带值
            assert entry.detail.get("unknown_reason"), entry  # 且必说原因


def test_unknown_never_disguised_as_zero_or_one():
    """缺数据的四维绝不能给出 0/1 冒充（假指标红线）。"""
    assert compute_coverage(context_scores=[], task_scores=[], missing_dimensions=[]).value is None
    assert compute_correctness(usage_opportunities=0, negative_corrections=0, unresolved_conflicts=0).value is None
    assert compute_scope_precision(scope_feedback_total=0, scope_negative=0).value is None
    assert compute_freshness(lag_days_samples=[]).value is None
    assert compute_utility(accepted=0, corrected=0, denied=0).value is None


# ---------------------------------------------------------------------------
# 验收②：纠正与错误使用合理降低相关维度（单调性钉死）
# ---------------------------------------------------------------------------


def test_more_corrections_lower_correctness_monotonically():
    previous = None
    for negatives in range(0, 12):
        value = compute_correctness(
            usage_opportunities=10, negative_corrections=negatives, unresolved_conflicts=0
        ).value
        assert value is not None
        if previous is not None:
            assert value <= previous, f"correctness must be non-increasing in negatives (at {negatives})"
        previous = value


def test_conflicts_lower_correctness_independently():
    without = compute_correctness(usage_opportunities=10, negative_corrections=1, unresolved_conflicts=0).value
    with_conflict = compute_correctness(usage_opportunities=10, negative_corrections=1, unresolved_conflicts=2).value
    assert with_conflict < without


def test_more_scope_misuse_lower_scope_precision_monotonically():
    previous = None
    for negatives in range(0, 9):
        value = compute_scope_precision(scope_feedback_total=8, scope_negative=negatives).value
        assert value is not None
        if previous is not None:
            assert value <= previous
        previous = value


def test_longer_lag_lower_freshness_monotonically():
    previous = None
    for lag in (0.0, 5.0, 10.0, 20.0, 40.0, 100.0):
        value = compute_freshness(lag_days_samples=[lag]).value
        assert value is not None
        if previous is not None:
            assert value <= previous
        previous = value


def test_more_denials_lower_utility():
    good = compute_utility(accepted=5, corrected=0, denied=0).value
    bad = compute_utility(accepted=0, corrected=0, denied=5).value
    assert bad < good


# ---------------------------------------------------------------------------
# 冻结常数（改常数 = 改契约，必须显式）
# ---------------------------------------------------------------------------


def test_frozen_constants():
    assert MIN_COVERAGE_SAMPLE == 3
    assert CORRECTNESS_TOLERANCE == 0.5
    assert SCOPE_TOLERANCE == 0.25
    assert FRESHNESS_LAG_TOLERANCE_DAYS == 30.0
    assert MIN_UTILITY_SAMPLE == 3
    assert MAX_LAG_DAYS == 365.0
    assert UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION == "understanding.dimensions.v1"


def test_band_of_thresholds():
    assert band_of(0.9) == "sufficient"
    assert band_of(0.66) == "sufficient"
    assert band_of(0.6599) == "partial"
    assert band_of(0.33) == "partial"
    assert band_of(0.1) == "insufficient"


def test_summarize_has_no_composite_percentage():
    values = dimensions_from_inputs(
        WindowInputs(
            context_scores=[1.0] * 3,
            usage_opportunities=10,
            scope_feedback_total=4,
            lag_days=[5.0],
            utility_accepted=5,
            utility_corrected=1,
        )
    )
    summary = summarize(values)
    assert "score" not in summary and "percentage" not in json.dumps(summary).lower()
    assert set(summary["dimensions"]) == {dim.value for dim in ALL_DIMENSIONS}
    assert summary["overall"]["ok_dimensions"] + summary["overall"]["unknown_dimensions"] == 5
    # 证据不足面：五维全 unknown → overall 如实说
    empty = summarize(dimensions_from_inputs(WindowInputs()))
    assert empty["overall"]["evidence"] == "insufficient_evidence"


# ---------------------------------------------------------------------------
# 词表分区校验（不发明新动作名；分区漂移 → 红）
# ---------------------------------------------------------------------------


def test_scope_negatives_subset_of_scope_feedback():
    assert SCOPE_NEGATIVE_ACTIONS <= SCOPE_FEEDBACK_ACTIONS


def test_correctness_negatives_disjoint_from_scope_channel():
    """correctness 负动作与 scope 反馈通道不相交（一个动作只算一类信号）。"""
    assert not (CORRECTNESS_NEGATIVE_ACTIONS & SCOPE_FEEDBACK_ACTIONS)


def test_utility_decisive_disjoint_from_correctness_negatives():
    assert not (UTILITY_DECISIVE_ACTIONS & CORRECTNESS_NEGATIVE_ACTIONS)


def test_freshness_actions_are_state_changes_only():
    """freshness 面 = 撤回级否定 + 用户编辑更新；confirm/epoch_bump 不在内。"""
    assert "user_edit" in FRESHNESS_STATE_CHANGE_ACTIONS
    assert "user_update" in FRESHNESS_STATE_CHANGE_ACTIONS
    assert CORRECTNESS_NEGATIVE_ACTIONS <= FRESHNESS_STATE_CHANGE_ACTIONS
    assert "confirm" not in FRESHNESS_STATE_CHANGE_ACTIONS
    assert "epoch_bump" not in FRESHNESS_STATE_CHANGE_ACTIONS


def test_referenced_actions_exist_in_writer_vocabularies():
    """D-03 分区引用的每个动作名必须真实存在于写方词表（防引用幻觉）。

    写方词表全部从代码导入（不硬编码旁路）：
    - M-08 ``_USER_GOVERNANCE_ACTIONS``（retract/delete/reject/…/scope_*/user_edit*/user_update）；
    - ``MEMORY_REFERENCE_OUTCOMES`` → memory_reference_<outcome> 全族；
    - M-01 EPOCH_BUMP / NON_EPOCH 动作族（delete/reject/no_longer_applicable/
      lower_confidence/confirm/epoch_bump）。
    写方新增动作不进分区不影响本测试；分区引用了不存在的动作 → 红。
    """
    from app.services.memory_epistemic_contract import (
        EPOCH_BUMP_CORRECTION_ACTIONS,
        NON_EPOCH_CORRECTION_ACTIONS,
    )
    from app.services.memory_provenance_service import _USER_GOVERNANCE_ACTIONS
    from app.services.memory_service import MEMORY_REFERENCE_OUTCOMES

    known = (
        set(_USER_GOVERNANCE_ACTIONS)
        | {f"memory_reference_{outcome}" for outcome in MEMORY_REFERENCE_OUTCOMES}
        | set(EPOCH_BUMP_CORRECTION_ACTIONS)
        | set(NON_EPOCH_CORRECTION_ACTIONS)
        | {"epoch_bump"}
    )
    referenced = (
        CORRECTNESS_NEGATIVE_ACTIONS
        | SCOPE_FEEDBACK_ACTIONS
        | FRESHNESS_STATE_CHANGE_ACTIONS
        | UTILITY_DECISIVE_ACTIONS
    )
    unknown = referenced - known
    assert not unknown, f"D-03 references actions that no writer produces: {sorted(unknown)}"


def test_all_dimensions_order_frozen():
    assert [dim.value for dim in ALL_DIMENSIONS] == [
        "coverage",
        "correctness",
        "scope_precision",
        "freshness",
        "utility",
    ]
    assert len({dim.value for dim in ALL_DIMENSIONS}) == 5
