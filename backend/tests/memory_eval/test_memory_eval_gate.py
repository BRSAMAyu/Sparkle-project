"""M-09 gate guards — pytest assertions over the evaluation suite.

What these tests enforce (and what they deliberately do NOT):

1. Schema/coverage floor: >=80 cases, 10 personas, every (persona x dimension)
   cell covered, every case multi-session, schema vocabularies frozen.
2. The full suite runs against the REAL merged memory chain on isolated
   sqlite and produces machine-readable results with the three paired
   metrics correctly computed.
3. GATE SIGNATURE: the gate enforces GREEN since V3-FIX-35/36 (registered
   bug fixed: the Stage20 resolver used to resurrect superseded preference
   values — see v3-output/M-09/REPORT.md 产品bug登记 and
   v3-output/V3-FIX-35-36/REPORT.md). Any failing case makes this test red:
   new chain regressions and case drift are both caught. Should a product
   bug need temporary registration again, populate REGISTERED_BUG_CASE_IDS
   in its fixing card and keep the set EXACTLY equal to the failing set.
4. Mutation self-tests (non-vacuity): one injected invalid-use marker MUST
   surface as a named failing case — proven both on real run results and on
   an all-green synthetic baseline.
5. Real-model artifact integrity: the committed 5x5 stability report exists,
   has <=25 calls recorded, majority verdicts computed (no live network here
   — live re-run is ``python -m tests.memory_eval.runner --real-model``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.memory_eval.gate import evaluate_gate, mutation_selftest
from tests.memory_eval.grading import CaseVerdict, grade_case
from tests.memory_eval.harness import run_suite
from tests.memory_eval.memory_eval_schema import (
    DIMENSIONS,
    MIN_TOTAL_CASES,
    REQUIRED_PERSONA_COUNT,
    coverage_report,
    load_suite,
)

HERE = Path(__file__).parent
REAL_MODEL_ARTIFACT = HERE / "real_model_stability_report.json"

# REGISTERED PRODUCT BUG REGISTRY — EMPTY since V3-FIX-35+FIX-36 (2026-09-20).
# Historical record (do not repopulate without a fixing card): the 20-case
# signature below was the Stage20 supersede-resurrection bug —
# ContextPackBuilder.build -> MemoryConflictResolver.resolve_preferences
# picked winners from the full unfiltered preference history by
# (evidence_score, updated_at, confidence), ignoring replaced_by_id, while
# M-07's supersede branch bumped the OLD row's updated_at (commit 0ea1e198)
# so the superseded value outranked the chain head -> pack.preferences
# returned the OLD value on every same-evidence-channel preference update.
# Fixed chain-aware in _pick_preference_winner + precise head/old shared
# supersede instant in upsert_preference + M-05 CJK domain glosses for the
# two residual relevance-downgrade cases (P09-D5/P10-D3).
REGISTERED_BUG_CASE_IDS = frozenset()

_OUTCOMES_CACHE: list = []
_VERDICTS_CACHE: list[CaseVerdict] = []


async def _outcomes() -> list:
    if not _OUTCOMES_CACHE:
        personas, cases = load_suite()
        assert personas and cases
        _OUTCOMES_CACHE.extend(await run_suite(None, cases))
    return _OUTCOMES_CACHE


async def _verdicts() -> list[CaseVerdict]:
    if not _VERDICTS_CACHE:
        _VERDICTS_CACHE.extend(grade_case(o) for o in await _outcomes())
    return _VERDICTS_CACHE


def _coverage() -> dict:
    personas, cases = load_suite()
    return coverage_report(personas, cases)


@pytest.mark.asyncio
async def test_schema_frozen_and_coverage_floor():
    personas, cases = load_suite()
    assert len(personas) == REQUIRED_PERSONA_COUNT
    assert len(cases) >= MIN_TOTAL_CASES
    report = _coverage()
    assert report["meets_minimum"], report
    assert report["matrix_holes"] == []
    assert report["all_multi_session"]
    assert report["cases_per_dimension"].keys() == DIMENSIONS
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids))
    assert all(c.expectations.must_use or c.expectations.must_not_use for c in cases)
    key_cases = [c for c in cases if c.real_model.key_case]
    assert len(key_cases) == 5
    assert {c.dimension for c in key_cases} == set(DIMENSIONS)


@pytest.mark.asyncio
async def test_full_suite_gate_signature():
    """Gate is RED with EXACTLY the registered product-bug failure set."""
    personas, _ = load_suite()
    verdicts = await _verdicts()
    gate = evaluate_gate(verdicts, personas, _coverage())
    metrics = gate.metrics

    failing = set(metrics["failed_case_ids"])
    assert failing == set(REGISTERED_BUG_CASE_IDS), (
        f"gate failure set drifted from the registered bug signature.\n"
        f"unexpected failures: {sorted(failing - set(REGISTERED_BUG_CASE_IDS))}\n"
        f"registered-but-passing (bug fixed? update REGISTERED_BUG_CASE_IDS "
        f"via the fixing card): {sorted(set(REGISTERED_BUG_CASE_IDS) - failing)}"
    )
    for verdict in verdicts:
        if verdict.case_id in REGISTERED_BUG_CASE_IDS:
            assert verdict.must_use_missing or verdict.invalid_use_markers
    non_bug_fails = [v for v in verdicts if not v.passed and v.case_id not in REGISTERED_BUG_CASE_IDS]
    assert non_bug_fails == []
    # failure is never averaged away: every failing case id is listed
    assert sorted(metrics["failure_breakdown"]["invalid_use"]) == sorted(
        v.case_id for v in verdicts if v.invalid_use_markers
    )


@pytest.mark.asyncio
async def test_three_metrics_computed_correctly():
    verdicts = await _verdicts()
    metrics = evaluate_gate(verdicts, personas=None).metrics

    invalid_total = sum(len(v.invalid_use_markers) for v in verdicts)
    assert metrics["invalid_use_total"] == invalid_total
    # Gate enforces green since V3-FIX-35/36: zero invalid use suite-wide
    # (the supersede-resurrection bug that made this > 0 is fixed).
    assert metrics["invalid_use_total"] == 0

    precision = metrics["valid_use_precision"]
    recomputed = precision["valid_items"] / (precision["valid_items"] + precision["invalid_items"])
    assert abs(precision["precision"] - round(recomputed, 4)) < 1e-9

    uplift = metrics["uplift"]
    assert uplift["eligible_cases"] > 0
    assert uplift["uplift_pp"] == round(
        (uplift["with_memory_personalized_rate"] - uplift["no_history_personalized_rate"]) * 100,
        2,
    )
    # No-history arm must never carry personalization the user never stated.
    assert uplift["no_history_personalized_rate"] == 0.0

    op = metrics["overpersonalization"]
    assert op["watched_probes"] >= 10  # every persona contributes a watched probe
    assert op["events"] == sum(1 for v in verdicts if v.overpersonalized)


@pytest.mark.asyncio
async def test_paired_baseline_records_both_arms():
    for outcome in await _outcomes():
        assert outcome.with_memory is not None, outcome.case_id
        assert outcome.no_history is not None, outcome.case_id
    verdicts = await _verdicts()
    uplift_eligible = [v for v in verdicts if v.uplift_positive is not None]
    assert len(uplift_eligible) >= 20
    assert any(v.uplift_positive for v in uplift_eligible)


@pytest.mark.asyncio
async def test_mutation_injected_invalid_use_is_named_by_gate():
    """Acceptance (变异必红): construct an invalid-use result -> the gate
    must name that case in its failure breakdown, with the count rising —
    proved on REAL run verdicts (baseline-red notwithstanding)."""
    verdicts = await _verdicts()
    baseline = evaluate_gate(verdicts, personas=None)
    doctored = copy.deepcopy(verdicts)
    victim = next(v for v in doctored if v.passed)
    victim.invalid_use_markers = ["MUTATION-INJECTED-FORBIDDEN-MARKER"]
    victim.surfaced_invalid_items += 1
    victim.passed = False
    mutated = evaluate_gate(doctored, personas=None)

    assert not mutated.passed
    assert victim.case_id in mutated.metrics["failed_case_ids"]
    assert victim.case_id in mutated.metrics["failure_breakdown"]["invalid_use"]
    assert mutated.metrics["invalid_use_total"] == baseline.metrics["invalid_use_total"] + 1
    assert "invalid_use_zero" in mutated.failing_checks()


def test_mutation_selftest_on_green_baseline():
    """Mutation non-vacuity on an all-green synthetic baseline: gate flips."""
    green = [
        CaseVerdict(
            case_id=f"SYN-{i}-pass",
            persona_id="SYN",
            dimension="D1_valid_use",
            passed=True,
            surfaced_valid_items=2,
        )
        for i in range(3)
    ]
    assert evaluate_gate(green, coverage={"meets_minimum": True, "persona_count": 10, "case_count": 80}).passed
    result = mutation_selftest(green)
    assert result["gate_flipped"] is True, result
    assert "all_cases_pass_per_case_verdict" in result["mutated_failed_checks"]
    assert "invalid_use_zero" in result["mutated_failed_checks"]


def test_real_model_artifact_integrity():
    """The committed 5x5 real-model stability report is complete: 5 key cases,
    5 runs each, <=25 calls, majority verdicts, no secrets."""
    assert REAL_MODEL_ARTIFACT.is_file(), (
        "real_model_stability_report.json missing — run "
        "`SECRET_KEY=test python3.11 -m tests.memory_eval.runner --real-model` "
        "and register the artifact"
    )
    payload = json.loads(REAL_MODEL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["key_cases_expected"] == 5
    assert payload["calls_used"] <= payload["max_calls"] == 25
    assert "api_key" not in json.dumps(payload)
    cases = [c for c in payload["cases"] if "runs" in c]
    assert len(cases) == 5
    for case in cases:
        assert len(case["runs"]) == 5
        assert "majority_pass" in case and "stability" in case
        for run in case["runs"]:
            assert {"answer", "passed", "latency_s"} <= set(run)
    assert "majority_all_pass" in payload
