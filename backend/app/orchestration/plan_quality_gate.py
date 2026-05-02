from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.orchestration.ai_strategy_renderer import build_semantic_control, evaluate_semantic_control_compliance
from app.orchestration.plan_quality_contract import (
    PLAN_MODE_FULL,
    PLAN_MODE_NEXT_STEP_ONLY,
    PLAN_MODE_PROVISIONAL,
    PlanQualityContract,
    build_contract_payload,
    build_plan_quality_contract,
)
from app.orchestration.rendered_plan_artifact import parse_rendered_plan_artifact


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


@dataclass(frozen=True)
class PlanQualityIssue:
    code: str
    message: str
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class PlanQualityReport:
    overall_score: float
    fit_score: float
    feasibility_score: float
    grounding_score: float
    next_action_score: float
    adaptation_score: float
    outcome_learning_score: float
    issues: tuple[PlanQualityIssue, ...] = field(default_factory=tuple)
    decision: str = "approve"
    contract_mode: str = PLAN_MODE_FULL
    section_coverage: dict[str, Any] = field(default_factory=dict)
    artifact_coverage: dict[str, Any] = field(default_factory=dict)
    metadata_expectations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(float(self.overall_score), 4),
            "fit_score": round(float(self.fit_score), 4),
            "feasibility_score": round(float(self.feasibility_score), 4),
            "grounding_score": round(float(self.grounding_score), 4),
            "next_action_score": round(float(self.next_action_score), 4),
            "adaptation_score": round(float(self.adaptation_score), 4),
            "outcome_learning_score": round(float(self.outcome_learning_score), 4),
            "issues": [item.to_dict() for item in self.issues],
            "decision": self.decision,
            "contract_mode": self.contract_mode,
            "section_coverage": dict(self.section_coverage),
            "artifact_coverage": dict(self.artifact_coverage),
            "metadata_expectations": dict(self.metadata_expectations),
        }


class PlanQualityGate:
    """Evaluate plan quality before the executable review result is finalized."""

    def __init__(self, contract: PlanQualityContract | None = None) -> None:
        self.contract = contract or build_plan_quality_contract()

    def evaluate(
        self,
        *,
        plan: Any,
        user_message: str,
        user_context: dict[str, Any] | None,
    ) -> PlanQualityReport:
        normalized_context = _as_dict(user_context)
        situation_brief = _as_dict(normalized_context.get("situation_brief"))
        decision_context = _as_dict(situation_brief.get("decision_context"))
        planning_strategy = _as_dict(
            situation_brief.get("planning_strategy")
            or normalized_context.get("planning_strategy")
        )
        semantic_control = _as_dict(
            situation_brief.get("semantic_control")
            or normalized_context.get("semantic_control")
            or build_semantic_control(
                decision_context=decision_context,
                planning_strategy=planning_strategy,
                body_awareness_guidance=_as_dict(decision_context.get("body_awareness_guidance")),
                user_strategy_state=_as_dict(normalized_context.get("user_strategy_state")),
                outcome_learning=_as_dict(situation_brief.get("outcome_learning") or normalized_context.get("outcome_learning")),
                language="zh",
            ).to_dict()
        )
        material_grounding = _as_dict(normalized_context.get("user_material_grounding"))
        rendered_plan_artifact = parse_rendered_plan_artifact(normalized_context.get("rendered_plan_artifact"))
        outcome_learning = _as_dict(
            situation_brief.get("outcome_learning")
            or normalized_context.get("outcome_learning")
            or normalized_context.get("validated_outcome_learning")
        )
        readiness_action = _strip(decision_context.get("planning_readiness_action"))
        contract_mode = self.contract.classify_mode(
            readiness_action=readiness_action,
            explicit_mode=_strip(planning_strategy.get("plan_mode")),
        )

        payload = build_contract_payload(
            mode=contract_mode,
            situation_brief=situation_brief,
            planning_strategy=planning_strategy,
            user_material_grounding=material_grounding,
        )
        metadata_expectations = self.contract.evaluate_coverage(mode=contract_mode, payload=payload)
        artifact_payload = (
            dict(getattr(rendered_plan_artifact, "sections", {}) or {})
            if rendered_plan_artifact is not None
            else {}
        )
        coverage = self.contract.evaluate_coverage(mode=contract_mode, payload=artifact_payload)
        issues: list[PlanQualityIssue] = []
        if contract_mode in {PLAN_MODE_FULL, PLAN_MODE_PROVISIONAL} and rendered_plan_artifact is None:
            issues.append(
                PlanQualityIssue(
                    code="missing_plan_artifact",
                    message="Missing rendered plan artifact for artifact-level validation.",
                    severity="critical",
                )
            )

        fit_score = self._score_fit(
            contract_mode=contract_mode,
            readiness_action=readiness_action,
            planning_strategy=planning_strategy,
            issues=issues,
        )
        feasibility_score = self._score_feasibility(
            plan=plan,
            planning_strategy=planning_strategy,
            issues=issues,
        )
        grounding_score = self._score_grounding(
            contract_mode=contract_mode,
            planning_strategy=planning_strategy,
            material_grounding=material_grounding,
            rendered_plan_artifact=rendered_plan_artifact,
            issues=issues,
        )
        next_action_score = self._score_next_action(
            plan=plan,
            user_message=user_message,
            rendered_plan_artifact=rendered_plan_artifact,
            issues=issues,
        )
        adaptation_score = self._score_adaptation(
            contract_mode=contract_mode,
            planning_strategy=planning_strategy,
            rendered_plan_artifact=rendered_plan_artifact,
            issues=issues,
        )
        outcome_learning_score = self._score_outcome_learning_alignment(
            planning_strategy=planning_strategy,
            outcome_learning=outcome_learning,
            rendered_plan_artifact=rendered_plan_artifact,
            issues=issues,
        )
        semantic_compliance = evaluate_semantic_control_compliance(
            text=getattr(rendered_plan_artifact, "text", "") if rendered_plan_artifact is not None else "",
            semantic_control=semantic_control,
            tool_call_count=len(self._tool_calls(plan)),
            question_count=(getattr(rendered_plan_artifact, "text", "").count("?") + getattr(rendered_plan_artifact, "text", "").count("？"))
            if rendered_plan_artifact is not None
            else 0,
        )
        for violation in semantic_compliance.violations:
            issues.append(
                PlanQualityIssue(
                    code=str(violation.get("code") or "semantic_control_violation"),
                    message=str(violation.get("message") or "Semantic control contract was violated."),
                    severity="critical" if str(violation.get("code") or "").startswith("missing_") else "warning",
                )
            )

        for missing in coverage.missing_sections:
            severity = "critical" if contract_mode == PLAN_MODE_FULL else "warning"
            issues.append(
                PlanQualityIssue(
                    code=f"missing_section:{missing}",
                    message=f"Missing required planning section: {missing}",
                    severity=severity,
                )
            )

        overall_score = (
            fit_score * 0.25
            + feasibility_score * 0.20
            + grounding_score * 0.20
            + next_action_score * 0.20
            + adaptation_score * 0.10
            + outcome_learning_score * 0.05
        )
        if coverage.missing_sections:
            overall_score = max(0.0, overall_score - min(len(coverage.missing_sections) * 0.06, 0.24))
        if not semantic_compliance.passed:
            overall_score = max(0.0, overall_score - min(len(semantic_compliance.violations) * 0.08, 0.24))

        decision = self._decide(
            contract_mode=contract_mode,
            readiness_action=readiness_action,
            overall_score=overall_score,
            fit_score=fit_score,
            feasibility_score=feasibility_score,
            grounding_score=grounding_score,
            next_action_score=next_action_score,
            issues=issues,
        )
        return PlanQualityReport(
            overall_score=overall_score,
            fit_score=fit_score,
            feasibility_score=feasibility_score,
            grounding_score=grounding_score,
            next_action_score=next_action_score,
            adaptation_score=adaptation_score,
            outcome_learning_score=outcome_learning_score,
            issues=tuple(issues),
            decision=decision,
            contract_mode=contract_mode,
            section_coverage=coverage.to_dict(),
            artifact_coverage=coverage.to_dict(),
            metadata_expectations={
                **metadata_expectations.to_dict(),
                "semantic_control": semantic_compliance.to_dict(),
            },
        )

    def _score_outcome_learning_alignment(
        self,
        *,
        planning_strategy: dict[str, Any],
        outcome_learning: dict[str, Any],
        rendered_plan_artifact: Any,
        issues: list[PlanQualityIssue],
    ) -> float:
        hints = [_strip(item) for item in _as_list(outcome_learning.get("plan_generation_hints_from_outcomes")) if _strip(item)]
        if not hints:
            return 0.75
        constraints = _as_dict(outcome_learning.get("planning_bias_constraints"))
        score = 0.9
        strategy_hint_text = " | ".join(
            part
            for part in (
                _strip(planning_strategy.get("first_step_hint")),
                " | ".join(_strip(item) for item in _as_list(planning_strategy.get("outcome_learning_hints")) if _strip(item)),
                _strip(planning_strategy.get("grounding_mode")),
                _strip(planning_strategy.get("scaffold_level")),
            )
            if part
        ).lower()
        if constraints.get("lighter_first_step") is True and "light" not in strategy_hint_text:
            score -= 0.25
            issues.append(
                PlanQualityIssue(
                    code="missed_validated_light_first_step",
                    message="Validated outcome learning says to start lighter, but the planning strategy did not reflect that.",
                    severity="warning",
                )
            )
        if constraints.get("grounding_mode") == "mandatory" and _strip(planning_strategy.get("grounding_mode")) != "mandatory":
            score -= 0.3
            issues.append(
                PlanQualityIssue(
                    code="missed_validated_grounding_requirement",
                    message="Validated outcome learning requires grounding, but the planning strategy did not enforce it.",
                    severity="critical",
                )
            )
        if constraints.get("scaffold_level") == "high" and _strip(planning_strategy.get("scaffold_level")) != "high":
            score -= 0.2
            issues.append(
                PlanQualityIssue(
                    code="missed_validated_scaffold_level",
                    message="Validated outcome learning requires higher scaffolding than the current strategy provides.",
                    severity="warning",
                )
            )
        return max(0.0, score)

    @staticmethod
    def _tool_calls(plan: Any) -> list[Any]:
        return list(getattr(plan, "tool_calls", []) or [])

    def _score_fit(
        self,
        *,
        contract_mode: str,
        readiness_action: str,
        planning_strategy: dict[str, Any],
        issues: list[PlanQualityIssue],
    ) -> float:
        strategy_mode = _strip(planning_strategy.get("plan_mode"))
        if strategy_mode and strategy_mode != contract_mode:
            issues.append(
                PlanQualityIssue(
                    code="strategy_mode_mismatch",
                    message=f"Planning strategy mode {strategy_mode} disagrees with contract mode {contract_mode}.",
                    severity="warning",
                )
            )
            return 0.55
        if readiness_action == "ask" and contract_mode != PLAN_MODE_NEXT_STEP_ONLY:
            issues.append(
                PlanQualityIssue(
                    code="phase_a_guardrail_breach",
                    message="Phase A says ask-first, but the plan is not constrained to next-step-only mode.",
                    severity="critical",
                )
            )
            return 0.25
        if readiness_action == "provisional" and contract_mode == PLAN_MODE_FULL:
            issues.append(
                PlanQualityIssue(
                    code="provisional_required",
                    message="Readiness requires a provisional plan, but the plan mode is full.",
                    severity="critical",
                )
            )
            return 0.4
        return 0.9 if contract_mode == PLAN_MODE_FULL else 0.82 if contract_mode == PLAN_MODE_PROVISIONAL else 0.78

    def _score_feasibility(
        self,
        *,
        plan: Any,
        planning_strategy: dict[str, Any],
        issues: list[PlanQualityIssue],
    ) -> float:
        tool_calls = self._tool_calls(plan)
        overload_signal = bool(planning_strategy.get("overload_signal"))
        max_session_minutes = planning_strategy.get("max_session_minutes")
        workload_fit = _strip(planning_strategy.get("workload_fit"))
        feasibility_flags = {_strip(item) for item in _as_list(planning_strategy.get("feasibility_flags")) if _strip(item)}
        estimated_minutes = 0
        for tool_call in tool_calls:
            params = _as_dict(getattr(tool_call, "params", None))
            try:
                estimated_minutes += int(params.get("estimated_minutes") or 0)
            except (TypeError, ValueError):
                continue

        score = 0.88
        if workload_fit == "impossible" or "impossible_schedule_risk" in feasibility_flags:
            score -= 0.42
            issues.append(
                PlanQualityIssue(
                    code="impossible_schedule_risk",
                    message=(
                        "Deadline and daily capacity do not support a credible full plan; shrink scope or ask "
                        "for a tradeoff before presenting it as feasible."
                    ),
                    severity="critical",
                )
            )
        elif workload_fit == "tight" or "deadline_with_low_capacity" in feasibility_flags:
            score -= 0.16
            issues.append(
                PlanQualityIssue(
                    code="tight_schedule_requires_review_cadence",
                    message=(
                        "The schedule is tight; the plan should include a short review cadence and a "
                        "scope-reduction fallback."
                    ),
                    severity="warning",
                )
            )
        if "daily_capacity_missing" in feasibility_flags and planning_strategy.get("deadline_days") is not None:
            score -= 0.12
            issues.append(
                PlanQualityIssue(
                    code="deadline_without_capacity",
                    message="A deadline is known but daily capacity is missing, so workload confidence should stay provisional.",
                    severity="warning",
                )
            )
        if overload_signal and len(tool_calls) > 4:
            score -= 0.32
            issues.append(
                PlanQualityIssue(
                    code="overload_too_many_steps",
                    message="Overload signals are present, but the plan still schedules too many steps.",
                    severity="critical",
                )
            )
        if max_session_minutes and estimated_minutes and estimated_minutes > int(max_session_minutes) * max(len(tool_calls), 1) * 1.4:
            score -= 0.18
            issues.append(
                PlanQualityIssue(
                    code="duration_budget_mismatch",
                    message="Planned task duration appears to exceed the compiled pacing budget.",
                    severity="warning",
                )
            )
        if not tool_calls:
            score -= 0.25
            issues.append(
                PlanQualityIssue(
                    code="no_executable_steps",
                    message="The executable plan has no tool calls or concrete execution steps.",
                    severity="critical",
                )
            )
        return max(0.0, min(score, 1.0))

    def _score_grounding(
        self,
        *,
        contract_mode: str,
        planning_strategy: dict[str, Any],
        material_grounding: dict[str, Any],
        rendered_plan_artifact: Any,
        issues: list[PlanQualityIssue],
    ) -> float:
        grounding_mode = _strip(planning_strategy.get("grounding_mode"))
        status = _strip(material_grounding.get("status"))
        artifact_material_mentions = list(getattr(rendered_plan_artifact, "material_mentions", []) or [])
        grounded_results = [
            _strip(item.get("file_name") or item.get("section_title"))
            for item in _as_list(material_grounding.get("results"))
            if isinstance(item, dict) and _strip(item.get("file_name") or item.get("section_title"))
        ]
        artifact_grounding_basis = ""
        if rendered_plan_artifact is not None:
            artifact_grounding_basis = _strip(getattr(rendered_plan_artifact, "sections", {}).get("grounding_basis"))
        if grounding_mode == "mandatory":
            mentions_grounding = bool(artifact_material_mentions) or any(
                item and item in artifact_grounding_basis for item in grounded_results
            )
            if status == "grounded" and _as_list(material_grounding.get("results")) and mentions_grounding:
                return 0.95
            issues.append(
                PlanQualityIssue(
                    code="grounding_required_but_missing",
                    message="The planning strategy requires user-material grounding, but the rendered plan does not explicitly use user materials.",
                    severity="critical",
                )
            )
            return 0.35
        if grounding_mode == "required_from_profile":
            return 0.82
        if contract_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return 0.8
        return 0.72 if status in {"grounded", "no_hits"} else 0.68

    def _score_next_action(
        self,
        *,
        plan: Any,
        user_message: str,
        rendered_plan_artifact: Any,
        issues: list[PlanQualityIssue],
    ) -> float:
        explicit_next_action = _strip(
            getattr(rendered_plan_artifact, "explicit_next_action", "")
            if rendered_plan_artifact is not None
            else ""
        )
        if explicit_next_action:
            return 0.92
        tool_calls = self._tool_calls(plan)
        if tool_calls:
            return 0.9 if len(tool_calls) <= 3 else 0.76
        if _strip(getattr(plan, "rationale", "")) and _strip(user_message):
            issues.append(
                PlanQualityIssue(
                    code="next_action_inferred_not_explicit",
                    message="The next move can be inferred from rationale, but it is not explicit enough.",
                    severity="warning",
                )
            )
            return 0.48
        issues.append(
            PlanQualityIssue(
                code="no_next_action",
                message="The plan does not provide an actionable next move.",
                severity="critical",
            )
        )
        return 0.2

    def _score_adaptation(
        self,
        *,
        contract_mode: str,
        planning_strategy: dict[str, Any],
        rendered_plan_artifact: Any,
        issues: list[PlanQualityIssue],
    ) -> float:
        adaptation_trigger = _strip(planning_strategy.get("adaptation_trigger"))
        fallback_policy = _strip(planning_strategy.get("fallback_policy"))
        artifact_sections = getattr(rendered_plan_artifact, "sections", {}) if rendered_plan_artifact is not None else {}
        artifact_adaptation = any(
            _strip(artifact_sections.get(key))
            for key in ("adaptation_trigger", "failure_guard", "fallback_uncertainty")
        )
        if adaptation_trigger and fallback_policy and artifact_adaptation:
            return 0.9
        if contract_mode == PLAN_MODE_NEXT_STEP_ONLY:
            unlock_question = _strip(
                getattr(rendered_plan_artifact, "explicit_unlock_question", "")
                if rendered_plan_artifact is not None
                else ""
            )
            return 0.82 if unlock_question else 0.78
        issues.append(
            PlanQualityIssue(
                code="adaptation_logic_thin",
                message="The rendered plan lacks a clear adaptation trigger or fallback path.",
                severity="warning",
            )
        )
        return 0.52

    def _decide(
        self,
        *,
        contract_mode: str,
        readiness_action: str,
        overall_score: float,
        fit_score: float,
        feasibility_score: float,
        grounding_score: float,
        next_action_score: float,
        issues: list[PlanQualityIssue],
    ) -> str:
        if readiness_action == "ask" or contract_mode == PLAN_MODE_NEXT_STEP_ONLY:
            return "ask_more"
        if next_action_score < 0.5:
            return "ask_more"
        if contract_mode != PLAN_MODE_FULL:
            return "downgrade_to_provisional"
        if feasibility_score < 0.5 or grounding_score < 0.5:
            return "downgrade_to_provisional"
        critical_issue = any(item.severity == "critical" and item.code.startswith("missing_section:") for item in issues)
        if critical_issue or overall_score < 0.6:
            return "revise"
        core_scores = (fit_score, feasibility_score, grounding_score, next_action_score)
        if overall_score >= 0.8 and all(score >= 0.7 for score in core_scores):
            return "approve"
        if overall_score >= 0.6 and any(0.5 <= score < 0.7 for score in core_scores):
            return "revise"
        return "revise"
