#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.cache import cache_service  # noqa: E402
from app.services.analytics.belief_trace_inspector import BeliefTraceInspector  # noqa: E402


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Aurora belief shadow traces for one user.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    if cache_service.redis is None:
        await cache_service.init_redis()
    redis = cache_service.redis
    if redis is None:
        print("Redis is not configured", file=sys.stderr)
        return 2

    summary = await BeliefTraceInspector().summarize_redis(redis, user_id=args.user_id, limit=args.limit)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"Redis key: {summary['redis_key']}")
    print(f"Total traces: {summary['total_traces']}")
    print(f"Comparable traces: {summary['comparable_traces']}")
    print(f"Disagreements: {summary['disagreements']} ({summary['disagreement_rate']:.2%})")
    print(f"Observed outcomes: {summary['observed_outcomes']} ({summary['outcome_coverage_rate']:.2%})")
    print(f"Training eligible: {summary['training_eligible_traces']} ({summary['training_eligible_rate']:.2%})")
    print(f"Actual modes: {summary['actual_mode_counts']}")
    print(f"Shadow modes: {summary['shadow_mode_counts']}")
    print(f"Disagreement types: {summary['disagreement_type_counts']}")
    print(f"Outcomes: {summary['outcome_counts']}")
    print(f"Reward signals: {summary['reward_signal_counts']}")
    print(f"Reward categories: {summary.get('reward_category_counts', {})}")
    print(f"Average reward: {summary['average_total_reward']}")
    print(f"Average evidence per trace: {summary.get('average_evidence_per_trace', 0.0)}")
    print(f"Trace evidence coverage: {summary.get('trace_evidence_coverage_rate', 0.0):.2%}")
    print(
        "LLM evidence rate: "
        f"{summary.get('llm_evidence_rate', 0.0):.2%}; "
        f"fallback evidence rate: {summary.get('heuristic_fallback_evidence_rate', 0.0):.2%}"
    )
    print(f"F1 quality gate: {summary.get('f1_quality_gate', {})}")
    print(f"Average belief means: {summary.get('average_belief_mean_by_target', {})}")
    print(f"Evidence sources: {summary['evidence_source_counts']}")
    print(f"Target evidence counts: {summary['target_evidence_counts']}")
    print(f"High uncertainty targets: {summary['high_uncertainty_targets']}")
    if summary["missing_field_counts"]:
        print(f"Missing fields: {summary['missing_field_counts']}")
    if summary["examples"]:
        print("\nExamples:")
        for item in summary["examples"]:
            print(
                "- "
                f"{item.get('timestamp')} actual={item.get('actual_router_mode')} "
                f"shadow={item.get('shadow_mode')} type={item.get('disagreement_type')} "
                f"support={item.get('support_pressure_score')} readiness={item.get('execution_readiness_score')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
