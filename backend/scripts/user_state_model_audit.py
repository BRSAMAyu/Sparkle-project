#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.analytics.user_state_model_audit import UserStateModelAuditor  # noqa: E402


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run batch self-checks for UserStateModel dynamics.")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = UserStateModelAuditor().run(samples_per_archetype=args.samples, steps=args.steps, seed=args.seed)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"Samples per archetype: {report['samples_per_archetype']}")
    print(f"Steps: {report['steps']}")
    for key, summary in report["summaries"].items():
        print(
            f"{key}: collapse={summary['collapse_rate']:.2%} "
            f"abandon={summary['abandon_rate']:.2%} complete={summary['completion_rate']:.2%} "
            f"consistency_fail={summary['consistency_failure_rate']:.2%}"
        )
    if report["warnings"]:
        print("\nWarnings:")
        for item in report["warnings"]:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
