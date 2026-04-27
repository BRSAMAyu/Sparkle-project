"""
Core: execution
Phase: sense
Stage: Signal-to-Action Spine P2-8 Directive Quota & Cooldown

Per-user, per-directive-type rate limiting to prevent directive flooding.
Each directive type has an hourly quota and a minimum cooldown between emissions.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


# Default quotas: max directives per hour by type
_DEFAULT_HOURLY_QUOTA: dict[str, int] = {
    "execution": 6,
    "response": 20,
    "notification": 4,
    "retrieval": 8,
    "plan": 3,
    "model_write": 4,
    "ux": 10,
    "community": 3,
    "skill": 5,
}

# Minimum seconds between same-type directives
_MIN_COOLDOWN_SECONDS: dict[str, int] = {
    "execution": 300,     # 5 min
    "response": 0,        # no cooldown (chat responses are natural)
    "notification": 1800, # 30 min
    "retrieval": 600,     # 10 min
    "plan": 1800,         # 30 min
    "model_write": 300,   # 5 min
    "ux": 120,            # 2 min
    "community": 600,     # 10 min
    "skill": 300,         # 5 min
}


class DirectiveQuotaService:
    """Rate-limit directive emission per user per type."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def check_allowed(
        self, user_id: str, directive_type: str,
    ) -> dict[str, Any]:
        """Check if a directive of this type is allowed for the user.

        Returns {"allowed": bool, "reason": str, "quota_remaining": int}
        """
        hourly_key = f"spine:quota:hourly:{user_id}:{directive_type}"
        cooldown_key = f"spine:quota:cooldown:{user_id}:{directive_type}"

        # Check hourly quota
        quota = _DEFAULT_HOURLY_QUOTA.get(directive_type, 6)
        raw_count = await self.redis.get(hourly_key)
        current_count = int(raw_count) if raw_count else 0
        if isinstance(raw_count, bytes):
            current_count = int(raw_count.decode())

        if current_count >= quota:
            return {
                "allowed": False,
                "reason": "hourly_quota_exceeded",
                "quota_remaining": 0,
                "quota": quota,
                "current": current_count,
            }

        # Check cooldown
        cooldown_secs = _MIN_COOLDOWN_SECONDS.get(directive_type, 300)
        if cooldown_secs > 0:
            raw_last = await self.redis.get(cooldown_key)
            if raw_last:
                return {
                    "allowed": False,
                    "reason": "cooldown_active",
                    "quota_remaining": quota - current_count,
                    "quota": quota,
                    "current": current_count,
                }

        return {
            "allowed": True,
            "reason": "ok",
            "quota_remaining": quota - current_count,
            "quota": quota,
            "current": current_count,
        }

    async def record_emission(self, user_id: str, directive_type: str) -> None:
        """Record that a directive was emitted. Increments quota and sets cooldown."""
        hourly_key = f"spine:quota:hourly:{user_id}:{directive_type}"
        cooldown_key = f"spine:quota:cooldown:{user_id}:{directive_type}"

        # Increment hourly counter (TTL 1 hour, set on first increment)
        pipe = self.redis.pipeline() if hasattr(self.redis, 'pipeline') else None
        if pipe:
            async with pipe:
                pipe.incr(hourly_key)
                pipe.expire(hourly_key, 3600)
                cooldown_secs = _MIN_COOLDOWN_SECONDS.get(directive_type, 300)
                if cooldown_secs > 0:
                    pipe.set(cooldown_key, "1", ex=cooldown_secs)
                await pipe.execute()
        else:
            # Fallback for FakeRedis or clients without incr
            raw_count = await self.redis.get(hourly_key)
            count = int(raw_count) if raw_count else 0
            count += 1
            await self.redis.set(hourly_key, str(count), ex=3600)
            cooldown_secs = _MIN_COOLDOWN_SECONDS.get(directive_type, 300)
            if cooldown_secs > 0:
                await self.redis.set(cooldown_key, "1", ex=cooldown_secs)

        logger.debug(
            "DirectiveQuota: emitted user={} type={}",
            user_id, directive_type,
        )

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Get quota status for all directive types for a user."""
        status = {}
        for dtype, quota in _DEFAULT_HOURLY_QUOTA.items():
            hourly_key = f"spine:quota:hourly:{user_id}:{dtype}"
            raw_count = await self.redis.get(hourly_key)
            current = int(raw_count) if raw_count else 0
            status[dtype] = {
                "quota": quota,
                "used": current,
                "remaining": quota - current,
                "cooldown_active": bool(await self.redis.get(
                    f"spine:quota:cooldown:{user_id}:{dtype}",
                )),
            }
        return status
