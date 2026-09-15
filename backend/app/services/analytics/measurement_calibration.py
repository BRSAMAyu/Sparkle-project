from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _loads(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


@dataclass(frozen=True)
class CalibratedThreshold:
    parameter: str
    expert_default: float
    data_driven_suggestion: float
    data_count: int
    estimation_method: str
    confidence_interval_low: float | None
    confidence_interval_high: float | None
    should_adopt: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "expert_default": round(self.expert_default, 4),
            "data_driven_suggestion": round(self.data_driven_suggestion, 4),
            "data_count": self.data_count,
            "estimation_method": self.estimation_method,
            "confidence_interval_low": (
                round(self.confidence_interval_low, 4)
                if self.confidence_interval_low is not None
                else None
            ),
            "confidence_interval_high": (
                round(self.confidence_interval_high, 4)
                if self.confidence_interval_high is not None
                else None
            ),
            "should_adopt": self.should_adopt,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MeasurementCalibrationReport:
    total_traces: int
    total_users: int
    thresholds: list[CalibratedThreshold]
    summary: str
    warnings: list[str] = field(default_factory=list)
    schema_version: str = "measurement_calibration.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "total_traces": self.total_traces,
            "total_users": self.total_users,
            "thresholds": [t.to_dict() for t in self.thresholds],
            "summary": self.summary,
            "warnings": self.warnings,
        }


class MeasurementCalibrator:
    """Estimate measurement thresholds from real trace data.

    The expert-assigned firewall thresholds (max_target_mean_gap=0.30,
    min_evidence_per_trace=2.0, max_mode_distribution_gap=0.30) were set
    before any real data existed. This module uses the empirical distribution
    of real traces to suggest data-driven alternatives.

    The goal is not to blindly replace expert defaults — it is to flag
    thresholds that are clearly too tight or too loose for the observed data.
    """

    def __init__(
        self,
        *,
        min_traces_for_calibration: int = 50,
        min_users_for_calibration: int = 3,
        max_threshold_shift_ratio: float = 2.0,
    ) -> None:
        self.min_traces_for_calibration = min_traces_for_calibration
        self.min_users_for_calibration = min_users_for_calibration
        self.max_threshold_shift_ratio = max_threshold_shift_ratio

    def calibrate(self, raw_traces: list[Any]) -> MeasurementCalibrationReport:
        traces = []
        user_ids: set[str] = set()
        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                continue
            traces.append(trace)
            uid = trace.get("user_id")
            if uid:
                user_ids.add(str(uid))

        if len(traces) < self.min_traces_for_calibration or len(user_ids) < self.min_users_for_calibration:
            return MeasurementCalibrationReport(
                total_traces=len(traces),
                total_users=len(user_ids),
                thresholds=[],
                summary="insufficient_data_keep_expert_defaults",
                warnings=[
                    f"need_at_least_{self.min_traces_for_calibration}_traces_and"
                    f"_{self.min_users_for_calibration}_users"
                ],
            )

        thresholds: list[CalibratedThreshold] = []
        thresholds.append(self._calibrate_target_mean_gap(traces))
        thresholds.append(self._calibrate_evidence_density(traces))
        thresholds.append(self._calibrate_mode_distribution_gap(traces))
        thresholds.append(self._calibrate_belief_variance_threshold(traces))

        adoptions = [t for t in thresholds if t.should_adopt]
        warnings: list[str] = []
        for t in thresholds:
            if t.data_driven_suggestion < 0 or t.data_count < 10:
                warnings.append(f"{t.parameter}: insufficient_data_for_accurate_estimation")

        if adoptions:
            summary = f"suggest_{len(adoptions)}_threshold_adjustments"
        elif [t for t in thresholds if t.data_count >= 10]:
            summary = "expert_defaults_consistent_with_data"
        else:
            summary = "keep_expert_defaults_insufficient_data"

        return MeasurementCalibrationReport(
            total_traces=len(traces),
            total_users=len(user_ids),
            thresholds=thresholds,
            summary=summary,
            warnings=warnings,
        )

    def _calibrate_target_mean_gap(self, traces: list[dict[str, Any]]) -> CalibratedThreshold:
        targets = [
            "emotional_block", "task_aversion", "cognitive_load",
            "goal_clarity", "execution_capacity", "metacognition_accuracy",
            "system_dissatisfaction",
        ]
        target_values: dict[str, list[float]] = {t: [] for t in targets}
        for trace in traces:
            bsv = trace.get("belief_state_vector")
            if not isinstance(bsv, dict):
                continue
            for target in targets:
                if f"{target}_mean" in bsv:
                    target_values[target].append(_as_float(bsv.get(f"{target}_mean"), default=0.5))
                    continue
                entry = bsv.get(target)
                if isinstance(entry, dict):
                    val = _as_float(entry.get("mean"), default=0.5)
                    target_values[target].append(val)

        expert_default = 0.30
        pairwise_gaps: list[float] = []
        target_names = sorted(target_values)
        for i, t1 in enumerate(target_names):
            vals1 = target_values[t1]
            if len(vals1) < 10:
                continue
            for t2 in target_names[i + 1:]:
                vals2 = target_values[t2]
                if len(vals2) < 10:
                    continue
                gap = abs(mean(vals1) - mean(vals2))
                pairwise_gaps.append(gap)

        if len(pairwise_gaps) < 5:
            return CalibratedThreshold(
                parameter="max_target_mean_gap",
                expert_default=expert_default,
                data_driven_suggestion=expert_default,
                data_count=0,
                estimation_method="pairwise_target_mean_differences",
                confidence_interval_low=None,
                confidence_interval_high=None,
                should_adopt=False,
                reason="insufficient_target_data",
            )

        avg_gap = mean(pairwise_gaps)
        std_gap = pstdev(pairwise_gaps) if len(pairwise_gaps) > 1 else 0.0
        suggested = avg_gap + 2.0 * std_gap
        suggested = max(0.10, min(0.50, suggested))
        capped = max(
            expert_default / self.max_threshold_shift_ratio,
            min(expert_default * self.max_threshold_shift_ratio, suggested),
        )
        should_adopt = abs(capped - expert_default) / expert_default > 0.33

        return CalibratedThreshold(
            parameter="max_target_mean_gap",
            expert_default=expert_default,
            data_driven_suggestion=round(capped, 4),
            data_count=sum(len(v) for v in target_values.values()),
            estimation_method="pairwise_target_mean_differences_plus_2sd",
            confidence_interval_low=round(max(0.05, avg_gap - 2.0 * std_gap), 4),
            confidence_interval_high=round(min(0.60, avg_gap + 2.0 * std_gap), 4),
            should_adopt=should_adopt,
            reason=(
                f"data_suggests_{round(capped, 2)}_vs_expert_{expert_default}"
                if should_adopt
                else "expert_default_within_data_range"
            ),
        )

    def _calibrate_evidence_density(self, traces: list[dict[str, Any]]) -> CalibratedThreshold:
        evidence_counts: list[float] = []
        for trace in traces:
            counts = trace.get("belief_variable_evidence_counts")
            if isinstance(counts, dict):
                evidence_counts.append(float(sum(int(v) for v in counts.values() if isinstance(v, (int, float)))))
            elif isinstance(counts, (int, float)):
                evidence_counts.append(float(counts))
            else:
                ev_count = trace.get("evidence_count")
                if ev_count is not None:
                    evidence_counts.append(_as_float(ev_count))

        expert_default = 2.0
        if len(evidence_counts) < 10:
            return CalibratedThreshold(
                parameter="min_evidence_per_trace",
                expert_default=expert_default,
                data_driven_suggestion=expert_default,
                data_count=len(evidence_counts),
                estimation_method="empirical_evidence_count_distribution",
                confidence_interval_low=None,
                confidence_interval_high=None,
                should_adopt=False,
                reason="insufficient_evidence_density_data",
            )

        avg_evidence = mean(evidence_counts)
        std_evidence = pstdev(evidence_counts) if len(evidence_counts) > 1 else 0.0
        suggested = max(0.5, avg_evidence - 1.0 * std_evidence)
        suggested = min(8.0, suggested)
        should_adopt = abs(suggested - expert_default) / expert_default > 0.25

        return CalibratedThreshold(
            parameter="min_evidence_per_trace",
            expert_default=expert_default,
            data_driven_suggestion=round(suggested, 2),
            data_count=len(evidence_counts),
            estimation_method="mean_minus_1sd_with_floor",
            confidence_interval_low=round(max(0.0, avg_evidence - 2.0 * std_evidence), 2),
            confidence_interval_high=round(avg_evidence + 2.0 * std_evidence, 2),
            should_adopt=should_adopt,
            reason=(
                f"real_evidence_density_avg_{round(avg_evidence, 1)}_per_turn_suggests_{round(suggested, 1)}"
                if should_adopt
                else "expert_default_within_observed_range"
            ),
        )

    def _calibrate_mode_distribution_gap(self, traces: list[dict[str, Any]]) -> CalibratedThreshold:
        mode_counter: Counter[str] = Counter()
        for trace in traces:
            mode = trace.get("actual_router_mode")
            if mode:
                mode_counter[str(mode)] += 1
            else:
                snapshot = trace.get("router_snapshot")
                if isinstance(snapshot, dict) and snapshot.get("actual_router_mode"):
                    mode_counter[str(snapshot["actual_router_mode"])] += 1

        total = sum(mode_counter.values())
        expert_default = 0.30
        if total < 10:
            return CalibratedThreshold(
                parameter="max_mode_distribution_gap",
                expert_default=expert_default,
                data_driven_suggestion=expert_default,
                data_count=total,
                estimation_method="mode_proportion_stability",
                confidence_interval_low=None,
                confidence_interval_high=None,
                should_adopt=False,
                reason="insufficient_mode_data",
            )

        proportions = {}
        for mode, count in mode_counter.items():
            p = count / total
            se = math.sqrt(p * (1 - p) / total)
            proportions[mode] = (p, se)

        max_se = max(se for _, se in proportions.values()) if proportions else 0.05
        suggested = max(0.05, min(0.50, max_se * 3.0))
        should_adopt = abs(suggested - expert_default) > 0.10

        return CalibratedThreshold(
            parameter="max_mode_distribution_gap",
            expert_default=expert_default,
            data_driven_suggestion=round(suggested, 4),
            data_count=total,
            estimation_method="max_standard_error_of_mode_proportion_x3",
            confidence_interval_low=round(max(0.01, max_se * 1.96), 4),
            confidence_interval_high=round(min(0.50, max_se * 3.0), 4),
            should_adopt=should_adopt,
            reason=(
                f"mode_distribution_se_{round(max_se, 3)}_suggests_{round(suggested, 2)}"
                if should_adopt
                else "expert_default_within_estimation_range"
            ),
        )

    def _calibrate_belief_variance_threshold(self, traces: list[dict[str, Any]]) -> CalibratedThreshold:
        variance_values: list[float] = []
        for trace in traces:
            bsv = trace.get("belief_state_vector") or trace.get("belief_uncertainty_vector")
            if not isinstance(bsv, dict):
                continue
            for entry in bsv.values():
                if isinstance(entry, dict):
                    v = _as_float(entry.get("variance"), default=0.25)
                    if 0.01 <= v <= 0.25:
                        variance_values.append(v)

        expert_default = 0.10
        if len(variance_values) < 20:
            return CalibratedThreshold(
                parameter="belief_variance_uncertainty_threshold",
                expert_default=expert_default,
                data_driven_suggestion=expert_default,
                data_count=len(variance_values),
                estimation_method="empirical_variance_distribution_percentile",
                confidence_interval_low=None,
                confidence_interval_high=None,
                should_adopt=False,
                reason="insufficient_variance_data",
            )

        sorted_variances = sorted(variance_values)
        p25_idx = int(len(sorted_variances) * 0.25)
        p25 = sorted_variances[p25_idx]
        suggested = round(p25, 4)
        suggested = max(0.04, min(0.18, suggested))
        should_adopt = abs(suggested - expert_default) > 0.03

        return CalibratedThreshold(
            parameter="belief_variance_uncertainty_threshold",
            expert_default=expert_default,
            data_driven_suggestion=suggested,
            data_count=len(variance_values),
            estimation_method="25th_percentile_of_observed_variances",
            confidence_interval_low=round(sorted_variances[max(0, int(len(sorted_variances) * 0.10))], 4),
            confidence_interval_high=round(sorted_variances[min(len(sorted_variances) - 1, int(len(sorted_variances) * 0.40))], 4),
            should_adopt=should_adopt,
            reason=(
                f"observed_p25_variance_{suggested}_vs_expert_{expert_default}"
                if should_adopt
                else "expert_default_within_observed_variance_range"
            ),
        )
