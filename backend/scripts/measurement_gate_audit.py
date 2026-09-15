#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.analytics.belief_recovery_simulator import BeliefRecoverySimulator  # noqa: E402
from app.services.analytics.learning_cutover_audit import LearningCutoverAuditor, dumps_report  # noqa: E402
from app.services.analytics.observation_firewall import ObservationQualityFirewall  # noqa: E402
from app.services.analytics.ope_gatekeeper import OPEGatekeeper  # noqa: E402
from app.services.analytics.sim_real_diagnostics import SimRealDiagnostics  # noqa: E402


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def _redis_traces(*, limit_per_user: int, max_users: int) -> tuple[dict[str, Any] | None, list[Any]]:
    auditor = LearningCutoverAuditor()
    try:
        from app.core.cache import cache_service

        if cache_service.redis is None:
            await cache_service.init_redis()
        if cache_service.redis is None:
            return None, []
        summary = await auditor.summarize_redis_traces(
            cache_service.redis,
            limit_per_user=limit_per_user,
            max_users=max_users,
        )
        keys = await auditor._trace_keys(cache_service.redis, max_users=max_users)  # noqa: SLF001
        raw_traces: list[Any] = []
        for key in keys:
            raw = await cache_service.redis.lrange(key, 0, max(0, limit_per_user - 1))
            raw_traces.extend(list(raw or []))
        return summary, raw_traces
    except Exception as exc:
        return {
            "schema_version": "belief_trace_inspection.v1",
            "error": str(exc),
            "total_traces": 0,
            "comparable_traces": 0,
            "observed_outcomes": 0,
            "outcome_coverage_rate": 0.0,
        }, []


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run measurement gates for Sparkle routing learning.")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--skip-redis", action="store_true")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--trace-limit", type=int, default=100)
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--real-traces-json", help="Optional JSON list of raw trace dicts.")
    parser.add_argument("--sim-report-json", help="Optional BeliefRecoverySimulator report JSON.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    auditor = LearningCutoverAuditor()
    event_density = None
    trace_summary = None
    raw_traces: list[Any] = []

    loaded_traces = _load_json(args.real_traces_json)
    if isinstance(loaded_traces, list):
        raw_traces = loaded_traces
        from app.services.analytics.belief_trace_inspector import BeliefTraceInspector

        trace_summary = BeliefTraceInspector().summarize(raw_traces)
    elif not args.skip_redis:
        trace_summary, raw_traces = await _redis_traces(limit_per_user=args.trace_limit, max_users=args.max_users)

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

    sim_report = _load_json(args.sim_report_json)
    if not isinstance(sim_report, dict):
        sim_report = BeliefRecoverySimulator().run_batch(samples_per_archetype=1, steps=6, seed=17)

    firewall_report = ObservationQualityFirewall().evaluate(
        real_trace_summary=trace_summary or {},
        simulation_summary=sim_report,
    ).to_dict()
    ope_report = OPEGatekeeper().evaluate(raw_traces).to_dict()

    real_vectors = SimRealDiagnostics.vectors_from_traces(raw_traces)
    sim_vectors = SimRealDiagnostics.vectors_from_simulation_steps(sim_report.get("sample_steps", []))
    sim_real_report = (
        SimRealDiagnostics().evaluate(real_vectors=real_vectors, sim_vectors=sim_vectors).to_dict()
        if real_vectors and sim_vectors
        else {
            "schema_version": "sim_real_diagnostics.v1",
            "warnings": ["insufficient_real_or_sim_vectors"],
            "caveat": "W2 measures distribution distance only; it is not a policy-effectiveness proof.",
        }
    )
    report = auditor.build_report(
        event_density=event_density,
        trace_summary=trace_summary,
        observation_firewall=firewall_report,
        ope_gate=ope_report,
        sim_real_diagnostics=sim_real_report,
    )

    if args.json:
        print(dumps_report(report))
        return 0

    recommendation = report["recommendation"]
    print(f"Recommended route: {recommendation['route']}")
    print(f"Blockers: {recommendation['blockers']}")
    print(f"Observation firewall: {firewall_report['recommendation']} passed={firewall_report['passed']}")
    print(f"OPE: {ope_report['recommendation']} labeled={ope_report['labeled_divergence_points']}")
    print(f"Sim-real warnings: {sim_real_report.get('warnings', [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
