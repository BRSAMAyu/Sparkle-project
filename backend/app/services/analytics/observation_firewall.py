from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _distribution(counts: dict[str, Any]) -> dict[str, float]:
    parsed = {str(key): max(0.0, _as_float(value)) for key, value in (counts or {}).items()}
    total = sum(parsed.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in parsed.items()}


@dataclass(frozen=True)
class FirewallGateResult:
    name: str
    passed: bool
    severity: str
    blockers: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservationQualityFirewallReport:
    passed: bool
    recommendation: str
    gates: list[FirewallGateResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "observation_quality_firewall.v1",
            "passed": self.passed,
            "recommendation": self.recommendation,
            "gates": [gate.to_dict() for gate in self.gates],
            "blockers": [
                blocker
                for gate in self.gates
                for blocker in gate.blockers
            ],
        }


class ObservationQualityFirewall:
    """Pre-OPE sanity gates for real belief traces.

    This is intentionally blunt. It answers whether real traces have enough
    scale, evidence density, and action comparability to make the later
    statistics meaningful.
    """

    def __init__(
        self,
        *,
        max_target_mean_gap: float = 0.30,
        min_evidence_per_trace: float = 2.0,
        max_mode_distribution_gap: float = 0.30,
        min_comparable_traces: int = 20,
    ) -> None:
        self.max_target_mean_gap = max_target_mean_gap
        self.min_evidence_per_trace = min_evidence_per_trace
        self.max_mode_distribution_gap = max_mode_distribution_gap
        self.min_comparable_traces = min_comparable_traces

    def evaluate(
        self,
        *,
        real_trace_summary: dict[str, Any],
        simulation_summary: dict[str, Any] | None = None,
    ) -> ObservationQualityFirewallReport:
        gates = [
            self._trace_scale_gate(real_trace_summary),
            self._target_mean_gate(real_trace_summary, simulation_summary or {}),
            self._evidence_density_gate(real_trace_summary, simulation_summary or {}),
            self._action_distribution_gate(real_trace_summary, simulation_summary or {}),
        ]
        passed = all(gate.passed for gate in gates)
        recommendation = "eligible_for_ope" if passed else "fix_observation_baseline_before_ope"
        return ObservationQualityFirewallReport(
            passed=passed,
            recommendation=recommendation,
            gates=gates,
        )

    def _trace_scale_gate(self, real: dict[str, Any]) -> FirewallGateResult:
        comparable = int(real.get("comparable_traces") or 0)
        blockers: list[str] = []
        if comparable < self.min_comparable_traces:
            blockers.append("insufficient_actual_shadow_comparable_traces")
        return FirewallGateResult(
            name="trace_scale",
            passed=not blockers,
            severity="blocker" if blockers else "ok",
            blockers=blockers,
            metrics={
                "comparable_traces": comparable,
                "min_comparable_traces": self.min_comparable_traces,
            },
        )

    def _target_mean_gate(self, real: dict[str, Any], sim: dict[str, Any]) -> FirewallGateResult:
        real_means = real.get("average_belief_mean_by_target") or {}
        sim_means = sim.get("average_belief_mean_by_target") or sim.get("average_true_mean_by_target") or {}
        gaps: dict[str, float] = {}
        blockers: list[str] = []
        if not real_means:
            blockers.append("missing_real_target_means")
        if sim and not sim_means:
            blockers.append("missing_sim_target_means")
        for target, real_mean in real_means.items():
            if target not in sim_means:
                continue
            gap = abs(_as_float(real_mean, default=0.5) - _as_float(sim_means[target], default=0.5))
            gaps[target] = round(gap, 4)
            if gap > self.max_target_mean_gap:
                blockers.append(f"target_mean_level_mismatch:{target}")
        return FirewallGateResult(
            name="per_target_mean",
            passed=not blockers,
            severity="blocker" if any(item.startswith("target_mean") for item in blockers) else (
                "warning" if blockers else "ok"
            ),
            blockers=blockers,
            metrics={
                "max_allowed_gap": self.max_target_mean_gap,
                "gaps": gaps,
                "real_means": dict(real_means),
                "simulation_means": dict(sim_means),
            },
        )

    def _evidence_density_gate(self, real: dict[str, Any], sim: dict[str, Any]) -> FirewallGateResult:
        real_density = _as_float(real.get("average_evidence_per_trace"))
        sim_density = _as_float(sim.get("avg_evidence_per_step")) if sim else 0.0
        blockers: list[str] = []
        if real_density < self.min_evidence_per_trace:
            blockers.append("sparse_real_evidence")
        density_ratio = real_density / sim_density if sim_density > 0 else None
        return FirewallGateResult(
            name="evidence_density",
            passed=not blockers,
            severity="blocker" if blockers else "ok",
            blockers=blockers,
            metrics={
                "real_average_evidence_per_trace": round(real_density, 4),
                "simulation_average_evidence_per_step": round(sim_density, 4),
                "density_ratio_real_over_sim": round(density_ratio, 4) if density_ratio is not None else None,
                "min_evidence_per_trace": self.min_evidence_per_trace,
            },
        )

    def _action_distribution_gate(self, real: dict[str, Any], sim: dict[str, Any]) -> FirewallGateResult:
        real_dist = _distribution(real.get("actual_mode_counts") or {})
        sim_dist = _distribution(sim.get("route_mode_counts") or {}) if sim else {}
        blockers: list[str] = []
        gaps: dict[str, float] = {}
        if not real_dist:
            blockers.append("missing_real_action_distribution")
        if sim and not sim_dist:
            blockers.append("missing_sim_action_distribution")
        for mode in sorted(set(real_dist) | set(sim_dist)):
            gap = abs(real_dist.get(mode, 0.0) - sim_dist.get(mode, 0.0))
            gaps[mode] = round(gap, 4)
            if sim_dist and gap > self.max_mode_distribution_gap:
                blockers.append(f"action_distribution_mismatch:{mode}")
        return FirewallGateResult(
            name="action_distribution",
            passed=not blockers,
            severity="blocker" if any(item.startswith("action_distribution") for item in blockers) else (
                "warning" if blockers else "ok"
            ),
            blockers=blockers,
            metrics={
                "real_distribution": {key: round(value, 4) for key, value in real_dist.items()},
                "simulation_distribution": {key: round(value, 4) for key, value in sim_dist.items()},
                "gaps": gaps,
                "max_allowed_gap": self.max_mode_distribution_gap,
            },
        )
