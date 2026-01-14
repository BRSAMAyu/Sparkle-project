"""
测试：熔断器功能 (Phase 5A)

验证熔断器在多 worker 环境下的全局一致性
"""
import pytest
import time
import asyncio
from app.services.circuit_breaker import (
    RedisCircuitBreaker,
    CircuitBreakerOpenException
)
from app.core.cache import cache_service


@pytest.mark.asyncio
async def test_circuit_breaker_basic():
    """基础测试：正常情况下熔断器不应触发"""
    cb = RedisCircuitBreaker(failure_threshold=3, recovery_timeout=5)

    # 应该通过检查
    await cb.check("test_provider")

    # 记录成功
    await cb.record_success("test_provider")

    # 应该仍然通过
    await cb.check("test_provider")


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """测试：连续失败达到阈值后熔断器应打开"""
    cb = RedisCircuitBreaker(failure_threshold=3, recovery_timeout=2)

    provider = f"test_provider_{int(time.time())}"

    # 前两次失败
    await cb.record_failure(provider)
    await cb.record_failure(provider)

    # 应该还能通过
    await cb.check(provider)

    # 第三次失败 - 触发熔断
    await cb.record_failure(provider)

    # 现在应该抛出异常
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        await cb.check(provider)

    assert provider in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_breaker_auto_recovery():
    """测试：熔断器在恢复超时后应自动关闭"""
    cb = RedisCircuitBreaker(failure_threshold=2, recovery_timeout=2)

    provider = f"test_provider_{int(time.time())}"

    # 触发熔断
    await cb.record_failure(provider)
    await cb.record_failure(provider)

    # 确认熔断器打开
    with pytest.raises(CircuitBreakerOpenException):
        await cb.check(provider)

    # 等待恢复时间
    await asyncio.sleep(2.5)

    # 现在应该可以通过了
    await cb.check(provider)  # 不应抛出异常


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_failures():
    """测试：成功请求应清零失败计数"""
    cb = RedisCircuitBreaker(failure_threshold=3, recovery_timeout=5)

    provider = f"test_provider_{int(time.time())}"

    # 两次失败
    await cb.record_failure(provider)
    await cb.record_failure(provider)

    # 一次成功 - 应该清零
    await cb.record_success(provider)

    # 再次两次失败 - 不应触发熔断（计数已重置）
    await cb.record_failure(provider)
    await cb.record_failure(provider)

    # 应该还能通过
    await cb.check(provider)


@pytest.mark.asyncio
async def test_circuit_breaker_multi_worker_consistency():
    """
    测试：多 worker 环境下的全局一致性
    模拟多个 worker 同时记录失败，验证熔断器全局生效
    """
    cb1 = RedisCircuitBreaker(failure_threshold=3, recovery_timeout=5)
    cb2 = RedisCircuitBreaker(failure_threshold=3, recovery_timeout=5)

    provider = f"test_provider_{int(time.time())}"

    # Worker 1 记录失败
    await cb1.record_failure(provider)
    await cb1.record_failure(provider)

    # Worker 2 也应该看到失败计数
    await cb2.record_failure(provider)  # 第三次 - 应触发熔断

    # 两个 worker 都应该看到熔断器打开
    with pytest.raises(CircuitBreakerOpenException):
        await cb1.check(provider)

    with pytest.raises(CircuitBreakerOpenException):
        await cb2.check(provider)


@pytest.mark.asyncio
async def test_circuit_breaker_isolated_providers():
    """测试：不同 provider 的熔断器应该隔离"""
    cb = RedisCircuitBreaker(failure_threshold=2, recovery_timeout=5)

    provider1 = f"test_provider_1_{int(time.time())}"
    provider2 = f"test_provider_2_{int(time.time())}"

    # Provider 1 触发熔断
    await cb.record_failure(provider1)
    await cb.record_failure(provider1)

    # Provider 1 应该熔断
    with pytest.raises(CircuitBreakerOpenException):
        await cb.check(provider1)

    # Provider 2 应该正常
    await cb.check(provider2)  # 不应抛出异常


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
