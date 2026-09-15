from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.cache import cache_service
from app.services.simulation.simulation_state import LearningSimulationState


async def cleanup_stale_sessions(max_age_hours: int = 6) -> int:
    """Mark stale simulation sessions as completed and remove old checkpoints."""
    redis_client = cache_service.redis
    if redis_client is None:
        return 0

    cutoff = datetime.now(UTC) - timedelta(hours=max(max_age_hours, 1))
    cleaned = 0
    async for raw_key in redis_client.scan_iter("simulation:session:*"):
        key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
        payload = await cache_service.get(key)
        if not isinstance(payload, dict):
            continue
        raw_last_active = str(payload.get("last_active_at") or "").strip()
        if not raw_last_active:
            await cache_service.delete(key)
            cleaned += 1
            continue
        try:
            last_active = datetime.fromisoformat(raw_last_active.replace("Z", "+00:00"))
        except ValueError:
            await cache_service.delete(key)
            cleaned += 1
            continue
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=UTC)
        else:
            last_active = last_active.astimezone(UTC)
        if last_active > cutoff:
            continue
        payload["state"] = LearningSimulationState.COMPLETED.value
        payload["pending_interaction"] = None
        payload["interaction_prompt"] = ""
        payload["suggested_replies"] = []
        payload["interaction_options"] = []
        await cache_service.set(key, payload, ttl=300)
        cleaned += 1
    return cleaned
