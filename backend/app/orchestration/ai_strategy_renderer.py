from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.orchestration.ai_strategy_ontology import get_term_definition, get_value_doctrine
from app.orchestration.plan_quality_contract import build_plan_quality_contract


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
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


def _bool(value: Any) -> bool:
    return bool(value)


def _derived_support_posture(user_strategy_state: dict[str, Any]) -> str:
    push_vs_support = user_strategy_state.get("push_vs_support")
    if not isinstance(push_vs_support, (int, float)):
        return ""
    if float(push_vs_support) >= 0.65:
        return "directive"
    if float(push_vs_support) <= 0.35:
        return "support_first"
    return "balanced"


def _safe_text_items(value: Any) -> list[str]:
    lines: list[str] = []
    for item in _as_list(value):
        if isinstance(item, str):
            text = _strip(item)
            if text:
                lines.append(text)
    return lines


@dataclass(frozen=True)
class RenderedSemanticDoctrine:
    selected_terms: list[dict[str, Any]]
    rendered_doctrine_summary: dict[str, Any]
    response_contract: dict[str, Any]
    compliance_expectations: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_terms": list(self.selected_terms),
            "rendered_doctrine_summary": dict(self.rendered_doctrine_summary),
            "response_contract": dict(self.response_contract),
            "compliance_expectations": dict(self.compliance_expectations),
        }


@dataclass(frozen=True)
class SemanticControlComplianceReport:
    passed: bool
    checks: dict[str, bool]
    violations: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": dict(self.checks),
            "violations": list(self.violations),
        }


def _localize_summary(term: str, value: str, *, language: str) -> str:
    doctrine = get_value_doctrine(term, value)
    if doctrine is None:
        return ""
    return doctrine.model_summary_zh if language == "zh" else doctrine.model_summary_en


def _add_selected_term(selected_terms: list[dict[str, Any]], *, term: str, value: Any, language: str) -> None:
    normalized = _strip(value)
    if not normalized:
        return
    definition = get_term_definition(term)
    if definition is None:
        return
    doctrine = definition.get(normalized)
    if doctrine is None:
        return
    selected_terms.append(
        {
            "term": term,
            "family": definition.family,
            "value": normalized,
            "exposure_class": definition.exposure_class,
            "summary": doctrine.model_summary_zh if language == "zh" else doctrine.model_summary_en,
        }
    )


def _required_section_labels(*, language: str, mode: str) -> list[str]:
    contract = build_plan_quality_contract()
    if language == "zh":
        return contract.build_prompt_requirements(mode=mode)
    labels = {
        "goal_frame": "goal frame",
        "assumptions": "key assumptions",
        "readiness_fit": "readiness fit",
        "workload_model": "workload model",
        "sequence": "sequence and rationale",
        "grounding_basis": "grounding basis",
        "next_action": "next action within 24 hours",
        "adaptation_trigger": "adaptation trigger",
        "failure_guard": "failure guard",
        "scope_and_horizon": "narrowed scope and horizon",
        "fallback_uncertainty": "fallback path and uncertainty",
        "withhold_reason": "why a full plan is withheld",
        "unlock_question": "one unlock question or blocker",
    }
    return [labels.get(section, section) for section in contract.get_required_sections(mode)]


def build_semantic_control(
    *,
    decision_context: dict[str, Any] | None,
    planning_strategy: dict[str, Any] | None,
    body_awareness_guidance: dict[str, Any] | None = None,
    user_strategy_state: dict[str, Any] | None = None,
    outcome_learning: dict[str, Any] | None = None,
    language: str = "zh",
) -> RenderedSemanticDoctrine:
    decision_context = _as_dict(decision_context)
    planning_strategy = _as_dict(planning_strategy)
    body_awareness_guidance = _as_dict(body_awareness_guidance or decision_context.get("body_awareness_guidance"))
    user_strategy_state = _as_dict(user_strategy_state)
    outcome_learning = _as_dict(outcome_learning)

    selected_terms: list[dict[str, Any]] = []
    for term in (
        "primary_residual",
        "loop_type",
        "confidence_label",
        "planning_readiness",
        "planning_readiness_action",
        "experience_mode",
        "intervention_family",
        "reversibility_level",
        "plan_mode",
        "plan_depth",
        "pacing_profile",
        "grounding_mode",
        "fallback_policy",
        "session_mode",
        "explanation_style",
        "retrieval_emphasis",
        "intervention_intensity",
        "support_posture",
    ):
        source = decision_context if term in decision_context else planning_strategy
        if term in {
            "session_mode",
            "explanation_style",
            "retrieval_emphasis",
            "intervention_intensity",
        }:
            source = user_strategy_state
        if term == "support_posture":
            source = {"support_posture": _derived_support_posture(user_strategy_state)}
        _add_selected_term(selected_terms, term=term, value=source.get(term), language=language)

    mode = _strip(planning_strategy.get("plan_mode"))
    primary_subsystem = _as_dict(body_awareness_guidance.get("primary_subsystem"))
    subsystem_label = _strip(primary_subsystem.get("label") or primary_subsystem.get("id"))
    subsystem_why = _strip(primary_subsystem.get("why"))
    learning_hints = _safe_text_items(outcome_learning.get("plan_generation_hints_from_outcomes"))

    decision_lines: list[str] = []
    planning_lines: list[str] = []
    strategy_lines: list[str] = []
    body_lines: list[str] = []
    learning_lines: list[str] = []

    for term in (
        "planning_readiness_action",
        "experience_mode",
        "intervention_family",
        "reversibility_level",
    ):
        summary = _localize_summary(term, decision_context.get(term), language=language)
        if summary:
            decision_lines.append(summary)

    for term in (
        "plan_mode",
        "plan_depth",
        "pacing_profile",
        "grounding_mode",
        "fallback_policy",
    ):
        summary = _localize_summary(term, planning_strategy.get(term), language=language)
        if summary:
            planning_lines.append(summary)

    for term, value in (
        ("session_mode", user_strategy_state.get("session_mode")),
        ("explanation_style", user_strategy_state.get("explanation_style")),
        ("retrieval_emphasis", user_strategy_state.get("retrieval_emphasis")),
        ("intervention_intensity", user_strategy_state.get("intervention_intensity")),
        ("support_posture", _derived_support_posture(user_strategy_state)),
    ):
        summary = _localize_summary(term, value, language=language)
        if summary:
            strategy_lines.append(summary)

    if mode:
        section_labels = _required_section_labels(language=language, mode=mode)
        if section_labels:
            if language == "zh":
                planning_lines.append(f"如果这轮在做计划，最终回答必须显式覆盖：{'，'.join(section_labels)}。")
            else:
                planning_lines.append(
                    "If this turn produces a plan, the final answer must explicitly cover: "
                    + ", ".join(section_labels)
                    + "."
                )

    if subsystem_label:
        if language == "zh":
            body_lines.append(
                f"这轮优先让「{subsystem_label}」型能力提供支持"
                + (f"，原因是：{subsystem_why}。" if subsystem_why else "。")
            )
        else:
            body_lines.append(
                f"Prefer support from the '{subsystem_label}' capability path"
                + (f" because {subsystem_why}." if subsystem_why else ".")
            )

    if learning_hints:
        if language == "zh":
            learning_lines.append(f"已验证的学习线索也要落地进本轮回答：{learning_hints[0]}")
        else:
            learning_lines.append(f"Carry this validated learning hint into the response: {learning_hints[0]}")

    response_contract = {
        "should_ask_high_value_question_first": _strip(decision_context.get("planning_readiness_action")) == "ask"
        or _strip(decision_context.get("experience_mode")) == "clarify",
        "max_clarification_questions": 1 if _strip(decision_context.get("experience_mode")) == "clarify" else None,
        "withhold_multi_step_plan": _strip(planning_strategy.get("plan_mode")) == "next_step_only",
        "must_name_assumptions": _strip(planning_strategy.get("plan_mode")) == "provisional"
        or _strip(planning_strategy.get("assumption_policy")) == "explicit_all",
        "must_narrow_scope": _strip(planning_strategy.get("plan_mode")) in {"provisional", "next_step_only"}
        or _strip(decision_context.get("experience_mode")) == "stabilize",
        "must_reduce_pressure": _strip(decision_context.get("experience_mode")) == "stabilize"
        or _strip(planning_strategy.get("pacing_profile")) == "light",
        "must_use_user_material_evidence": _strip(planning_strategy.get("grounding_mode")) == "mandatory",
        "must_surface_tradeoffs": _strip(decision_context.get("experience_mode")) == "decide",
        "must_preserve_identity_safety": _strip(decision_context.get("experience_mode")) == "reframe",
        "must_include_required_plan_sections": list(_as_list(planning_strategy.get("required_plan_sections"))),
    }
    compliance_expectations = {
        "expect_explicit_unlock_question": response_contract["withhold_multi_step_plan"],
        "expect_assumption_section": response_contract["must_name_assumptions"],
        "expect_grounding_basis": response_contract["must_use_user_material_evidence"],
        "expect_low_pressure_shape": response_contract["must_reduce_pressure"],
        "expect_tradeoff_language": response_contract["must_surface_tradeoffs"],
        "expect_identity_reframe": response_contract["must_preserve_identity_safety"],
    }

    summary_lines = [*decision_lines, *planning_lines, *strategy_lines, *body_lines, *learning_lines]
    if not summary_lines and language == "zh":
        summary_lines.append("当前没有额外的语义控制约束。")
    if not summary_lines and language != "zh":
        summary_lines.append("No additional semantic control guidance is active for this turn.")

    return RenderedSemanticDoctrine(
        selected_terms=selected_terms,
        rendered_doctrine_summary={
            "language": language,
            "decision_doctrine": decision_lines,
            "planning_doctrine": planning_lines,
            "strategy_doctrine": strategy_lines,
            "body_doctrine": body_lines,
            "learning_doctrine": learning_lines,
            "summary": " ".join(summary_lines),
        },
        response_contract=response_contract,
        compliance_expectations=compliance_expectations,
    )


def format_semantic_control_lines(
    semantic_control: dict[str, Any] | RenderedSemanticDoctrine | None,
    *,
    language: str,
    section: str,
) -> list[str]:
    payload = semantic_control.to_dict() if isinstance(semantic_control, RenderedSemanticDoctrine) else _as_dict(semantic_control)
    summary = _as_dict(payload.get("rendered_doctrine_summary"))
    key = {
        "decision": "decision_doctrine",
        "planning": "planning_doctrine",
        "strategy": "strategy_doctrine",
        "body": "body_doctrine",
        "learning": "learning_doctrine",
        "all": "summary",
    }.get(section, "summary")
    if key == "summary":
        text = _strip(summary.get("summary"))
        return [text] if text else []
    return [_strip(item) for item in _as_list(summary.get(key)) if _strip(item)]


def evaluate_semantic_control_compliance(
    *,
    text: str,
    semantic_control: dict[str, Any] | RenderedSemanticDoctrine | None,
    tool_call_count: int = 0,
    question_count: int = 0,
) -> SemanticControlComplianceReport:
    payload = semantic_control.to_dict() if isinstance(semantic_control, RenderedSemanticDoctrine) else _as_dict(semantic_control)
    contract = _as_dict(payload.get("response_contract"))
    lowered = _strip(text).lower()

    checks = {
        "clarify_question_first": True,
        "provisional_assumptions": True,
        "mandatory_grounding": True,
        "stabilize_low_pressure": True,
    }
    violations: list[dict[str, str]] = []

    if _bool(contract.get("should_ask_high_value_question_first")):
        checks["clarify_question_first"] = question_count == 1 and tool_call_count <= 1
        if not checks["clarify_question_first"]:
            violations.append(
                {
                    "code": "clarify_over_scoped",
                    "message": "Clarify-mode output did not stay constrained to one high-value question or micro-step.",
                }
            )

    if _bool(contract.get("must_name_assumptions")):
        checks["provisional_assumptions"] = "assumption" in lowered or "假设" in text
        if not checks["provisional_assumptions"]:
            violations.append(
                {
                    "code": "missing_explicit_assumptions",
                    "message": "Provisional planning requires explicit assumptions, but none were visible.",
                }
            )

    if _bool(contract.get("must_use_user_material_evidence")):
        grounding_markers = ("grounding basis", "uploaded", ".pdf", ".csv", "材料", "笔记", "错题", "grounded")
        checks["mandatory_grounding"] = any(marker in lowered or marker in text for marker in grounding_markers)
        if not checks["mandatory_grounding"]:
            violations.append(
                {
                    "code": "missing_user_material_grounding",
                    "message": "Mandatory grounding requires explicit user-material evidence, but it was not visible.",
                }
            )

    if _bool(contract.get("must_reduce_pressure")):
        pressure_markers = ("push harder", "harder", "intensive", "strict", "更狠", "高强度", "push")
        checks["stabilize_low_pressure"] = not any(marker in lowered or marker in text for marker in pressure_markers) and tool_call_count <= 3
        if not checks["stabilize_low_pressure"]:
            violations.append(
                {
                    "code": "stabilize_pressure_too_high",
                    "message": "Stabilize-mode output still sounded too high-pressure or too broad.",
                }
            )

    passed = all(checks.values())
    return SemanticControlComplianceReport(passed=passed, checks=checks, violations=violations)
