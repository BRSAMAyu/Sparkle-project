#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.evidence_health_service import EvidenceHealthService
from app.services.analytics.behavior_pattern_decay_service import BehaviorPatternDecayService


async def run_evidence_health(user_id: UUID, limit: int, force: bool) -> None:
    if not settings.ENABLE_EVIDENCE_HEALTH_JOB and not force:
        raise SystemExit("ENABLE_EVIDENCE_HEALTH_JOB is disabled; use --force to run manually.")
    async with AsyncSessionLocal() as db:
        service = EvidenceHealthService(db)
        counts = await service.run_health_check(user_id, limit=limit)
        print(f"Evidence health updated: {counts}")


async def run_decay(user_id: UUID, window_days: int, decay_factor: float, min_confidence: float, force: bool) -> None:
    if not settings.ENABLE_BEHAVIOR_DECAY and not force:
        raise SystemExit("ENABLE_BEHAVIOR_DECAY is disabled; use --force to run manually.")
    async with AsyncSessionLocal() as db:
        service = BehaviorPatternDecayService(db)
        updated = await service.apply_decay(
            user_id=user_id,
            window_days=window_days,
            decay_factor=decay_factor,
            min_confidence=min_confidence,
        )
        print(f"Behavior pattern decay applied: {updated} patterns updated")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LTM maintenance jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("evidence-health", help="Run evidence health check")
    health_parser.add_argument("--user-id", required=True)
    health_parser.add_argument("--limit", type=int, default=50)
    health_parser.add_argument("--force", action="store_true")

    decay_parser = subparsers.add_parser("behavior-decay", help="Run behavior pattern decay")
    decay_parser.add_argument("--user-id", required=True)
    decay_parser.add_argument("--window-days", type=int, default=30)
    decay_parser.add_argument("--decay-factor", type=float, default=0.9)
    decay_parser.add_argument("--min-confidence", type=float, default=0.35)
    decay_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    user_id = UUID(args.user_id)

    if args.command == "evidence-health":
        asyncio.run(run_evidence_health(user_id, args.limit, args.force))
    elif args.command == "behavior-decay":
        asyncio.run(run_decay(user_id, args.window_days, args.decay_factor, args.min_confidence, args.force))


if __name__ == "__main__":
    main()
