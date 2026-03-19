"""
LLM 并发控制模块

功能：
1. 按提供商分组限制并发，避免 API 限流
2. 对 GLM batch 使用按时段自适应的动态并发
3. 在 429 后立即退避，并逐步恢复到更优并发
4. 提供可观测的运行时状态，供 batch 分发决策使用
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from loguru import logger

from app.config import settings
from app.core.cache import cache_service


class ProviderType(str, Enum):
    """LLM 提供商类型"""

    ZHIPU = "zhipu"
    ZHIPU_CODING = "zhipu_coding"
    DEEPSEEK = "deepseek"
    XIAOMI = "xiaomi"
    DASHSCOPE = "dashscope"
    SILICONFLOW = "siliconflow"


@dataclass
class ConcurrencyConfig:
    """并发配置"""

    max_concurrent: int = 3
    queue_timeout: float = 30.0
    adaptive: bool = False
    min_concurrent: int = 1


@dataclass
class ProviderRuntimeState:
    """运行时并发状态"""

    config: ConcurrencyConfig
    current_limit: int
    active: int = 0
    waiting: int = 0
    consecutive_successes: int = 0
    total_successes: int = 0
    total_rate_limits: int = 0
    cooldown_until: float = 0.0
    last_adjustment_at: float = 0.0
    last_rate_limit_at: float = 0.0
    last_bucket: str = ""
    hydrated: bool = False
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


def _get_zhipu_concurrent_limit() -> int:
    """根据智谱套餐等级获取普通 API 并发限制。"""
    env_limit = os.getenv("ZHIPU_CONCURRENT_LIMIT")
    if env_limit:
        try:
            return int(env_limit)
        except ValueError:
            logger.warning(f"Invalid ZHIPU_CONCURRENT_LIMIT: {env_limit}")

    env_level = os.getenv("ZHIPU_USER_LEVEL", "0").lower()
    level_limits = {
        "free": 5,
        "0": 5,
        "1": 10,
        "2": 20,
        "3": 30,
        "4": 100,
        "5": 200,
        "pro": 30,
    }

    limit = level_limits.get(env_level, 30)
    logger.info(f"ZHIPU concurrent limit: {limit} (user_level={env_level})")
    return limit


PROVIDER_CONFIGS: dict[ProviderType, ConcurrencyConfig] = {
    ProviderType.ZHIPU: ConcurrencyConfig(
        max_concurrent=_get_zhipu_concurrent_limit(),
        queue_timeout=30.0,
    ),
    ProviderType.ZHIPU_CODING: ConcurrencyConfig(
        max_concurrent=settings.GLM_BATCH_MAX_CONCURRENCY,
        min_concurrent=settings.GLM_BATCH_MIN_CONCURRENCY,
        queue_timeout=120.0,
        adaptive=True,
    ),
    ProviderType.DEEPSEEK: ConcurrencyConfig(
        max_concurrent=10,
        queue_timeout=30.0,
    ),
    ProviderType.XIAOMI: ConcurrencyConfig(
        max_concurrent=20,
        queue_timeout=10.0,
    ),
    ProviderType.DASHSCOPE: ConcurrencyConfig(
        max_concurrent=20,
        queue_timeout=30.0,
    ),
    ProviderType.SILICONFLOW: ConcurrencyConfig(
        max_concurrent=10,
        queue_timeout=30.0,
    ),
}


class LLMConcurrencyManager:
    """LLM 并发管理器。"""

    _ADAPTIVE_LIMIT_KEY = "glm_batch:adaptive:hour:{bucket}:limit"
    _DEFAULT_TIMEZONE = ZoneInfo("Asia/Shanghai")

    def __init__(self):
        self._runtime: dict[ProviderType, ProviderRuntimeState] = {}
        self._lock = asyncio.Lock()
        self._initialize_runtime()

    def _initialize_runtime(self):
        for provider_type, config in PROVIDER_CONFIGS.items():
            initial_limit = min(config.max_concurrent, max(config.min_concurrent, config.max_concurrent))
            if provider_type == ProviderType.ZHIPU_CODING:
                initial_limit = self._default_glm_limit()
            self._runtime[provider_type] = ProviderRuntimeState(
                config=config,
                current_limit=initial_limit,
            )
        logger.info(f"LLMConcurrencyManager initialized with {len(self._runtime)} providers")

    def _get_provider_type(self, provider: str) -> ProviderType:
        provider_lower = provider.lower()
        if provider_lower == ProviderType.ZHIPU_CODING.value:
            return ProviderType.ZHIPU_CODING
        for pt in ProviderType:
            if pt.value in provider_lower or provider_lower in pt.value:
                return pt
        return ProviderType.ZHIPU

    def _now(self) -> datetime:
        return datetime.now(self._DEFAULT_TIMEZONE)

    def _is_peak_hour(self, now: datetime | None = None) -> bool:
        current = now or self._now()
        start = int(settings.GLM_BATCH_PEAK_START_HOUR)
        end = int(settings.GLM_BATCH_PEAK_END_HOUR)
        hour = current.hour
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    def _bucket_for(self, now: datetime | None = None) -> str:
        current = now or self._now()
        return f"{current.hour:02d}"

    def _adaptive_key(self, bucket: str) -> str:
        return self._ADAPTIVE_LIMIT_KEY.format(bucket=bucket)

    def _default_glm_limit(self, now: datetime | None = None) -> int:
        current = now or self._now()
        if self._is_peak_hour(current):
            return settings.GLM_BATCH_PEAK_CONCURRENCY
        return min(
            settings.GLM_BATCH_MAX_CONCURRENCY,
            max(settings.GLM_BATCH_PEAK_CONCURRENCY, settings.GLM_BATCH_OFFPEAK_DEFAULT_CONCURRENCY),
        )

    async def _hydrate_runtime_if_needed(self, provider_type: ProviderType) -> None:
        state = self._runtime[provider_type]
        if not state.config.adaptive or state.hydrated:
            return

        bucket = self._bucket_for()
        learned_limit = await self._load_learned_limit(bucket)
        default_limit = self._default_glm_limit()
        async with state.condition:
            state.last_bucket = bucket
            state.current_limit = self._clamp_glm_limit(
                learned_limit if learned_limit is not None else default_limit
            )
            state.hydrated = True
            state.condition.notify_all()

    async def _load_learned_limit(self, bucket: str) -> int | None:
        redis_client = cache_service.redis
        if redis_client is None:
            return None
        raw_value = await redis_client.get(self._adaptive_key(bucket))
        if raw_value is None:
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    async def _persist_learned_limit(self, bucket: str, limit: int) -> None:
        redis_client = cache_service.redis
        if redis_client is None:
            return
        await redis_client.set(self._adaptive_key(bucket), str(limit), ex=86400 * 14)

    def _clamp_glm_limit(self, limit: int, now: datetime | None = None) -> int:
        current = now or self._now()
        min_limit = settings.GLM_BATCH_MIN_CONCURRENCY
        max_limit = settings.GLM_BATCH_MAX_CONCURRENCY
        if self._is_peak_hour(current):
            max_limit = min(max_limit, settings.GLM_BATCH_PEAK_CONCURRENCY)
        return max(min_limit, min(int(limit), max_limit))

    async def _maybe_roll_bucket(self, provider_type: ProviderType) -> None:
        state = self._runtime[provider_type]
        if not state.config.adaptive:
            return

        bucket = self._bucket_for()
        current_time = time.time()
        if bucket == state.last_bucket:
            if self._is_peak_hour():
                peak_limit = self._clamp_glm_limit(settings.GLM_BATCH_PEAK_CONCURRENCY)
                async with state.condition:
                    if state.current_limit > peak_limit:
                        state.current_limit = peak_limit
                        state.last_adjustment_at = current_time
                        state.condition.notify_all()
            return

        learned_limit = await self._load_learned_limit(bucket)
        next_limit = self._clamp_glm_limit(
            learned_limit if learned_limit is not None else self._default_glm_limit()
        )
        async with state.condition:
            state.last_bucket = bucket
            if current_time >= state.cooldown_until:
                state.current_limit = next_limit
            else:
                state.current_limit = min(state.current_limit, next_limit)
            state.consecutive_successes = 0
            state.condition.notify_all()

    async def _acquire_slot(self, provider_type: ProviderType, timeout: float) -> None:
        state = self._runtime[provider_type]
        await self._hydrate_runtime_if_needed(provider_type)
        await self._maybe_roll_bucket(provider_type)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        async with state.condition:
            state.waiting += 1
            try:
                while state.active >= state.current_limit:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise TimeoutError(
                            f"LLM API {provider_type.value} is busy. Please try again later."
                        )
                    await asyncio.wait_for(state.condition.wait(), timeout=remaining)
                state.active += 1
            finally:
                state.waiting = max(0, state.waiting - 1)

    async def _release_slot(self, provider_type: ProviderType) -> None:
        state = self._runtime[provider_type]
        async with state.condition:
            state.active = max(0, state.active - 1)
            state.condition.notify_all()

    def acquire(self, provider: str, timeout: float | None = None):
        provider_type = self._get_provider_type(provider)
        config = PROVIDER_CONFIGS.get(provider_type, ConcurrencyConfig())
        queue_timeout = timeout if timeout is not None else config.queue_timeout
        return _ConcurrencyLimiter(
            manager=self,
            provider_type=provider_type,
            timeout=queue_timeout,
        )

    def limit(self, provider: str, timeout: float | None = None):
        import functools

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                async with self.acquire(provider, timeout=timeout):
                    return await func(*args, **kwargs)

            return wrapper

        return decorator

    async def report_success(self, provider: str) -> None:
        provider_type = self._get_provider_type(provider)
        state = self._runtime[provider_type]
        if not state.config.adaptive:
            return

        await self._hydrate_runtime_if_needed(provider_type)
        await self._maybe_roll_bucket(provider_type)
        now = time.time()
        bucket = self._bucket_for()

        async with state.condition:
            state.total_successes += 1
            state.consecutive_successes += 1
            should_try_increase = (
                settings.GLM_BATCH_ADAPTIVE_ENABLED
                and not self._is_peak_hour()
                and now >= state.cooldown_until
                and (state.waiting > 0 or state.active >= max(1, state.current_limit - 1))
                and state.current_limit < settings.GLM_BATCH_MAX_CONCURRENCY
                and state.consecutive_successes >= settings.GLM_BATCH_ADAPTIVE_SUCCESS_THRESHOLD
                and (now - state.last_adjustment_at) >= settings.GLM_BATCH_ADAPTIVE_INCREASE_COOLDOWN_SECONDS
            )
            if should_try_increase:
                state.current_limit = self._clamp_glm_limit(state.current_limit + 1)
                state.last_adjustment_at = now
                state.consecutive_successes = 0
                logger.info(
                    "[GLMBatchConcurrency] Increased adaptive limit to {} for bucket={}".format(
                        state.current_limit,
                        bucket,
                    )
                )
                await self._persist_learned_limit(bucket, state.current_limit)
                state.condition.notify_all()

    async def report_rate_limit(self, provider: str) -> None:
        provider_type = self._get_provider_type(provider)
        state = self._runtime[provider_type]
        if not state.config.adaptive:
            return

        await self._hydrate_runtime_if_needed(provider_type)
        await self._maybe_roll_bucket(provider_type)
        now = time.time()
        bucket = self._bucket_for()
        cooldown_seconds = settings.GLM_BATCH_ADAPTIVE_RATE_LIMIT_COOLDOWN_SECONDS

        async with state.condition:
            state.total_rate_limits += 1
            state.last_rate_limit_at = now
            state.consecutive_successes = 0
            state.current_limit = self._clamp_glm_limit(state.current_limit - 1)
            state.cooldown_until = max(state.cooldown_until, now + cooldown_seconds)
            state.last_adjustment_at = now
            logger.warning(
                "[GLMBatchConcurrency] Rate limited, reduced adaptive limit to {} until {:.0f}".format(
                    state.current_limit,
                    state.cooldown_until,
                )
            )
            await self._persist_learned_limit(bucket, state.current_limit)
            state.condition.notify_all()

    def get_provider_runtime_state(self, provider: str) -> dict[str, int | float | bool | str]:
        provider_type = self._get_provider_type(provider)
        state = self._runtime[provider_type]
        peak_mode = provider_type == ProviderType.ZHIPU_CODING and self._is_peak_hour()
        current_limit = self.get_runtime_limit(provider)
        return {
            "provider": provider_type.value,
            "current_limit": current_limit,
            "configured_max_limit": state.config.max_concurrent,
            "active": state.active,
            "waiting": state.waiting,
            "cooldown_until": state.cooldown_until,
            "cooldown_active": bool(state.cooldown_until and time.time() < state.cooldown_until),
            "total_successes": state.total_successes,
            "total_rate_limits": state.total_rate_limits,
            "peak_mode": peak_mode,
            "time_bucket": self._bucket_for(),
        }

    def get_runtime_limit(self, provider: str) -> int:
        provider_type = self._get_provider_type(provider)
        state = self._runtime[provider_type]
        if provider_type == ProviderType.ZHIPU_CODING and self._is_peak_hour():
            return min(state.current_limit, settings.GLM_BATCH_PEAK_CONCURRENCY)
        return state.current_limit

    def get_stats(self) -> dict[str, dict]:
        stats: dict[str, dict] = {}
        for provider_type, state in self._runtime.items():
            stats[provider_type.value] = {
                "max_concurrent": state.config.max_concurrent,
                "current_limit": state.current_limit,
                "current_active": state.active,
                "current_waiting": state.waiting,
                "cooldown_until": state.cooldown_until,
                "cooldown_active": bool(state.cooldown_until and time.time() < state.cooldown_until),
                "adaptive": state.config.adaptive,
                "peak_mode": provider_type == ProviderType.ZHIPU_CODING and self._is_peak_hour(),
            }
        return stats


class _ConcurrencyLimiter:
    """内部使用的并发限制上下文管理器"""

    def __init__(
        self,
        manager: LLMConcurrencyManager,
        provider_type: ProviderType,
        timeout: float,
    ):
        self.manager = manager
        self.provider_type = provider_type
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self):
        try:
            await self.manager._acquire_slot(self.provider_type, self.timeout)
            self._acquired = True
            return self
        except TimeoutError:
            logger.warning(
                f"[LLMConcurrency] Timeout waiting for {self.provider_type.value} "
                f"(timeout={self.timeout}s)"
            )
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            await self.manager._release_slot(self.provider_type)


llm_concurrency = LLMConcurrencyManager()
