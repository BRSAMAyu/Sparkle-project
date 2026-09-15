from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLAN_QUALITY_CONTRACT_VERSION = "2026-04-05.v1"

PLAN_MODE_FULL = "full"
PLAN_MODE_PROVISIONAL = "provisional"
PLAN_MODE_NEXT_STEP_ONLY = "next_step_only"

SECTION_GOAL_FRAME = "goal_frame"
SECTION_ASSUMPTIONS = "assumptions"
SECTION_READINESS_FIT = "readiness_fit"
SECTION_WORKLOAD_MODEL = "workload_model"
SECTION_SEQUENCE = "sequence"
SECTION_GROUNDING_BASIS = "grounding_basis"
SECTION_NEXT_ACTION = "next_action"
SECTION_ADAPTATION_TRIGGER = "adaptation_trigger"
SECTION_FAILURE_GUARD = "failure_guard"
SECTION_SCOPE_AND_HORIZON = "scope_and_horizon"
SECTION_FALLBACK_UNCERTAINTY = "fallback_uncertainty"
SECTION_WITHHOLD_REASON = "withhold_reason"
SECTION_UNLOCK_QUESTION = "unlock_question"


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


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_value(item) for item in value)
    return True


@dataclass(frozen=True)
class PlanSectionCoverage:
    mode: str
    required_sections: tuple[str, ...]
    present_sections: tuple[str, ...]
    missing_sections: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "required_sections": list(self.required_sections),
            "present_sections": list(self.present_sections),
            "missing_sections": list(self.missing_sections),
        }


@dataclass(frozen=True)
class PlanQualityContract:
    version: str = PLAN_QUALITY_CONTRACT_VERSION
    required_sections_by_mode: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            PLAN_MODE_FULL: (
                SECTION_GOAL_FRAME,
                SECTION_ASSUMPTIONS,
                SECTION_READINESS_FIT,
                SECTION_WORKLOAD_MODEL,
                SECTION_SEQUENCE,
                SECTION_GROUNDING_BASIS,
                SECTION_NEXT_ACTION,
                SECTION_ADAPTATION_TRIGGER,
                SECTION_FAILURE_GUARD,
            ),
            PLAN_MODE_PROVISIONAL: (
                SECTION_GOAL_FRAME,
                SECTION_ASSUMPTIONS,
                SECTION_READINESS_FIT,
                SECTION_SCOPE_AND_HORIZON,
                SECTION_NEXT_ACTION,
                SECTION_FALLBACK_UNCERTAINTY,
            ),
            PLAN_MODE_NEXT_STEP_ONLY: (
                SECTION_GOAL_FRAME,
                SECTION_WITHHOLD_REASON,
                SECTION_NEXT_ACTION,
                SECTION_UNLOCK_QUESTION,
            ),
        }
    )

    def get_required_sections(self, mode: str) -> tuple[str, ...]:
        normalized = _strip(mode) or PLAN_MODE_FULL
        return self.required_sections_by_mode.get(normalized, self.required_sections_by_mode[PLAN_MODE_FULL])

    def classify_mode(
        self,
        *,
        readiness_action: str | None = None,
        explicit_mode: str | None = None,
    ) -> str:
        normalized_mode = _strip(explicit_mode)
        if normalized_mode in self.required_sections_by_mode:
            return normalized_mode

        action = _strip(readiness_action).lower()
        if action == "ask":
            return PLAN_MODE_NEXT_STEP_ONLY
        if action == "provisional":
            return PLAN_MODE_PROVISIONAL
        return PLAN_MODE_FULL

    def evaluate_coverage(
        self,
        *,
        mode: str,
        payload: dict[str, Any] | None,
    ) -> PlanSectionCoverage:
        normalized_payload = _as_dict(payload)
        required = self.get_required_sections(mode)
        present = tuple(
            section
            for section in required
            if _has_value(normalized_payload.get(section))
        )
        missing = tuple(section for section in required if section not in present)
        return PlanSectionCoverage(
            mode=mode,
            required_sections=required,
            present_sections=present,
            missing_sections=missing,
        )

    def build_prompt_requirements(self, *, mode: str) -> list[str]:
        labels = {
            SECTION_GOAL_FRAME: "明确目标、期限与为什么是现在",
            SECTION_ASSUMPTIONS: "显式写出关键假设",
            SECTION_READINESS_FIT: "说明这是完整计划、暂定计划还是仅下一步",
            SECTION_WORKLOAD_MODEL: "说明时间/精力/难度假设",
            SECTION_SEQUENCE: "说明先后顺序与理由",
            SECTION_GROUNDING_BASIS: "说明用了哪些用户材料、约束或薄弱点",
            SECTION_NEXT_ACTION: "给出未来 24 小时内可执行的下一步",
            SECTION_ADAPTATION_TRIGGER: "说明什么信号会触发调整",
            SECTION_FAILURE_GUARD: "说明太难、太空或过度乐观时怎么办",
            SECTION_SCOPE_AND_HORIZON: "明确这是缩窄后的范围与时间窗",
            SECTION_FALLBACK_UNCERTAINTY: "说明暂定路径和待确认点",
            SECTION_WITHHOLD_REASON: "说明为什么现在不该给完整计划",
            SECTION_UNLOCK_QUESTION: "提出一个最高价值的解锁问题或阻塞点",
        }
        return [labels.get(section, section) for section in self.get_required_sections(mode)]


def build_plan_quality_contract() -> PlanQualityContract:
    return PlanQualityContract()


def build_contract_payload(
    *,
    mode: str,
    situation_brief: dict[str, Any] | None,
    planning_strategy: dict[str, Any] | None,
    user_material_grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    brief = _as_dict(situation_brief)
    strategy = _as_dict(planning_strategy)
    decision_context = _as_dict(brief.get("decision_context"))
    vision = _as_dict(brief.get("vision"))
    current_state = _as_dict(brief.get("current_state"))
    evidence = _as_dict(brief.get("evidence"))
    insight_state = _as_dict(brief.get("insight_state"))
    grounding = _as_dict(user_material_grounding or {})

    blocking_unknowns = [
        _strip(item)
        for item in _as_list(
            decision_context.get("planning_blocking_unknowns")
            or insight_state.get("blocking_unknowns")
            or insight_state.get("missing_information")
        )
        if _strip(item)
    ]
    clarifications = [
        _strip(item)
        for item in _as_list(decision_context.get("strategic_clarification_questions") or insight_state.get("recommended_clarification"))
        if _strip(item)
    ]

    payload = {
        SECTION_GOAL_FRAME: {
            "goal": _strip(vision.get("primary_goal") or vision.get("active_plan")),
            "why_now": _strip(vision.get("why_now") or current_state.get("time_pressure")),
        },
        SECTION_ASSUMPTIONS: list(_as_list(strategy.get("assumption_basis"))),
        SECTION_READINESS_FIT: {
            "mode": mode,
            "readiness": _strip(decision_context.get("planning_readiness") or insight_state.get("readiness_level")),
            "action": _strip(decision_context.get("planning_readiness_action") or insight_state.get("recommended_action")),
        },
        SECTION_WORKLOAD_MODEL: {
            "pacing_profile": _strip(strategy.get("pacing_profile")),
            "session_minutes": strategy.get("max_session_minutes"),
            "daily_capacity_minutes": strategy.get("daily_capacity_minutes"),
            "workload_fit": _strip(strategy.get("workload_fit")),
            "feasibility_flags": list(_as_list(strategy.get("feasibility_flags"))),
            "overload_signal": bool(strategy.get("overload_signal")),
        },
        SECTION_SEQUENCE: {
            "plan_type": _strip(strategy.get("plan_type")),
            "checkpoint_cadence": _strip(strategy.get("checkpoint_cadence")),
            "first_review_after_days": strategy.get("first_review_after_days"),
            "required_sections": list(_as_list(strategy.get("required_plan_sections"))),
        },
        SECTION_GROUNDING_BASIS: {
            "grounding_mode": _strip(strategy.get("grounding_mode")),
            "material_status": _strip(grounding.get("status")),
            "materials_used": [
                _strip(item.get("file_name") or item.get("section_title"))
                for item in _as_list(grounding.get("results"))
                if isinstance(item, dict) and _strip(item.get("file_name") or item.get("section_title"))
            ],
            "evidence_summary": _strip(evidence.get("summary")),
        },
        SECTION_NEXT_ACTION: {
            "fallback_policy": _strip(strategy.get("fallback_policy")),
            "suggested_first_move": _strip(strategy.get("first_step_hint")),
        },
        SECTION_ADAPTATION_TRIGGER: {
            "trigger": _strip(strategy.get("adaptation_trigger")),
            "checkpoint_cadence": _strip(strategy.get("checkpoint_cadence")),
        },
        SECTION_FAILURE_GUARD: {
            "fallback_policy": _strip(strategy.get("fallback_policy")),
            "blocking_unknowns": blocking_unknowns,
        },
        SECTION_SCOPE_AND_HORIZON: {
            "plan_horizon": _strip(strategy.get("plan_horizon")),
            "plan_depth": _strip(strategy.get("plan_depth")),
        },
        SECTION_FALLBACK_UNCERTAINTY: {
            "blocking_unknowns": blocking_unknowns,
            "clarifications": clarifications,
        },
        SECTION_WITHHOLD_REASON: {
            "phase_a_guardrail": _strip(decision_context.get("phase_a_guardrail")),
            "blocking_unknowns": blocking_unknowns,
        },
        SECTION_UNLOCK_QUESTION: clarifications[:1] or blocking_unknowns[:1],
    }
    if mode == PLAN_MODE_FULL and not payload[SECTION_ASSUMPTIONS]:
        payload[SECTION_ASSUMPTIONS] = list(blocking_unknowns[:2])
    if mode == PLAN_MODE_PROVISIONAL and not payload[SECTION_ASSUMPTIONS]:
        payload[SECTION_ASSUMPTIONS] = list(blocking_unknowns[:3])
    return payload
