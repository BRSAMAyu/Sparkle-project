"""M-09 regression gate — failure is never masked by averages.

Structure:

- EVERY case must pass its own dimension verdict (any invalid-use marker,
  any missing must_use marker, any overpersonalization event, any harness
  error -> that case id is listed and the gate is red).
- Coverage floor: >=80 cases, 10 personas, every (persona x dimension) cell
  >=1 case, every case multi-session (>=2 sessions).
- Aggregate thresholds (they can only TIGHTEN the verdict, never loosen it):
  invalid_use_total == 0; overpersonalization rate <= 5%; valid-use
  precision >= 95%. Uplift is reported (target +15pp per
  PERSONALIZATION_EVAL.md) but non-gating — real numbers are reported as-is.
- Mutation self-test (non-vacuity proof): a doctored verdict carrying one
  invalid-use marker MUST flip the gate red. Wired into the pytest guard and
  the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .grading import CaseVerdict, aggregate
from .memory_eval_schema import Persona

GATE_VERSION = "m09-memory-eval-gate.v1"

INVALID_USE_MAX = 0
OVERPERSONALIZATION_RATE_MAX = 0.05
VALID_USE_PRECISION_MIN = 0.95
UPLIFT_TARGET_PP = 15.0  # non-gating target (report real numbers)


@dataclass
class GateReport:
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)

    def failing_checks(self) -> list[str]:
        return [c["name"] for c in self.checks if not c["passed"]]

    def to_payload(self) -> dict[str, Any]:
        return {
            "gate_version": GATE_VERSION,
            "passed": self.passed,
            "checks": self.checks,
            "metrics": self.metrics,
            "coverage": self.coverage,
        }


def _check(name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def evaluate_gate(
    verdicts: list[CaseVerdict],
    personas: list[Persona] | None = None,
    coverage: dict[str, Any] | None = None,
) -> GateReport:
    metrics = aggregate(verdicts)
    coverage_payload = coverage  # supplied by caller (schema-level, pre-run)

    checks: list[dict[str, Any]] = []

    # 1. per-case verdicts — the anti-averaging core
    failed_ids = metrics["failed_case_ids"]
    checks.append(
        _check(
            "all_cases_pass_per_case_verdict",
            not failed_ids,
            {
                "failed": failed_ids,
                "breakdown": metrics["failure_breakdown"],
            },
        )
    )

    # 2. coverage floor
    checks.append(
        _check(
            "coverage_floor",
            bool(coverage_payload.get("meets_minimum")) if coverage_payload else False,
            {
                "persona_count": coverage_payload.get("persona_count") if coverage_payload else 0,
                "case_count": coverage_payload.get("case_count") if coverage_payload else 0,
                "matrix_holes": coverage_payload.get("matrix_holes") if coverage_payload else [],
                "all_multi_session": coverage_payload.get("all_multi_session") if coverage_payload else False,
            },
        )
    )

    # 3. invalid use hard zero
    checks.append(
        _check(
            "invalid_use_zero",
            metrics["invalid_use_total"] <= INVALID_USE_MAX,
            {
                "total": metrics["invalid_use_total"],
                "cases": metrics["failure_breakdown"]["invalid_use"],
            },
        )
    )

    # 4. overpersonalization <= 5%
    op = metrics["overpersonalization"]
    checks.append(
        _check(
            "overpersonalization_rate_le_5pct",
            op["rate"] <= OVERPERSONALIZATION_RATE_MAX,
            op,
        )
    )

    # 5. valid-use precision >= 95%
    precision = metrics["valid_use_precision"]
    checks.append(
        _check(
            "valid_use_precision_ge_95pct",
            precision["precision"] >= VALID_USE_PRECISION_MIN,
            precision,
        )
    )

    report = GateReport(
        passed=all(c["passed"] for c in checks),
        checks=checks,
        metrics=metrics,
        coverage=coverage_payload or {},
    )
    return report


def mutation_selftest(verdicts: list[CaseVerdict]) -> dict[str, Any]:
    """Non-vacuity proof: inject ONE invalid-use marker into a passing
    verdict; the gate MUST name that case and count the extra invalid use.

    Two modes, both proving the same property (an invalid use can never be
    averaged away):
    - green baseline -> the gate flips red;
    - red baseline (today: the registered product bug) -> the mutated case
      joins the named failure set with invalid_use_total rising by exactly 1
      and ``invalid_use_zero`` still failing.

    The coverage floor is orthogonal to the mutation proof, so both the
    baseline and mutated evaluations run with a satisfied-coverage payload."""
    if not verdicts:
        return {"gate_flipped": False, "reason": "no verdicts to mutate"}
    _coverage = {"meets_minimum": True, "persona_count": 10, "case_count": 80}
    base = evaluate_gate(verdicts, coverage=_coverage)

    import copy

    doctored = copy.deepcopy(verdicts)
    victim = next((v for v in doctored if v.passed), None)
    if victim is None:
        return {"gate_flipped": False, "reason": "no passing verdict to mutate"}
    victim.invalid_use_markers = (
        [victim.invalid_use_markers[0]] if victim.invalid_use_markers else ["MUTATION-INJECTED-FORBIDDEN-MARKER"]
    )
    victim.surfaced_invalid_items += 1
    victim.passed = False
    mutated = evaluate_gate(doctored, coverage=_coverage)
    caught = (
        (not mutated.passed)
        and victim.case_id in mutated.metrics["failed_case_ids"]
        and victim.case_id in mutated.metrics["failure_breakdown"]["invalid_use"]
        and mutated.metrics["invalid_use_total"] == base.metrics["invalid_use_total"] + 1
        and "invalid_use_zero" in mutated.failing_checks()
    )
    if base.passed:
        flipped = caught and "all_cases_pass_per_case_verdict" in mutated.failing_checks()
        mode = "green_baseline_flip"
    else:
        flipped = caught
        mode = "red_baseline_detection"
    return {
        "gate_flipped": flipped,
        "mode": mode,
        "mutated_case_id": victim.case_id,
        "injected_marker": victim.invalid_use_markers[0],
        "baseline_invalid_total": base.metrics["invalid_use_total"],
        "mutated_invalid_total": mutated.metrics["invalid_use_total"],
        "mutated_failed_checks": mutated.failing_checks(),
    }


def build_machine_readable_report(
    verdicts: list[CaseVerdict],
    gate: GateReport,
    coverage: dict[str, Any],
    run_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "gate": gate.to_payload(),
        "coverage": coverage,
        "per_case": [v.to_row() for v in verdicts],
        "run_meta": run_meta or {},
    }
