#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _readiness(counts: dict[str, Any], days: int) -> dict[str, Any]:
    observed_task_outcomes = int(counts.get("tasks_completed", 0)) + int(counts.get("tasks_abandoned", 0))
    labeled_route_outcomes = int(counts.get("routing_labeled_outcomes", 0))
    daily_task_outcomes = observed_task_outcomes / max(1, days)
    daily_labeled_routes = labeled_route_outcomes / max(1, days)
    if observed_task_outcomes < 50 or labeled_route_outcomes < 50:
        recommendation = "rules_plus_shadow_audit"
    elif observed_task_outcomes < 300 or labeled_route_outcomes < 300:
        recommendation = "contextual_bandit_cautious"
    else:
        recommendation = "bandit_ready_rl_not_yet"
    return {
        "observed_task_outcomes": observed_task_outcomes,
        "labeled_route_outcomes": labeled_route_outcomes,
        "daily_task_outcomes": round(daily_task_outcomes, 3),
        "daily_labeled_route_outcomes": round(daily_labeled_routes, 3),
        "recommendation": recommendation,
        "notes": [
            "Do not train RL from sparse 7-day North-Star outcomes alone.",
            "Use task outcomes and explicit corrections as short-horizon labels first.",
            "Only consider RL once route-level labels and retention outcomes are dense enough for stable OPE.",
        ],
    }


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


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Audit real event density for Bandit/RL readiness.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from app.db.session import AsyncSessionLocal

    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(1, args.days))
    queries = {
        "tasks_created": ("tasks", "select count(*) from tasks where created_at >= :since"),
        "tasks_completed": ("tasks", "select count(*) from tasks where completed_at >= :since"),
        "tasks_abandoned": ("tasks", "select count(*) from tasks where status = 'ABANDONED' and updated_at >= :since"),
        "task_feedbacks": ("task_feedbacks", "select count(*) from task_feedbacks where created_at >= :since"),
        "routing_decisions": ("routing_decision_log", "select count(*) from routing_decision_log where decided_at >= :since"),
        "routing_labeled_outcomes": (
            "routing_decision_log",
            "select count(*) from routing_decision_log "
            "where decided_at >= :since and (outcome is not null or outcome_type is not null)",
        ),
        "behavioral_outcomes": ("behavioral_outcomes", "select count(*) from behavioral_outcomes where timestamp >= :since"),
        "active_task_users": ("tasks", "select count(distinct user_id) from tasks where created_at >= :since"),
        "active_routing_users": (
            "routing_decision_log",
            "select count(distinct user_id) from routing_decision_log where decided_at >= :since",
        ),
    }
    counts: dict[str, Any] = {}
    missing_tables: list[str] = []
    async with AsyncSessionLocal() as db:
        table_cache: dict[str, bool] = {}
        for key, (table_name, sql) in queries.items():
            if table_name not in table_cache:
                table_cache[table_name] = await _table_exists(db, table_name)
            if not table_cache[table_name]:
                counts[key] = 0
                if table_name not in missing_tables:
                    missing_tables.append(table_name)
                continue
            result = await db.execute(text(sql), {"since": since})
            counts[key] = int(result.scalar_one() or 0)

    payload = {
        "schema_version": "event_density_audit.v1",
        "window_days": args.days,
        "since": since.isoformat(),
        "counts": counts,
        "missing_tables": missing_tables,
        "readiness": _readiness(counts, args.days),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"Window: last {args.days} days since {payload['since']}")
    print(f"Counts: {counts}")
    if missing_tables:
        print(f"Missing tables: {missing_tables}")
    print(f"Readiness: {payload['readiness']['recommendation']}")
    print(f"Daily task outcomes: {payload['readiness']['daily_task_outcomes']}")
    print(f"Daily labeled route outcomes: {payload['readiness']['daily_labeled_route_outcomes']}")
    for note in payload["readiness"]["notes"]:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
