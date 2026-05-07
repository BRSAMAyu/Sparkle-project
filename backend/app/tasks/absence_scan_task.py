"""
MAGIC-004: Periodic absence scan.

Scans all users with heartbeat keys and runs absence signals
through the spine pipeline for policy directive generation.
"""

from __future__ import annotations

import asyncio

from celery import shared_task
from loguru import logger

from app.core.cache import cache_service


@shared_task(
    name="tasks.absence.scan_absent_users",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def scan_absent_users() -> dict[str, int]:
    """Periodic task: scan for absent users and run signal pipeline."""

    async def _run() -> dict[str, int]:
        from app.signals.absence_detector import AbsenceDetector
        from app.signals.spine_orchestrator import get_spine_orchestrator

        if cache_service.redis is None:
            await cache_service.init_redis()

        redis = cache_service.redis
        detector = AbsenceDetector()
        spine = get_spine_orchestrator(redis)

        snapshots = await detector.scan_absent_users(redis, min_level="short")
        counts: dict[str, int] = {"short": 0, "prolonged": 0, "extended": 0, "errors": 0}

        for snap in snapshots:
            try:
                await spine.on_absence_detected(snap.user_id, snap)

                counts[snap.absence_level] = counts.get(snap.absence_level, 0) + 1
                logger.info(
                    "Absence scan: user={} level={} elapsed={:.0f}min",
                    snap.user_id, snap.absence_level, snap.elapsed_minutes,
                )
            except Exception:
                counts["errors"] += 1
                logger.warning("Absence scan failed for user={}", snap.user_id, exc_info=True)

        logger.info("Absence scan complete: {}", counts)
        return counts

    return asyncio.run(_run())
