from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from app.core.time_utils import DEFAULT_USER_TIMEZONE, local_date
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
    workload_fit: str = "unknown"
    feasibility_flags: tuple[str, ...] = ()
    first_review_after_days: int | None = None
    overload_signal: bool = False
    adaptation_trigger: str = ""
    first_step_hint: str = ""
    assumption_basis: tuple[str, ...] = ()
    outcome_learning_hints: tuple[str, ...] = ()
    known_failure_avoidance_rules: tuple[str, ...] = ()
    known_success_patterns: tuple[str, ...] = ()
    planning_bias_constraints: dict[str, Any] = field(default_factory=dict)
    dual_core_mode: str = "balanced"
    mi_tension_level: str = "none"
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
            "workload_fit": self.workload_fit,
            "feasibility_flags": list(self.feasibility_flags),
            "first_review_after_days": self.first_review_after_days,
            "overload_signal": self.overload_signal,
            "adaptation_trigger": self.adaptation_trigger,
            "first_step_hint": self.first_step_hint,
            "assumption_basis": list(self.assumption_basis),
            "outcome_learning_hints": list(self.outcome_learning_hints),
            "known_failure_avoidance_rules": list(self.known_failure_avoidance_rules),
            "known_success_patterns": list(self.known_success_patterns),
            "planning_bias_constraints": dict(self.planning_bias_constraints),
            "dual_core_mode": self.dual_core_mode,
            "mi_tension_level": self.mi_tension_level,
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
        today: date | None = None,
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
        dual_core_mode = self._normalize_dual_core_mode(
            planning_constraints.get("dual_core_mode")
            or decision_context.get("dual_core_mode")
            or _as_dict(plan_context.get("metadata")).get("dual_core_mode")
        )
        dual_core_signal_scores = _as_dict(planning_constraints.get("dual_core_signal_scores"))
        cognitive_load_type = _strip(
            planning_constraints.get("dominant_cognitive_load_type")
            or dual_core_signal_scores.get("dominant_cognitive_load_type")
        )
        stage_of_change = _strip(
            planning_constraints.get("stage_of_change")
            or dual_core_signal_scores.get("stage_of_change")
            or planning_constraints.get("dominant_stage_of_change")
        )
        active_probe_target = _strip(
            planning_constraints.get("active_probe_target")
            or dual_core_signal_scores.get("active_probe_target")
        )
        outcome_learning_hints = tuple(
            _strip(item)
            for item in _as_list(outcome_learning.get("plan_generation_hints_from_outcomes"))
            if _strip(item)
        )
        known_failure_avoidance_rules = tuple(
            _strip(item) for item in _as_list(outcome_learning.get("known_failure_avoidance_rules")) if _strip(item)
        )
        known_success_patterns = tuple(
            _strip(item) for item in _as_list(outcome_learning.get("known_success_patterns")) if _strip(item)
        )

        readiness_action = _strip(
            decision_context.get("planning_readiness_action") or insight_state.get("recommended_action")
        )
        readiness_level = _strip(decision_context.get("planning_readiness") or insight_state.get("readiness_level"))
        plan_mode = self.contract.classify_mode(readiness_action=readiness_action)

        deadline_days = self._derive_deadline_days(vision=vision, plan_context=plan_context, today=today)
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
        pacing_profile = (
            "light" if overload_signal else ("push" if deadline_days is not None and deadline_days <= 7 else "steady")
        )
        checkpoint_cadence = (
            "daily"
            if deadline_days is not None and deadline_days <= 14
            else ("every_2_days" if overload_signal else "twice_weekly")
        )
        grounding_mode = self._derive_grounding_mode(
            plan_mode=plan_mode,
            material_available=material_available,
            weak_knowledge_nodes=weak_knowledge_nodes,
            decision_context=decision_context,
        )
        assumption_policy = (
            "explicit_all"
            if plan_mode != PLAN_MODE_FULL
            else ("explicit_key" if readiness_level == "high" else "explicit_all")
        )
        fallback_policy = self._derive_fallback_policy(
            plan_mode=plan_mode, overload_signal=overload_signal, grounding_mode=grounding_mode
        )
        required_sections = self.contract.get_required_sections(plan_mode)
        max_session_minutes = self._safe_int(planning_constraints.get("max_session_minutes")) or self._safe_int(
            _as_dict(planning_constraints.get("persona_constraints")).get("max_session_minutes")
        )
        daily_capacity_minutes = self._derive_daily_capacity_minutes(
            plan_context=plan_context,
            planning_constraints=planning_constraints,
        )
        workload_fit, feasibility_flags = self._derive_workload_fit(
            deadline_days=deadline_days,
            daily_capacity_minutes=daily_capacity_minutes,
            overload_signal=overload_signal,
            plan_mode=plan_mode,
            plan_type=plan_type,
        )
        if workload_fit == "impossible":
            fallback_policy = "shrink_scope_then_retry"
            pacing_profile = "light"
            checkpoint_cadence = "daily"
        first_review_after_days = self._derive_first_review_after_days(
            deadline_days=deadline_days,
            overload_signal=overload_signal,
            plan_mode=plan_mode,
        )

        assumption_basis: list[str] = []
        for item in _as_list(
            decision_context.get("planning_blocking_unknowns") or insight_state.get("missing_information")
        )[:3]:
            text = _strip(item)
            if text:
                assumption_basis.append(text)
        if material_available and grounding_mode == "mandatory":
            assumption_basis.append("use_attached_materials")
        if overload_signal:
            assumption_basis.append("respect_current_capacity")
        for flag in feasibility_flags[:3]:
            assumption_basis.append(flag)

        first_step_hint = self._build_first_step_hint(
            plan_mode=plan_mode, overload_signal=overload_signal, plan_type=plan_type
        )
        adaptation_trigger = self._build_adaptation_trigger(
            overload_signal=overload_signal, deadline_days=deadline_days, plan_mode=plan_mode
        )
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

        (
            plan_depth,
            scaffold_level,
            pacing_profile,
            checkpoint_cadence,
            first_step_hint,
            planning_bias_constraints,
            assumption_basis,
            mi_tension_level,
        ) = self._apply_dual_core_mode(
            dual_core_mode=dual_core_mode,
            plan_depth=plan_depth,
            scaffold_level=scaffold_level,
            pacing_profile=pacing_profile,
            checkpoint_cadence=checkpoint_cadence,
            first_step_hint=first_step_hint,
            planning_bias_constraints=planning_bias_constraints,
            assumption_basis=assumption_basis,
            cognitive_load_type=cognitive_load_type,
            stage_of_change=stage_of_change,
            active_probe_target=active_probe_target,
        )

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
            workload_fit=workload_fit,
            feasibility_flags=tuple(feasibility_flags),
            first_review_after_days=first_review_after_days,
            overload_signal=overload_signal,
            adaptation_trigger=adaptation_trigger,
            first_step_hint=first_step_hint,
            assumption_basis=tuple(assumption_basis),
            outcome_learning_hints=outcome_learning_hints,
            known_failure_avoidance_rules=known_failure_avoidance_rules,
            known_success_patterns=known_success_patterns,
            planning_bias_constraints=planning_bias_constraints,
            dual_core_mode=dual_core_mode,
            mi_tension_level=mi_tension_level,
        )

    @staticmethod
    def _normalize_dual_core_mode(value: Any) -> str:
        raw = _strip(value)
        if raw in {"execution_first", "execution"}:
            return "execution_first"
        if raw in {"cognitive_first", "cognitive"}:
            return "cognitive_first"
        return "balanced"

    @staticmethod
    def _apply_dual_core_mode(
        *,
        dual_core_mode: str,
        plan_depth: str,
        scaffold_level: str,
        pacing_profile: str,
        checkpoint_cadence: str,
        first_step_hint: str,
        planning_bias_constraints: dict[str, Any],
        assumption_basis: list[str],
        cognitive_load_type: str,
        stage_of_change: str,
        active_probe_target: str,
    ) -> tuple[str, str, str, str, str, dict[str, Any], list[str], str]:
        constraints = dict(planning_bias_constraints)
        constraints["dual_core_mode"] = dual_core_mode
        mi_tension_level = "none"
        if dual_core_mode == "cognitive_first":
            plan_depth = "light"
            scaffold_level = "high"
            pacing_profile = "light"
            checkpoint_cadence = "daily"
            first_step_hint = "start_with_one_micro-step_within_5_minutes"
            constraints.update(
                {
                    "max_first_step_minutes": 5,
                    "avoid_dense_task_list": True,
                    "micro_first_step": True,
                    "explanation_depth": "brief_supportive",
                }
            )
            assumption_basis.append("dual_core_cognitive_first_micro_step")
        elif dual_core_mode == "execution_first":
            plan_depth = "standard" if plan_depth == "light" else plan_depth
            scaffold_level = "low" if scaffold_level == "medium" else scaffold_level
            pacing_profile = "push"
            constraints.update(
                {
                    "direct_execution": True,
                    "explanation_depth": "minimal",
                    "avoid_over_explaining": True,
                }
            )
            assumption_basis.append("dual_core_execution_first_direct")
        else:
            constraints.update({"micro_first_step": True, "first_screen_progressive_disclosure": True})
            assumption_basis.append("dual_core_balanced_progressive_disclosure")

        if cognitive_load_type == "intrinsic":
            constraints.update({"lower_difficulty": True, "include_prerequisite_review": True})
            assumption_basis.append("cognitive_load_intrinsic_reduce_difficulty")
        elif cognitive_load_type == "extraneous":
            constraints.update({"simplify_explanation": True, "reduce_card_count": True, "compress_context": True})
            plan_depth = "light" if dual_core_mode != "execution_first" else plan_depth
            assumption_basis.append("cognitive_load_extraneous_simplify_system_output")
        elif cognitive_load_type == "germane":
            constraints.update({"preserve_challenge": True, "add_reflection_checkpoint": True})
            assumption_basis.append("cognitive_load_germane_preserve_challenge")

        if stage_of_change in {"precontemplation", "contemplation"} and dual_core_mode in {
            "cognitive_first",
            "balanced",
        }:
            mi_tension_level = "develop_discrepancy"
            constraints.update(
                {
                    "mi_tension_level": mi_tension_level,
                    "avoid_validating_avoidance": True,
                    "connect_to_galaxy_goal": True,
                    "ask_discrepancy_question": True,
                    "stage_of_change": stage_of_change,
                    "disallow_escape_confirmation": True,
                }
            )
            assumption_basis.append(f"stage_of_change_{stage_of_change}_develop_discrepancy")

        if active_probe_target:
            constraints.update(
                {
                    "active_probe_target": active_probe_target,
                    "ask_state_clarification": True,
                }
            )
            assumption_basis.append(f"active_probe_{active_probe_target}")

        return (
            plan_depth,
            scaffold_level,
            pacing_profile,
            checkpoint_cadence,
            first_step_hint,
            constraints,
            assumption_basis,
            mi_tension_level,
        )

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

    def _derive_daily_capacity_minutes(
        self,
        *,
        plan_context: dict[str, Any],
        planning_constraints: dict[str, Any],
    ) -> int | None:
        for source in (plan_context, planning_constraints):
            minutes = self._safe_int(source.get("daily_available_minutes") or source.get("available_minutes_per_day"))
            if minutes is not None:
                return minutes
            hours = self._safe_float(source.get("daily_available_hours") or source.get("available_hours_per_day"))
            if hours is not None and hours > 0:
                return max(1, int(round(hours * 60)))
        return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

    @staticmethod
    def _derive_workload_fit(
        *,
        deadline_days: int | None,
        daily_capacity_minutes: int | None,
        overload_signal: bool,
        plan_mode: str,
        plan_type: str,
    ) -> tuple[str, list[str]]:
        flags: list[str] = []
        if deadline_days is None:
            flags.append("deadline_missing")
        if daily_capacity_minutes is None:
            flags.append("daily_capacity_missing")
        if deadline_days is None or daily_capacity_minutes is None:
            return "unknown", flags

        days = max(deadline_days, 1)
        total_capacity = days * daily_capacity_minutes
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "next_step_only", flags
        if deadline_days <= 3 and daily_capacity_minutes < 90:
            flags.append("impossible_schedule_risk")
            return "impossible", flags
        if plan_type == "exam_sprint" and deadline_days <= 7 and total_capacity < 420:
            flags.append("impossible_schedule_risk")
            return "impossible", flags
        if deadline_days <= 7 or overload_signal or daily_capacity_minutes < 60:
            flags.append("deadline_with_low_capacity")
            return "tight", flags
        return "realistic", flags

    @staticmethod
    def _derive_first_review_after_days(
        *,
        deadline_days: int | None,
        overload_signal: bool,
        plan_mode: str,
    ) -> int | None:
        if plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return None
        if overload_signal:
            return 1
        if deadline_days is None:
            return 3
        if deadline_days <= 14:
            return 1
        return 3

    def _derive_deadline_days(
        self, *, vision: dict[str, Any], plan_context: dict[str, Any], today: date | None = None
    ) -> int | None:
        target = _parse_date(vision.get("target_date") or plan_context.get("target_date"))
        if target is None:
            return None
        # V3-FIX-221（209 同族 days_left）：target 是日界语义，右值须用「今
        # 天」的同一网格——修前 ``_utcnow().date()`` 是 UTC date，上海晨间
        # （UTC 尚在前日）deadline_days 偏一日。编译器无 db 通道：today 形
        # 参供有 tz 通路的调用方显式传入，缺省回落主市场 Asia/Shanghai 本地
        # 日（与族先例缺省一致，去 UTC/宿主机钟依赖）。
        today = today if today is not None else local_date(_utcnow(), DEFAULT_USER_TIMEZONE)
        delta = (target - today).days
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
