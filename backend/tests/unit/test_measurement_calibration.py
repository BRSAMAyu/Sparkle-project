from __future__ import annotations

from app.services.analytics.measurement_calibration import (
    CalibratedThreshold,
    MeasurementCalibrationReport,
    MeasurementCalibrator,
)


def _make_trace(
    *,
    actual_mode: str = "balanced",
    belief_means: dict | None = None,
    evidence_count: float | None = None,
) -> dict:
    trace: dict = {
        "actual_router_mode": actual_mode,
        "router_snapshot": {"actual_router_mode": actual_mode},
    }
    if belief_means:
        trace["belief_state_vector"] = belief_means
    if evidence_count is not None:
        trace["belief_variable_evidence_counts"] = {"total": evidence_count}
    return trace


def _means(**kwargs: float) -> dict:
    return {
        target: {"mean": kwargs.get(target, 0.5), "variance": kwargs.get(f"{target}_var", 0.15)}
        for target in [
            "emotional_block", "task_aversion", "cognitive_load",
            "goal_clarity", "execution_capacity", "metacognition_accuracy",
            "system_dissatisfaction",
        ]
    }


class TestMeasurementCalibrator:
    def test_insufficient_data(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=50, min_users_for_calibration=3)
        traces = [
            _make_trace(actual_mode="balanced", belief_means=_means(), evidence_count=2.0),
        ]
        report = calibrator.calibrate(traces)
        assert report.total_traces == 1
        assert report.summary == "insufficient_data_keep_expert_defaults"
        assert len(report.thresholds) == 0

    def test_sufficient_data_keeps_defaults(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=20, min_users_for_calibration=2)
        traces = []
        for i in range(30):
            traces.append(_make_trace(
                actual_mode="balanced",
                belief_means=_means(emotional_block=0.4 + (i % 5) * 0.05),
                evidence_count=3.5,
            ))
        for i, trace in enumerate(traces):
            trace["user_id"] = f"user_{(i % 3) + 1}"
        report = calibrator.calibrate(traces)
        assert report.total_traces == 30
        assert report.total_users >= 2
        assert len(report.thresholds) == 4

    def test_threshold_report_format(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=20, min_users_for_calibration=2)
        traces = []
        for i in range(25):
            traces.append(_make_trace(
                actual_mode="balanced",
                belief_means=_means(emotional_block=0.35 + (i % 3) * 0.1),
                evidence_count=3.0,
            ))
        for i, trace in enumerate(traces):
            trace["user_id"] = f"user_{(i % 3) + 1}"
        report = calibrator.calibrate(traces)
        for threshold in report.thresholds:
            assert threshold.parameter
            assert threshold.expert_default > 0
            assert threshold.data_count >= 0
            assert threshold.estimation_method

    def test_mode_distribution_threshold(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=15, min_users_for_calibration=2)
        traces = []
        modes = ["balanced"] * 10 + ["cognitive_first"] * 5 + ["execution_first"] * 15
        for mode in modes:
            traces.append(_make_trace(actual_mode=mode, belief_means=_means(), evidence_count=3.0))
        for i, trace in enumerate(traces):
            trace["user_id"] = f"user_{(i % 3) + 1}"
        report = calibrator.calibrate(traces)
        mode_threshold = [t for t in report.thresholds if t.parameter == "max_mode_distribution_gap"][0]
        assert mode_threshold.data_count == 30
        assert mode_threshold.data_driven_suggestion > 0

    def test_belief_variance_threshold(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=15, min_users_for_calibration=2)
        traces = []
        for i in range(30):
            means = _means(
                emotional_block_var=0.05 + (i % 10) * 0.01,
                task_aversion_var=0.06 + (i % 10) * 0.01,
            )
            traces.append(_make_trace(actual_mode="balanced", belief_means=means, evidence_count=2.0))
        for i, trace in enumerate(traces):
            trace["user_id"] = f"user_{(i % 3) + 1}"
        report = calibrator.calibrate(traces)
        var_threshold = [t for t in report.thresholds if t.parameter == "belief_variance_uncertainty_threshold"][0]
        assert var_threshold.data_driven_suggestion > 0

    def test_report_to_dict(self):
        report = MeasurementCalibrationReport(
            total_traces=100,
            total_users=5,
            thresholds=[],
            summary="keep_expert_defaults_insufficient_data",
            warnings=["low_data"],
        )
        d = report.to_dict()
        assert d["schema_version"] == "measurement_calibration.v1"
        assert d["total_traces"] == 100
        assert d["total_users"] == 5
        assert d["summary"] == "keep_expert_defaults_insufficient_data"

    def test_threshold_to_dict(self):
        t = CalibratedThreshold(
            parameter="test_param",
            expert_default=0.30,
            data_driven_suggestion=0.25,
            data_count=50,
            estimation_method="empirical_p25",
            confidence_interval_low=0.20,
            confidence_interval_high=0.35,
            should_adopt=True,
            reason="data_suggests_adjustment",
        )
        d = t.to_dict()
        assert d["parameter"] == "test_param"
        assert d["should_adopt"] is True

    def test_evidence_density_calibration(self):
        calibrator = MeasurementCalibrator(min_traces_for_calibration=10, min_users_for_calibration=2)
        traces = []
        for _i in range(15):
            traces.append(_make_trace(
                actual_mode="balanced",
                belief_means=_means(),
                evidence_count=1.2,
            ))
        for i, trace in enumerate(traces):
            trace["user_id"] = f"user_{(i % 2) + 1}"
        report = calibrator.calibrate(traces)
        evidence_threshold = [t for t in report.thresholds if t.parameter == "min_evidence_per_trace"][0]
        assert evidence_threshold.data_driven_suggestion < 2.0
        assert evidence_threshold.should_adopt
