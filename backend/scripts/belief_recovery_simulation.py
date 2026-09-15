#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.analytics.belief_recovery_simulator import (  # noqa: E402
    BeliefRecoverySimulator,
    ObservationModelConfig,
)


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Run numeric wind-tunnel simulation for Evidence -> FusionEngine -> BeliefState -> Router.",
    )
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--policy", default="router")
    parser.add_argument("--fusion-model", choices=("independent", "block_diagonal"), default="independent")
    parser.add_argument("--compare-fusion-models", action="store_true")
    parser.add_argument("--noise-sigma", type=float, default=0.08)
    parser.add_argument("--confidence", type=float, default=0.76)
    parser.add_argument("--missing-rate", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    simulator = BeliefRecoverySimulator(
        observation_config=ObservationModelConfig(
            noise_sigma=args.noise_sigma,
            confidence=args.confidence,
            missing_rate=args.missing_rate,
        ),
        fusion_model=args.fusion_model,
    )
    if args.compare_fusion_models:
        reports = {
            model: simulator.run_batch(
                samples_per_archetype=args.samples,
                steps=args.steps,
                seed=args.seed,
                policy=args.policy,
                fusion_model=model,
            )
            for model in ("independent", "block_diagonal")
        }
        report = {
            "schema_version": "belief_recovery_fusion_comparison.v1",
            "reports": reports,
            "mse_delta_block_minus_independent": round(
                reports["block_diagonal"]["overall_mse"] - reports["independent"]["overall_mse"],
                6,
            ),
            "mae_delta_block_minus_independent": round(
                reports["block_diagonal"]["overall_mae"] - reports["independent"]["overall_mae"],
                6,
            ),
        }
    else:
        report = simulator.run_batch(
            samples_per_archetype=args.samples,
            steps=args.steps,
            seed=args.seed,
            policy=args.policy,
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    if args.compare_fusion_models:
        print("Fusion model comparison:")
        for model, item in report["reports"].items():
            print(f"- {model}: mse={item['overall_mse']:.6f} mae={item['overall_mae']:.6f}")
        print(f"MSE delta block-independent: {report['mse_delta_block_minus_independent']:.6f}")
        print(f"MAE delta block-independent: {report['mae_delta_block_minus_independent']:.6f}")
        return 0

    print(f"Policy: {report['policy']}")
    print(f"Fusion model: {report['fusion_model']}")
    print(f"Runs: {report['run_count']} | Steps: {report['step_count']}")
    print(f"Overall MSE: {report['overall_mse']:.6f}")
    print(f"Overall MAE: {report['overall_mae']:.6f}")
    print(f"Route modes: {report['route_mode_counts']}")
    print(f"Outcomes: {report['outcome_counts']}")
    print("\nPer-target error:")
    for target, metrics in report["per_target"].items():
        print(
            f"- {target}: mse={metrics['mse']:.6f} "
            f"mae={metrics['mae']:.6f} bias={metrics['bias']:.6f}"
        )
    if report["warnings"]:
        print("\nWarnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
