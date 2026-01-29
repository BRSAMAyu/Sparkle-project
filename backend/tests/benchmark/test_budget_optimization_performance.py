"""
Performance Benchmark Tests for Budget Optimization
预算优化性能基准测试

Tests performance characteristics:
1. UCB1 algorithm speed
2. Budget allocation calculation
3. ROI evaluation efficiency
4. Scalability with many context packs
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.budget_optimization_service import BudgetOptimizationService


@pytest.fixture
def db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def budget_service(db_session):
    """Create budget optimization service"""
    return BudgetOptimizationService(db_session)


@pytest.mark.benchmark
async def test_ucb1_allocation_performance(budget_service):
    """
    Benchmark UCB1 budget allocation
    UCB1预算分配性能基准
    """
    # Mock performance data for 10 context packs
    performance_data = {}
    for i in range(10):
        performance_data[f"pack-{i}"] = {
            "avg_reward": 0.5 + (i % 5) * 0.1,
            "run_count": 10 + i * 5,
            "avg_tokens_used": 100 + i * 10,
        }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        total_budget = 10000
        context_packs = list(performance_data.keys())

        start = time.time()
        allocation = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=total_budget,
            context_packs=context_packs,
            performance_window_days=7
        )
        elapsed = time.time() - start

        # Should be very fast (< 50ms)
        assert elapsed < 0.05

        # Verify allocation sums to budget
        assert abs(sum(allocation.values()) - total_budget) / total_budget < 0.01


@pytest.mark.benchmark
async def test_ucb1_with_many_packs(budget_service):
    """
    Benchmark UCB1 with 100 context packs
    UCB1处理100个上下文包性能基准
    """
    # Mock many context packs
    performance_data = {}
    for i in range(100):
        performance_data[f"pack-{i}"] = {
            "avg_reward": 0.5 + (i % 10) * 0.05,
            "run_count": i + 1,
            "avg_tokens_used": 100 + i * 5,
        }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        start = time.time()
        allocation = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=50000,
            context_packs=list(performance_data.keys()),
        )
        elapsed = time.time() - start

        # Should scale reasonably (< 200ms)
        assert elapsed < 0.2


@pytest.mark.benchmark
async def test_constraint_application_performance(budget_service):
    """
    Benchmark constraint checking and adjustment
    约束条件应用性能基准
    """
    performance_data = {
        "high_performer": {"avg_reward": 1.0, "run_count": 100, "avg_tokens_used": 50},
        "low_performer": {"avg_reward": 0.1, "run_count": 100, "avg_tokens_used": 200},
        "medium": {"avg_reward": 0.5, "run_count": 100, "avg_tokens_used": 100},
    }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        # Run optimization many times
        start = time.time()
        for _ in range(100):
            allocation = await budget_service.optimize_budget_allocation(
                user_id="test-user",
                total_budget=1000,
                context_packs=list(performance_data.keys()),
            )

            # Verify constraints
            for amount in allocation.values():
                assert amount >= 50  # Minimum (5% of 1000)
                assert amount <= 500  # Maximum (50% of 1000)

        elapsed = time.time() - start

        # 100 optimizations should be fast (< 2 seconds)
        assert elapsed < 2.0


@pytest.mark.benchmark
async def test_roi_calculation_performance(budget_service):
    """
    Benchmark ROI calculation
    ROI计算性能基准
    """
    performance_data = {
        "test_pack": {
            "avg_reward": 0.8,
            "run_count": 50,
            "avg_tokens_used": 150,
        }
    }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        start = time.time()
        for _ in range(100):
            roi = await budget_service.evaluate_roi(
                user_id="test-user",
                context_pack_id="test_pack",
                days=30
            )

            assert "roi" in roi
            assert roi["roi"] >= 0

        elapsed = time.time() - start

        # 100 ROI calculations should be fast (< 50ms)
        assert elapsed < 0.05


@pytest.mark.benchmark
async def test_performance_query_optimization(budget_service):
    """
    Benchmark performance data fetching with caching
    性能数据查询优化（缓存）
    """
    # Mock database query
    with patch.object(budget_service.db, "execute") as mock_execute:
        # Simulate query returning data
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = Mock(
            user_id="test-user",
            context_pack_id="pack-1",
            tokens_used=150,
            success=True
        )
        mock_execute.return_value = mock_result

        # First call (cache miss)
        start = time.time()
        perf1 = await budget_service._get_pack_performance(
            user_id="test-user",
            context_pack_ids=["pack-1"],
            days=7
        )
        time_miss = time.time() - start

        # Subsequent calls would use cache (if implemented)
        # For now, we just verify it's fast enough

        # Should be reasonably fast (< 10ms per query)
        assert time_miss < 0.01


@pytest.mark.asyncio
async def test_algorithm_correctness_vs_speed(budget_service):
    """
    Test that optimization doesn't sacrifice accuracy for speed
    测试优化不牺牲准确性
    """
    import numpy as np

    # Create synthetic data with known optimal allocation
    # Pack A: 80% success rate, should get ~50% budget
    # Pack B: 60% success rate, should get ~30% budget
    # Pack C: 40% success rate, should get ~20% budget

    performance_data = {
        "pack_a": {"avg_reward": 0.8, "run_count": 100},
        "pack_b": {"avg_reward": 0.6, "run_count": 100},
        "pack_c": {"avg_reward": 0.4, "run_count": 100},
    }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        allocation = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=1000,
            context_packs=list(performance_data.keys()),
        )

        # Higher reward should get more budget
        assert allocation["pack_a"] > allocation["pack_b"]
        assert allocation["pack_b"] > allocation["pack_c"]

        # But unexplored arms should get minimum exploration
        # (In this case, all have run_count=100, so exploration bonus is 0)


@pytest.mark.benchmark
async def test_realtime_budget_adjustment(budget_service):
    """
    Test real-time budget adjustment as performance changes
    测试性能变化时的实时预算调整
    """
    # Simulate changing performance over time
    performance_snapshots = []
    for i in range(5):
        snapshot = {
            "pack-1": {"avg_reward": 0.5 + i * 0.1, "run_count": 10},
            "pack-2": {"avg_reward": 0.5 - i * 0.1, "run_count": 10},
        }
        performance_snapshots.append(snapshot)

    allocations = []
    for performance in performance_snapshots:
        with patch.object(budget_service, "_get_pack_performance") as mock_perf:
            mock_perf.return_value = performance

            allocation = await budget_service.optimize_budget_allocation(
                user_id="test-user",
                total_budget=1000,
                context_packs=["pack-1", "pack-2"],
            )
            allocations.append(allocation)

    # Verify budget shifts toward better performing pack
    # As pack-1 improves, it should get more budget
    pack1_budgets = [a["pack-1"] for a in allocations]

    # Should see trend (allowing for noise due to exploration)
    assert pack1_budgets[-1] >= pack1_budgets[0] * 0.9  # At least maintain or increase


@pytest.mark.benchmark
async def test_concurrent_optimization_requests(budget_service):
    """
    Test handling multiple concurrent optimization requests
    测试并发优化请求处理
    """
    import asyncio

    async def optimize_request(request_id):
        performance_data = {
            "pack-1": {"avg_reward": 0.7, "run_count": 10},
        }

        with patch.object(budget_service, "_get_pack_performance") as mock_perf:
            mock_perf.return_value = performance_data

            return await budget_service.optimize_budget_allocation(
                user_id=f"user-{request_id}",
                total_budget=1000,
                context_packs=["pack-1"],
            )

    # Run 50 concurrent requests
    start = time.time()
    results = await asyncio.gather(*[optimize_request(i) for i in range(50)])
    elapsed = time.time() - start

    # All should complete
    assert len(results) == 50

    # Should be reasonably fast (< 1 second for 50 requests)
    assert elapsed < 1.0


@pytest.mark.benchmark
async def test_memory_efficiency_large_scale(budget_service):
    """
    Test memory efficiency with large-scale optimization
    大规模优化内存效率测试
    """
    import tracemalloc

    # Create large-scale scenario
    performance_data = {}
    for i in range(1000):
        performance_data[f"pack-{i}"] = {
            "avg_reward": 0.5 + (i % 10) * 0.05,
            "run_count": 10 + i,
            "avg_tokens_used": 100,
        }

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        tracemalloc.start()
        current, peak = tracemalloc.get_traced_memory()

        allocation = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=100000,
            context_packs=list(performance_data.keys()),
        )

        current_after, peak_after = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be reasonable
        memory_increase = (peak_after - peak) / 1024 / 1024
        assert memory_increase < 10  # < 10MB for 1000 packs


@pytest.mark.benchmark
async def test_budget_reallocation_speed(budget_service):
    """
    Test speed of reallocating budget when pack added/removed
    测试添加/删除上下文包时重分配速度
    """
    # Initial optimization with 10 packs
    initial_packs = [f"pack-{i}" for i in range(10)]
    performance_data = {p: {"avg_reward": 0.5, "run_count": 10} for p in initial_packs}

    with patch.object(budget_service, "_get_pack_performance") as mock_perf:
        mock_perf.return_value = performance_data

        # Initial allocation
        start = time.time()
        allocation1 = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=1000,
            context_packs=initial_packs,
        )
        time1 = time.time() - start

        # Add 10 more packs and reallocate
        new_packs = [f"pack-{i}" for i in range(10, 20)]
        all_packs = initial_packs + new_packs
        performance_data.update({p: {"avg_reward": 0.5, "run_count": 10} for p in new_packs})

        mock_perf.return_value = performance_data

        start = time.time()
        allocation2 = await budget_service.optimize_budget_allocation(
            user_id="test-user",
            total_budget=1000,
            context_packs=all_packs,
        )
        time2 = time.time() - start

        # Re-allocation should not be much slower
        # (UCB1 is O(n) where n is number of packs)
        assert time2 < time1 * 3  # At most 3x slower for 2x data
