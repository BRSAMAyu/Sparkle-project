from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.evidence.belief_state import MAX_VARIANCE, MIN_VARIANCE, BeliefState
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.unified_evidence import EvidenceTarget

MODE_TARGET_IMPORTANCE: dict[EvidenceTarget, float] = {
    EvidenceTarget.EMOTIONAL_BLOCK: 1.0,
    EvidenceTarget.TASK_AVERSION: 0.94,
    EvidenceTarget.COGNITIVE_LOAD: 0.82,
    EvidenceTarget.GOAL_CLARITY: 0.76,
    EvidenceTarget.EXECUTION_CAPACITY: 0.76,
    EvidenceTarget.METACOGNITION_ACCURACY: 0.58,
    EvidenceTarget.SYSTEM_DISSATISFACTION: 0.86,
}


@dataclass(frozen=True)
class ProbeDecision:
    should_probe: bool
    target: str | None
    probe_kind: str
    expected_information_value: float
    friction_cost: float
    wrong_route_cost: float
    decision_margin: float
    current_variance: float
    expected_variance_after_probe: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expected_information_value"] = round(self.expected_information_value, 6)
        payload["friction_cost"] = round(self.friction_cost, 6)
        payload["wrong_route_cost"] = round(self.wrong_route_cost, 6)
        payload["decision_margin"] = round(self.decision_margin, 6)
        payload["current_variance"] = round(self.current_variance, 6)
        payload["expected_variance_after_probe"] = round(self.expected_variance_after_probe, 6)
        return payload


class ActiveProbePolicy:
    """Value-of-information policy for Aurora active sensing.

    This decides whether a micro-probe is worth the interaction cost. It does
    not render UI; it only emits a structured recommendation that future Aurora
    dialogue code can consume.
    """

    def __init__(
        self,
        *,
        explicit_probe_confidence: float = 0.94,
        base_friction_cost: float = 0.045,
        high_uncertainty_threshold: float = 0.18,
        low_margin_threshold: float = 0.08,
    ) -> None:
        self.explicit_probe_confidence = explicit_probe_confidence
        self.base_friction_cost = base_friction_cost
        self.high_uncertainty_threshold = high_uncertainty_threshold
        self.low_margin_threshold = low_margin_threshold

    def decide(
        self,
        belief_state: BeliefState,
        *,
        router_projection: dict[str, Any] | None = None,
        user_probe_fatigue: float = 0.0,
    ) -> ProbeDecision:
        projection = router_projection or FusionEngine(belief_state.user_id).project_router_signals(belief_state)
        decision_margin = self._decision_margin(projection)
        wrong_route_cost = self._wrong_route_cost(projection)
        candidates = [
            self._candidate_value(
                belief_state,
                target=target,
                wrong_route_cost=wrong_route_cost,
                decision_margin=decision_margin,
            )
            for target in MODE_TARGET_IMPORTANCE
        ]
        best = max(candidates, key=lambda item: item["expected_information_value"])
        friction_cost = self.base_friction_cost * (1.0 + max(0.0, min(1.0, user_probe_fatigue)))
        reasons: list[str] = []
        if best["current_variance"] >= self.high_uncertainty_threshold:
            reasons.append("high_uncertainty")
        if decision_margin <= self.low_margin_threshold:
            reasons.append("low_decision_margin")
        if best["expected_information_value"] > friction_cost:
            reasons.append("positive_value_of_information")
        should_probe = (
            best["expected_information_value"] > friction_cost
            and (
                best["current_variance"] >= self.high_uncertainty_threshold
                or decision_margin <= self.low_margin_threshold
            )
        )
        return ProbeDecision(
            should_probe=should_probe,
            target=best["target"].value if should_probe else None,
            probe_kind="micro_probe",
            expected_information_value=best["expected_information_value"],
            friction_cost=friction_cost,
            wrong_route_cost=wrong_route_cost,
            decision_margin=decision_margin,
            current_variance=best["current_variance"],
            expected_variance_after_probe=best["expected_variance_after_probe"],
            reasons=reasons or ["probe_not_worth_cost"],
        )

    def _candidate_value(
        self,
        belief_state: BeliefState,
        *,
        target: EvidenceTarget,
        wrong_route_cost: float,
        decision_margin: float,
    ) -> dict[str, Any]:
        variable = belief_state.peek_variable(target)
        current_variance = float(variable.variance) if variable is not None else MAX_VARIANCE
        expected_variance = self._posterior_variance_after_probe(current_variance)
        variance_reduction = max(0.0, current_variance - expected_variance)
        margin_multiplier = 1.0 + max(0.0, self.low_margin_threshold - decision_margin) / self.low_margin_threshold
        expected_information_value = (
            variance_reduction
            / MAX_VARIANCE
            * MODE_TARGET_IMPORTANCE[target]
            * wrong_route_cost
            * margin_multiplier
        )
        return {
            "target": target,
            "current_variance": current_variance,
            "expected_variance_after_probe": expected_variance,
            "expected_information_value": expected_information_value,
        }

    def _posterior_variance_after_probe(self, current_variance: float) -> float:
        obs_variance = max(MIN_VARIANCE, min(MAX_VARIANCE, (1.0 - self.explicit_probe_confidence) ** 2))
        bounded_current = max(MIN_VARIANCE, min(MAX_VARIANCE, current_variance))
        total = bounded_current + obs_variance
        kalman_gain = bounded_current / total if total else 0.0
        return max(MIN_VARIANCE, min(MAX_VARIANCE, (1.0 - kalman_gain) * bounded_current))

    @staticmethod
    def _decision_margin(projection: dict[str, Any]) -> float:
        support = float(projection.get("support_pressure_score") or 0.5)
        readiness = float(projection.get("execution_readiness_score") or 0.5)
        return abs(support - readiness)

    @staticmethod
    def _wrong_route_cost(projection: dict[str, Any]) -> float:
        support = float(projection.get("support_pressure_score") or 0.5)
        readiness = float(projection.get("execution_readiness_score") or 0.5)
        shadow_mode = str(projection.get("shadow_mode") or "balanced")
        if shadow_mode == "execution_first":
            return max(0.2, support)
        if shadow_mode == "cognitive_first":
            return max(0.2, readiness)
        return max(0.2, 1.0 - abs(support - readiness))
