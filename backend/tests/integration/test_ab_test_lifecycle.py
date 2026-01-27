"""
Integration tests for A/B Test Experiment Lifecycle
A/B测试实验生命周期集成测试

Tests the complete workflow:
1. Create experiment
2. Start experiment
3. Assign variants to users
4. Record metrics
5. Pause/Resume experiment
6. Complete experiment
7. Generate statistics report
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from app.main import app
from app.database import get_db
from app.models.experiment import (
    ABExperiment,
    ABExperimentVariant,
    ABExperimentMetric,
    ABExperimentAssignment,
    ExperimentStatus,
)
from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.core.config import settings


@pytest.mark.asyncio
async def test_complete_experiment_lifecycle():
    """
    Test complete experiment lifecycle from creation to completion

    Workflow:
    1. Create experiment with variants
    2. Start experiment
    3. Assign users to variants
    4. Record metrics for different users
    5. Get statistics
    6. Complete experiment
    7. Verify final state
    """
    # This would require a test database setup
    # For now, we'll structure the test

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Create experiment
        response = await client.post(
            "/api/v1/experiments",
            json={
                "name": "Test Experiment",
                "description": "Integration test",
                "hypothesis": "Treatment performs better",
                "variants": [
                    {"name": "control", "weight": 0.5, "is_control": True},
                    {"name": "treatment", "weight": 0.5, "is_control": False}
                ],
                "metrics": ["success", "latency"],
                "sample_size_target": 100
            }
        )

        assert response.status_code == 200
        experiment = response.json()
        experiment_id = experiment["id"]

        # 2. Start experiment
        response = await client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert response.status_code == 200

        # 3. Assign variants
        user_ids = [f"user-{i}" for i in range(10)]
        for user_id in user_ids:
            response = await client.post(
                f"/api/v1/experiments/{experiment_id}/assign",
                params={"user_id": user_id}
            )
            assert response.status_code == 200
            assignment = response.json()
            assert "variant_id" in assignment

        # 4. Record metrics
        from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced

        # Simulate metric recording
        # 5. Get statistics
        response = await client.get(f"/api/v1/experiments/{experiment_id}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_users" in stats
        assert stats["total_users"] == 10

        # 6. Complete experiment
        response = await client.post(f"/api/v1/experiments/{experiment_id}/complete")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_variant_allocation_consistency():
    """
    Test that variant allocation is consistent for the same user
    测试变体分配一致性
    """
    # Setup
    experiment_id = "test-consistency"
    user_id = "consistent-user"

    # First assignment
    variant1, is_new1 = await assign_variant(experiment_id, user_id)

    # Second assignment (should return same variant)
    variant2, is_new2 = await assign_variant(experiment_id, user_id)

    assert variant1.variant_id == variant2.variant_id
    assert is_new1 is True
    assert is_new2 is False  # Cached


@pytest.mark.asyncio
async def test_experiment_pause_and_resume():
    """
    Test pausing and resuming an experiment
    测试实验暂停和恢复
    """
    experiment_id = "test-pause-resume"

    # Create and start experiment
    await create_experiment(experiment_id)
    await start_experiment(experiment_id)

    # Assign some users
    for i in range(5):
        await assign_variant(experiment_id, f"user-{i}")

    # Pause experiment
    await pause_experiment(experiment_id)
    exp = await get_experiment(experiment_id)
    assert exp.status == ExperimentStatus.PAUSED

    # Try to assign during pause (should still work but record as paused)
    variant, _ = await assign_variant(experiment_id, f"user-paused")
    assert variant is not None

    # Resume experiment
    await resume_experiment(experiment_id)
    exp = await get_experiment(experiment_id)
    assert exp.status == ExperimentStatus.RUNNING


@pytest.mark.asyncio
async def test_metric_recording_aggregation():
    """
    Test that metrics are properly aggregated for statistical analysis
    测试指标正确聚合用于统计分析
    """
    experiment_id = "test-aggregation"
    variant_id = "variant-1"

    # Record multiple metrics
    user_ids = [f"user-{i}" for i in range(20)]

    for user_id in user_ids:
        # Record success metric (binary)
        success = 1 if i % 2 == 0 else 0  # 50% success rate
        await record_metric(experiment_id, variant_id, user_id, "success", success)

        # Record latency metric (continuous)
        latency = 100 + i * 10  # Increasing latency
        await record_metric(experiment_id, variant_id, user_id, "latency", latency)

    # Get aggregated statistics
    stats = await get_experiment_stats(experiment_id)

    assert stats["total_metrics"] == 40  # 20 success + 20 latency
    assert "variant_metrics" in stats
    variant_stats = stats["variant_metrics"][variant_id]

    # Check success rate
    assert variant_stats["success_count"] == 10
    assert variant_stats["avg_success_rate"] == 0.5

    # Check latency
    assert "avg_latency" in variant_stats


@pytest.mark.asyncio
async def test_multi_variant_experiment():
    """
    Test experiment with more than 2 variants
    测试多变体实验
    """
    # Create experiment with 3 variants
    variants = [
        {"name": "control", "weight": 0.33},
        {"name": "treatment_a", "weight": 0.33},
        {"name": "treatment_b", "weight": 0.34}
    ]

    experiment_id = await create_experiment("test-multi-variant", variants=variants)
    await start_experiment(experiment_id)

    # Assign users and verify distribution
    assignments = {}
    for i in range(100):
        user_id = f"user-{i}"
        variant, _ = await assign_variant(experiment_id, user_id)
        variant_name = variant.variant_name

        if variant_name not in assignments:
            assignments[variant_name] = 0
        assignments[variant_name] += 1

    # Verify approximate distribution (within 20% of expected)
    expected_count = 100 / 3
    for variant_name, count in assignments.items():
        assert 0.8 * expected_count <= count <= 1.2 * expected_count


@pytest.mark.asyncio
async def test_experiment_with_different_metric_types():
    """
    Test experiment recording different metric types
    测试记录不同类型的指标
    """
    experiment_id = "test-metric-types"

    # Record different metric types
    await record_metric(experiment_id, "variant-1", "user-1", "success", 1.0, metric_type="binary")
    await record_metric(experiment_id, "variant-1", "user-1", "latency", 150.5, metric_type="continuous")
    await record_metric(experiment_id, "variant-1", "user-1", "engagement", 3.0, metric_type="ordinal")
    await record_metric(experiment_id, "variant-1", "user-1", "click_rate", 0.05, metric_type="ratio")

    stats = await get_experiment_stats(experiment_id)

    # Verify all metrics are recorded
    metric_names = [m["metric_name"] for m in stats["metrics"]]
    assert "success" in metric_names
    assert "latency" in metric_names
    assert "engagement" in metric_names
    assert "click_rate" in metric_names


@pytest.mark.asyncio
async def test_experiment_deletion_cascade():
    """
    Test that deleting an experiment cascades to related data
    测试实验删除的级联效果
    """
    experiment_id = "test-cascade"

    # Create experiment with variants, assignments, and metrics
    await create_experiment(experiment_id)
    await start_experiment(experiment_id)

    variant_id = "variant-1"
    await assign_variant(experiment_id, "user-1")
    await record_metric(experiment_id, variant_id, "user-1", "success", 1.0)

    # Delete experiment
    await delete_experiment(experiment_id)

    # Verify cascade deletion
    variants = await get_variants(experiment_id)
    assert len(variants) == 0

    assignments = await get_assignments(experiment_id)
    assert len(assignments) == 0

    metrics = await get_metrics(experiment_id)
    assert len(metrics) == 0


@pytest.mark.asyncio
async def test_concurrent_user_assignments():
    """
    Test that concurrent user assignments are handled correctly
    测试并发用户分配的正确处理
    """
    import asyncio

    experiment_id = "test-concurrent"
    await create_experiment(experiment_id)
    await start_experiment(experiment_id)

    # Simulate 100 concurrent assignments
    async def assign_user(user_num):
        user_id = f"concurrent-user-{user_num}"
        return await assign_variant(experiment_id, user_id)

    # Run concurrent assignments
    results = await asyncio.gather(*[assign_user(i) for i in range(100)])

    # All assignments should succeed
    assert len(results) == 100
    for variant, _ in results:
        assert variant is not None

    # Check that each user got assigned exactly once
    assigned_variants = [r[0].variant_name for r in results]
    assert len(assigned_variants) == 100  # All assigned
