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
from app.services.evidence import (  # noqa: E402
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    FusionEngine,
    RoutingRewardModel,
    UnifiedEvidence,
)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Write one synthetic Aurora belief shadow trace to Redis.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--actual-router-mode", default="execution_first")
    parser.add_argument("--target", default=EvidenceTarget.EMOTIONAL_BLOCK.value)
    parser.add_argument("--strength", type=float, default=0.9)
    parser.add_argument("--confidence", type=float, default=0.9)
    args = parser.parse_args()

    if cache_service.redis is None:
        await cache_service.init_redis()
    redis = cache_service.redis
    if redis is None:
        print("Redis is not configured", file=sys.stderr)
        return 2

    target = EvidenceTarget(args.target)
    evidence = UnifiedEvidence(
        source_type=EvidenceSourceType.HEURISTIC_FALLBACK,
        target_latent_variable=target,
        direction=EvidenceDirection.INCREASE,
        strength=args.strength,
        confidence=args.confidence,
        evidence_text=f"Smoke evidence for {target.value}",
        scope={"source": "belief_shadow_smoke"},
        metadata={"script": "belief_shadow_smoke.py"},
    )
    engine = FusionEngine(args.user_id)
    state = await engine.update_user_state(redis, user_id=args.user_id, evidence_items=[evidence])
    trace = engine.generate_rl_trace(
        state,
        action_taken={
            "source": "belief_shadow_smoke",
            "action_type": "smoke",
            "mode": args.actual_router_mode,
        },
        actual_router_mode=args.actual_router_mode,
        router_snapshot={"source": "belief_shadow_smoke", "actual_router_mode": args.actual_router_mode},
        outcome="unknown",
        reward=RoutingRewardModel.unknown(),
        training_eligible=False,
    )
    await engine.append_trace(redis, user_id=args.user_id, trace=trace)
    print(json.dumps(trace, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
