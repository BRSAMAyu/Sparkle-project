"""
Circuit Breaker - Phase 3

Responsibilities:
1. Monitor LangGraph execution failure rate
2. Trip to direct mode when failure rate exceeds threshold
3. Auto-recovery mechanism (half-open state)
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

from loguru import logger

from app.orchestration.schemas import CircuitBreakerState


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CircuitState(Enum):
    """Circuit breaker state"""
    CLOSED = "closed"      # Normal state, requests allowed
    OPEN = "open"          # Tripped state, requests blocked
    HALF_OPEN = "half_open"  # Testing state, allow trial requests


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5        # Consecutive failures threshold
    success_threshold: int = 2        # Success threshold in half-open state
    timeout_ms: int = 60000           # Trip timeout (milliseconds)
    failure_rate_threshold: float = 0.5  # Failure rate threshold (50%)
    window_size: int = 10             # Sliding window size


class CircuitBreaker:
    """Circuit Breaker

    Responsibilities:
    1. Track LangGraph execution success/failure
    2. Trip when threshold reached
    3. Enter half-open for testing after timeout
    4. Recover on success, re-trip on failure
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        redis_client=None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.redis = redis_client

        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._last_state_change = _utcnow()
        self._opened_count = 0

        # Sliding window (for failure rate calculation)
        self._result_window = []  # list of (timestamp, success)

        # Redis key for persistence
        self._redis_key = f"circuit_breaker:{name}"

    async def initialize(self):
        """Load state from Redis"""
        if not self.redis:
            return

        try:
            raw = await self.redis.get(self._redis_key)
            if raw:
                data = json.loads(raw)
                self._state = CircuitState(data["state"])
                self._failure_count = data["failure_count"]
                self._success_count = data["success_count"]
                self._opened_count = data.get("opened_count", 0)
                self._last_state_change = datetime.fromisoformat(data["last_state_change"])
                logger.info(f"CircuitBreaker '{self.name}' loaded from Redis: {self._state.value}")
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker state: {e}")

    async def save_state(self):
        """Save state to Redis"""
        if not self.redis:
            return

        try:
            data = {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "opened_count": self._opened_count,
                "last_state_change": self._last_state_change.isoformat()
            }
            await self.redis.setex(self._redis_key, 3600, json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to save circuit breaker state: {e}")

    def get_state(self) -> CircuitBreakerState:
        """Get current state"""
        return CircuitBreakerState(
            name=self.name,
            state=self._state.value,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time.isoformat() if self._last_failure_time else None,
            last_state_change=self._last_state_change.isoformat(),
            opened_count=self._opened_count
        )

    async def allow_request(self) -> tuple[bool, str | None]:
        """Check if request is allowed

        Returns:
            (allow, reason): Whether allowed, and reason
        """
        # Check if need to transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to(CircuitState.HALF_OPEN, "timeout")
                return True, "circuit_half_open_attempting"
            return False, "circuit_open_rejected"

        return True, None

    async def on_success(self):
        """Record success"""
        self._success_count += 1

        # Update sliding window
        self._result_window.append((_utcnow(), True))
        self._trim_window()

        # HALF_OPEN state: consecutive success reaches threshold -> CLOSED
        if self._state == CircuitState.HALF_OPEN and self._success_count >= self.config.success_threshold:
            await self._transition_to(CircuitState.CLOSED, "success_threshold_reached")
            logger.info(f"CircuitBreaker '{self.name}' recovered to CLOSED")

        # CLOSED state: reset failure count
        if self._state == CircuitState.CLOSED:
            self._failure_count = 0

        await self.save_state()

    async def on_failure(self, error: str | None = None):
        """Record failure"""
        self._failure_count += 1
        self._last_failure_time = _utcnow()

        # Update sliding window
        self._result_window.append((_utcnow(), False))
        self._trim_window()

        # Check if should trip
        should_trip = False
        reason = ""

        if self._state == CircuitState.HALF_OPEN:
            # HALF_OPEN: any failure re-trips
            should_trip = True
            reason = "half_open_failure"
        elif self._state == CircuitState.CLOSED:
            # Check consecutive failures
            if self._failure_count >= self.config.failure_threshold:
                should_trip = True
                reason = f"failure_threshold_exceeded ({self._failure_count}/{self.config.failure_threshold})"

            # Check failure rate
            failure_rate = self._calculate_failure_rate()
            if failure_rate >= self.config.failure_rate_threshold:
                should_trip = True
                reason = f"failure_rate_exceeded ({failure_rate:.2%})"

        if should_trip:
            await self._transition_to(CircuitState.OPEN, reason)
            logger.warning(
                f"CircuitBreaker '{self.name}' tripped OPEN: {reason}"
            )

        await self.save_state()

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset"""
        if not self._last_failure_time:
            return False

        elapsed = (_utcnow() - self._last_failure_time).total_seconds() * 1000
        return elapsed >= self.config.timeout_ms

    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate in sliding window"""
        if not self._result_window:
            return 0.0

        failures = sum(1 for _, success in self._result_window if not success)
        return failures / len(self._result_window)

    def _trim_window(self):
        """Trim sliding window"""
        cutoff = _utcnow() - timedelta(seconds=60)
        self._result_window = [
            (ts, success) for ts, success in self._result_window
            if ts > cutoff
        ]

        # Limit window size
        if len(self._result_window) > self.config.window_size:
            self._result_window = self._result_window[-self.config.window_size:]

    async def _transition_to(self, new_state: CircuitState, reason: str):
        """Transition to new state"""
        old_state = self._state
        self._state = new_state
        self._last_state_change = _utcnow()

        if new_state == CircuitState.OPEN:
            self._opened_count += 1
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0

        # Log state change event
        logger.info(
            f"CircuitBreaker '{self.name}' state transition: "
            f"{old_state.value} -> {new_state.value} (reason: {reason})"
        )

        # Emit observability event
        await self._emit_state_change_event(old_state.value, new_state.value, reason)

    async def _emit_state_change_event(self, old_state: str, new_state: str, reason: str):
        """Emit state change event"""
        try:
            from app.orchestration.observability_logger import observability_logger

            await observability_logger.log_event(
                event_type="circuit_state_change",
                data={
                    "circuit_name": self.name,
                    "old_state": old_state,
                    "new_state": new_state,
                    "reason": reason,
                    "failure_count": self._failure_count,
                    "opened_count": self._opened_count
                }
            )
        except ImportError:
            # observability_logger not yet initialized
            pass

    def reset(self):
        """Manual reset (for testing)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_state_change = _utcnow()
        self._result_window.clear()


class CircuitBreakerRegistry:
    """Circuit breaker registry"""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(self, breaker: CircuitBreaker):
        """Register a circuit breaker"""
        self._breakers[breaker.name] = breaker

    def get(self, name: str) -> CircuitBreaker | None:
        """Get circuit breaker by name"""
        return self._breakers.get(name)

    def get_all_states(self) -> dict[str, CircuitBreakerState]:
        """Get all circuit breaker states"""
        return {
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        }


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()
