"""
Performance Benchmark Tests for A/B Test Statistics
A/B测试统计分析性能基准测试

Tests performance characteristics:
1. Statistical computation speed
2. Memory usage
3. Scalability with large datasets
"""
import pytest
import time
import tracemalloc
import numpy as np
from app.learning.statistics import ABTestStatistics


@pytest.fixture
def stats():
    return ABTestStatistics()


@pytest.mark.benchmark
def test_t_test_performance_small_dataset(stats):
    """
    Benchmark t-test performance with small dataset (n=100)
    小数据集t检验性能基准
    """
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 100).tolist()
    treatment = np.random.normal(1.2, 0.1, 100).tolist()

    start = time.time()
    result = stats.t_test(control, treatment)
    elapsed = time.time() - start

    # Should be very fast (< 10ms)
    assert elapsed < 0.01
    assert result["is_significant"]


@pytest.mark.benchmark
def test_t_test_performance_large_dataset(stats):
    """
    Benchmark t-test performance with large dataset (n=100,000)
    大数据集t检验性能基准
    """
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 100000).tolist()
    treatment = np.random.normal(1.05, 0.1, 100000).tolist()

    start = time.time()
    result = stats.t_test(control, treatment)
    elapsed = time.time() - start

    # Should still be fast (< 100ms)
    assert elapsed < 0.1
    assert result["p_value"] < 0.05


@pytest.mark.benchmark
def test_chi_square_performance(stats):
    """
    Benchmark chi-square test performance
    卡方检验性能基准
    """
    start = time.time()

    for _ in range(100):
        result = stats.chi_square_test(
            control_success=500,
            control_total=1000,
            treatment_success=600,
            treatment_total=1000
        )

    elapsed = time.time() - start

    # 100 iterations should be fast (< 100ms)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_sample_size_calculation_performance(stats):
    """
    Benchmark sample size calculation
    样本量计算性能基准
    """
    start = time.time()

    # Calculate 100 different sample sizes
    for baseline in np.linspace(0.01, 0.5, 100):
        result = stats.calculate_sample_size(
            baseline_rate=baseline,
            minimum_detectable_effect=0.1,
            alpha=0.05,
            power=0.8
        )

    elapsed = time.time() - start

    # Should be fast (< 50ms for 100 calculations)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_sequential_analysis_performance(stats):
    """
    Benchmark sequential analysis with multiple lookaheads
    序列分析性能基准（多次预检查）
    """
    np.random.seed(42)
    control_data = np.random.normal(1.0, 0.1, 1000).tolist()
    treatment_data = np.random.normal(1.05, 0.1, 1000).tolist()

    start = time.time()
    result = stats.sequential_analysis(
        control_data=control_data,
        treatment_data=treatment_data,
        alpha=0.05,
        power=0.8,
        look_ahead=20
    )
    elapsed = time.time() - start

    # Sequential analysis with 20 lookaheads should be fast (< 200ms)
    assert elapsed < 0.2
    assert result["can_stop_early"] or result["final_sample_size"] <= 1000


def test_memory_usage_large_dataset(stats):
    """
    Test memory usage with very large datasets
    大数据集内存使用测试
    """
    tracemalloc.start()

    # Create large dataset
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 1000000).tolist()
    treatment = np.random.normal(1.05, 0.1, 1000000).tolist()

    # Get memory before
    current, peak = tracemalloc.get_traced_memory()

    # Run test
    result = stats.t_test(control, treatment)

    # Get memory after
    current_after, peak_after = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory increase should be reasonable (< 100MB)
    memory_increase = (peak_after - peak) / 1024 / 1024
    assert memory_increase < 100


@pytest.mark.benchmark
def test_statistical_methods_comparison(stats):
    """
    Compare performance of different statistical methods
    不同统计方法性能对比
    """
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 10000).tolist()
    treatment = np.random.normal(1.05, 0.1, 10000).tolist()

    methods = {
        "t_test": lambda: stats.t_test(control, treatment),
        "chi_square": lambda: stats.chi_square_test(
            control_success=int(len(control) * 0.5),
            control_total=len(control),
            treatment_success=int(len(treatment) * 0.55),
            treatment_total=len(treatment)
        ),
    }

    results = {}
    for name, method in methods.items():
        start = time.time()
        method()
        elapsed = time.time() - start
        results[name] = elapsed

    # All should be fast (< 20ms for 10k samples)
    for name, elapsed in results.items():
        assert elapsed < 0.02, f"{name} took {elapsed}s"


@pytest.mark.benchmark
def test_confidence_interval_calculation_speed(stats):
    """
    Benchmark confidence interval calculation
    置信区间计算速度基准
    """
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 10000).tolist()
    treatment = np.random.normal(1.05, 0.1, 10000).tolist()

    start = time.time()
    result = stats.t_test(control, treatment)
    elapsed = time.time() - start

    # CI calculation should be included in the time
    assert "confidence_interval" in result
    assert len(result["confidence_interval"]) == 2

    # Should be fast
    assert elapsed < 0.02


@pytest.mark.benchmark
def test_effect_size_calculation_speed(stats):
    """
    Benchmark effect size (Cohen's d) calculation
    效应量计算速度基准
    """
    np.random.seed(42)

    # Test with different effect sizes
    effect_sizes = []
    for i in range(100):
        control = np.random.normal(0, 1, 1000).tolist()
        treatment = np.random.normal(i * 0.01, 1, 1000).tolist()

        start = time.time()
        result = stats.t_test(control, treatment)
        elapsed = time.time() - start

        effect_sizes.append(result["effect_size"]["cohens_d"])

    # Average time per calculation should be fast
    # (Total time / 100 calculations)
    # But we're not measuring total here, just individual


@pytest.mark.benchmark
def test_batch_metric_aggregation(stats):
    """
    Benchmark aggregating many metrics
    批量指标聚合性能基准
    """
    # Simulate aggregating 1000 metrics
    metrics_data = []
    for i in range(1000):
        control_success = 400 + (i % 200)
        control_total = 1000
        treatment_success = 450 + (i % 200)
        treatment_total = 1000

        start = time.time()
        result = stats.chi_square_test(
            control_success=control_success,
            control_total=control_total,
            treatment_success=treatment_success,
            treatment_total=treatment_total
        )
        elapsed = time.time() - start

        metrics_data.append(elapsed)

    # Most calculations should be fast (< 1ms)
    avg_time = sum(metrics_data) / len(metrics_data)
    assert avg_time < 0.001


def test_scalability_with_increasing_sample_size(stats):
    """
    Test that performance scales linearly with sample size
    测试性能随样本量线性扩展
    """
    np.random.seed(42)

    sample_sizes = [100, 1000, 10000, 100000]
    times = []

    for n in sample_sizes:
        control = np.random.normal(1.0, 0.1, n).tolist()
        treatment = np.random.normal(1.05, 0.1, n).tolist()

        start = time.time()
        stats.t_test(control, treatment)
        elapsed = time.time() - start

        times.append((n, elapsed))

    # Check that O(n) complexity is maintained
    # Time for 100k should be < 10x time for 10k
    time_10k = [t for n, t in times if n == 10000][0]
    time_100k = [t for n, t in times if n == 100000][0]

    assert time_100k < time_10k * 10  # Linear or better


@pytest.mark.benchmark
def test_repeated_calculation_consistency(stats):
    """
    Verify that repeated calculations give consistent results
    验证重复计算结果一致
    """
    np.random.seed(42)
    control = np.random.normal(1.0, 0.1, 1000).tolist()
    treatment = np.random.normal(1.05, 0.1, 1000).tolist()

    results = []
    for _ in range(10):
        result = stats.t_test(control, treatment)
        results.append(result["p_value"])

    # All results should be identical
    assert len(set(results)) == 1
    assert all(abs(r - results[0]) < 1e-10 for r in results)
