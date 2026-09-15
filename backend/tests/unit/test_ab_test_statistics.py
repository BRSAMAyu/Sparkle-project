"""
Unit tests for A/B Test Statistics
A/B测试统计分析单元测试
"""
import pytest
import numpy as np
from app.learning.statistics import ABTestStatistics


@pytest.fixture
def stats():
    """Create statistics instance"""
    return ABTestStatistics()


class TestTTest:
    """Test t-test implementation"""

    def test_t_test_significant_difference(self, stats: ABTestStatistics):
        """Test t-test with significant difference"""
        control = [1.0, 1.2, 1.1, 1.3, 1.0]
        treatment = [1.5, 1.6, 1.4, 1.7, 1.5]

        result = stats.t_test(control, treatment, alpha=0.05)

        assert result["test_type"] == "welch_t_test"
        assert result["is_significant"] is True
        assert result["p_value"] < 0.05
        assert result["effect_size"]["cohens_d"] > 0

    def test_t_test_no_significant_difference(self, stats: ABTestStatistics):
        """Test t-test without significant difference"""
        control = [1.0, 1.1, 1.0, 1.2, 1.1]
        treatment = [1.1, 1.0, 1.1, 1.0, 1.1]

        result = stats.t_test(control, treatment, alpha=0.05)

        assert result["is_significant"] is False
        assert result["p_value"] > 0.05

    def test_t_test_confidence_interval(self, stats: ABTestStatistics):
        """Test t-test confidence interval"""
        control = [1.0, 1.0, 1.0, 1.0, 1.0]
        treatment = [2.0, 2.0, 2.0, 2.0, 2.0]

        result = stats.t_test(control, treatment, alpha=0.05)

        ci = result["confidence_interval"]
        assert len(ci) == 2
        assert ci[0] < ci[1]  # Lower bound < upper bound
        assert 0.9 < ci[0] < 1.1  # Around 1.0
        assert 0.9 < ci[1] < 1.1  # Around 1.0


class TestChiSquareTest:
    """Test chi-square test implementation"""

    def test_chi_square_significant(self, stats: ABTestStatistics):
        """Test chi-square test with significant difference"""
        result = stats.chi_square_test(
            control_success=50,
            control_total=100,
            treatment_success=70,
            treatment_total=100,
            alpha=0.05
        )

        assert result["test_type"] == "chi_square"
        assert result["is_significant"] is True
        assert result["p_value"] < 0.05
        assert result["relative_lift"] > 0

    def test_chi_square_not_significant(self, stats: ABTestStatistics):
        """Test chi-square test without significant difference"""
        result = stats.chi_square_test(
            control_success=50,
            control_total=100,
            treatment_success=52,
            treatment_total=100,
            alpha=0.05
        )

        assert result["is_significant"] is False
        assert result["p_value"] > 0.05

    def test_chi_square_relative_lift(self, stats: ABTestStatistics):
        """Test relative lift calculation"""
        result = stats.chi_square_test(
            control_success=50,
            control_total=100,
            treatment_success=75,
            treatment_total=100,
            alpha=0.05
        )

        # (0.75 - 0.50) / 0.50 = 0.50 = 50% lift
        assert result["relative_lift"] == 0.5


class TestSampleSizeCalculation:
    """Test sample size calculation"""

    def test_calculate_sample_size_basic(self, stats: ABTestStatistics):
        """Test basic sample size calculation"""
        result = stats.calculate_sample_size(
            baseline_rate=0.1,
            minimum_detectable_effect=0.1,  # 10% relative lift
            alpha=0.05,
            power=0.8
        )

        assert "sample_size_per_group" in result
        assert "total_sample_size" in result
        assert result["sample_size_per_group"] > 0
        assert result["total_sample_size"] == result["sample_size_per_group"] * 2

    def test_calculate_sample_size_small_effect(self, stats: ABTestStatistics):
        """Test that smaller effect requires larger sample"""
        result_small = stats.calculate_sample_size(
            baseline_rate=0.1,
            minimum_detectable_effect=0.05,  # 5% lift
            alpha=0.05,
            power=0.8
        )

        result_large = stats.calculate_sample_size(
            baseline_rate=0.1,
            minimum_detectable_effect=0.2,  # 20% lift
            alpha=0.05,
            power=0.8
        )

        # Smaller effect requires larger sample
        assert result_small["sample_size_per_group"] > result_large["sample_size_per_group"]


class TestSequentialAnalysis:
    """Test sequential analysis implementation"""

    def test_sequential_analysis_early_stop(self, stats: ABTestStatistics):
        """Test early stopping when significance reached"""
        control = [1.0] * 50  # Consistent low values
        treatment = [2.0] * 50  # Consistent high values

        result = stats.sequential_analysis(
            control_data=control,
            treatment_data=treatment,
            alpha=0.05,
            power=0.8,
            look_ahead=10
        )

        assert "can_stop_early" in result
        assert result["final_sample_size"] <= len(control)

    def test_sequential_analysis_continuation(self, stats: ABTestStatistics):
        """Test continuation when no significance"""
        control = [1.0, 1.1, 1.0, 1.1, 1.0]
        treatment = [1.1, 1.0, 1.1, 1.0, 1.1]

        result = stats.sequential_analysis(
            control_data=control,
            treatment_data=treatment,
            alpha=0.05,
            power=0.8,
            look_ahead=5
        )

        assert result["can_stop_early"] is False
        assert result["final_decision"] == "continue"
