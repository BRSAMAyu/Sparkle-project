"""
Core: execution
Phase: execute
Stage: Signal-to-Action Spine — Redis resilience utilities

Circuit breaker + retry wrapper for Redis operations in the signal pipeline.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger


class CircuitBreaker:
    """Simple circuit breaker for Redis operations.

    States: closed (normal) → open (failing) → half-open (probing)
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._state = "closed"  # closed | open | half_open

    @property
    def state(self) -> str:
        if self._state == "open" and (time.monotonic() - self._last_failure_time) > self.recovery_timeout:
            self._state = "half_open"
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "CircuitBreaker '{}' opened after {} failures",
                self.name, self._failure_count,
            )

    def allow_request(self) -> bool:
        return self.state != "open"


# Global circuit breakers for key Redis operations
_spine_pipeline_breaker = CircuitBreaker("spine_pipeline", failure_threshold=5, recovery_timeout=30)
_state_register_breaker = CircuitBreaker("state_register", failure_threshold=5, recovery_timeout=30)
_chronicle_breaker = CircuitBreaker("chronicle", failure_threshold=3, recovery_timeout=15)


def get_breaker(name: str) -> CircuitBreaker:
    """Get a named circuit breaker instance."""
    breakers = {
        "spine_pipeline": _spine_pipeline_breaker,
        "state_register": _state_register_breaker,
        "chronicle": _chronicle_breaker,
    }
    return breakers.get(name, CircuitBreaker(name))


async def resilient_redis_call(
    breaker_name: str,
    coro: Any,
    fallback: Any = None,
    max_retries: int = 2,
) -> Any:
    """Execute a Redis coroutine with circuit breaker + retry.

    Args:
        breaker_name: Which circuit breaker to use
        coro: The awaitable Redis call
        fallback: Value to return if all retries fail (default None)
        max_retries: Number of retries before giving up

    Returns:
        The result of the coroutine, or fallback on failure
    """
    breaker = get_breaker(breaker_name)

    if not breaker.allow_request():
        logger.debug("CircuitBreaker '{}' is open, returning fallback", breaker_name)
        return fallback

    import asyncio

    for attempt in range(max_retries + 1):
        try:
            result = await coro
            breaker.record_success()
            return result
        except Exception as exc:
            breaker.record_failure()
            if attempt < max_retries:
                await asyncio.sleep(0.1 * (attempt + 1))  # simple backoff
                continue
            logger.warning(
                "Redis call failed after {} attempts (breaker={}): {}",
                max_retries + 1, breaker_name, exc,
            )
            return fallback
