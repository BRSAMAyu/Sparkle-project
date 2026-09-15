"""Quality gates for DistilledStrategy publication and reuse."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import DistilledStrategy


@dataclass(frozen=True)
class QualityGateDecision:
    passed: bool
    reasons: tuple[str, ...] = ()
    score: float = 0.0


def evaluate_strategy_quality(strategy: DistilledStrategy) -> QualityGateDecision:
    """Evaluate whether a distilled strategy is safe and strong enough to keep."""

    reasons: list[str] = []
    if strategy.evidence_strength < 0.5:
        reasons.append("evidence_strength_below_threshold")
    if strategy.diversity_score < 0.2:
        reasons.append("diversity_score_below_threshold")
    if not strategy.deidentification_verified:
        reasons.append("deidentification_not_verified")
    safety_audit = strategy.safety_audit or {}
    required_true = ("deidentified", "reviewed", "safe")
    missing_or_false = [key for key in required_true if not safety_audit.get(key, False)]
    if missing_or_false:
        reasons.append(f"safety_audit_failed:{','.join(missing_or_false)}")
    score = round((strategy.evidence_strength * 0.6) + (strategy.diversity_score * 0.4), 3)
    return QualityGateDecision(passed=not reasons, reasons=tuple(reasons), score=score)
