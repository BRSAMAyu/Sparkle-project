from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.planning_benchmark_service import (  # noqa: E402
    PLANNING_BENCHMARK_DIMENSIONS,
    PlanningBenchmarkHarness,
    PlanningBenchmarkRun,
    RAW_BASELINE_MODEL_KEYS,
)


DEFAULT_FIXTURE = REPO_ROOT / "backend" / "tests" / "fixtures" / "planning_benchmark_scenarios.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "verification" / "SPARKLE_PHASE_B_PLANNING_BENCHMARK_RESULTS_2026-04-05.json"


def _variant_label(variant: str, model_key: str) -> str:
    if variant == "sparkle_current":
        return f"sparkle_current:{model_key}"
    if variant == "sparkle_phase_b":
        return f"sparkle_phase_b:{model_key}"
    return f"raw_baseline:{model_key}"


def _blank_scorecard(run: PlanningBenchmarkRun) -> dict[str, Any]:
    excerpt = " ".join(line.strip() for line in run.output_text.splitlines()[:4] if line.strip())[:240]
    return {
        "scenario_id": run.scenario_id,
        "variant": run.variant,
        "model_key": run.model_key,
        "dimensions": {
            dimension: {
                "score": None,
                "notes": "",
                "evidence_excerpt": excerpt,
            }
            for dimension in PLANNING_BENCHMARK_DIMENSIONS
        },
    }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    harness = PlanningBenchmarkHarness()
    scenarios = harness.load_scenarios(args.fixture)
    if not scenarios:
        raise RuntimeError(f"No benchmark scenarios found in {args.fixture}")

    sparkle_model = args.sparkle_model
    runs: list[dict[str, Any]] = []
    scorecards: list[dict[str, Any]] = []

    for scenario in scenarios:
        current_run = await harness.run_prompt_variant(
            scenario=scenario,
            variant="sparkle_current",
            model_key=sparkle_model,
        )
        phase_b_run = await harness.run_prompt_variant(
            scenario=scenario,
            variant="sparkle_phase_b",
            model_key=sparkle_model,
        )
        baseline_runs = await harness.run_mixed_provider_baselines(scenario=scenario)

        all_runs = [current_run, phase_b_run, *baseline_runs]
        for run in all_runs:
            runs.append(run.to_dict())
            scorecards.append(_blank_scorecard(run))

    return {
        "fixture": str(args.fixture),
        "sparkle_model": sparkle_model,
        "baseline_models": list(RAW_BASELINE_MODEL_KEYS),
        "runs": runs,
        "scorecards": scorecards,
        "scenario_count": len(scenarios),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase B mixed-provider planning benchmark.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sparkle-model", default="dashscope_chat")
    args = parser.parse_args()

    payload = asyncio.run(_run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
