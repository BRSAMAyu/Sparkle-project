"""Causal attribution: counterfactual Individual Treatment Effect estimation.

Estimates what would have happened without a parameter change by comparing
to similar historical runs (nearest-neighbor matching on pre-treatment features).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class CausalEffect:
    """Estimated causal effect of a parameter change."""
    parameter: str
    delta: float                    # proposed change direction/magnitude
    metric: str                     # affected metric
    ate: float                      # Average Treatment Effect
    ite_std: float                  # Standard deviation of ITE estimates
    n_matched: int                  # Number of matched controls
    confidence: float               # 0-1

    @property
    def significant(self) -> bool:
        """Effect is significant if ATE > 2 * std (rough 95% CI)."""
        if self.n_matched < 3:
            return False
        return abs(self.ate) > 2 * self.ite_std


class CausalAttributor:
    """Counterfactual causal attribution via nearest-neighbor matching.

    For each parameter change, finds historical runs where:
    1. The parameter was NOT changed (or changed differently)
    2. The pre-treatment state was similar (cosine similarity on state vector)

    Then estimates: ITE = outcome_treatment - outcome_control_matched
    """

    def __init__(self, *, min_matches: int = 3, similarity_threshold: float = 0.7):
        self.min_matches = min_matches
        self.similarity_threshold = similarity_threshold

    def estimate_effect(
        self,
        *,
        parameter: str,
        delta: float,
        metric: str,
        pre_state: list[float],
        post_value: float,
        history: list[dict[str, Any]],
    ) -> CausalEffect | None:
        """Estimate causal effect of a parameter change.

        Args:
            parameter: which parameter was changed
            delta: the magnitude/direction of change
            metric: which metric to measure effect on
            pre_state: state vector before the change
            post_value: metric value after the change
            history: list of historical trajectory records, each with:
                     'state_vector' (list[float]), 'action_taken' (dict),
                     'metric_before' (float), 'metric_after' (float)

        Returns:
            CausalEffect if enough matched controls found, None otherwise.
        """
        if len(pre_state) == 0 or len(history) < self.min_matches:
            return None

        # Find matched controls: same parameter area, similar pre-treatment state
        matched: list[tuple[float, float]] = []  # (metric_before, metric_after)

        for record in history:
            action = record.get("action_taken", {})
            if parameter in action:
                continue  # treatment: this record also changed the param, not a control

            ctrl_state = record.get("state_vector", [])
            if not ctrl_state:
                continue

            similarity = _cosine_similarity(pre_state, ctrl_state)
            if similarity < self.similarity_threshold:
                continue

            before = record.get("metric_before", 0.0)
            after = record.get("metric_after", 0.0)
            matched.append((before, after))

        if len(matched) < self.min_matches:
            return None

        # Compute ITE for each match: control outcome - control baseline
        control_effects = [after - before for before, after in matched]
        mean_control = sum(control_effects) / len(control_effects)

        # Treatment effect = observed outcome change - expected control change
        # We need pre_value to compute treatment change
        # Since we don't have it directly, use the matched controls' baseline
        mean_baseline = sum(b for b, _ in matched) / len(matched)
        treatment_change = post_value - mean_baseline
        ate = treatment_change - mean_control

        # Standard deviation of control effects
        if len(control_effects) > 1:
            std = math.sqrt(sum((e - mean_control) ** 2 for e in control_effects) / (len(control_effects) - 1))
        else:
            std = abs(mean_control)

        confidence = min(1.0, len(matched) / 10) * (1.0 - min(1.0, std / max(abs(ate), 0.01)))

        return CausalEffect(
            parameter=parameter,
            delta=delta,
            metric=metric,
            ate=round(ate, 6),
            ite_std=round(std, 6),
            n_matched=len(matched),
            confidence=round(max(0.0, confidence), 4),
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return dot / (norm_a * norm_b)
