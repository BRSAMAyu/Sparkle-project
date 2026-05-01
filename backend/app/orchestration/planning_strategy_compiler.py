from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from app.orchestration.plan_quality_contract import (
    PLAN_MODE_FULL,
    PLAN_MODE_NEXT_STEP_ONLY,
    PLAN_MODE_PROVISIONAL,
    PlanQualityContract,
    build_plan_quality_contract,
)

PLANNING_STRATEGY_VERSION = "2026-04-05.v1"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    with_timezone = normalized if "T" in normalized else f"{normalized}T00:00:00"
    try:
        parsed = datetime.fromisoformat(with_timezone)
    except ValueError:
        return None
    return parsed.date()


@dataclass(frozen=True)
class CompiledPlanningStrategy:
    plan_type: str
    plan_horizon: str
    plan_depth: str
    scaffold_level: str
    pacing_profile: str
    checkpoint_cadence: str
    grounding_mode: str
    assumption_policy: str
    fallback_policy: str
    required_plan_sections: tuple[str, ...]
    plan_mode: str
    deadline_days: int | None = None
    max_session_minutes: int | None = None
    daily_capacity_minutes: int | None = None
    overload_signal: bool = False
    adaptation_trigger: str = ""
    first_step_hint: str = ""
    assumption_basis: tuple[str, ...] = ()
    outcome_learning_hints: tuple[str, ...] = ()
    known_failure_avoidance_rules: tuple[str, ...] = ()
    known_success_patterns: tuple[str, ...] = ()
    planning_bias_constraints: dict[str, Any] = field(default_factory=dict)
    version: str = PLANNING_STRATEGY_VERSION
    generated_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_type": self.plan_type,
            "plan_horizon": self.plan_horizon,
            "plan_depth": self.plan_depth,
            "scaffold_level": self.scaffold_level,
            "pacing_profile": self.pacing_profile,
            "checkpoint_cadence": self.checkpoint_cadence,
            "grounding_mode": self.grounding_mode,
            "assumption_policy": self.assumption_policy,
            "fallback_policy": self.fallback_policy,
            "required_plan_sections": list(self.required_plan_sections),
            "plan_mode": self.plan_mode,
            "deadline_days": self.deadline_days,
            "max_session_minutes": self.max_session_minutes,
            "daily_capacity_minutes": self.daily_capacity_minutes,
            "overload_signal": self.overload_signal,
            "adaptation_trigger": self.adaptation_trigger,
            "first_step_hint": self.first_step_hint,
            "assumption_basis": list(self.assumption_basis),
            "outcome_learning_hints": list(self.outcome_learning_hints),
            "known_failure_avoidance_rules": list(self.known_failure_avoidance_rules),
            "known_success_patterns": list(self.known_success_patterns),
            "planning_bias_constraints": dict(self.planning_bias_constraints),
            "version": self.version,
            "generated_at": self.generated_at,
        }


class PlanningStrategyCompiler:
    """Compile planning runtime state into a deterministic planning recipe."""

    def __init__(self, contract: PlanQualityContract | None = None) -> None:
        self.contract = contract or build_plan_quality_contract()

    def compile(
        self,
        *,
        situation_brief: dict[str, Any] | None = None,
        user_context_payload: dict[str, Any] | None = None,
        plan_context: dict[str, Any] | None = None,
        planning_constraints: dict[str, Any] | None = None,
    ) -> CompiledPlanningStrategy:
        brief = _as_dict(situation_brief)
        user_context = _as_dict(user_context_payload)
        plan_context = _as_dict(plan_context)
        planning_constraints = _as_dict(planning_constraints)
        decision_context = _as_dict(brief.get("decision_context"))
        insight_state = _as_dict(brief.get("insight_state"))
        vision = _as_dict(brief.get("vision"))
        current_state = _as_dict(brief.get("current_state"))
        user_strategy_state = _as_dict(user_context.get("user_strategy_state"))
        material_grounding = _as_dict(user_context.get("user_material_grounding"))
        outcome_learning = _as_dict(
            brief.get("outcome_learning")
            or user_context.get("outcome_learning")
            or user_context.get("validated_outcome_learning")
        )
        planning_bias_constraints = _as_dict(outcome_learning.get("planning_bias_constraints"))
        outcome_learning_hints = tuple(
            _strip(item)
            for item in _as_list(outcome_learning.get("plan_generation_hints_from_outcomes"))
            if _strip(item)
        )
        known_failure_avoidance_rules = tuple(
            _strip(item)
            for item in _as_list(outcome_learning.get("known_failure_avoidance_rules"))
            if _strip(item)
        )
        known_success_patterns = tuple(
            _strip(item)
            for item in _as_list(outcome_learning.get("known_success_patterns"))
            if _strip(item)
        )

        readiness_action = _strip(decision_context.get("planning_readiness_action") or insight_state.get("recommended_action"))
        readiness_level = _strip(decision_context.get("planning_readiness") or insight_state.get("readiness_level"))
        plan_mode = self.contract.classify_mode(readiness_action=readiness_action)

        deadline_days = self._derive_deadline_days(vision=vision, plan_context=plan_context)
        overload_signal = self._detect_overload(
            decision_context=decision_context,
            current_state=current_state,
            user_strategy_state=user_strategy_state,
            planning_constraints=planning_constraints,
        )
        material_available = self._material_available(material_grounding=material_grounding, user_context=user_context)
        weak_knowledge_nodes = _as_list(planning_constraints.get("weak_knowledge_nodes"))
        route_intent = _strip(planning_constraints.get("route_intent"))

        plan_type = self._derive_plan_type(
            deadline_days=deadline_days,
            route_intent=route_intent,
            overload_signal=overload_signal,
            weak_knowledge_nodes=weak_knowledge_nodes,
        )
        plan_horizon = self._derive_plan_horizon(deadline_days=deadline_days, plan_mode=plan_mode)
        plan_depth = "light" if plan_mode == PLAN_MODE_NEXT_STEP_ONLY else ("standard" if overload_signal else "deep")
        scaffold_level = "high" if overload_signal or readiness_level in {"low", "medium"} else "medium"
        pacing_profile = "light" if overload_signal else ("push" if deadline_days is not None and deadline_days <= 7 else "steady")
        checkpoint_cadence = "daily" if deadline_days is not None and deadline_days <= 14 else ("every_2_days" if overload_signal else "twice_weekly")
        grounding_mode = self._derive_grounding_mode(
            plan_mode=plan_mode,
            material_available=material_available,
            weak_knowledge_nodes=weak_knowledge_nodes,
            decision_context=decision_context,
        )
        assumption_policy = "explicit_all" if plan_mode != PLAN_MODE_FULL else ("explicit_key" if readiness_level == "high" else "explicit_all")
        fallback_policy = self._derive_fallback_policy(plan_mode=plan_mode, overload_signal=overload_signal, grounding_mode=grounding_mode)
        required_sections = self.contract.get_required_sections(plan_mode)
        max_session_minutes = self._safe_int(planning_constraints.get("max_session_minutes")) or self._safe_int(
            _as_dict(planning_constraints.get("persona_constraints")).get("max_session_minutes")
        )
        daily_capacity_minutes = self._safe_int(plan_context.get("daily_available_minutes"))

        assumption_basis: list[str] = []
        for item in _as_list(decision_context.get("planning_blocking_unknowns") or insight_state.get("missing_information"))[:3]:
            text = _strip(item)
            if text:
                assumption_basis.append(text)
        if material_available and grounding_mode == "mandatory":
            assumption_basis.append("use_attached_materials")
        if overload_signal:
            assumption_basis.append("respect_current_capacity")

        first_step_hint = self._build_first_step_hint(plan_mode=plan_mode, overload_signal=overload_signal, plan_type=plan_type)
        adaptation_trigger = self._build_adaptation_trigger(overload_signal=overload_signal, deadline_days=deadline_days, plan_mode=plan_mode)
        scaffold_level = str(planning_bias_constraints.get("scaffold_level") or scaffold_level)
        if planning_bias_constraints.get("grounding_mode") == "mandatory":
            grounding_mode = "mandatory"
        if planning_bias_constraints.get("checkpoint_cadence") == "short":
            checkpoint_cadence = "daily"
        if planning_bias_constraints.get("lighter_first_step") is True:
            first_step_hint = "Start with the lightest validated first step before expanding scope."
            pacing_profile = "light"
            assumption_basis.append("validated_learning_prefers_light_first_step")
        if outcome_learning_hints:
            assumption_basis.extend(item for item in outcome_learning_hints[:2] if item not in assumption_basis)

        return CompiledPlanningStrategy(
            plan_type=plan_type,
            plan_horizon=plan_horizon,
            plan_depth=plan_depth,
            scaffold_level=scaffold_level,
            pacing_profile=pacing_profile,
            checkpoint_cadence=checkpoint_cadence,
            grounding_mode=grounding_mode,
            assumption_policy=assumption_policy,
            fallback_policy=fallback_policy,
            required_plan_sections=required_sections,
            plan_mode=plan_mode,
            deadline_days=deadline_days,
            max_session_minutes=max_session_minutes,
            daily_capacity_minutes=daily_capacity_minutes,
            overload_signal=overload_signal,
            adaptation_trigger=adaptation_trigger,
            first_step_hint=first_step_hint,
            assumption_basis=tuple(assumption_basis),
            outcome_learning_hints=outcome_learning_hints,
            known_failure_avoidance_rules=known_failure_avoidance_rules,
            known_success_patterns=known_success_patterns,
            planning_bias_constraints=planning_bias_constraints,
        )

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

    def _derive_deadline_days(self, *, vision: dict[str, Any], plan_context: dict[str, Any]) -> int | None:
        target = _parse_date(vision.get("target_date") or plan_context.get("target_date"))
        if target is None:
            return None
        delta = (target - _utcnow().date()).days
        return max(delta, 0)

    @staticmethod
    def _material_available(*, material_grounding: dict[str, Any], user_context: dict[str, Any]) -> bool:
        if _strip(material_grounding.get("status")) == "grounded" and _as_list(material_grounding.get("results")):
            return True
        file_ids = _as_list(user_context.get("file_ids"))
        return bool(file_ids)

    @staticmethod
    def _detect_overload(
        *,
        decision_context: dict[str, Any],
        current_state: dict[str, Any],
        user_strategy_state: dict[str, Any],
        planning_constraints: dict[str, Any],
    ) -> bool:
        if _strip(user_strategy_state.get("session_mode")) == "recovery":
            return True
        if _strip(decision_context.get("experience_mode")) == "stabilize":
            return True
        if _strip(decision_context.get("predicted_overload_risk")) == "high":
            return True
        if planning_constraints.get("require_warmup_task") is True:
            return True
        text_blob = " | ".join(
            part
            for part in (
                _strip(current_state.get("snapshot")),
                _strip(decision_context.get("what_matters_now")),
                _strip(decision_context.get("primary_obstacle_label")),
            )
            if part
        ).lower()
        overload_markers = ("overwhelmed", "cannot start", "too much", "开始不了", "扛不住", "没精力", "负荷太高")
        return any(marker in text_blob for marker in overload_markers)

    @staticmethod
    def _derive_plan_type(
        *,
        deadline_days: int | None,
        route_intent: str,
        overload_signal: bool,
        weak_knowledge_nodes: list[Any],
    ) -> str:
        if overload_signal:
            return "recovery"
        if deadline_days is not None and deadline_days <= 14:
            return "exam_sprint"
        if weak_knowledge_nodes:
            return "grounded_remediation"
        if route_intent in {"time_planning", "create_plan"}:
            return "structured_growth"
        return "general_planning"

    @staticmethod
    def _derive_plan_horizon(*, deadline_days: int | None, plan_mode: str) -> str:
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "next_24_hours"
        if deadline_days is None:
            return "1_to_2_weeks" if plan_mode == PLAN_MODE_PROVISIONAL else "2_to_4_weeks"
        if deadline_days <= 3:
            return "next_72_hours"
        if deadline_days <= 7:
            return "7_days"
        if deadline_days <= 14:
            return "14_days"
        return "30_days_plus"

    @staticmethod
    def _derive_grounding_mode(
        *,
        plan_mode: str,
        material_available: bool,
        weak_knowledge_nodes: list[Any],
        decision_context: dict[str, Any],
    ) -> str:
        if material_available:
            return "mandatory"
        if weak_knowledge_nodes:
            return "required_from_profile"
        if _strip(decision_context.get("phase_a_guardrail")) == "provisional_plan_with_assumptions":
            return "preferred"
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "light"
        return "preferred"

    @staticmethod
    def _derive_fallback_policy(*, plan_mode: str, overload_signal: bool, grounding_mode: str) -> str:
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "ask_more"
        if plan_mode == PLAN_MODE_PROVISIONAL:
            return "downgrade_to_provisional"
        if overload_signal:
            return "shrink_scope_then_retry"
        if grounding_mode == "mandatory":
            return "use_materials_or_downgrade"
        return "revise"

    @staticmethod
    def _build_first_step_hint(*, plan_mode: str, overload_signal: bool, plan_type: str) -> str:
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "ask_one_high_value_question_or_give_one_micro-step"
        if overload_signal:
            return "start_with_one_low-friction_task_within_20_minutes"
        if plan_type == "exam_sprint":
            return "anchor_the_plan_on_the_next_high-risk_exam_topic"
        return "start_with_the_first_concrete_phase_and_one_action"

    @staticmethod
    def _build_adaptation_trigger(*, overload_signal: bool, deadline_days: int | None, plan_mode: str) -> str:
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "if_the_missing_fact_is_provided_or_the_blocker_changes"
        if overload_signal:
            return "if_two_consecutive_tasks_are_skipped_or_feedback_says_too_hard"
        if deadline_days is not None and deadline_days <= 14:
            return "if_daily_checkpoint_slips_or_material_gap_persists"
        return "if_checkpoint_is_missed_or_constraints_change"
