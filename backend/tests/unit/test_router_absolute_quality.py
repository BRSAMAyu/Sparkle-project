from __future__ import annotations

from app.services.analytics.router_absolute_quality import (
    RouterAbsoluteQualityAnalyzer,
    _actual_mode,
    _belief_bucket,
    _belief_means_vector,
    _reward_value,
    _wilson_interval,
)


def _make_trace(*, actual_mode: str, reward: dict | None = None, belief_means: dict | None = None) -> dict:
    return {
        "actual_router_mode": actual_mode,
        "reward": reward or {},
        "belief_state_vector": belief_means or {},
        "router_snapshot": {"actual_router_mode": actual_mode},
    }


def _reward(positive: bool, signal_type: str = "task.completed") -> dict:
    return {
        "total_reward": 1.0 if positive else -1.0,
        "signal_type": signal_type,
        "is_censored": False,
    }


def _means(
    emotional: float = 0.5,
    task_aversion: float = 0.5,
    cognitive: float = 0.5,
    goal: float = 0.5,
    execution: float = 0.5,
    metacognition: float = 0.5,
    dissatisfaction: float = 0.5,
) -> dict:
    return {
        "emotional_block": {"mean": emotional, "variance": 0.15},
        "task_aversion": {"mean": task_aversion, "variance": 0.15},
        "cognitive_load": {"mean": cognitive, "variance": 0.15},
        "goal_clarity": {"mean": goal, "variance": 0.15},
        "execution_capacity": {"mean": execution, "variance": 0.15},
        "metacognition_accuracy": {"mean": metacognition, "variance": 0.15},
        "system_dissatisfaction": {"mean": dissatisfaction, "variance": 0.15},
    }


class TestBeliefBucket:
    def test_high_support_need(self):
        v = (0.8, 0.7, 0.7, 0.3, 0.3, 0.5, 0.6)
        assert _belief_bucket(v) == "high_support_need"

    def test_high_execution_ready(self):
        v = (0.2, 0.2, 0.3, 0.9, 0.8, 0.7, 0.2)
        assert _belief_bucket(v) == "high_execution_ready"

    def test_mixed_lean_support(self):
        v = (0.5, 0.5, 0.5, 0.4, 0.4, 0.5, 0.5)
        assert _belief_bucket(v) == "mixed_lean_support"

    def test_neutral(self):
        v = (0.35, 0.35, 0.35, 0.4, 0.4, 0.4, 0.35)
        assert _belief_bucket(v) == "neutral"


class TestRewardValue:
    def test_positive_reward(self):
        assert _reward_value(_make_trace(actual_mode="balanced", reward=_reward(True))) == 1.0

    def test_negative_reward(self):
        assert _reward_value(_make_trace(actual_mode="balanced", reward=_reward(False, "task.abandoned"))) == -1.0

    def test_censored_ignored(self):
        trace = _make_trace(
            actual_mode="balanced",
            reward={"total_reward": 0.5, "signal_type": "unknown", "is_censored": True},
        )
        assert _reward_value(trace) is None

    def test_excluded_signal_ignored(self):
        trace = _make_trace(
            actual_mode="balanced",
            reward={"total_reward": 0.3, "signal_type": "no_negative_followup_signal", "is_censored": False},
        )
        assert _reward_value(trace) is None

    def test_no_reward_dict(self):
        assert _reward_value(_make_trace(actual_mode="balanced")) is None


class TestWilsonInterval:
    def test_empty_interval(self):
        assert _wilson_interval(0, 0) == (0.0, 0.0)

    def test_interval_bounds_positive_rate(self):
        low, high = _wilson_interval(8, 10)
        assert 0.45 < low < 0.8
        assert 0.8 < high <= 1.0


class TestActualMode:
    def test_direct_field(self):
        assert _actual_mode(_make_trace(actual_mode="execution_first")) == "execution_first"

    def test_from_snapshot(self):
        trace = {"router_snapshot": {"actual_router_mode": "cognitive_first"}}
        assert _actual_mode(trace) == "cognitive_first"

    def test_from_action(self):
        trace = {"action_taken": {"mode": "balanced"}}
        assert _actual_mode(trace) == "balanced"

    def test_none_when_missing(self):
        assert _actual_mode({}) is None


class TestRouterAbsoluteQualityAnalyzer:
    def test_empty_traces(self):
        analyzer = RouterAbsoluteQualityAnalyzer(min_labeled_per_cell=3, min_mode_samples=1)
        report = analyzer.evaluate([])
        assert report.total_labeled_traces == 0
        assert "no_labeled_traces_with_belief_vectors" in report.blockers
        assert report.recommendation == "collect_more_labeled_traces"
        assert report.router_leverage_assessment == "indeterminate"

    def test_insufficient_data(self):
        analyzer = RouterAbsoluteQualityAnalyzer(min_labeled_per_cell=8, min_mode_samples=3)
        traces = [
            _make_trace(
                actual_mode="execution_first",
                reward=_reward(True),
                belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.8, execution=0.8),
            ),
        ]
        report = analyzer.evaluate(traces)
        assert report.total_labeled_traces == 1
        assert not report.overall_detectable
        assert report.router_leverage_assessment in ("indeterminate", "low")

    def test_detectable_effect_across_regions(self):
        analyzer = RouterAbsoluteQualityAnalyzer(
            min_labeled_per_cell=4,
            min_mode_samples=1,
            detectable_effect_min=0.05,
        )
        traces = []
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="execution_first",
                reward=_reward(True),
                belief_means=_means(emotional=0.9, task_aversion=0.8, cognitive=0.8, goal=0.2, dissatisfaction=0.7),
            ))
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="cognitive_first",
                reward=_reward(False, "task.abandoned"),
                belief_means=_means(emotional=0.9, task_aversion=0.8, cognitive=0.8, goal=0.2, dissatisfaction=0.7),
            ))
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="execution_first",
                reward=_reward(True),
                belief_means=_means(emotional=0.5, task_aversion=0.5, goal=0.5, execution=0.7),
            ))
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="cognitive_first",
                reward=_reward(False, "task.abandoned"),
                belief_means=_means(emotional=0.5, task_aversion=0.5, goal=0.5, execution=0.7),
            ))
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="balanced",
                reward=_reward(True),
                belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.9, execution=0.9),
            ))
        for _ in range(10):
            traces.append(_make_trace(
                actual_mode="execution_first",
                reward=_reward(False, "task.abandoned"),
                belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.9, execution=0.9),
            ))
        report = analyzer.evaluate(traces)
        assert report.total_labeled_traces == 60
        assert len(report.buckets) == 5
        assert report.router_leverage_assessment in ("high", "moderate")

    def test_no_effect_across_modes(self):
        analyzer = RouterAbsoluteQualityAnalyzer(
            min_labeled_per_cell=4,
            min_mode_samples=1,
            detectable_effect_min=0.10,
        )
        traces = []
        modes = ["execution_first", "balanced", "cognitive_first"]
        for i in range(30):
            mode = modes[i % 3]
            reward_val = 0.5 if i % 2 == 0 else -0.5
            traces.append(_make_trace(
                actual_mode=mode,
                reward=_reward(reward_val > 0, "task.completed" if reward_val > 0 else "task.abandoned"),
                belief_means=_means(emotional=0.5, task_aversion=0.5, goal=0.5, execution=0.5),
            ))
        report = analyzer.evaluate(traces)
        assert not report.overall_detectable

    def test_belief_means_vector(self):
        trace = _make_trace(
            actual_mode="balanced",
            belief_means=_means(emotional=0.3, task_aversion=0.4, cognitive=0.5, goal=0.7, execution=0.6),
        )
        vector = _belief_means_vector(trace)
        assert vector is not None
        assert len(vector) == 7

    def test_mixed_modes_with_rewards(self):
        analyzer = RouterAbsoluteQualityAnalyzer(min_labeled_per_cell=3, min_mode_samples=1)
        traces = [
            _make_trace(actual_mode="execution_first", reward=_reward(True), belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.8, execution=0.8)),
            _make_trace(actual_mode="execution_first", reward=_reward(True), belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.8, execution=0.8)),
            _make_trace(actual_mode="cognitive_first", reward=_reward(False, "task.abandoned"), belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.8, execution=0.8)),
            _make_trace(actual_mode="cognitive_first", reward=_reward(False, "task.abandoned"), belief_means=_means(emotional=0.2, task_aversion=0.2, goal=0.8, execution=0.8)),
        ]
        report = analyzer.evaluate(traces)
        assert report.total_labeled_traces == 4
        cell = report.buckets[-1].mode_results["execution_first"]
        assert cell.positive_rate_ci_low <= cell.positive_rate <= cell.positive_rate_ci_high
        assert cell.interval_method == "wilson_95"
