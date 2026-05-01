from __future__ import annotations

"""
LLM 模型回退管理器 (Model Fallback Manager)

功能：
1. 检测 429/Rate Limit 错误，自动切换同层级替代模型
2. 指数退避重试策略
3. 集成熔断器进行分布式健康追踪
4. 请求上下文保持，确保回退后请求完整性

设计原则：
- 快速失败：检测到 429 立即切换，不等待
- 智能降级：优先切换同 tier 模型，然后降级 tier
- 可观测：记录每次回退的模型、原因、结果
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from app.core.agent_profiles import ModelTier
from app.core.cache import cache_service
from app.core.llm_router import LLMSelection, llm_router


class FallbackReason(StrEnum):
    """回退触发原因"""
    RATE_LIMIT_429 = "rate_limit_429"       # 429 Too Many Requests
    RATE_LIMIT_QUOTA = "rate_limit_quota"   # 配额用尽
    TIMEOUT = "timeout"                     # 请求超时
    SERVICE_UNAVAILABLE = "service_unavailable"  # 503 服务不可用
    CONNECTION_ERROR = "connection_error"   # 连接错误
    UNKNOWN_ERROR = "unknown_error"         # 其他错误


@dataclass
class FallbackAttempt:
    """单次回退尝试记录"""
    model_key: str
    provider: str
    reason: FallbackReason
    timestamp: float
    success: bool | None = None  # None=进行中, True=成功, False=失败
    error_message: str | None = None
    ttfc_ms: float | None = None  # Time To First Chunk


@dataclass
class FallbackSession:
    """一次请求的回退会话"""
    original_selection: LLMSelection
    attempts: list[FallbackAttempt] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    final_success: bool = False
    final_model_key: str | None = None


class ModelHealthTracker:
    """
    模型健康追踪器

    使用 Redis 存储各模型的健康状态，支持：
    - 失败计数
    - 最后失败时间
    - 熔断状态
    """

    # Redis Key 前缀
    FAILURE_COUNT_PREFIX = "llm:fail:"
    LAST_FAILURE_PREFIX = "llm:last_fail:"
    CIRCUIT_OPEN_PREFIX = "llm:circuit:"

    # 默认配置
    FAILURE_THRESHOLD = 5          # 失败阈值，超过则标记为不健康
    RECOVERY_TIMEOUT = 60          # 不健康恢复时间（秒）
    FAILURE_WINDOW = 300           # 失败计数窗口（秒）

    def __init__(self, failure_threshold: int | None = None, recovery_timeout: int | None = None):
        self.failure_threshold = failure_threshold or self.FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or self.RECOVERY_TIMEOUT

    async def is_healthy(self, model_key: str) -> bool:
        """检查模型是否健康"""
        if not cache_service.redis:
            return True  # Redis 不可用时默认健康

        # 检查熔断状态
        open_until = await cache_service.redis.get(f"{self.CIRCUIT_OPEN_PREFIX}{model_key}")
        if open_until:
            try:
                reset_at = float(open_until)
                if time.time() < reset_at:
                    logger.warning(f"Model {model_key} is in circuit breaker open state until {reset_at}")
                    return False
            except ValueError:
                pass

        # 检查失败次数
        count = await cache_service.redis.get(f"{self.FAILURE_COUNT_PREFIX}{model_key}")
        if count and int(count) >= self.failure_threshold:
            logger.warning(f"Model {model_key} has {count} failures, considered unhealthy")
            return False

        return True

    async def record_failure(self, model_key: str, reason: FallbackReason) -> None:
        """记录模型失败"""
        if not cache_service.redis:
            return

        now = time.time()

        # 增加失败计数
        fail_key = f"{self.FAILURE_COUNT_PREFIX}{model_key}"
        count = await cache_service.redis.incr(fail_key)

        # 设置过期时间
        if count == 1:
            await cache_service.redis.expire(fail_key, self.FAILURE_WINDOW)

        # 记录最后失败时间和原因
        await cache_service.redis.set(
            f"{self.LAST_FAILURE_PREFIX}{model_key}",
            f"{now}:{reason.value}",
            ex=self.FAILURE_WINDOW
        )

        logger.warning(
            f"Recorded failure for {model_key}: count={count}, reason={reason.value}"
        )

        # 失败次数达到阈值，打开熔断器
        if count >= self.failure_threshold:
            reset_at = now + self.recovery_timeout
            await cache_service.redis.set(
                f"{self.CIRCUIT_OPEN_PREFIX}{model_key}",
                str(reset_at),
                ex=self.recovery_timeout
            )
            logger.error(
                f"Circuit breaker OPENED for {model_key} until {reset_at} "
                f"(failures: {count})"
            )

    async def record_success(self, model_key: str) -> None:
        """记录模型成功，清除失败计数"""
        if not cache_service.redis:
            return

        # 清除失败计数
        await cache_service.redis.delete(f"{self.FAILURE_COUNT_PREFIX}{model_key}")

        # 清除熔断状态
        await cache_service.redis.delete(f"{self.CIRCUIT_OPEN_PREFIX}{model_key}")

        logger.debug(f"Recorded success for {model_key}, cleared failure state")

    async def get_failure_count(self, model_key: str) -> int:
        """获取失败次数"""
        if not cache_service.redis:
            return 0

        count = await cache_service.redis.get(f"{self.FAILURE_COUNT_PREFIX}{model_key}")
        return int(count) if count else 0


class LLMModelFallbackManager:
    """
    LLM 模型回退管理器

    检测 429 和其他错误，自动切换到同层级的替代模型。

    使用方式：
        fallback_manager = LLMModelFallbackManager()

        async with fallback_manager.fallback_context(selection) as ctx:
            # 使用 ctx.selection 获取当前模型配置
            response = await llm_call(ctx.selection)
    """

    def __init__(
        self,
        max_fallback_attempts: int = 3,
        health_tracker: ModelHealthTracker | None = None,
    ):
        self.max_fallback_attempts = max_fallback_attempts
        self.health_tracker = health_tracker or ModelHealthTracker()

    def _detect_fallback_reason(self, error: Exception) -> FallbackReason | None:
        """
        检测错误是否需要触发回退

        Args:
            error: 捕获的异常

        Returns:
            如果需要回退，返回原因；否则返回 None
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # 429 Too Many Requests / Rate Limit
        if "429" in error_str or error_type == "RateLimitError":
            return FallbackReason.RATE_LIMIT_429

        if "rate limit" in error_str or "too many request" in error_str:
            return FallbackReason.RATE_LIMIT_429

        # Quota exceeded
        if "quota" in error_str and ("exceed" in error_str or "insufficient" in error_str):
            return FallbackReason.RATE_LIMIT_QUOTA

        # Timeout
        if "timeout" in error_str or "timed out" in error_str:
            return FallbackReason.TIMEOUT

        # Service Unavailable
        if "503" in error_str or "service unavailable" in error_str:
            return FallbackReason.SERVICE_UNAVAILABLE

        # Connection Error
        if "connection" in error_str or "network" in error_str:
            return FallbackReason.CONNECTION_ERROR

        return None

    def _get_fallback_candidates(
        self,
        failed_selection: LLMSelection,
        exclude_models: set[str],
    ) -> list[LLMSelection]:
        """
        获取可用的回退候选模型

        优先级：
        1. 同 tier 的其他模型
        2. 下一级 tier 的模型

        Args:
            failed_selection: 失败的模型选择
            exclude_models: 要排除的模型 key（已尝试过的）

        Returns:
            候选模型列表（按优先级排序）
        """
        candidates = []
        current_tier = failed_selection.config.tier
        agent_role = failed_selection.agent_role
        task_type = failed_selection.task_type

        # 获取 tier 映射
        tier_mapping = llm_router._tier_mapping

        # 1. 同 tier 的其他模型
        same_tier_models = tier_mapping.get(current_tier, [])
        for model_key in same_tier_models:
            if model_key not in exclude_models and model_key in llm_router._available_models:
                config = llm_router._available_models[model_key]
                selection = LLMSelection(
                    model_key=model_key,
                    config=config,
                    agent_role=agent_role,
                    task_type=task_type,
                    reason=f"Fallback from {failed_selection.config.model_name} (same tier)",
                    is_fallback=True,
                )
                candidates.append(selection)

        # 2. 降级到下一级 tier
        tier_order = [
            ModelTier.MAX,
            ModelTier.PRO,
            ModelTier.PLUS,
            ModelTier.STANDARD,
            ModelTier.FAST,
            ModelTier.FREE_FAST,
            ModelTier.FREE_REASONING,
        ]

        try:
            current_index = tier_order.index(current_tier)
        except ValueError:
            current_index = 0

        for lower_tier in tier_order[current_index + 1:]:
            lower_models = tier_mapping.get(lower_tier, [])
            for model_key in lower_models:
                if model_key not in exclude_models and model_key in llm_router._available_models:
                    config = llm_router._available_models[model_key]
                    selection = LLMSelection(
                        model_key=model_key,
                        config=config,
                        agent_role=agent_role,
                        task_type=task_type,
                        reason=f"Fallback from {failed_selection.config.model_name} (downgraded to {lower_tier.value})",
                        is_fallback=True,
                    )
                    candidates.append(selection)

        return candidates

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        计算指数退避延迟

        Args:
            attempt: 当前尝试次数

        Returns:
            延迟秒数
        """
        # 基础延迟 100ms，指数增长，最大 2 秒
        return min(0.1 * (2 ** attempt), 2.0)

    async def execute_with_fallback(
        self,
        original_selection: LLMSelection,
        call_fn,  # AsyncCallable[[LLMSelection], Any]
        operation_type: str = "chat",
    ) -> Any:
        """
        执行 LLM 调用，支持自动回退

        Args:
            original_selection: 原始模型选择
            call_fn: 异步调用函数，接收 LLMSelection 作为参数
            operation_type: 操作类型（用于日志）

        Returns:
            LLM 响应

        Raises:
            Exception: 所有尝试都失败后抛出最后一个异常
        """
        session = FallbackSession(original_selection=original_selection)
        exclude_models: set[str] = set()

        current_selection = original_selection

        for attempt in range(self.max_fallback_attempts):
            model_key = self._get_model_key_from_selection(current_selection)
            provider = current_selection.config.provider.value if current_selection.config.provider else "unknown"

            # 检查模型健康状态
            is_healthy = await self.health_tracker.is_healthy(model_key)

            attempt_record = FallbackAttempt(
                model_key=model_key,
                provider=provider,
                reason=FallbackReason.UNKNOWN_ERROR,
                timestamp=time.time(),
            )
            session.attempts.append(attempt_record)

            # 如果模型不健康，提前切换
            if not is_healthy and attempt > 0:
                logger.warning(f"Model {model_key} is unhealthy, skipping to fallback")
                attempt_record.success = False
                attempt_record.error_message = "Model unhealthy (circuit breaker open)"
                exclude_models.add(model_key)

                # 获取候选模型
                candidates = self._get_fallback_candidates(
                    current_selection or original_selection,
                    exclude_models,
                )
                if candidates:
                    current_selection = candidates[0]
                    continue
                else:
                    # 没有更多候选，抛出异常
                    raise Exception(f"No healthy fallback models available after {attempt} attempts")

            try:
                logger.info(
                    f"[LLMFallback] Attempt {attempt + 1}/{self.max_fallback_attempts}: "
                    f"model={current_selection.config.model_name}, "
                    f"reason={current_selection.reason}"
                )

                start = time.perf_counter()
                result = await call_fn(current_selection)
                elapsed = (time.perf_counter() - start) * 1000

                # 成功
                attempt_record.success = True
                attempt_record.ttfc_ms = elapsed

                await self.health_tracker.record_success(model_key)

                session.final_success = True
                session.final_model_key = model_key
                session.end_time = time.time()

                # 记录回退成功
                if attempt > 0 or current_selection.is_fallback:
                    logger.success(
                        f"[LLMFallback] SUCCESS after {attempt} attempts: "
                        f"final_model={current_selection.config.model_name}, "
                        f"elapsed={elapsed:.0f}ms, "
                        f"original={original_selection.config.model_name}"
                    )

                return result

            except Exception as e:
                fallback_reason = self._detect_fallback_reason(e)

                if fallback_reason is None:
                    # 非回退类型的错误，直接抛出
                    logger.error(f"[LLMFallback] Non-retryable error: {e}")
                    raise

                # 记录失败
                attempt_record.reason = fallback_reason
                attempt_record.success = False
                attempt_record.error_message = str(e)

                await self.health_tracker.record_failure(model_key, fallback_reason)

                logger.warning(
                    f"[LLMFallback] Attempt {attempt + 1} failed: "
                    f"model={current_selection.config.model_name}, "
                    f"reason={fallback_reason.value}, "
                    f"error={str(e)[:100]}"
                )

                # 添加到排除列表
                exclude_models.add(model_key)

                # 获取候选模型
                candidates = self._get_fallback_candidates(current_selection, exclude_models)

                if not candidates:
                    logger.error(f"[LLMFallback] No more fallback candidates after {attempt + 1} attempts")
                    # 最后一次尝试也失败了，抛出异常
                    session.end_time = time.time()
                    raise e

                # 切换到候选模型
                current_selection = candidates[0]

                # 指数退避
                delay = self._calculate_backoff_delay(attempt)
                logger.info(f"[LLMFallback] Waiting {delay:.2f}s before retry...")
                await asyncio.sleep(delay)

        # 理论上不会到达这里
        session.end_time = time.time()
        raise Exception(f"Max fallback attempts ({self.max_fallback_attempts}) exceeded")

    async def execute_stream_with_fallback(
        self,
        original_selection: LLMSelection,
        stream_fn,  # AsyncCallable[[LLMSelection], AsyncGenerator[str, None]]
        operation_type: str = "stream_chat",
    ) -> AsyncGenerator[str, None]:
        """
        执行流式 LLM 调用，支持自动回退

        注意：流式调用的回退只在首次 chunk 之前生效，
        一旦开始流式传输，中断并重新建立连接的开销太大。

        Args:
            original_selection: 原始模型选择
            stream_fn: 异步流式调用函数，返回 AsyncGenerator
            operation_type: 操作类型

        Yields:
            流式响应内容
        """
        # 对于流式调用，我们只在首次连接时支持回退
        # 一旦开始接收数据，就不再回退（因为用户已经开始看到响应）

        class StreamingFallbackHandler:
            def __init__(self, manager: LLMModelFallbackManager):
                self.manager = manager
                self.first_chunk_received = False

            async def execute(
                self,
                selection: LLMSelection,
                fn,
            ) -> AsyncGenerator[str, None]:
                try:
                    async for chunk in fn(selection):
                        if not self.first_chunk_received:
                            # 首个 chunk 到达，记录成功
                            model_key = self._get_model_key(selection)
                            await self.manager.health_tracker.record_success(model_key)
                            self.first_chunk_received = True
                        yield chunk
                except Exception as e:
                    if self.first_chunk_received:
                        # 流式传输中途失败，直接抛出（不回退）
                        raise e
                    else:
                        # 首次连接失败，触发回退
                        raise e

            def _get_model_key(self, selection: LLMSelection) -> str:
                return self.manager._get_model_key_from_selection(selection)

        # 非回退模式下的流式处理
        handler = StreamingFallbackHandler(self)

        try:
            async for chunk in handler.execute(original_selection, stream_fn):
                yield chunk
        except Exception as e:
            fallback_reason = self._detect_fallback_reason(e)
            if fallback_reason is None:
                raise

            # 尝试回退
            logger.warning(f"[LLMFallback] Stream connection failed: {fallback_reason.value}, attempting fallback...")

            original_model_key = self._get_model_key_from_selection(original_selection)
            await self.health_tracker.record_failure(original_model_key, fallback_reason)

            exclude_models: set[str] = {original_model_key}
            candidates = self._get_fallback_candidates(original_selection, exclude_models)

            for selection in candidates:
                model_key = self._get_model_key_from_selection(selection)
                if not await self.health_tracker.is_healthy(model_key):
                    logger.warning(f"[LLMFallback] Skipping unhealthy stream fallback model: {selection.config.model_name}")
                    continue
                try:
                    logger.info(f"[LLMFallback] Trying fallback model: {selection.config.model_name}")
                    async for chunk in handler.execute(selection, stream_fn):
                        yield chunk
                    return  # 成功
                except Exception as fallback_error:
                    fallback_failure_reason = self._detect_fallback_reason(fallback_error)
                    if fallback_failure_reason is not None:
                        await self.health_tracker.record_failure(model_key, fallback_failure_reason)
                    logger.warning(f"[LLMFallback] Fallback to {selection.config.model_name} also failed: {fallback_error}")
                    exclude_models.add(model_key)

            # 所有回退都失败
            raise e

    def _get_model_key_from_selection(self, selection: LLMSelection) -> str:
        if selection.model_key and selection.model_key in llm_router._available_models:
            return selection.model_key

        for key, config in llm_router._available_models.items():
            if (
                config.model_name == selection.config.model_name
                and config.provider == selection.config.provider
                and config.base_url == selection.config.base_url
                and config.clear_thinking == selection.config.clear_thinking
            ):
                return key
        return selection.model_key or "unknown"


# 全局单例
llm_fallback_manager = LLMModelFallbackManager()
