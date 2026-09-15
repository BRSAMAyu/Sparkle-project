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

from app.services.analytics.signal_inventory import ProductionSignalInventory  # noqa: E402


async def _main() -> int:
    parser = argparse.ArgumentParser(description="List current production evidence/reward signal sources.")
    parser.add_argument("--user-id", help="Optionally summarize observed signal counts from Redis traces.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = {"configured": ProductionSignalInventory.configured_inventory()}
    if args.user_id:
        from app.core.cache import cache_service

        if cache_service.redis is None:
            await cache_service.init_redis()
        redis = cache_service.redis
        if redis is None:
            print("Redis is not configured", file=sys.stderr)
            return 2
        raw = await redis.lrange(f"aurora:belief_trace:v1:{args.user_id}", 0, max(0, args.limit - 1))
        payload["observed"] = ProductionSignalInventory.observed_from_traces(list(raw or []))

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0

    configured = payload["configured"]
    print(f"Configured evidence routes: {configured['evidence_route_count']}")
    print(f"Evidence sources: {configured['evidence_source_counts']}")
    print(f"Evidence targets: {configured['evidence_target_counts']}")
    print(f"Reward signals: {configured['reward_signal_counts']}")
    print("Missing or weak signals:")
    for item in configured["currently_missing_or_weak"]:
        print(f"- {item}")
    observed = payload.get("observed")
    if observed:
        print("\nObserved traces:")
        print(f"Total traces: {observed['total_traces']}")
        print(f"Outcomes: {observed['observed_outcome_counts']}")
        print(f"Reward signals: {observed['observed_reward_signal_counts']}")
        print(f"Evidence sources: {observed['observed_evidence_source_counts']}")
        print(f"Evidence targets: {observed['observed_target_evidence_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
