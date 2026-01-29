"""
A/B Test Statistical Analysis Library
A/B测试统计分析库

Provides statistical methods for analyzing A/B test experiments including:
- Hypothesis testing (t-test, chi-square)
- Sample size calculation
- Sequential analysis
- Confidence intervals
- Effect size estimation
"""
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    stats = None
    HAS_SCIPY = False
import numpy as np


class ABTestStatistics:
    """A/B测试统计分析工具"""

    @staticmethod
    def t_test(
        control_data: list[float],
        treatment_data: list[float],
        alpha: float = 0.05,
    ) -> dict:
        """
        Independent sample t-test (Welch's t-test)

        Args:
            control_data: Control group data
            treatment_data: Treatment group data
            alpha: Significance level

        Returns:
            Dict with test results including:
            - t_statistic: T-statistic value
            - p_value: Two-tailed p-value
            - is_significant: Whether result is statistically significant
            - effect_size: Cohen's d effect size
            - confidence_interval: 95% CI for the difference
            - recommendation: Text recommendation
        """
        if not HAS_SCIPY:
            return {
                "error": "scipy is required for Welch's t-test",
                "test_type": "welch_t_test",
            }

        if len(control_data) == 0 or len(treatment_data) == 0:
            return {
                "error": "Both groups must have at least one observation",
                "test_type": "welch_t_test",
            }

        # Execute Welch's t-test (does not assume equal variance)
        t_statistic, p_value = stats.ttest_ind(
            control_data,
            treatment_data,
            equal_var=False,  # Welch's t-test
        )

        # Calculate effect size (Cohen's d)
        control_mean = np.mean(control_data)
        treatment_mean = np.mean(treatment_data)
        control_std = np.std(control_data, ddof=1)
        treatment_std = np.std(treatment_data, ddof=1)

        # Pooled standard deviation
        n1, n2 = len(control_data), len(treatment_data)
        pooled_std = np.sqrt(
            ((n1 - 1) * control_std**2 + (n2 - 1) * treatment_std**2) / (n1 + n2 - 2)
        )

        cohens_d = (treatment_mean - control_mean) / pooled_std if pooled_std > 0 else 0

        # Confidence interval for difference
        ci_diff = ABTestStatistics._confidence_interval_difference(
            control_data, treatment_data, alpha
        )

        # Determine significance
        is_significant = p_value < alpha

        return {
            "test_type": "welch_t_test",
            "t_statistic": float(t_statistic),
            "p_value": float(p_value),
            "alpha": alpha,
            "is_significant": is_significant,
            "effect_size": {
                "cohens_d": float(cohens_d),
                "interpretation": ABTestStatistics._interpret_cohens_d(cohens_d),
            },
            "control_mean": float(control_mean),
            "treatment_mean": float(treatment_mean),
            "mean_difference": float(treatment_mean - control_mean),
            "control_std": float(control_std),
            "treatment_std": float(treatment_std),
            "control_n": n1,
            "treatment_n": n2,
            "confidence_interval": ci_diff,
            "recommendation": ABTestStatistics._make_recommendation(
                is_significant, cohens_d, p_value
            ),
        }

    @staticmethod
    def chi_square_test(
        control_success: int,
        control_total: int,
        treatment_success: int,
        treatment_total: int,
        alpha: float = 0.05,
    ) -> dict:
        """
        Chi-square test for proportion comparison

        Args:
            control_success: Number of successes in control group
            control_total: Total observations in control group
            treatment_success: Number of successes in treatment group
            treatment_total: Total observations in treatment group
            alpha: Significance level

        Returns:
            Dict with test results
        """
        if not HAS_SCIPY:
            return {
                "error": "scipy is required for chi-square test",
                "test_type": "chi_square",
            }

        # Build contingency table
        control_failure = control_total - control_success
        treatment_failure = treatment_total - treatment_success

        contingency_table = [[control_success, control_failure],
                            [treatment_success, treatment_failure]]

        # Execute chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

        # Calculate proportions
        control_rate = control_success / control_total if control_total > 0 else 0
        treatment_rate = treatment_success / treatment_total if treatment_total > 0 else 0

        # Calculate confidence interval for difference using normal approximation
        se_diff = np.sqrt(
            (control_rate * (1 - control_rate) / control_total)
            + (treatment_rate * (1 - treatment_rate) / treatment_total)
        )
        z_critical = stats.norm.ppf(1 - alpha / 2)
        ci_diff = (
            (treatment_rate - control_rate) - z_critical * se_diff,
            (treatment_rate - control_rate) + z_critical * se_diff,
        )

        # Calculate relative lift
        relative_lift = (
            (treatment_rate - control_rate) / control_rate if control_rate > 0 else 0
        )

        is_significant = p_value < alpha

        return {
            "test_type": "chi_square",
            "chi2_statistic": float(chi2),
            "p_value": float(p_value),
            "alpha": alpha,
            "degrees_of_freedom": dof,
            "is_significant": is_significant,
            "control_rate": float(control_rate),
            "treatment_rate": float(treatment_rate),
            "absolute_difference": float(treatment_rate - control_rate),
            "relative_lift": float(relative_lift),
            "confidence_interval": ci_diff,
            "contingency_table": contingency_table,
            "expected_frequencies": expected.tolist(),
            "control_success": control_success,
            "control_total": control_total,
            "treatment_success": treatment_success,
            "treatment_total": treatment_total,
            "recommendation": ABTestStatistics._make_recommendation_proportion(
                is_significant, relative_lift, p_value
            ),
        }

    @staticmethod
    def calculate_sample_size(
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8,
        two_tailed: bool = True,
    ) -> dict:
        """
        Calculate required sample size for proportion test

        Args:
            baseline_rate: Baseline conversion rate (0-1)
            minimum_detectable_effect: Minimum detectable effect (relative, e.g., 0.1 for 10%)
            alpha: Significance level
            power: Statistical power (1-beta)
            two_tailed: Whether to use two-tailed test

        Returns:
            Dict with sample size calculation results
        """
        try:
            from statsmodels.stats.power import NormalIndPower
            from statsmodels.stats.proportion import proportion_effectsize
        except ImportError:
            # Fallback calculation using normal approximation
            return ABTestStatistics._calculate_sample_size_approx(
                baseline_rate, minimum_detectable_effect, alpha, power
            )

        # Calculate effect size
        target_rate = baseline_rate * (1 + minimum_detectable_effect)
        effect_size = proportion_effectsize(target_rate, baseline_rate)

        # Calculate sample size
        power_analysis = NormalIndPower()
        alpha_adjusted = alpha if two_tailed else alpha * 2

        sample_size_per_group = power_analysis.solve_power(
            effect_size=effect_size,
            alpha=alpha_adjusted,
            power=power,
            ratio=1.0,
            alternative="two-sided" if two_tailed else "larger",
        )

        # Round up
        sample_size_per_group = int(np.ceil(sample_size_per_group))
        total_sample_size = sample_size_per_group * 2

        return {
            "baseline_rate": float(baseline_rate),
            "target_rate": float(target_rate),
            "minimum_detectable_effect": float(minimum_detectable_effect),
            "effect_size": float(effect_size),
            "alpha": alpha,
            "power": power,
            "two_tailed": two_tailed,
            "sample_size_per_group": sample_size_per_group,
            "total_sample_size": total_sample_size,
            "estimated_duration_days": ABTestStatistics._estimate_duration(total_sample_size),
            "recommendation": ABTestStatistics._make_sample_size_recommendation(
                sample_size_per_group, total_sample_size, minimum_detectable_effect
            ),
        }

    @staticmethod
    def sequential_analysis(
        control_data: list[float],
        treatment_data: list[float],
        alpha: float = 0.05,
        power: float = 0.8,
        look_ahead: int = 10,
    ) -> dict:
        """
        Sequential analysis (supports early stopping)

        Args:
            control_data: Control group cumulative data
            treatment_data: Treatment group cumulative data
            alpha: Significance level
            power: Statistical power
            look_ahead: Number of interim analyses

        Returns:
            Dict with sequential analysis results
        """
        if not HAS_SCIPY:
            return {
                "error": "scipy is required for sequential analysis",
                "test_type": "sequential_analysis",
            }

        # Calculate boundaries
        boundaries = ABTestStatistics._calculate_sequential_boundaries(alpha, power, look_ahead)

        # Perform sequential tests
        results = []
        current_control = []
        current_treatment = []

        sample_size = min(len(control_data), len(treatment_data))
        check_interval = max(1, sample_size // look_ahead)

        for i in range(1, sample_size + 1):
            current_control.append(control_data[i - 1])
            current_treatment.append(treatment_data[i - 1])

            # Periodic checks
            if i % check_interval == 0 or i == sample_size:
                t_stat, p_value = stats.ttest_ind(
                    current_control,
                    current_treatment,
                    equal_var=False,
                )

                # Convert p-value to z-score (two-tailed)
                z_score = stats.norm.ppf(1 - p_value / 2) if p_value < 1 else 0

                # Check if boundaries crossed
                if z_score >= boundaries["upper"]:
                    decision = "reject_null"
                    can_stop = True
                elif z_score <= boundaries["lower"]:
                    decision = "accept_null"
                    can_stop = True
                else:
                    decision = "continue"
                    can_stop = False

                results.append(
                    {
                        "sample_size": i,
                        "t_statistic": float(t_stat),
                        "p_value": float(p_value),
                        "z_score": float(z_score),
                        "decision": decision,
                        "can_stop": can_stop,
                        "boundaries": boundaries,
                    }
                )

                if can_stop:
                    break

        return {
            "look_ahead": look_ahead,
            "alpha": alpha,
            "power": power,
            "final_sample_size": len(current_control),
            "can_stop_early": any(r["can_stop"] for r in results),
            "stopping_point": next(
                (r["sample_size"] for r in results if r["can_stop"]), None
            ),
            "final_decision": results[-1]["decision"],
            "analysis_steps": results,
            "recommendation": ABTestStatistics._make_sequential_recommendation(results[-1]),
        }

    @staticmethod
    def _confidence_interval_difference(
        control_data: list[float],
        treatment_data: list[float],
        alpha: float,
    ) -> tuple[float, float]:
        """Calculate confidence interval for difference"""
        if not HAS_SCIPY:
            return (0.0, 0.0)
        diff_mean = np.mean(treatment_data) - np.mean(control_data)
        n1, n2 = len(control_data), len(treatment_data)

        var1 = np.var(control_data, ddof=1)
        var2 = np.var(treatment_data, ddof=1)

        se_diff = np.sqrt(var1 / n1 + var2 / n2)

        # Use t-distribution for small samples
        df = n1 + n2 - 2
        t_critical = stats.t.ppf(1 - alpha / 2, df)

        margin_error = t_critical * se_diff
        return (float(diff_mean - margin_error), float(diff_mean + margin_error))

    @staticmethod
    def _interpret_cohens_d(cohens_d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    @staticmethod
    def _calculate_sequential_boundaries(
        alpha: float, power: float, look_ahead: int
    ) -> dict:
        """Calculate sequential analysis boundaries (O'Brien-Fleming)"""
        if not HAS_SCIPY:
            return {"upper": 0.0, "lower": 0.0, "alpha_spending": 0.0}
        from scipy.stats import norm

        # Calculate adjusted significance boundary
        alpha_spending = 2 * (1 - norm.ppf(1 - alpha / (2 * look_ahead)))

        return {
            "upper": float(norm.ppf(1 - alpha / 2)),
            "lower": float(norm.ppf(alpha / 2)),
            "alpha_spending": float(alpha_spending),
        }

    @staticmethod
    def _make_recommendation(is_significant: bool, cohens_d: float, p_value: float) -> str:
        """Generate recommendation"""
        if is_significant:
            if abs(cohens_d) >= 0.8:
                return "Strong recommendation to adopt treatment (large effect size)"
            elif abs(cohens_d) >= 0.5:
                return "Recommendation to adopt treatment (medium effect size)"
            else:
                return "Consider adopting treatment (small effect size, weigh costs)"
        else:
            return "Difference not significant, continue experiment or maintain control"

    @staticmethod
    def _make_recommendation_proportion(
        is_significant: bool, relative_lift: float, p_value: float
    ) -> str:
        """Generate proportion test recommendation"""
        if is_significant:
            if relative_lift >= 0.1:
                return f"Strong recommendation to adopt treatment ({relative_lift * 100:.1f}% lift)"
            elif relative_lift >= 0.05:
                return f"Recommendation to adopt treatment ({relative_lift * 100:.1f}% lift)"
            else:
                return f"Consider adopting treatment (small lift of {relative_lift * 100:.1f}%)"
        else:
            return "Difference not significant, continue collecting data"

    @staticmethod
    def _make_sample_size_recommendation(
        sample_per_group: int, total: int, mde: float
    ) -> str:
        """Generate sample size recommendation"""
        return f"Need {sample_per_group} samples per group (total {total}) to detect {mde * 100:.1f}% effect"

    @staticmethod
    def _make_sequential_recommendation(final_result: dict) -> str:
        """Generate sequential analysis recommendation"""
        if final_result["decision"] == "reject_null":
            return f"Significance reached at {final_result['sample_size']} samples, can stop early"
        elif final_result["decision"] == "accept_null":
            return f"No significant difference confirmed at {final_result['sample_size']} samples, can stop early"
        else:
            return "Stopping criteria not met, continue collecting data"

    @staticmethod
    def _estimate_duration(sample_size: int) -> int:
        """Estimate experiment duration in days"""
        daily_samples = 100  # Assumption
        return max(1, int(np.ceil(sample_size / daily_samples)))

    @staticmethod
    def _calculate_sample_size_approx(
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float,
        power: float,
    ) -> dict:
        """Fallback sample size calculation using normal approximation"""
        if not HAS_SCIPY:
            return {
                "error": "scipy is required for sample size approximation",
                "test_type": "sample_size",
            }
        from scipy.stats import norm

        target_rate = baseline_rate * (1 + minimum_detectable_effect)
        p_pooled = (baseline_rate + target_rate) / 2

        # Z-values
        z_alpha = norm.ppf(1 - alpha / 2)
        z_beta = norm.ppf(power)

        # Sample size formula
        numerator = (z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled)) +
                    z_beta * np.sqrt(baseline_rate * (1 - baseline_rate) +
                                    target_rate * (1 - target_rate)))**2
        denominator = (target_rate - baseline_rate) ** 2

        sample_size_per_group = int(np.ceil(numerator / denominator))
        total_sample_size = sample_size_per_group * 2

        return {
            "baseline_rate": float(baseline_rate),
            "target_rate": float(target_rate),
            "minimum_detectable_effect": float(minimum_detectable_effect),
            "alpha": alpha,
            "power": power,
            "sample_size_per_group": sample_size_per_group,
            "total_sample_size": total_sample_size,
            "estimated_duration_days": ABTestStatistics._estimate_duration(total_sample_size),
            "recommendation": ABTestStatistics._make_sample_size_recommendation(
                sample_size_per_group, total_sample_size, minimum_detectable_effect
            ),
        }
