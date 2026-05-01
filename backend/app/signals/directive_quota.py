"""
Core: execution
Phase: sense
Stage: Signal-to-Action Spine P2-8 Directive Quota & Cooldown

D10 Ruling: 按场景配额，不做统一配额。
- user_initiated: Full Aurora sessions per day, varies by sprint mode
- system_initiated: risk budget for system-triggered sessions
- quick_calibration: unlimited but lightweight (no full Aurora)

Per-type hourly quotas and cooldowns remain for directive-level rate limiting.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

# ── D10: Per-scenario daily quotas for Aurora Core Sessions ──────────
# normal = standard goal, sprint = 7/14-day exam sprint, crisis = exam 48h/24h
_SCENARIO_DAILY_QUOTA: dict[str, dict[str, int]] = {
    "normal": {"user_initiated": 1, "system_initiated": 1},
    "sprint": {"user_initiated": 2, "system_initiated": 2},
    "crisis": {"user_initiated": 3, "system_initiated": 3},
}

# Quick calibration is always unlimited (it's lightweight, no full Aurora)
# Technical failures don't consume quota (handled in record logic)
# User exits before model_write: refund partial quota (P4 future)


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

    # ── D10: Per-scenario Aurora Core Session quotas ──────────────────

    async def check_aurora_session_allowed(
        self,
        user_id: str,
        scenario: str,
        initiated_by: str = "user_initiated",
    ) -> dict[str, Any]:
        """D10: Check if an Aurora Core Session is allowed per scenario quota.

        Args:
            user_id: user identifier
            scenario: "normal" | "sprint" | "crisis"
            initiated_by: "user_initiated" | "system_initiated" | "quick_calibration"

        Returns:
            {"allowed": bool, "reason": str, "daily_quota": int, "daily_used": int}
        """
        # Quick calibration is always allowed (lightweight, no full Aurora)
        if initiated_by == "quick_calibration":
            return {
                "allowed": True,
                "reason": "quick_calibration_unlimited",
                "daily_quota": -1,
                "daily_used": 0,
            }

        scenario_quotas = _SCENARIO_DAILY_QUOTA.get(scenario, _SCENARIO_DAILY_QUOTA["normal"])
        quota = scenario_quotas.get(initiated_by, 1)

        daily_key = f"spine:aurora_quota:daily:{user_id}:{scenario}:{initiated_by}"
        raw_count = await self.redis.get(daily_key)
        current = int(raw_count) if raw_count else 0
        if isinstance(raw_count, bytes):
            current = int(raw_count.decode())

        if current >= quota:
            return {
                "allowed": False,
                "reason": "daily_quota_exceeded",
                "daily_quota": quota,
                "daily_used": current,
                "scenario": scenario,
                "initiated_by": initiated_by,
            }

        # Crisis mode: system can exceed user quota, but must write wake_reason
        # (wake_reason enforcement is caller's responsibility)
        if scenario == "crisis" and initiated_by == "system_initiated":
            return {
                "allowed": True,
                "reason": "crisis_system_override",
                "daily_quota": quota,
                "daily_used": current,
                "scenario": scenario,
                "initiated_by": initiated_by,
                "requires_wake_reason": True,
            }

        return {
            "allowed": True,
            "reason": "ok",
            "daily_quota": quota,
            "daily_used": current,
            "scenario": scenario,
            "initiated_by": initiated_by,
        }

    async def record_aurora_session(
        self,
        user_id: str,
        scenario: str,
        initiated_by: str = "user_initiated",
        *,
        was_technical_failure: bool = False,
        user_exited_early: bool = False,
    ) -> None:
        """D10: Record an Aurora Core Session consumption.

        Technical failures don't consume quota.
        User exits before model_write get partial refund (P4).
        """
        if initiated_by == "quick_calibration":
            return

        if was_technical_failure:
            logger.info(
                "AuroraQuota: technical failure — not consuming quota user={} scenario={}",
                user_id, scenario,
            )
            return

        daily_key = f"spine:aurora_quota:daily:{user_id}:{scenario}:{initiated_by}"

        raw_count = await self.redis.get(daily_key)
        count = int(raw_count) if raw_count else 0
        if isinstance(raw_count, bytes):
            count = int(raw_count.decode())

        count += 1

        # TTL until end of day (max 24h)
        await self.redis.set(daily_key, str(count), ex=24 * 3600)

        logger.info(
            "AuroraQuota: consumed user={} scenario={} by={} count={}/{}",
            user_id, scenario, initiated_by, count,
            _SCENARIO_DAILY_QUOTA.get(scenario, _SCENARIO_DAILY_QUOTA["normal"]).get(initiated_by, 1),
        )

    async def get_aurora_quota_status(self, user_id: str) -> dict[str, Any]:
        """D10: Get Aurora session quota status across all scenarios."""
        status = {}
        for scenario, quotas in _SCENARIO_DAILY_QUOTA.items():
            scenario_status = {}
            for initiated_by, quota in quotas.items():
                daily_key = f"spine:aurora_quota:daily:{user_id}:{scenario}:{initiated_by}"
                raw_count = await self.redis.get(daily_key)
                current = int(raw_count) if raw_count else 0
                if isinstance(raw_count, bytes):
                    current = int(raw_count.decode())
                scenario_status[initiated_by] = {
                    "daily_quota": quota,
                    "daily_used": current,
                    "remaining": quota - current,
                }
            status[scenario] = scenario_status
        return status

    # ── Directive-level quotas (unchanged) ─────────────────────────────

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
