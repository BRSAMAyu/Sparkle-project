from __future__ import annotations

import time

from loguru import logger

from app.config.phase5_config import phase5_config
from app.core.cache import cache_service

# Fallback in-memory state when Redis isn't available.
_LOCAL_FAILURES: dict[str, tuple[int, float]] = {}
_LOCAL_OPEN: dict[str, float] = {}


class CircuitBreakerOpenException(Exception):
    def __init__(self, provider: str, reset_at: float):
        self.provider = provider
        self.reset_at = reset_at
        super().__init__(f"Circuit breaker open for {provider}, reset at {reset_at}")

class RedisCircuitBreaker:
    """
    Redis-backed Circuit Breaker for distributed rate limiting protection.
    Shared state across multiple workers/instances.

    Configuration (from phase5_config):
    - CIRCUIT_BREAKER_FAILURE_THRESHOLD: 失败次数阈值
    - CIRCUIT_BREAKER_RECOVERY_TIMEOUT: 熔断恢复时间（秒）
    - CIRCUIT_BREAKER_FAILURE_WINDOW: 失败窗口时间（秒）
    """
    def __init__(self,
                 failure_threshold: int | None = None,
                 recovery_timeout: int | None = None,
                 failure_window: int | None = None):
        self.failure_threshold = failure_threshold or phase5_config.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or phase5_config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
        self.failure_window = failure_window or phase5_config.CIRCUIT_BREAKER_FAILURE_WINDOW

        logger.info(f"Circuit Breaker initialized: threshold={self.failure_threshold}, "
                   f"recovery={self.recovery_timeout}s, window={self.failure_window}s")

    async def check(self, provider: str):
        """
        Check if the circuit is open. Raises CircuitBreakerOpenException if open.
        """
        if not cache_service.redis:
            reset_at = _LOCAL_OPEN.get(provider)
            if reset_at and time.time() < reset_at:
                raise CircuitBreakerOpenException(provider, reset_at)
            return

        open_key = f"cb:open:{provider}"

        # Check if open
        open_until = await cache_service.redis.get(open_key)
        if open_until:
            try:
                reset_at = float(open_until)
                if time.time() < reset_at:
                    raise CircuitBreakerOpenException(provider, reset_at)
            except ValueError:
                pass # Invalid data, allow traffic

    async def record_failure(self, provider: str):
        """
        Record a failure. If threshold reached, open the circuit.
        """
        if not cache_service.redis:
            now = time.time()
            count, first_at = _LOCAL_FAILURES.get(provider, (0, now))
            if now - first_at > self.failure_window:
                count, first_at = 0, now
            count += 1
            _LOCAL_FAILURES[provider] = (count, first_at)
            if count >= self.failure_threshold:
                reset_at = now + self.recovery_timeout
                _LOCAL_OPEN[provider] = reset_at
                _LOCAL_FAILURES.pop(provider, None)
                logger.warning(f"Circuit breaker OPENED for {provider} until {reset_at} (local)")
            return

        fail_key = f"cb:fail:{provider}"
        open_key = f"cb:open:{provider}"

        # Increment failure count
        count = await cache_service.redis.incr(fail_key)

        # Set expiry for the window if new
        if count == 1:
            await cache_service.redis.expire(fail_key, self.failure_window)

        if count >= self.failure_threshold:
            # Open the circuit
            reset_at = time.time() + self.recovery_timeout
            await cache_service.redis.set(open_key, str(reset_at), ex=self.recovery_timeout)
            # Reset failure count so we start fresh after recovery
            await cache_service.redis.delete(fail_key)
            logger.warning(f"Circuit breaker OPENED for {provider} until {reset_at}")

    async def record_success(self, provider: str):
        """
        Record a success. Clears failure count (or could decay).
        """
        if not cache_service.redis:
            _LOCAL_FAILURES.pop(provider, None)
            return

        fail_key = f"cb:fail:{provider}"
        # Simple strategy: success clears failures.
        # Alternatively, could do nothing and let TTL expire, but clearing is faster recovery for sporadic errors.
        await cache_service.redis.delete(fail_key)

circuit_breaker_service = RedisCircuitBreaker()
