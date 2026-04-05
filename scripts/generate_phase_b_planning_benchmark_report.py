from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.planning_benchmark_evaluator import PlanningBenchmarkEvaluator  # noqa: E402
from app.services.planning_benchmark_service import (  # noqa: E402
    PlanningBenchmarkHarness,
    PlanningBenchmarkRun,
)


DEFAULT_FIXTURE = REPO_ROOT / "backend" / "tests" / "fixtures" / "planning_benchmark_scenarios.json"
DEFAULT_RESULTS = REPO_ROOT / "docs" / "verification" / "SPARKLE_PHASE_B_PLANNING_BENCHMARK_RESULTS_2026-04-05.json"
DEFAULT_SCORED_JSON = REPO_ROOT / "docs" / "verification" / "SPARKLE_PHASE_B_PLANNING_BENCHMARK_SCORECARDS_2026-04-05.json"
DEFAULT_REPORT = REPO_ROOT / "docs" / "verification" / "SPARKLE_PHASE_B_PLANNING_BENCHMARK_REPORT_2026-04-05.md"


def _as_runs(raw_runs: list[dict[str, Any]]) -> list[PlanningBenchmarkRun]:
    runs: list[PlanningBenchmarkRun] = []
    for item in raw_runs:
        if not isinstance(item, dict):
            continue
        runs.append(
            PlanningBenchmarkRun(
                scenario_id=str(item.get("scenario_id") or "").strip(),
                variant=str(item.get("variant") or "").strip(),
                model_key=str(item.get("model_key") or "").strip(),
                prompt=str(item.get("prompt") or ""),
                output_text=str(item.get("output_text") or ""),
            )
        )
    return runs


def _build_markdown_report(
    *,
    results_path: Path,
    fixture_path: Path,
    evaluation: dict[str, Any],
) -> str:
    variant_summary = evaluation.get("variant_summary", {})
    scenario_outcomes = evaluation.get("scenario_outcomes", [])
    phase_b_vs_field = evaluation.get("phase_b_vs_field", {})
    credible = bool(evaluation.get("credible_win_profile"))

    lines = [
        "# Sparkle Phase B Planning Benchmark Report",
        "",
        "> Date: 2026-04-05  ",
        f"> Fixture: `{fixture_path}`  ",
        f"> Raw results: `{results_path}`  ",
        f"> Proof level: `{evaluation.get('proof_level', 'benchmark_v1')}`  ",
        f"> Human eval required: `{'yes' if evaluation.get('human_eval_required') else 'no'}`",
        "",
        "## Completion Verdict",
        "",
        f"- Credible win profile: `{'yes' if credible else 'no'}`",
        f"- Phase B vs field: `{phase_b_vs_field.get('wins', 0)} wins / {phase_b_vs_field.get('ties', 0)} ties / {phase_b_vs_field.get('losses', 0)} losses`",
        "- Tie margin: `0.01` overall-score points",
        "",
        "## Variant Summary",
        "",
        "| Variant | Average overall score | Scenario count |",
        "| --- | ---: | ---: |",
    ]
    for label, summary in variant_summary.items():
        lines.append(
            f"| `{label}` | {summary.get('average_overall_score', 0.0):.4f} | {summary.get('scenario_count', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Scenario Outcomes",
            "",
            "| Scenario | Winner | Winner score | Phase B outcome |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for item in scenario_outcomes:
        lines.append(
            f"| `{item.get('scenario_id', '')}` | `{item.get('winner', '')}` | {float(item.get('winner_score', 0.0)):.4f} | `{item.get('phase_b_outcome', '')}` |"
        )

    lines.extend(["", "## Notes", ""])
    if credible:
        lines.append("- Phase B clears the benchmark bar: it leads the field on average and wins a majority of dossier comparisons.")
    else:
        lines.append("- Phase B is implemented and benchmarked, but the proof bar is not yet satisfied because the scored comparison does not show a clear majority win profile.")
    lines.append("- Scores are rubric-based deterministic evaluations over the live model outputs captured in the raw results artifact.")
    lines.append("- This benchmark is proof v1: an automated regression and comparative signal, not the final source of product truth.")
    lines.append("- Sparkle Phase B is compared as a system-level planning stack with compiled strategy shaping; the raw baselines remain direct dossier prompts.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the Phase B planning benchmark and generate a report.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--scored-json", type=Path, default=DEFAULT_SCORED_JSON)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    harness = PlanningBenchmarkHarness()
    scenarios = harness.load_scenarios(args.fixture)
    raw = json.loads(args.results.read_text(encoding="utf-8"))
    evaluator = PlanningBenchmarkEvaluator()
    evaluation = evaluator.evaluate_results(scenarios=scenarios, runs=_as_runs(raw.get("runs", [])))

    args.scored_json.parent.mkdir(parents=True, exist_ok=True)
    args.scored_json.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
    args.report.write_text(
        _build_markdown_report(results_path=args.results, fixture_path=args.fixture, evaluation=evaluation),
        encoding="utf-8",
    )
    print(args.scored_json)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
