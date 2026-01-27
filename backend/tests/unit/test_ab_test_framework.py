"""
Unit tests for A/B Testing Framework
A/B测试框架单元测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.models.experiment import (
    ABExperiment,
    ABExperimentVariant,
    ExperimentStatus,
)


@pytest.fixture
def db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def ab_framework(db_session):
    """Create AB test framework instance"""
    from app.core.config import settings
    return ABTestFrameworkEnhanced(db_session, settings)


@pytest.mark.asyncio
async def test_create_experiment(ab_framework: ABTestFrameworkEnhanced):
    """Test creating a new experiment"""
    # Mock experiment creation
    with patch.object(ab_framework, '_save_to_db') as mock_save:
        mock_exp = Mock(spec=ABExperiment)
        mock_exp.id = "test-exp-1"
        mock_exp.name = "Test Experiment"
        mock_exp.status = ExperimentStatus.CREATED

        mock_save.return_value = mock_exp

        result = await ab_framework.create_experiment(
            name="Test Experiment",
            description="Test description",
            hypothesis="Test hypothesis",
            variants=[
                {"name": "control", "weight": 0.5},
                {"name": "treatment", "weight": 0.5}
            ],
            metrics=["success"]
        )

        assert result.name == "Test Experiment"
        assert result.status == ExperimentStatus.CREATED
        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_assign_variant_consistency(ab_framework: ABTestFrameworkEnhanced):
    """Test that variant assignment is consistent for same user"""
    experiment_id = "test-exp-1"
    user_id = "test-user-1"

    with patch.object(ab_framework, '_get_or_create_assignment') as mock_get:
        mock_variant = Mock(spec=ABExperimentVariant)
        mock_variant.id = "variant-1"
        mock_variant.variant_name = "control"

        mock_get.return_value = mock_variant

        # First assignment
        variant1, is_new1 = await ab_framework.assign_variant(experiment_id, user_id)

        # Second assignment (should return same variant)
        variant2, is_new2 = await ab_framework.assign_variant(experiment_id, user_id)

        assert variant1.variant_name == variant2.variant_name
        assert is_new1 is True  # First time
        assert is_new2 is False  # Cached


@pytest.mark.asyncio
async def test_record_metric(ab_framework: ABTestFrameworkEnhanced):
    """Test recording experiment metrics"""
    with patch.object(ab_framework, '_save_metric') as mock_save:
        await ab_framework.record_metric(
            experiment_id="test-exp-1",
            variant_id="variant-1",
            metric_name="success",
            metric_value=1.0,
            metric_type="success",
            user_id="test-user-1"
        )

        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_get_experiment_stats(ab_framework: ABTestFrameworkEnhanced):
    """Test getting experiment statistics"""
    with patch.object(ab_framework, '_calculate_stats') as mock_calc:
        mock_calc.return_value = {
            "total_users": 100,
            "control_count": 50,
            "treatment_count": 50,
            "control_success_rate": 0.6,
            "treatment_success_rate": 0.7
        }

        stats = await ab_framework.get_experiment_stats("test-exp-1")

        assert stats["total_users"] == 100
        assert stats["treatment_success_rate"] > stats["control_success_rate"]
