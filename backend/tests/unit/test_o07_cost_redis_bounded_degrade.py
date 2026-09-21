"""O-07 · cost 预算核算 Redis 有界降级测试.

覆盖卡面 acceptance「Redis 故障不会无界成本」的 tier 预算面：
- Redis 缺失/故障 → 进程内保守累计继续闸门（fresh 时降级放行不变）；
- 降级期累计支出越过预算 → 闸门**真实关闭**（不再无界 fail-open）；
- Redis 恢复 → 降级态清除、回落 Redis 真值；
- ``COST_BUDGET_REDIS_FALLBACK_ENABLED=False`` → 保留旧 fail-open 行为
  （显式运维开关，非默认）。

fixture 模式与 test_cost_controller.py 同款（sys.modules 换 app.core.cache）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.core.cost_controller import BudgetCircuitBreaker, CostCategory


def _make_mock_redis(**overrides):
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.incrbyfloat = AsyncMock()
    redis.expire = AsyncMock()
    for k, v in overrides.items():
        setattr(redis, k, AsyncMock(return_value=v))
    return redis


def _patch_cache(mock_redis):
    mock_cache = MagicMock()
    mock_cache.redis = mock_redis
    return patch.dict("sys.modules", {"app.core.cache": MagicMock(cache_service=mock_cache)})


class TestBoundedDegradeOnRedisMissing:
    async def test_fresh_breaker_within_budget_degraded_open(self):
        """无 Redis + 无本地累计 → 仍在预算内（可用性保留；与既有语义一致）。"""
        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 10.0})
            assert await breaker.check_budget(CostCategory.LLM) is True

    async def test_local_spend_crossing_budget_closes_gate(self):
        """降级期累计越过预算 → 闸门关闭（有界，不再无界 fail-open）。"""
        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 1.0})
            await breaker.record_spend(CostCategory.LLM, 0.6, operation="chat")
            assert await breaker.check_budget(CostCategory.LLM) is True  # 0.6 < 1.0
            await breaker.record_spend(CostCategory.LLM, 0.6, operation="chat")
            # 1.2 >= 1.0：降级态下成本仍有上界
            assert await breaker.check_budget(CostCategory.LLM) is False
            assert await breaker.check_and_trip(CostCategory.LLM) is True

    async def test_read_returns_local_total(self):
        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 10.0})
            await breaker.record_spend(CostCategory.LLM, 0.25)
            assert await breaker.read_daily_spend(CostCategory.LLM) == pytest.approx(0.25)
            assert breaker.daily_spend(CostCategory.LLM) == pytest.approx(0.25)

    async def test_zero_spend_not_recorded(self):
        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 1.0})
            await breaker.record_spend(CostCategory.LLM, 0.0, operation="noop")
            assert breaker.daily_spend(CostCategory.LLM) == 0.0


class TestBoundedDegradeOnRedisError:
    async def test_get_error_falls_back_to_local(self):
        redis = _make_mock_redis()
        redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
        with _patch_cache(redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 1.0})
            # 先在降级期累计（incrbyfloat 失败也累计）
            breaker._enter_degraded(CostCategory.LLM)
            breaker._local_spend[CostCategory.LLM] = 1.5
            assert await breaker.check_budget(CostCategory.LLM) is False

    async def test_record_error_accumulates_locally(self):
        redis = _make_mock_redis()
        redis.incrbyfloat = AsyncMock(side_effect=ConnectionError("redis down"))
        with _patch_cache(redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 0.5})
            await breaker.record_spend(CostCategory.LLM, 0.4, operation="chat")
            await breaker.record_spend(CostCategory.LLM, 0.4, operation="chat")
            # 本地累计 0.8；读路径 get 也失败 → 本地值参与闸门（0.8 >= 0.5 关闭）
            redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
            assert await breaker.check_budget(CostCategory.LLM) is False

    async def test_recovery_clears_degraded_state(self):
        redis = _make_mock_redis()
        redis.incrbyfloat = AsyncMock(side_effect=ConnectionError("redis down"))
        with _patch_cache(redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 1.0})
            await breaker.record_spend(CostCategory.LLM, 2.0, operation="chat")  # 降级累计 2.0
            assert CostCategory.LLM in breaker._redis_degraded

            # Redis 恢复：get 返回真值 0.1 → 降级态清除，Redis 真值接管
            redis.get = AsyncMock(return_value=b"0.1")
            assert await breaker.check_budget(CostCategory.LLM) is True
            assert CostCategory.LLM not in breaker._redis_degraded
            assert breaker.daily_spend(CostCategory.LLM) == 0.0
            assert await breaker.read_daily_spend(CostCategory.LLM) == pytest.approx(0.1)

    async def test_redis_healthy_normal_accounting_unchanged(self):
        """Redis 健康时行为与既有语义完全一致（防回归）。"""
        redis = _make_mock_redis(get=b"15.0")
        with _patch_cache(redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 10.0})
            assert await breaker.check_and_trip(CostCategory.LLM) is True
            assert breaker.daily_spend(CostCategory.LLM) == 0.0  # 未进降级态


class TestFallbackToggle:
    async def test_disabled_fallback_keeps_legacy_fail_open(self, monkeypatch):
        monkeypatch.setattr(settings, "COST_BUDGET_REDIS_FALLBACK_ENABLED", False)
        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 1.0})
            await breaker.record_spend(CostCategory.LLM, 5.0, operation="chat")
            # 显式关闭降级 → 旧 fail-open 语义（读 0.0，放行）
            assert await breaker.check_budget(CostCategory.LLM) is True
            assert CostCategory.LLM not in breaker._redis_degraded
