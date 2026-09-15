from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from statistics import mean, pvariance
from typing import Any


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


def _safe_values(values: list[Any]) -> list[float]:
    parsed: list[float] = []
    for value in values:
        try:
            parsed.append(float(value))
        except (TypeError, ValueError):
            pass
    return parsed


def _ks_statistic(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    xs = sorted(set(left + right))
    left_sorted = sorted(left)
    right_sorted = sorted(right)
    i = j = 0
    max_gap = 0.0
    for x in xs:
        while i < len(left_sorted) and left_sorted[i] <= x:
            i += 1
        while j < len(right_sorted) and right_sorted[j] <= x:
            j += 1
        max_gap = max(max_gap, abs(i / len(left_sorted) - j / len(right_sorted)))
    return max_gap


def _ks_p_value(statistic: float, n_left: int, n_right: int) -> float:
    if n_left <= 0 or n_right <= 0:
        return 1.0
    effective_n = n_left * n_right / (n_left + n_right)
    # Asymptotic two-sample KS approximation.
    value = 2.0 * math.exp(-2.0 * effective_n * statistic * statistic)
    return max(0.0, min(1.0, value))


def _wasserstein_1d(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    n = max(len(left), len(right))
    left_sorted = sorted(left)
    right_sorted = sorted(right)
    squared = 0.0
    for index in range(n):
        q = (index + 0.5) / n
        li = min(len(left_sorted) - 1, max(0, int(q * len(left_sorted))))
        ri = min(len(right_sorted) - 1, max(0, int(q * len(right_sorted))))
        squared += (left_sorted[li] - right_sorted[ri]) ** 2
    return math.sqrt(squared / n)


@dataclass(frozen=True)
class TargetDistributionDiagnostic:
    target: str
    n_real: int
    n_sim: int
    mean_real: float
    mean_sim: float
    mean_gap: float
    variance_real: float
    variance_sim: float
    variance_ratio: float | None
    ks_statistic: float
    ks_p_value: float
    wasserstein_1d: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimRealDiagnosticsReport:
    target_diagnostics: list[TargetDistributionDiagnostic]
    diagonal_w2: float
    stress_cluster_w2: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "sim_real_diagnostics.v1",
            "target_diagnostics": [item.to_dict() for item in self.target_diagnostics],
            "diagonal_w2": round(self.diagonal_w2, 6),
            "stress_cluster_w2": round(self.stress_cluster_w2, 6),
            "warnings": list(self.warnings),
            "caveat": "W2 measures distribution distance only; it is not a policy-effectiveness proof.",
        }


class SimRealDiagnostics:
    STRESS_CLUSTER = ("emotional_block", "task_aversion", "cognitive_load")

    def evaluate(
        self,
        *,
        real_vectors: list[dict[str, float]],
        sim_vectors: list[dict[str, float]],
    ) -> SimRealDiagnosticsReport:
        targets = sorted(set().union(*(item.keys() for item in real_vectors), *(item.keys() for item in sim_vectors)))
        diagnostics: list[TargetDistributionDiagnostic] = []
        warnings: list[str] = []
        w2_terms: list[float] = []
        stress_terms: list[float] = []
        for target in targets:
            real_values = _safe_values([item.get(target) for item in real_vectors])
            sim_values = _safe_values([item.get(target) for item in sim_vectors])
            if not real_values or not sim_values:
                warnings.append(f"missing_distribution:{target}")
                continue
            mean_real = mean(real_values)
            mean_sim = mean(sim_values)
            var_real = pvariance(real_values) if len(real_values) > 1 else 0.0
            var_sim = pvariance(sim_values) if len(sim_values) > 1 else 0.0
            ks = _ks_statistic(real_values, sim_values)
            w1 = _wasserstein_1d(real_values, sim_values)
            w2_terms.append(w1 * w1)
            if target in self.STRESS_CLUSTER:
                stress_terms.append(w1 * w1)
            diagnostics.append(
                TargetDistributionDiagnostic(
                    target=target,
                    n_real=len(real_values),
                    n_sim=len(sim_values),
                    mean_real=round(mean_real, 6),
                    mean_sim=round(mean_sim, 6),
                    mean_gap=round(abs(mean_real - mean_sim), 6),
                    variance_real=round(var_real, 6),
                    variance_sim=round(var_sim, 6),
                    variance_ratio=round(var_real / var_sim, 6) if var_sim > 0 else None,
                    ks_statistic=round(ks, 6),
                    ks_p_value=round(_ks_p_value(ks, len(real_values), len(sim_values)), 6),
                    wasserstein_1d=round(w1, 6),
                )
            )
            if abs(mean_real - mean_sim) > 0.30:
                warnings.append(f"mean_gap_above_0.30:{target}")
        return SimRealDiagnosticsReport(
            target_diagnostics=diagnostics,
            diagonal_w2=math.sqrt(sum(w2_terms)) if w2_terms else 0.0,
            stress_cluster_w2=math.sqrt(sum(stress_terms)) if stress_terms else 0.0,
            warnings=warnings,
        )

    @staticmethod
    def vectors_from_traces(raw_traces: list[Any]) -> list[dict[str, float]]:
        vectors: list[dict[str, float]] = []
        for raw in raw_traces:
            trace = _loads(raw)
            if not trace:
                continue
            state_vector = trace.get("belief_state_vector")
            if not isinstance(state_vector, dict):
                continue
            vector: dict[str, float] = {}
            for key, value in state_vector.items():
                key = str(key)
                if not key.endswith("_mean"):
                    continue
                try:
                    vector[key[: -len("_mean")]] = float(value)
                except (TypeError, ValueError):
                    pass
            if vector:
                vectors.append(vector)
        return vectors

    @staticmethod
    def vectors_from_simulation_steps(steps: list[dict[str, Any]]) -> list[dict[str, float]]:
        vectors: list[dict[str, float]] = []
        for step in steps:
            estimate = step.get("belief_estimate") if isinstance(step, dict) else None
            if not isinstance(estimate, dict):
                continue
            vector: dict[str, float] = {}
            for key, value in estimate.items():
                try:
                    vector[str(key)] = float(value)
                except (TypeError, ValueError):
                    pass
            if vector:
                vectors.append(vector)
        return vectors
