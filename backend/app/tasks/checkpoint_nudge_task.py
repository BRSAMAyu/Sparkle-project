from __future__ import annotations

import asyncio

from celery import shared_task

from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal
from app.services.checkpoint_nudge_service import (
    scan_and_dispatch_checkpoint_wakes,
    scan_and_send_checkpoint_nudges,
)


@shared_task(name="tasks.checkpoint_nudge.scan_daily_checkpoints")
def scan_daily_checkpoints() -> dict[str, int]:
    async def _run() -> dict[str, int]:
        if cache_service.redis is None:
            await cache_service.init_redis()
        async with AsyncSessionLocal() as session:
            return await scan_and_send_checkpoint_nudges(
                db=session,
                redis=cache_service.redis,
            )

    return asyncio.run(_run())


@shared_task(name="tasks.checkpoint_nudge.run_due_checkpoint_wakes")
def run_due_checkpoint_wakes() -> dict[str, int]:
    async def _run() -> dict[str, int]:
        if cache_service.redis is None:
            await cache_service.init_redis()
        async with AsyncSessionLocal() as session:
            return await scan_and_dispatch_checkpoint_wakes(
                db=session,
                redis=cache_service.redis,
            )

    return asyncio.run(_run())
