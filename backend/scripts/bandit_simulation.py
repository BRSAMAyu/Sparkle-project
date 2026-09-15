#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.analytics.contextual_bandit import BanditSimulationRunner  # noqa: E402


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run simulator-only Contextual Thompson Bandit prototype.")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--fusion-model", choices=("independent", "block_diagonal"), default="independent")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = BanditSimulationRunner(seed=args.seed, fusion_model=args.fusion_model).run(
        episodes_per_archetype=args.episodes,
        steps=args.steps,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"Episodes: {report['episodes']} | Steps: {report['steps']}")
    print(f"Fusion model: {report['fusion_model']}")
    print(f"Average simulated reward: {report['average_reward']:.6f}")
    print(f"Arm counts: {report['arm_counts']}")
    print(f"Outcomes: {report['outcome_counts']}")
    print(report["warning"])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
