"""
Unit tests for Budget Optimization Service
预算优化服务单元测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.services.budget_optimization_service import BudgetOptimizationService
from app.models.context_pack import ContextPackRun


@pytest.fixture
def db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def budget_service(db_session):
    """Create budget optimization service instance"""
    return BudgetOptimizationService(db_session)


@pytest.mark.asyncio
async def test_optimize_budget_allocation(budget_service: BudgetOptimizationService):
    """Test optimizing budget allocation across context packs"""
    user_id = "test-user-1"
    total_budget = 1000
    context_packs = ["pack-1", "pack-2", "pack-3"]

    with patch.object(budget_service, '_get_pack_performance') as mock_perf:
        # Mock performance data
        mock_perf.return_value = {
            "pack-1": {
                "avg_reward": 0.7,
                "run_count": 10,
                "avg_tokens_used": 100
            },
            "pack-2": {
                "avg_reward": 0.5,
                "run_count": 5,
                "avg_tokens_used": 150
            },
            "pack-3": {
                "avg_reward": 0.0,  # No data yet
                "run_count": 0,
                "avg_tokens_used": 100
            }
        }

        allocation = await budget_service.optimize_budget_allocation(
            user_id=user_id,
            total_budget=total_budget,
            context_packs=context_packs,
            performance_window_days=7
        )

        # Verify allocation
        assert "pack-1" in allocation
        assert "pack-2" in allocation
        assert "pack-3" in allocation

        # Sum should not exceed total budget
        total_allocated = sum(allocation.values())
        assert total_allocated <= total_budget

        # pack-1 should get more than pack-2 (higher reward)
        assert allocation["pack-1"] > allocation["pack-2"]

        # pack-3 should get minimum (no data, but unexplored)
        assert allocation["pack-3"] >= int(total_budget * 0.05)  # Minimum 5%


@pytest.mark.asyncio
async def test_optimize_budget_with_constraints(budget_service: BudgetOptimizationService):
    """Test that budget constraints are applied"""
    user_id = "test-user-2"
    total_budget = 1000
    context_packs = ["pack-1", "pack-2"]

    with patch.object(budget_service, '_get_pack_performance') as mock_perf:
        # Mock very high performance for pack-1
        mock_perf.return_value = {
            "pack-1": {
                "avg_reward": 1.0,
                "run_count": 100,
                "avg_tokens_used": 50
            },
            "pack-2": {
                "avg_reward": 0.0,
                "run_count": 0,
                "avg_tokens_used": 100
            }
        }

        allocation = await budget_service.optimize_budget_allocation(
            user_id=user_id,
            total_budget=total_budget,
            context_packs=context_packs
        )

        # Verify maximum constraint (50%)
        max_allocation = max(allocation.values())
        assert max_allocation <= int(total_budget * 0.5)

        # Verify minimum constraint (5%)
        min_allocation = min(allocation.values())
        assert min_allocation >= int(total_budget * 0.05)


@pytest.mark.asyncio
async def test_evaluate_roi(budget_service: BudgetOptimizationService):
    """Test ROI evaluation for a context pack"""
    user_id = "test-user-3"
    context_pack_id = "pack-roi"

    with patch.object(budget_service, '_get_pack_performance') as mock_perf:
        mock_perf.return_value = {
            context_pack_id: {
                "avg_reward": 0.8,
                "success_rate": 0.8,
                "run_count": 10,
                "avg_tokens_used": 100
            }
        }

        roi_result = await budget_service.evaluate_roi(
            user_id=user_id,
            context_pack_id=context_pack_id,
            days=30
        )

        assert "roi" in roi_result
        assert "learning_effect" in roi_result
        assert "token_cost" in roi_result
        assert "success_rate" in roi_result

        # ROI should be positive
        assert roi_result["roi"] > 0


@pytest.mark.asyncio
async def test_get_pack_performance_no_data(budget_service: BudgetOptimizationService):
    """Test performance data for pack with no history"""
    user_id = "test-user-4"
    context_packs = ["new-pack"]

    with patch.object(budget_service.db, 'execute') as mock_execute:
        # Empty result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_execute.return_value = mock_result

        perf = await budget_service._get_pack_performance(
            user_id=user_id,
            context_pack_ids=context_packs,
            days=7
        )

        # Should return default values for new pack
        assert "new-pack" in perf
        assert perf["new-pack"]["avg_reward"] == 0.5  # Default
        assert perf["new-pack"]["run_count"] == 0
