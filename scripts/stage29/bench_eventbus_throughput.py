#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.event_bus import event_bus
from app.db.session import engine
from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.user import User
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService


TOTAL_EVENTS = 1000
BENCH_STREAM = "sparkle_events_stage29_bench"
BENCH_GROUP = "srl_phase_tracker_bench"


async def main() -> int:
    await event_bus.connect()
    if event_bus.redis is None:
        raise SystemExit("Redis is required for Stage 29 throughput bench")

    async with engine.begin() as conn:
        await conn.run_sync(SRLPhaseStateRecord.__table__.create, checkfirst=True)

    kill_switch = AuroraStage29SRLKillSwitchService()
    await kill_switch.ordered_startup("live")

    tracker = SRLPhaseTrackerService(event_bus=event_bus, redis=event_bus.redis)
    await event_bus.redis.delete(BENCH_STREAM)
    await event_bus.redis.delete(f"{BENCH_STREAM}:dlq")
    try:
        await event_bus.redis.xgroup_destroy(BENCH_STREAM, BENCH_GROUP)
    except Exception:
        pass

    consumer_name = f"srl-bench-{uuid4().hex[:8]}"
    await event_bus.subscribe(
        stream=BENCH_STREAM,
        group_name=BENCH_GROUP,
        consumer_name=consumer_name,
        callback=tracker.handle_event,
    )
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id = (
                await session.execute(
                    select(User.id).limit(1)
                )
            ).scalar_one_or_none()
            if user_id is None:
                raise SystemExit("Stage29 throughput bench requires at least one user row in the database")

            existing = (
                await session.execute(
                    select(SRLPhaseStateRecord).where(SRLPhaseStateRecord.user_id == user_id)
                )
            ).scalar_one_or_none()
            if existing is None:
                session.add(
                    SRLPhaseStateRecord(
                        user_id=user_id,
                        current_phase="FORETHOUGHT",
                        phase_started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        previous_phase=None,
                        transition_evidence_ids=["bench:bootstrap"],
                        confidence=1.0,
                        source="default",
                        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
                await session.commit()
        started = perf_counter()
        for index in range(TOTAL_EVENTS):
            await event_bus.publish(
                "srl.phase.transition",
                {
                    "event_type": "srl.phase.transition",
                    "user_id": str(user_id),
                    "trigger_event_type": "task.started" if index % 2 == 0 else "task.completed",
                    "evidence_id": f"bench-{index}",
                },
                stream=BENCH_STREAM,
            )

        await asyncio.sleep(2)
        lag_info = await event_bus.get_consumer_lag(stream=BENCH_STREAM, group_name=BENCH_GROUP)
        lag_p95 = max(
            [float(group.get("lag_time_seconds") or 0.0) for group in lag_info.get("groups", [])],
            default=0.0,
        )
        dlq_stats = await event_bus.get_dlq_stats(stream=BENCH_STREAM)
        stream_info = await event_bus.redis.xinfo_stream(BENCH_STREAM)
        elapsed = perf_counter() - started
        print(
            "Stage29 throughput bench "
            f"events={TOTAL_EVENTS} elapsed_seconds={elapsed:.3f} "
            f"events_per_minute={(TOTAL_EVENTS / elapsed) * 60:.2f} "
            f"lag_p95={lag_p95} stream_length={stream_info.get('length', 0)} "
            f"dlq_size={dlq_stats.get('message_count', 0)}"
        )
        return 0
    finally:
        await event_bus.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
