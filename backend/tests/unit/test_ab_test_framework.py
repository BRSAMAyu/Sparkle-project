"""Unit tests for ABTestFrameworkEnhanced."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.models.experiment import ExperimentStatus


@pytest.fixture
def db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def redis_client():
    client = AsyncMock()
    client.set = AsyncMock()
    return client


@pytest.fixture
def ab_framework(db_session, redis_client):
    return ABTestFrameworkEnhanced(db_session, redis_client)


@pytest.mark.asyncio
async def test_create_experiment(ab_framework: ABTestFrameworkEnhanced, db_session):
    ab_framework._cache_experiment_config = AsyncMock()

    result = await ab_framework.create_experiment(
        name="Test Experiment",
        description="Test description",
        hypothesis="Test hypothesis",
        variants=[
            {"name": "control", "is_control": True, "weight": 0.5},
            {"name": "treatment", "is_control": False, "weight": 0.5},
        ],
        metrics=["success"],
        created_by="user-1",
    )

    assert result.name == "Test Experiment"
    assert result.status == ExperimentStatus.CREATED
    assert db_session.add.called
    assert db_session.flush.await_count == 1
    assert db_session.commit.await_count == 1
    ab_framework._cache_experiment_config.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_variant_consistency(ab_framework: ABTestFrameworkEnhanced, db_session):
    existing_assignment = SimpleNamespace(variant_id="variant-1")
    existing_variant = SimpleNamespace(id="variant-1", variant_name="control")
    db_session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: existing_assignment,
    )
    db_session.get.return_value = existing_variant

    variant, is_new = await ab_framework.assign_variant("exp-1", "user-1")

    assert variant.variant_name == "control"
    assert is_new is False
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_metric(ab_framework: ABTestFrameworkEnhanced, db_session):
    await ab_framework.record_metric(
        experiment_id="exp-1",
        variant_id="variant-1",
        metric_name="success",
        metric_value=1.0,
        metric_type="success",
        user_id="user-1",
    )

    assert db_session.add.called
    assert db_session.commit.await_count == 1


@pytest.mark.asyncio
async def test_get_experiment_stats(ab_framework: ABTestFrameworkEnhanced, db_session):
    experiment = SimpleNamespace(
        id="exp-1",
        name="Experiment",
        status=ExperimentStatus.RUNNING,
        start_date=None,
        sample_size_target=100,
        variants=[
            SimpleNamespace(id="v1", variant_name="control", is_control=True),
            SimpleNamespace(id="v2", variant_name="treatment", is_control=False),
        ],
    )
    db_session.get.return_value = experiment

    row1 = SimpleNamespace(count=30, success_rate=0.5, avg_latency=120.0)
    row2 = SimpleNamespace(count=40, success_rate=0.7, avg_latency=110.0)
    db_session.execute.side_effect = [
        SimpleNamespace(one=lambda: row1),
        SimpleNamespace(one=lambda: row2),
    ]

    stats = await ab_framework.get_experiment_stats("exp-1")

    assert stats["sample_size_collected"] == 70
    assert stats["completion_percentage"] == 70.0
    assert len(stats["variants"]) == 2
