#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.analytics.learning_cutover_audit import LearningCutoverAuditor, dumps_report  # noqa: E402


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run Sparkle learning cutover readiness audit.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--trace-limit", type=int, default=100)
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--skip-redis", action="store_true")
    args = parser.parse_args()

    auditor = LearningCutoverAuditor()
    event_density = None
    trace_summary = None

    if not args.skip_db:
        try:
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                event_density = await auditor.event_density_from_db(db, days=args.days)
        except Exception as exc:
            event_density = {
                "schema_version": "event_density_cutover.v1",
                "error": str(exc),
                "readiness": {
                    "observed_task_outcomes": 0,
                    "labeled_route_outcomes": 0,
                    "daily_task_outcomes": 0.0,
                    "daily_labeled_route_outcomes": 0.0,
                },
            }

    if not args.skip_redis:
        try:
            from app.core.cache import cache_service

            if cache_service.redis is None:
                await cache_service.init_redis()
            if cache_service.redis is not None:
                trace_summary = await auditor.summarize_redis_traces(
                    cache_service.redis,
                    limit_per_user=args.trace_limit,
                    max_users=args.max_users,
                )
        except Exception as exc:
            trace_summary = {
                "schema_version": "belief_trace_inspection.v1",
                "error": str(exc),
                "total_traces": 0,
                "comparable_traces": 0,
                "observed_outcomes": 0,
                "outcome_coverage_rate": 0.0,
                "training_eligible_traces": 0,
            }

    report = auditor.build_report(event_density=event_density, trace_summary=trace_summary)
    if args.json:
        print(dumps_report(report))
        return 0

    recommendation = report["recommendation"]
    print(f"Recommended route: {recommendation['route']}")
    print(f"Blockers: {recommendation['blockers']}")
    print(f"Trace count: {recommendation['trace_count']}")
    print(f"Comparable traces: {recommendation['comparable_trace_count']}")
    print(f"Observed task outcomes: {recommendation['observed_task_outcomes']}")
    print(f"Labeled route outcomes: {recommendation['labeled_route_outcomes']}")
    print(f"Outcome coverage: {recommendation['outcome_coverage_rate']:.2%}")
    print("\nGuardrails:")
    for guardrail in report["guardrails"]:
        print(f"- {guardrail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
