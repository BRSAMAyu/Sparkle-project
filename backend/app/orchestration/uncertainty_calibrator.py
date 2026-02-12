from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings


@dataclass
class UncertaintyCalibrationResult:
    uncertainty_score: float
    clarification_needed: bool
    reasons: list[str] = field(default_factory=list)
    clarification_points: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, str]:
        return {
            "uncertainty_score": f"{self.uncertainty_score:.4f}",
            "clarification_needed": "true" if self.clarification_needed else "false",
        }


class UncertaintyCalibrator:
    """Calibrate execution uncertainty before running a generated plan."""

    AMBIGUOUS_TOKENS = (
        "随便",
        "差不多",
        "你看着办",
        "whatever",
        "something",
        "maybe",
        "大概",
        "先试试",
    )

    @classmethod
    def calibrate(
        cls,
        *,
        message: str,
        route_confidence: float,
        verifier_score: float,
        contract_coverage: float,
        plan_feasibility_score: float,
        decomposition_gap_count: int,
    ) -> UncertaintyCalibrationResult:
        reasons: list[str] = []
        msg = (message or "").lower()
        ambiguous_hit = any(token in msg for token in cls.AMBIGUOUS_TOKENS)

        route_confidence = max(0.0, min(float(route_confidence), 1.0))
        verifier_score = max(0.0, min(float(verifier_score), 1.0))
        contract_coverage = max(0.0, min(float(contract_coverage), 1.0))
        plan_feasibility_score = max(0.0, min(float(plan_feasibility_score), 1.0))
        gap_penalty = min(max(int(decomposition_gap_count), 0), 8) / 8.0

        uncertainty = (
            0.35 * (1.0 - verifier_score)
            + 0.25 * (1.0 - route_confidence)
            + 0.2 * (1.0 - contract_coverage)
            + 0.1 * (1.0 - plan_feasibility_score)
            + 0.1 * gap_penalty
        )
        if ambiguous_hit:
            uncertainty = min(1.0, uncertainty + 0.15)
            reasons.append("ambiguous_user_intent")

        if verifier_score < 0.7:
            reasons.append("low_verifier_score")
        if route_confidence < 0.55:
            reasons.append("low_route_confidence")
        if contract_coverage < 0.8:
            reasons.append("low_contract_coverage")
        if plan_feasibility_score < 0.65:
            reasons.append("low_plan_feasibility")
        if decomposition_gap_count > 0:
            reasons.append("decomposition_gaps_present")

        clarification_points = cls._select_clarification_points(reasons)
        threshold = float(getattr(settings, "UNCERTAINTY_CLARIFICATION_THRESHOLD", 0.62))
        clarification_needed = bool(uncertainty >= threshold)
        return UncertaintyCalibrationResult(
            uncertainty_score=round(uncertainty, 4),
            clarification_needed=clarification_needed,
            reasons=reasons,
            clarification_points=clarification_points,
        )

    @staticmethod
    def _select_clarification_points(reasons: list[str]) -> list[str]:
        mapping = {
            "low_verifier_score": "补充目标与约束",
            "low_contract_coverage": "补充里程碑和验收标准",
            "low_route_confidence": "明确任务类型和优先级",
            "low_plan_feasibility": "提供可用资源与时间预算",
            "decomposition_gaps_present": "补充缺失的拆解字段",
            "ambiguous_user_intent": "明确你最想先推进的结果",
        }
        selected: list[str] = []
        for reason in reasons:
            point = mapping.get(reason)
            if point and point not in selected:
                selected.append(point)
            if len(selected) >= 3:
                break
        return selected
