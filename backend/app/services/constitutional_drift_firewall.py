from __future__ import annotations

from typing import Any

from app.services.five_layer_learning_contract import ConstitutionalSafetyReport
from app.services.soul_drift_evaluator import SoulDriftEvaluator


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


class ConstitutionalDriftFirewall:
    """Block durable learning that drifts toward manipulation, attachment, or goal hijack."""

    MANIPULATION_MARKERS = (
        "dependent",
        "depend on me",
        "hooked",
        "keep them here",
        "retention",
        "make them need",
        "attachment",
    )
    FREEDOM_MARKERS = (
        "pressure them",
        "guilt",
        "do not let them choose",
        "remove choice",
        "trap",
    )
    GOAL_HIJACK_MARKERS = (
        "optimize engagement",
        "prioritize sparkle",
        "ignore the user's goal",
        "replace their goal",
    )
    TRUTH_MARKERS = (
        "hide the truth",
        "soften the truth",
        "flatter",
        "pretend certainty",
        "theatrical",
    )

    def __init__(self) -> None:
        self.soul_drift_evaluator = SoulDriftEvaluator()

    def evaluate_change(
        self,
        *,
        change_type: str,
        target_layer: str,
        proposed_value: Any,
        evidence: dict[str, Any] | None = None,
        runtime_signals: dict[str, Any] | None = None,
    ) -> ConstitutionalSafetyReport:
        text = " ".join(
            part for part in (
                _strip(proposed_value),
                _strip(_as_dict(evidence).get("snippet")),
                _strip(_as_dict(evidence).get("reason")),
                _strip(change_type),
                _strip(target_layer),
            ) if part
        ).lower()

        manipulation_risk = self._keyword_risk(text, self.MANIPULATION_MARKERS, baseline=0.08)
        freedom_risk = self._keyword_risk(text, self.FREEDOM_MARKERS, baseline=0.06)
        goal_hijack_risk = self._keyword_risk(text, self.GOAL_HIJACK_MARKERS, baseline=0.05)
        truth_discipline_risk = self._keyword_risk(text, self.TRUTH_MARKERS, baseline=0.08)

        runtime = _as_dict(runtime_signals)
        if runtime:
            soul = self.soul_drift_evaluator.evaluate(
                current_runtime=_as_dict(runtime.get("current_runtime")),
                previous_runtime=_as_dict(runtime.get("previous_runtime")),
                outcomes=_as_dict(runtime.get("outcomes")),
                signals=_as_dict(runtime.get("signals")),
            )
            drift = float(soul.drift_score)
            if "constitution_adjacent_proposals" in soul.drift_indicators:
                truth_discipline_risk = max(truth_discipline_risk, 0.65)
            manipulation_risk = max(manipulation_risk, drift * 0.6)
            freedom_risk = max(freedom_risk, drift * 0.45)
            if drift >= 0.4:
                truth_discipline_risk = max(truth_discipline_risk, 0.58)

        blocked_reasons: list[str] = []
        constraints: list[str] = []
        disposition = "allow"
        escalation_required = False

        if max(manipulation_risk, freedom_risk, goal_hijack_risk, truth_discipline_risk) >= 0.8:
            blocked_reasons.append("constitutional_block")
            disposition = "blocked"
        elif max(manipulation_risk, freedom_risk, goal_hijack_risk, truth_discipline_risk) >= 0.55:
            disposition = "escalate_review"
            escalation_required = True
            constraints.append("Require human review before durable promotion.")
        elif max(manipulation_risk, freedom_risk, goal_hijack_risk, truth_discipline_risk) >= 0.3:
            disposition = "allow_with_constraints"
            constraints.append("Keep the learning auditable, compact, and reversible.")

        allowed = disposition in {"allow", "allow_with_constraints"}
        explanation = (
            f"Evaluated {change_type} for {target_layer}: manipulation={manipulation_risk:.2f}, "
            f"freedom={freedom_risk:.2f}, goal_hijack={goal_hijack_risk:.2f}, truth={truth_discipline_risk:.2f}."
        )
        return ConstitutionalSafetyReport(
            allowed=allowed,
            blocked_reasons=tuple(blocked_reasons),
            manipulation_risk=round(manipulation_risk, 4),
            freedom_risk=round(freedom_risk, 4),
            goal_hijack_risk=round(goal_hijack_risk, 4),
            truth_discipline_risk=round(truth_discipline_risk, 4),
            disposition=disposition,
            allowed_with_constraints=tuple(constraints),
            escalation_required=escalation_required,
            explanation=explanation,
        )

    def evaluate_system_change(
        self,
        *,
        knob_id: str,
        reason: str,
        rights_model: str,
        reversible: bool,
    ) -> ConstitutionalSafetyReport:
        return self.evaluate_change(
            change_type=f"system_knob:{knob_id}:{rights_model}:{'reversible' if reversible else 'non_reversible'}",
            target_layer="system",
            proposed_value=reason,
            evidence={"reason": reason},
        )

    @staticmethod
    def _keyword_risk(text: str, markers: tuple[str, ...], *, baseline: float) -> float:
        score = baseline
        for marker in markers:
            if marker in text:
                score += 0.28
        return min(1.0, score)
