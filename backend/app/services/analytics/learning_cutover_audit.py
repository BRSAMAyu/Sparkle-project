from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.analytics.belief_trace_inspector import BeliefTraceInspector
from app.services.analytics.signal_inventory import ProductionSignalInventory


class LearningCutoverAuditor:
    """Combine real-data audits into one learning-readiness gate."""

    TRACE_PATTERN = "aurora:belief_trace:v1:*"

    def build_report(
        self,
        *,
        event_density: dict[str, Any] | None = None,
        trace_summary: dict[str, Any] | None = None,
        signal_inventory: dict[str, Any] | None = None,
        observation_firewall: dict[str, Any] | None = None,
        ope_gate: dict[str, Any] | None = None,
        sim_real_diagnostics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_inventory = signal_inventory or ProductionSignalInventory.configured_inventory()
        resolved_trace = trace_summary or {
            "total_traces": 0,
            "comparable_traces": 0,
            "observed_outcomes": 0,
            "outcome_coverage_rate": 0.0,
            "training_eligible_traces": 0,
            "disagreement_rate": 0.0,
        }
        resolved_density = event_density or {
            "counts": {},
            "readiness": {
                "observed_task_outcomes": 0,
                "labeled_route_outcomes": 0,
                "daily_task_outcomes": 0.0,
                "daily_labeled_route_outcomes": 0.0,
                "recommendation": "rules_plus_shadow_audit",
            },
        }
        recommendation = self.recommend(
            event_density=resolved_density,
            trace_summary=resolved_trace,
        )
        return {
            "schema_version": "learning_cutover_audit.v1",
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "recommendation": recommendation,
            "event_density": resolved_density,
            "trace_summary": resolved_trace,
            "signal_inventory": resolved_inventory,
            "observation_firewall": observation_firewall or {},
            "ope_gate": ope_gate or {},
            "sim_real_diagnostics": sim_real_diagnostics or {},
            "guardrails": [
                "Do not train final route policy on simulator reward alone.",
                "Do not enable Bandit/RL until real observed outcomes are dense enough.",
                "Use deterministic BeliefState routing while labels are sparse.",
                "Keep active probes bounded by VOI and probe fatigue.",
                "Use OPE on real labeled disagreement traces as the only production cutover gate.",
                "Treat sim-to-real distance as a diagnostic, not as proof of policy effectiveness.",
            ],
        }

    @staticmethod
    def recommend(*, event_density: dict[str, Any], trace_summary: dict[str, Any]) -> dict[str, Any]:
        readiness = event_density.get("readiness") if isinstance(event_density, dict) else {}
        observed_task_outcomes = int((readiness or {}).get("observed_task_outcomes") or 0)
        labeled_route_outcomes = int((readiness or {}).get("labeled_route_outcomes") or 0)
        total_traces = int(trace_summary.get("total_traces") or 0)
        comparable_traces = int(trace_summary.get("comparable_traces") or 0)
        observed_outcomes = int(trace_summary.get("observed_outcomes") or 0)
        outcome_coverage = float(trace_summary.get("outcome_coverage_rate") or 0.0)

        blockers: list[str] = []
        if total_traces == 0:
            blockers.append("no_belief_traces")
        if comparable_traces == 0:
            blockers.append("no_actual_vs_shadow_comparison")
        if observed_outcomes == 0 or outcome_coverage < 0.10:
            blockers.append("insufficient_observed_outcomes")

        if observed_task_outcomes >= 300 and labeled_route_outcomes >= 300 and outcome_coverage >= 0.35:
            route = "bandit_shadow_plus_rl_data_collection"
        elif observed_task_outcomes >= 50 and labeled_route_outcomes >= 50 and outcome_coverage >= 0.20:
            route = "contextual_bandit_shadow"
        else:
            route = "deterministic_belief_router"

        if "no_belief_traces" in blockers:
            route = "run_real_smoke_first"

        return {
            "route": route,
            "blockers": blockers,
            "observed_task_outcomes": observed_task_outcomes,
            "labeled_route_outcomes": labeled_route_outcomes,
            "trace_count": total_traces,
            "comparable_trace_count": comparable_traces,
            "outcome_coverage_rate": round(outcome_coverage, 4),
        }

    async def summarize_redis_traces(
        self,
        redis: Any,
        *,
        limit_per_user: int = 100,
        max_users: int = 100,
    ) -> dict[str, Any]:
        keys = await self._trace_keys(redis, max_users=max_users)
        raw_traces: list[Any] = []
        for key in keys:
            raw = await redis.lrange(key, 0, max(0, limit_per_user - 1))
            raw_traces.extend(list(raw or []))
        summary = BeliefTraceInspector().summarize(raw_traces)
        summary["redis_key_count"] = len(keys)
        summary["limit_per_user"] = limit_per_user
        return summary

    async def event_density_from_db(self, db: Any, *, days: int = 30) -> dict[str, Any]:
        from sqlalchemy import text

        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(1, days))
        queries = {
            "tasks_completed": ("tasks", "select count(*) from tasks where completed_at >= :since"),
            "tasks_abandoned": ("tasks", "select count(*) from tasks where status = 'ABANDONED' and updated_at >= :since"),
            "routing_labeled_outcomes": (
                "routing_decision_log",
                "select count(*) from routing_decision_log "
                "where decided_at >= :since and (outcome is not null or outcome_type is not null)",
            ),
        }
        counts: dict[str, int] = {}
        missing_tables: list[str] = []
        table_cache: dict[str, bool] = {}
        for key, (table_name, sql) in queries.items():
            if table_name not in table_cache:
                table_cache[table_name] = await self._table_exists(db, table_name)
            if not table_cache[table_name]:
                counts[key] = 0
                if table_name not in missing_tables:
                    missing_tables.append(table_name)
                continue
            result = await db.execute(text(sql), {"since": since})
            counts[key] = int(result.scalar_one() or 0)
        observed_task_outcomes = counts.get("tasks_completed", 0) + counts.get("tasks_abandoned", 0)
        return {
            "schema_version": "event_density_cutover.v1",
            "window_days": days,
            "since": since.isoformat(),
            "counts": counts,
            "missing_tables": missing_tables,
            "readiness": {
                "observed_task_outcomes": observed_task_outcomes,
                "labeled_route_outcomes": counts.get("routing_labeled_outcomes", 0),
                "daily_task_outcomes": round(observed_task_outcomes / max(1, days), 4),
                "daily_labeled_route_outcomes": round(counts.get("routing_labeled_outcomes", 0) / max(1, days), 4),
            },
        }

    async def _trace_keys(self, redis: Any, *, max_users: int) -> list[str]:
        if hasattr(redis, "scan_iter"):
            keys: list[str] = []
            async for key in redis.scan_iter(self.TRACE_PATTERN):
                keys.append(key.decode("utf-8") if isinstance(key, bytes) else str(key))
                if len(keys) >= max_users:
                    break
            return keys
        raw = await redis.keys(self.TRACE_PATTERN)
        return [
            key.decode("utf-8") if isinstance(key, bytes) else str(key)
            for key in list(raw or [])[:max_users]
        ]

    @staticmethod
    async def _table_exists(db: Any, table_name: str) -> bool:
        from sqlalchemy import text

        result = await db.execute(
            text(
                "select exists ("
                "select 1 from information_schema.tables "
                "where table_schema = current_schema() and table_name = :table_name"
                ")"
            ),
            {"table_name": table_name},
        )
        return bool(result.scalar_one())


def dumps_report(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, default=str)
