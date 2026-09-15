"""
Core: testing / infra
Phase: adapt
Stage: T6.4.2-4 — RAG/Aurora cost monitoring + budget circuit breaker

Tests cost recording, daily budget enforcement, and circuit breaker tripping.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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


class TestCostControllerMetrics:
    """Test Prometheus metrics registration."""

    def test_rag_cost_metric_exists(self):
        from app.core.cost_controller import COST_ESTIMATED_TOTAL
        COST_ESTIMATED_TOTAL.labels(category="rag", operation="pgvector_search").inc(0.001)

    def test_aurora_cost_metric_exists(self):
        from app.core.cost_controller import COST_ESTIMATED_TOTAL
        COST_ESTIMATED_TOTAL.labels(category="aurora", operation="l3_full_core").inc(0.005)

    def test_budget_gauge_exists(self):
        from app.core.cost_controller import COST_DAILY_BUDGET_USD
        COST_DAILY_BUDGET_USD.labels(category="llm").set(10.0)

    def test_circuit_trips_metric_exists(self):
        from app.core.cost_controller import BUDGET_CIRCUIT_TRIPS
        BUDGET_CIRCUIT_TRIPS.labels(category="aurora").inc()


class TestBudgetCircuitBreaker:
    """Test budget circuit breaker logic."""

    def test_default_budgets(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory
        breaker = BudgetCircuitBreaker()
        assert breaker.get_budget(CostCategory.LLM) == 10.0
        assert breaker.get_budget(CostCategory.RAG) == 2.0
        assert breaker.get_budget(CostCategory.AURORA) == 5.0

    def test_custom_budgets(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory
        breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 50.0})
        assert breaker.get_budget(CostCategory.LLM) == 50.0

    @pytest.mark.asyncio
    async def test_within_budget_when_no_spend(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            breaker = BudgetCircuitBreaker()
            within = await breaker.check_budget(CostCategory.LLM)
            assert within is True

    @pytest.mark.asyncio
    async def test_over_budget_trips(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        mock_redis = _make_mock_redis(get=b"15.0")
        with _patch_cache(mock_redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 10.0})
            over = await breaker.check_and_trip(CostCategory.LLM)
            assert over is True

    @pytest.mark.asyncio
    async def test_record_spend_increments_redis(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            breaker = BudgetCircuitBreaker()
            await breaker.record_spend(CostCategory.RAG, 0.5, operation="pgvector_search")

        mock_redis.incrbyfloat.assert_called_once()
        # Verify incrbyfloat was called with correct amount
        incr_args = mock_redis.incrbyfloat.call_args[0]
        assert incr_args[1] == 0.5  # amount matches the spend recorded
        assert "rag" in incr_args[0]  # key contains category name

        mock_redis.expire.assert_called_once()
        # Verify expire was called with 48-hour TTL
        expire_args = mock_redis.expire.call_args[0]
        assert expire_args[1] == 48 * 3600  # 48 hours in seconds

    @pytest.mark.asyncio
    async def test_record_spend_failure_graceful(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        mock_redis = _make_mock_redis()
        mock_redis.incrbyfloat = AsyncMock(side_effect=ConnectionError("redis down"))

        with _patch_cache(mock_redis):
            breaker = BudgetCircuitBreaker()
            await breaker.record_spend(CostCategory.LLM, 1.0, operation="chat")

    @pytest.mark.asyncio
    async def test_check_budget_without_redis_degrades_open(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        with _patch_cache(None):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.AURORA: 5.0})
            within = await breaker.check_budget(CostCategory.AURORA)

        assert within is True

    @pytest.mark.asyncio
    async def test_record_spend_without_redis_is_graceful(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        with _patch_cache(None):
            breaker = BudgetCircuitBreaker()
            await breaker.record_spend(CostCategory.RAG, 0.1, operation="pgvector_search")

    @pytest.mark.asyncio
    async def test_zero_budget_always_within(self):
        from app.core.cost_controller import BudgetCircuitBreaker, CostCategory

        mock_redis = _make_mock_redis(get=b"9999.0")
        with _patch_cache(mock_redis):
            breaker = BudgetCircuitBreaker(budgets={CostCategory.LLM: 0.0})
            within = await breaker.check_budget(CostCategory.LLM)
            assert within is True


class TestRAGCostRecording:
    """Test record_rag_cost helper."""

    @pytest.mark.asyncio
    async def test_records_known_operation(self):
        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            from app.core.cost_controller import record_rag_cost
            cost = await record_rag_cost("pgvector_search", units=10)
            assert cost > 0

    @pytest.mark.asyncio
    async def test_unknown_operation_uses_default(self):
        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            from app.core.cost_controller import record_rag_cost
            cost = await record_rag_cost("unknown_op", units=1)
            assert cost == 0.0001


class TestAuroraCostRecording:
    """Test record_aurora_cost helper."""

    @pytest.mark.asyncio
    async def test_l3_cost(self):
        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            from app.core.cost_controller import record_aurora_cost
            cost = await record_aurora_cost("l3_full_core")
            assert cost == 0.005

    @pytest.mark.asyncio
    async def test_l0_free(self):
        mock_redis = _make_mock_redis()
        with _patch_cache(mock_redis):
            from app.core.cost_controller import record_aurora_cost
            cost = await record_aurora_cost("l0_rule")
            assert cost == 0.0

    @pytest.mark.asyncio
    async def test_budget_check_blocks_expensive(self):
        mock_redis = _make_mock_redis(get=b"10.0")
        with _patch_cache(mock_redis):
            from app.core.cost_controller import is_aurora_within_budget
            within = await is_aurora_within_budget()
            assert within is False
