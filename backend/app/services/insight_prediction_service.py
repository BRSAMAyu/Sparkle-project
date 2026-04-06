from __future__ import annotations

from typing import Any

from app.core.user_insight_state import UserInsightState


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _bounded(value: float, *, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _level_from_score(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _confidence_from_support(support_count: int, *, base: float = 0.58, ceiling: float = 0.86) -> float:
    return round(min(ceiling, base + max(0, min(support_count, 6)) * 0.045), 3)


class InsightPredictionService:
    """Build evidence-bounded forward-looking guidance from the canonical insight state."""

    def compile_predictions(
        self,
        *,
        state: UserInsightState,
        turn_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        features = self._extract_features(state=state, turn_signals=turn_signals or {})
        predictions = {
            "planning_readiness": self._predict_planning_readiness(features),
            "overload_risk": self._predict_overload_risk(features),
            "schedule_fit": self._predict_schedule_fit(features),
            "plan_slippage_risk": self._predict_plan_slippage(features),
            "intervention_receptivity": self._predict_intervention_receptivity(features),
            "seed_effectiveness": self._predict_seed_effectiveness(features),
            "likely_task_failure_modes": self._predict_failure_modes(features),
        }
        return predictions

    def _extract_features(self, *, state: UserInsightState, turn_signals: dict[str, Any]) -> dict[str, Any]:
        analysis = state.multi_span_analysis if isinstance(state.multi_span_analysis, dict) else {}
        short_span = analysis.get("short_span") if isinstance(analysis.get("short_span"), dict) else {}
        medium_span = analysis.get("medium_span") if isinstance(analysis.get("medium_span"), dict) else {}
        confidence_decay = analysis.get("confidence_decay") if isinstance(analysis.get("confidence_decay"), dict) else {}
        calendar = state.temporal_patterns.get("calendar") if isinstance(state.temporal_patterns.get("calendar"), dict) else {}
        drift = medium_span.get("task_start_completion_drift") if isinstance(medium_span.get("task_start_completion_drift"), dict) else {}

        return {
            "goal_count": len(state.goals),
            "pain_count": len(state.recent_pain_points),
            "win_count": len(state.recent_wins),
            "bottleneck_count": len(state.active_bottlenecks),
            "contradiction_count": len(state.active_contradictions),
            "missing_count": len(state.missing_information),
            "stable_signal_count": len(confidence_decay.get("stable_signals") or []),
            "stale_signal_count": len(confidence_decay.get("stale_signals") or []),
            "traction": _strip(short_span.get("current_traction") or state.current_state.get("current_traction")),
            "overload_pressure": _strip(short_span.get("overload_pressure") or state.current_state.get("overload_pressure")),
            "focus_alignment": _strip(short_span.get("focus_alignment") or state.current_state.get("focus_alignment")),
            "calendar_density": _strip(calendar.get("density_level") or state.current_state.get("calendar_density_level")),
            "deadline_pressure": _strip(medium_span.get("deadline_pressure")),
            "drift_label": _strip(drift.get("label") or state.current_state.get("task_drift_label")),
            "completion_ratio": float(drift.get("completion_ratio") or 0.0),
            "has_focus_hours": bool(state.inferred_work_style.get("peak_focus_hours")),
            "has_fallback_focus_hours": bool(state.inferred_work_style.get("achievement_peak_hours")),
            "support_level": _strip(state.inferred_work_style.get("accountability_support")),
            "motivation_response": _strip(state.inferred_work_style.get("achievement_motivation_response")),
            "reward_sensitivity": _strip(state.inferred_work_style.get("achievement_reward_sensitivity")),
            "preferred_tools": list(state.inferred_work_style.get("preferred_tools") or []),
            "content_depth_preference": _strip(state.stable_preferences.get("content_depth_preference")),
            "curiosity_preference": state.stable_preferences.get("curiosity_preference"),
            "exam_days_left": self._safe_int(calendar.get("exam_urgency", {}).get("days_left")),
            "turn_low_capacity": bool(turn_signals.get("low_capacity_language")),
            "turn_wants_push": bool(turn_signals.get("wants_push")),
        }

    def _predict_planning_readiness(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.35
        signals = ["goals", "recent_progress", "overload_pressure", "missing_information"]
        if features["goal_count"] > 0:
            score += 0.14
        if features["win_count"] > 0:
            score += 0.12
        if features["stable_signal_count"] >= 3:
            score += 0.08
        if features["traction"] == "high":
            score += 0.08
        if features["overload_pressure"] == "high":
            score -= 0.17
        elif features["overload_pressure"] == "medium":
            score -= 0.08
        if features["missing_count"] >= 3:
            score -= 0.12
        elif features["missing_count"] >= 1:
            score -= 0.05
        if features["contradiction_count"] >= 2:
            score -= 0.1
        if features["drift_label"] == "high_drift":
            score -= 0.08

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        recommended_action = "proceed" if level == "high" else ("provisional" if level == "medium" else "ask")
        return self._payload(
            kind="guidance",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(4 + features["stable_signal_count"]),
            explanation=(
                "Planning readiness rises when goals, recent wins, and stable signals line up; it drops when overload, drift, or key unknowns dominate."
            ),
            recommended_action=recommended_action,
            evidence_signals=signals,
        )

    def _predict_overload_risk(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.2
        signals = ["overload_pressure", "calendar_density", "active_bottlenecks", "deadline_pressure"]
        if features["overload_pressure"] == "high":
            score += 0.3
        elif features["overload_pressure"] == "medium":
            score += 0.18
        if features["calendar_density"] == "high":
            score += 0.18
        elif features["calendar_density"] == "medium":
            score += 0.08
        if features["bottleneck_count"] >= 4:
            score += 0.12
        if features["deadline_pressure"] == "high":
            score += 0.12
        if features["pain_count"] > features["win_count"]:
            score += 0.08
        if features["support_level"] == "active":
            score -= 0.05
        if features["turn_low_capacity"]:
            score += 0.08

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        return self._payload(
            kind="risk",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(4 + features["bottleneck_count"]),
            explanation=(
                "Overload risk climbs when current pressure, calendar density, and unresolved bottlenecks pile up in the same window."
            ),
            recommended_action="shrink_scope" if level == "high" else "monitor_load",
            evidence_signals=signals,
        )

    def _predict_schedule_fit(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.35
        signals = ["focus_alignment", "calendar_density", "peak_focus_hours", "achievement_peak_hours"]
        if features["focus_alignment"] == "supported":
            score += 0.22
        elif features["focus_alignment"] == "constrained":
            score -= 0.1
        if features["has_focus_hours"]:
            score += 0.15
        elif features["has_fallback_focus_hours"]:
            score += 0.08
        if features["calendar_density"] == "high":
            score -= 0.18
        elif features["calendar_density"] == "medium":
            score -= 0.08
        if features["deadline_pressure"] == "high":
            score -= 0.05

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        return self._payload(
            kind="fit",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(3 + int(features["has_focus_hours"]) + int(features["has_fallback_focus_hours"])),
            explanation=(
                "Schedule fit is strongest when Sparkle knows a usable focus window and the calendar is not already saturated."
            ),
            recommended_action="use_focus_window" if level != "low" else "offer_fallback_slot",
            evidence_signals=signals,
        )

    def _predict_plan_slippage(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.22
        signals = ["task_drift", "overload_pressure", "contradictions", "missing_information"]
        if features["drift_label"] == "high_drift":
            score += 0.28
        elif features["drift_label"] == "moderate_drift":
            score += 0.15
        if features["overload_pressure"] == "high":
            score += 0.16
        if features["contradiction_count"] >= 1:
            score += 0.1
        if features["missing_count"] >= 2:
            score += 0.08
        if features["traction"] == "high":
            score -= 0.08

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        return self._payload(
            kind="risk",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(4 + features["contradiction_count"]),
            explanation=(
                "Slippage risk rises when starts do not convert into completions, pressure is high, or the profile still carries unresolved contradictions."
            ),
            recommended_action="tighten_plan" if level == "high" else "checkpoint_plan",
            evidence_signals=signals,
        )

    def _predict_intervention_receptivity(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.32
        signals = ["motivation_response", "reward_sensitivity", "support_level", "current_traction"]
        if features["motivation_response"]:
            score += 0.15
        if features["reward_sensitivity"] == "high":
            score += 0.08
        if features["support_level"] in {"active", "available"}:
            score += 0.1
        if features["traction"] == "high":
            score += 0.08
        elif features["traction"] == "low":
            score -= 0.06
        if features["overload_pressure"] == "high":
            score -= 0.12
        if features["turn_wants_push"] and features["overload_pressure"] != "high":
            score += 0.05

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        return self._payload(
            kind="guidance",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(4 + int(bool(features["motivation_response"]))),
            explanation=(
                "Intervention receptivity improves when Sparkle knows what kind of reinforcement lands well and the user still has enough traction to act on it."
            ),
            recommended_action="personalize_reinforcement" if level != "low" else "reduce_pressure_first",
            evidence_signals=signals,
        )

    def _predict_seed_effectiveness(self, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.3
        signals = ["content_depth_preference", "curiosity_preference", "preferred_tools", "schedule_fit"]
        if features["content_depth_preference"]:
            score += 0.12
        curiosity = features["curiosity_preference"]
        if isinstance(curiosity, (int, float)) and curiosity >= 0.6:
            score += 0.1
        if features["preferred_tools"]:
            score += 0.08
        if features["focus_alignment"] == "supported":
            score += 0.08
        if features["overload_pressure"] == "high":
            score -= 0.1
        if features["pain_count"] > features["win_count"] + 1:
            score -= 0.05

        bounded = round(_bounded(score), 3)
        level = _level_from_score(bounded)
        return self._payload(
            kind="opportunity",
            level=level,
            score=bounded,
            confidence=_confidence_from_support(3 + len(features["preferred_tools"])),
            explanation=(
                "Seed effectiveness is higher when the user has visible content appetite, reusable tool habits, and enough room in the current window to engage."
            ),
            recommended_action="offer_seed" if level != "low" else "wait_for_lighter_window",
            evidence_signals=signals,
        )

    def _predict_failure_modes(self, features: dict[str, Any]) -> dict[str, Any]:
        modes: list[str] = []
        if features["overload_pressure"] == "high":
            modes.append("scope_too_heavy_for_current_window")
        if features["drift_label"] == "high_drift":
            modes.append("starts_without_completion")
        if features["contradiction_count"] >= 1:
            modes.append("self_report_and_behavior_out_of_sync")
        if features["calendar_density"] == "high" and not features["has_focus_hours"]:
            modes.append("calendar_crowding_without_clear_focus_slot")
        if not modes:
            modes.append("no_dominant_failure_mode_detected")

        return {
            "kind": "risk",
            "level": "high" if len(modes) >= 3 else ("medium" if len(modes) >= 2 else "low"),
            "confidence": _confidence_from_support(len(modes), base=0.56, ceiling=0.8),
            "modes": modes,
            "explanation": "These are the failure patterns most likely to derail the next plan under the current profile state.",
        }

    @staticmethod
    def _payload(
        *,
        kind: str,
        level: str,
        score: float,
        confidence: float,
        explanation: str,
        recommended_action: str,
        evidence_signals: list[str],
    ) -> dict[str, Any]:
        return {
            "kind": kind,
            "level": level,
            "score": score,
            "confidence": confidence,
            "explanation": explanation,
            "recommended_action": recommended_action,
            "evidence_signals": evidence_signals,
        }

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
