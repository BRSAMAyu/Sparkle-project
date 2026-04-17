from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DECISION_POLICY_VERSION = "2026-04-04.v1"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int = 160) -> str:
    text = " ".join(_strip(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _contains_any(text: str, keywords: set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DecisionPolicyOutput:
    policy_version: str
    experience_mode: str
    intervention_family: str
    system_adjustments: tuple[dict[str, Any], ...]
    user_visible_expression: dict[str, Any]
    feedback_hook: dict[str, Any]
    reversibility_level: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "experience_mode": self.experience_mode,
            "intervention_family": self.intervention_family,
            "system_adjustments": list(self.system_adjustments),
            "user_visible_expression": dict(self.user_visible_expression),
            "feedback_hook": dict(self.feedback_hook),
            "reversibility_level": self.reversibility_level,
        }


class DecisionPolicyCompiler:
    """Compile a turn-level decision policy from residual diagnosis and bounded runtime state."""

    _OVERLOAD_KEYWORDS = {
        "too much",
        "overwhelmed",
        "burnout",
        "exhausted",
        "cannot start",
        "can't start",
        "太多",
        "扛不住",
        "开始不了",
        "撑不住",
        "压力太大",
        "负荷太高",
    }

    def compile(
        self,
        *,
        diagnosis: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        user_strategy_state: dict[str, Any] | None,
        recommended_stance: dict[str, Any] | None,
        vision: dict[str, Any] | None,
        current_state: dict[str, Any] | None,
        primary_obstacle: dict[str, Any] | None,
        intervention: dict[str, Any] | None,
        outcome: dict[str, Any] | None,
        sparkle_self_state: dict[str, Any] | None,
    ) -> DecisionPolicyOutput:
        diagnosis = _as_dict(diagnosis)
        user_context_payload = _as_dict(user_context_payload)
        user_strategy_state = _as_dict(user_strategy_state)
        recommended_stance = _as_dict(recommended_stance)
        vision = _as_dict(vision)
        current_state = _as_dict(current_state)
        primary_obstacle = _as_dict(primary_obstacle)
        intervention = _as_dict(intervention)
        outcome = _as_dict(outcome)
        sparkle_self_state = _as_dict(sparkle_self_state)

        confidence = _as_float(diagnosis.get("confidence"), _as_float(sparkle_self_state.get("confidence_estimate"), 0.6))
        primary_residual = _strip(diagnosis.get("primary_residual")) or "R_unknown"
        loop_type = _strip(diagnosis.get("loop_type")) or "truth_seeking"
        outcome_status = _strip(outcome.get("status"))
        session_mode = _strip(user_strategy_state.get("session_mode"))
        obstacle_type = _strip(primary_obstacle.get("obstacle_type"))
        intervention_active = bool(intervention.get("active"))
        decision_corpus = " | ".join(
            part
            for part in (
                _strip(user_context_payload.get("current_query")),
                _strip(primary_obstacle.get("summary")),
                _strip(current_state.get("snapshot")),
                _strip(diagnosis.get("what_matters_now")),
            )
            if part
        )

        experience_mode = self._choose_experience_mode(
            primary_residual=primary_residual,
            loop_type=loop_type,
            outcome_status=outcome_status,
            session_mode=session_mode,
            obstacle_type=obstacle_type,
            intervention_active=intervention_active,
            decision_corpus=decision_corpus,
        )
        intervention_family = self._choose_intervention_family(
            primary_residual=primary_residual,
            experience_mode=experience_mode,
            loop_type=loop_type,
        )
        reversibility_level = self._choose_reversibility_level(confidence)
        system_adjustments = self._build_system_adjustments(
            primary_residual=primary_residual,
            experience_mode=experience_mode,
            confidence=confidence,
            reversibility_level=reversibility_level,
            user_strategy_state=user_strategy_state,
            diagnosis=diagnosis,
            outcome=outcome,
        )
        user_visible_expression = self._build_user_visible_expression(
            experience_mode=experience_mode,
            intervention_family=intervention_family,
            recommended_stance=recommended_stance,
            diagnosis=diagnosis,
            vision=vision,
            primary_obstacle=primary_obstacle,
        )
        feedback_hook = self._build_feedback_hook(
            experience_mode=experience_mode,
            primary_residual=primary_residual,
            system_adjustments=system_adjustments,
            current_state=current_state,
            outcome=outcome,
        )
        return DecisionPolicyOutput(
            policy_version=DECISION_POLICY_VERSION,
            experience_mode=experience_mode,
            intervention_family=intervention_family,
            system_adjustments=tuple(system_adjustments),
            user_visible_expression=user_visible_expression,
            feedback_hook=feedback_hook,
            reversibility_level=reversibility_level,
        )

    def _choose_experience_mode(
        self,
        *,
        primary_residual: str,
        loop_type: str,
        outcome_status: str,
        session_mode: str,
        obstacle_type: str,
        intervention_active: bool,
        decision_corpus: str,
    ) -> str:
        if primary_residual == "R_unknown":
            return "clarify"
        if primary_residual == "R_n" or loop_type == "normative":
            return "decide"
        if primary_residual == "R_i":
            return "reframe"
        if primary_residual == "R_e":
            if intervention_active and outcome_status in {"mixed", "stalled"}:
                return "review"
            return "explain"
        if primary_residual == "R_c":
            overload = (
                session_mode == "recovery"
                or outcome_status in {"mixed", "stalled"}
                or obstacle_type in {"progress_risk", "plan_risk"}
                or _contains_any(decision_corpus, self._OVERLOAD_KEYWORDS)
            )
            return "stabilize" if overload else "mobilize"
        if primary_residual == "R_mixed":
            return "review" if outcome_status in {"mixed", "stalled"} else "clarify"
        return "clarify"

    def _choose_intervention_family(
        self,
        *,
        primary_residual: str,
        experience_mode: str,
        loop_type: str,
    ) -> str:
        if experience_mode == "review":
            return "trajectory_review"
        if experience_mode == "clarify":
            return "clarifying_probe"
        if experience_mode == "explain":
            return "understanding_repair"
        if experience_mode == "decide":
            return "criteria_construction" if loop_type == "normative" else "decision_navigation"
        if experience_mode == "reframe":
            return "identity_repair"
        if experience_mode == "stabilize":
            return "load_shedding"
        if experience_mode == "mobilize":
            return "scaffolded_activation"
        return {
            "R_e": "understanding_repair",
            "R_n": "criteria_construction",
            "R_c": "scaffolded_activation",
            "R_i": "identity_repair",
            "R_mixed": "diagnostic_rebalance",
        }.get(primary_residual, "clarifying_probe")

    def _choose_reversibility_level(self, confidence: float) -> str:
        if confidence < 0.65:
            return "high"
        if confidence < 0.82:
            return "medium"
        return "low"

    def _build_system_adjustments(
        self,
        *,
        primary_residual: str,
        experience_mode: str,
        confidence: float,
        reversibility_level: str,
        user_strategy_state: dict[str, Any],
        diagnosis: dict[str, Any],
        outcome: dict[str, Any],
    ) -> list[dict[str, Any]]:
        adjustments: list[dict[str, Any]] = []

        def recommend(field: str, value: Any, *, reason: str) -> None:
            current_value = user_strategy_state.get(field)
            if current_value == value:
                return
            adjustments.append(
                {
                    "field": field,
                    "current_value": current_value,
                    "recommended_value": value,
                    "target_layer": "session" if reversibility_level != "low" else "episode_candidate",
                    "reason": reason,
                    "confidence_gate": round(confidence, 2),
                    "reversible": reversibility_level != "low",
                }
            )

        if experience_mode == "explain":
            recommend(
                "retrieval_emphasis",
                "user_materials" if (diagnosis.get("grounding_priority") or [None])[0] == "user_materials" else "balanced",
                reason="Cognitive residuals should ground first in user materials before general explanation.",
            )
            recommend(
                "explanation_style",
                "step_by_step",
                reason="Understanding repair works better with a slower explanation path.",
            )
        elif experience_mode == "decide":
            recommend(
                "session_mode",
                "exploratory",
                reason="Normative turns benefit from comparison and criteria-building instead of a single answer path.",
            )
            recommend(
                "push_vs_support",
                0.35,
                reason="Decision support should avoid overprescribing before criteria are clear.",
            )
        elif experience_mode == "stabilize":
            recommend(
                "session_mode",
                "recovery",
                reason="Control overload should reduce task pressure in-session immediately.",
            )
            recommend(
                "intervention_intensity",
                "low",
                reason="When friction is high, lighter interventions are more reversible and easier to accept.",
            )
            current_difficulty = int(user_strategy_state.get("difficulty_level") or 3)
            recommend(
                "difficulty_level",
                max(1, current_difficulty - 1),
                reason="Lowering difficulty helps restart execution without moralizing the control gap.",
            )
        elif experience_mode == "mobilize":
            recommend(
                "session_mode",
                "guided",
                reason="Mobilization should convert intention into a crisp next step.",
            )
            recommend(
                "push_vs_support",
                0.55,
                reason="A moderate push helps action when the main issue is execution friction.",
            )
        elif experience_mode == "reframe":
            recommend(
                "session_mode",
                "review",
                reason="Identity tension benefits from evidence-based review before new pressure is added.",
            )
            recommend(
                "intervention_intensity",
                "low",
                reason="Identity repair should stay careful and restorative, not forceful.",
            )
            recommend(
                "push_vs_support",
                0.3,
                reason="Identity work should lead with grounded support rather than pressure.",
            )
        elif experience_mode == "review":
            recommend(
                "session_mode",
                "review",
                reason="When the prior move may be mismatched, the system should compare what changed before pushing ahead.",
            )
            recommend(
                "intervention_intensity",
                "low" if _strip(outcome.get("status")) in {"mixed", "stalled"} else "medium",
                reason="Review mode should stay reversible while the system checks fit.",
            )
        else:
            recommend(
                "intervention_intensity",
                "low",
                reason="When residual confidence is weak, smaller reversible adjustments are safer.",
            )

        return adjustments[:4]

    def _build_user_visible_expression(
        self,
        *,
        experience_mode: str,
        intervention_family: str,
        recommended_stance: dict[str, Any],
        diagnosis: dict[str, Any],
        vision: dict[str, Any],
        primary_obstacle: dict[str, Any],
    ) -> dict[str, Any]:
        goal = _strip(vision.get("primary_goal") or vision.get("active_plan"))
        obstacle = _strip(primary_obstacle.get("summary") or primary_obstacle.get("label"))
        what_matters_now = _strip(diagnosis.get("what_matters_now"))
        stance = _strip(recommended_stance.get("stance"))

        response_shape = {
            "clarify": "ask_one_targeted_question_then_hold_back",
            "explain": "repair_model_then_verify",
            "reframe": "name_tension_then_ground_in_evidence",
            "stabilize": "lower_load_then_offer_smallest_next_step",
            "mobilize": "give_one_concrete_move_then_follow_through",
            "decide": "surface_criteria_then_compare_futures",
            "review": "compare_last_move_with_outcome_then_recalibrate",
        }.get(experience_mode, "steady_guidance")
        opening_intent = {
            "clarify": "Do not act strongly yet; narrow the real problem first.",
            "explain": "Start from the real misconception, not generic encouragement.",
            "reframe": "Be careful, truthful, and continuity-based.",
            "stabilize": "Reduce burden immediately and make the next step feel survivable.",
            "mobilize": "Turn insight into motion without adding unnecessary theory.",
            "decide": "Help the user build judgment instead of outsourcing it to Sparkle.",
            "review": "Check fit before escalating the plan.",
        }.get(experience_mode, "Stay aligned with what matters now.")

        return {
            "opening_intent": opening_intent,
            "response_shape": response_shape,
            "should_feel_like": stance or what_matters_now,
            "anchor": _compact_text(obstacle or goal or what_matters_now, limit=96),
            "intervention_family": intervention_family,
        }

    def _build_feedback_hook(
        self,
        *,
        experience_mode: str,
        primary_residual: str,
        system_adjustments: list[dict[str, Any]],
        current_state: dict[str, Any],
        outcome: dict[str, Any],
    ) -> dict[str, Any]:
        monitor = {
            "explain": "whether the concept now feels clearer or still fuzzy",
            "decide": "whether the criteria now feel more explicit and usable",
            "reframe": "whether the user feels more grounded in evidence than in self-negation",
            "stabilize": "whether the next step now feels lighter and more doable",
            "mobilize": "whether the user can start immediately without new friction",
            "review": "whether the previous move helped, missed, or overloaded the user",
            "clarify": "whether the clarified target changes the kind of help needed",
        }.get(experience_mode, "whether the move improved fit")
        ask = {
            "R_e": "Does this make the actual confusion clearer, or is a different concept still blocking you?",
            "R_n": "Do these criteria fit what you really care about, or is an important standard still missing?",
            "R_c": "Does this now feel light enough to start, or is the bottleneck somewhere else?",
            "R_i": "Does this feel truer to the evidence, or am I still missing the part that hurts most?",
            "R_mixed": "Which part is heavier right now: understanding it or actually doing it?",
        }.get(primary_residual, "Did this move fit what you needed, or should we recalibrate?")
        return {
            "monitor": monitor,
            "ask": ask,
            "adjustment_count": len(system_adjustments),
            "current_outcome_status": _strip(outcome.get("status")) or _strip(current_state.get("progress_signal")),
        }
