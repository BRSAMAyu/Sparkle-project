"""
LLM 并发控制模块

功能：
1. Semaphore 控制并发请求数，避免 API 限流
2. 按提供商分组限制
3. 请求排队管理
4. 支持根据用户等级动态调整并发数
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class ProviderType(str, Enum):
    """LLM 提供商类型"""
    ZHIPU = "zhipu"          # GLM API
    DEEPSEEK = "deepseek"    # DeepSeek
    XIAOMI = "xiaomi"        # XiaoMi MIMO
    DASHSCOPE = "dashscope"  # Aliyun
    SILICONFLOW = "siliconflow"  # SiliconFlow


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_concurrent: int = 3    # 最大并发数（默认3，适合 GLM 限制）
    queue_timeout: float = 30.0  # 排队超时（秒）


def _get_zhipu_concurrent_limit() -> int:
    """
    根据 GLM 用户等级获取并发限制

    参考：https://www.bigmodel.cn/dev/howuse/rate-limits
    - Free: 5 并发
    - Level 1 (50-500元/月): 10 并发
    - Level 2 (500-5000元/月): 20 并发
    - Level 3 (5000-10000元/月): 30 并发
    - Level 4 (1万-3万/月): 100 并发
    - Level 5 (3万+/月): 200 并发

    对于 GLM-4-Flash 模型有更高限制：
    - Level 2: 50 并发
    - Level 3: 100 并发
    - Level 4: 200 并发
    - Level 5: 300 并发
    """
    # 支持通过环境变量覆盖
    env_limit = os.getenv("ZHIPU_CONCURRENT_LIMIT")
    if env_limit:
        try:
            return int(env_limit)
        except ValueError:
            logger.warning(f"Invalid ZHIPU_CONCURRENT_LIMIT: {env_limit}")

    # 检查用户等级配置
    env_level = os.getenv("ZHIPU_USER_LEVEL", "0").lower()

    # 根据用户等级返回对应的并发数
    level_limits = {
        "free": 5,
        "0": 5,      # Free
        "1": 10,     # Level 1
        "2": 20,     # Level 2 (50 for Flash models)
        "3": 30,     # Level 3 (100 for Flash models)
        "4": 100,    # Level 4 (200 for Flash models)
        "5": 200,    # Level 5 (300 for Flash models)
        "pro": 30,   # Pro 订阅默认对应 Level 3
    }

    limit = level_limits.get(env_level, 30)  # 默认 Level 3 (Pro)
    logger.info(f"ZHIPU concurrent limit: {limit} (user_level={env_level})")
    return limit


# 各提供商的并发限制配置
PROVIDER_CONFIGS: dict[ProviderType, ConcurrencyConfig] = {
    # GLM API - 根据 Pro 订阅等级动态设置
    # Level 3 (Pro): 30 并发，Level 4+: 100-200 并发
    ProviderType.ZHIPU: ConcurrencyConfig(
        max_concurrent=_get_zhipu_concurrent_limit(),
        queue_timeout=30.0,
    ),
    ProviderType.DEEPSEEK: ConcurrencyConfig(
        max_concurrent=10,  # DeepSeek Pro 支持更高并发
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
    """
    LLM 并发管理器

    使用 semaphore 限制对 LLM API 的并发请求数，避免触发 429 限流。

    使用方式：
        # 方式1: 使用 with 语句
        async with llm_concurrency.acquire("zhipu"):
            await llm_service.chat(...)

        # 方式2: 使用装饰器
        @llm_concurrency.limit("zhipu")
        async def my_llm_call():
            ...
    """

    def __init__(self):
        self._semaphores: dict[ProviderType, asyncio.Semaphore] = {}
        self._waiters: dict[ProviderType, int] = {}  # 当前等待的请求数
        self._lock = asyncio.Lock()
        self._initialize_semaphores()

    def _initialize_semaphores(self):
        """初始化所有 semaphore"""
        for provider_type, config in PROVIDER_CONFIGS.items():
            self._semaphores[provider_type] = asyncio.Semaphore(config.max_concurrent)
            self._waiters[provider_type] = 0
        logger.info(f"LLMConcurrencyManager initialized with {len(self._semaphores)} providers")

    def _get_provider_type(self, provider: str) -> ProviderType:
        """根据 provider 名称获取 ProviderType"""
        provider_lower = provider.lower()
        for pt in ProviderType:
            if pt.value in provider_lower or provider_lower in pt.value:
                return pt
        # 默认返回 ZHIPU（最严格的限制）
        return ProviderType.ZHIPU

    def acquire(self, provider: str, timeout: float | None = None):
        """
        获取并发许可

        Args:
            provider: 提供商名称（如 "zhipu", "deepseek"）
            timeout: 超时时间（秒），None 使用配置默认值

        Returns:
            AsyncContextManager，使用 async with 进入

        Example:
            async with llm_concurrency.acquire("zhipu"):
                await llm_api_call()
        """
        provider_type = self._get_provider_type(provider)
        config = PROVIDER_CONFIGS.get(provider_type, ConcurrencyConfig())
        queue_timeout = timeout if timeout is not None else config.queue_timeout

        return _ConcurrencyLimiter(
            manager=self,
            provider_type=provider_type,
            semaphore=self._semaphores[provider_type],
            timeout=queue_timeout,
        )

    def limit(self, provider: str, timeout: float | None = None):
        """
        并发限制装饰器

        Args:
            provider: 提供商名称
            timeout: 超时时间（秒）

        Example:
            @llm_concurrency.limit("zhipu")
            async def my_llm_function():
                return await llm_service.chat(...)
        """
        import functools

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                provider_type = self._get_provider_type(provider)
                config = PROVIDER_CONFIGS.get(provider_type, ConcurrencyConfig())
                queue_timeout = timeout if timeout is not None else config.queue_timeout

                async with _ConcurrencyLimiter(
                    manager=self,
                    provider_type=provider_type,
                    semaphore=self._semaphores[provider_type],
                    timeout=queue_timeout,
                ):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator

    async def _increment_waiters(self, provider_type: ProviderType):
        async with self._lock:
            self._waiters[provider_type] += 1

    async def _decrement_waiters(self, provider_type: ProviderType):
        async with self._lock:
            self._waiters[provider_type] = max(0, self._waiters[provider_type] - 1)

    def get_stats(self) -> dict[str, dict]:
        """获取当前统计信息"""
        stats = {}
        for pt, sem in self._semaphores.items():
            config = PROVIDER_CONFIGS.get(pt, ConcurrencyConfig())
            stats[pt.value] = {
                "max_concurrent": config.max_concurrent,
                "current_active": config.max_concurrent - sem._value,
                "current_waiting": self._waiters.get(pt, 0),
            }
        return stats


class _ConcurrencyLimiter:
    """内部使用的并发限制上下文管理器"""

    def __init__(
        self,
        manager: LLMConcurrencyManager,
        provider_type: ProviderType,
        semaphore: asyncio.Semaphore,
        timeout: float,
    ):
        self.manager = manager
        self.provider_type = provider_type
        self.semaphore = semaphore
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self):
        await self.manager._increment_waiters(self.provider_type)

        try:
            # 使用 asyncio.wait_for 添加超时控制
            await asyncio.wait_for(self.semaphore.acquire(), timeout=self.timeout)
            self._acquired = True
            return self
        except asyncio.TimeoutError:
            logger.warning(
                f"[LLMConcurrency] Timeout waiting for {self.provider_type.value} "
                f"(timeout={self.timeout}s, waiting={self.manager._waiters.get(self.provider_type, 0)})"
            )
            raise TimeoutError(
                f"LLM API {self.provider_type.value} is busy. Please try again later."
            )
        finally:
            await self.manager._decrement_waiters(self.provider_type)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            self.semaphore.release()


# 全局单例
llm_concurrency = LLMConcurrencyManager()
