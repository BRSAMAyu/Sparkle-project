"""M-09 runner — deterministic CLI for the memory longitudinal/adversarial suite.

Usage (from ``backend/``)::

    SECRET_KEY=test python3.11 -m tests.memory_eval.runner                 # full suite + gate
    SECRET_KEY=test python3.11 -m tests.memory_eval.runner --case P01-D1-evening_plan
    SECRET_KEY=test python3.11 -m tests.memory_eval.runner --persona P03
    SECRET_KEY=test python3.11 -m tests.memory_eval.runner --mutation-selftest
    SECRET_KEY=test python3.11 -m tests.memory_eval.runner --real-model    # 5 key cases x 5 calls (<=25)

Determinism: user identities are uuid5-derived from case ids; the only wall
clock dependency is the relative timeline anchor (``EvalEnvironment.
run_started_at``), so repeated runs yield identical verdicts and metrics.
Output: machine-readable JSON on stdout (or ``--out path``), human summary on
stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .gate import build_machine_readable_report, evaluate_gate, mutation_selftest
from .grading import grade_case
from .harness import run_suite, write_traces_summary
from .memory_eval_schema import (
    DIMENSION_ORDER,
    SCHEMA_VERSION,
    coverage_report,
    load_suite,
)


async def run_evaluation(
    persona_filter: str | None = None,
    case_filter: str | None = None,
) -> dict[str, Any]:
    personas, cases = load_suite()
    if persona_filter:
        cases = [c for c in cases if c.persona_id == persona_filter]
    if case_filter:
        cases = [c for c in cases if c.case_id == case_filter]
    coverage = coverage_report(personas, load_suite()[1])  # coverage over the FULL suite always
    outcomes = await run_suite(None, cases)
    verdicts = [grade_case(o) for o in outcomes]
    gate = evaluate_gate(verdicts, personas, coverage)
    run_meta = {
        "schema_version": SCHEMA_VERSION,
        "seed_namespace": "uuid5(a5d0f7de-09c9-4f0a-9b6b-11f0e6d09c09, case_id)",
        "db": "sqlite+aiosqlite:///:memory: (isolated, one deterministic user per case)",
        "dimensions": list(DIMENSION_ORDER),
        "write_traces": {o.case_id: write_traces_summary(o) for o in outcomes},
    }
    return build_machine_readable_report(verdicts, gate, coverage, run_meta)


def _summary_line(report: dict[str, Any]) -> str:
    gate = report["gate"]
    metrics = gate["metrics"]
    return (
        f"gate={'PASS' if gate['passed'] else 'RED'} "
        f"cases={metrics['case_count']} failed={len(metrics['failed_case_ids'])} "
        f"invalid_use_total={metrics['invalid_use_total']} "
        f"overpersonalization_rate={metrics['overpersonalization']['rate']} "
        f"valid_use_precision={metrics['valid_use_precision']['precision']} "
        f"uplift_pp={metrics['uplift']['uplift_pp']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tests.memory_eval.runner")
    parser.add_argument("--persona", help="run a single persona (e.g. P03)")
    parser.add_argument("--case", help="run a single case (e.g. P01-D1-evening_plan)")
    parser.add_argument("--out", type=Path, help="write machine-readable JSON to this path")
    parser.add_argument("--mutation-selftest", action="store_true", help="gate non-vacuity proof")
    parser.add_argument("--real-model", action="store_true", help="5 key cases x 5 real model calls")
    args = parser.parse_args(argv)

    if args.mutation_selftest:

        async def _mutation() -> int:
            # run the suite once, then mutate one passing verdict
            personas, cases = load_suite()
            outcomes = await run_suite(None, cases)
            verdicts = [grade_case(o) for o in outcomes]
            evaluate_gate(verdicts, personas, coverage_report(personas, cases))
            result = mutation_selftest(verdicts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("gate_flipped") else 1

        return asyncio.run(_mutation())

    if args.real_model:
        from .real_model import run_real_model_probe

        result = asyncio.run(run_real_model_probe())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("majority_all_pass") else 1

    report = asyncio.run(run_evaluation(persona_filter=args.persona, case_filter=args.case))
    payload = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload)
    print(_summary_line(report), file=sys.stderr)
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
