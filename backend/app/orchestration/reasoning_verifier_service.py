from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.orchestration.schemas import ExecutablePlan


@dataclass
class ReasoningVerificationResult:
    verifier_score: float
    verifier_ensemble_score: float
    contract_coverage: float
    verifier_fail_reasons: list[str] = field(default_factory=list)
    dimension_scores: dict[str, float] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "verifier_score": round(float(self.verifier_score), 4),
            "verifier_ensemble_score": round(float(self.verifier_ensemble_score), 4),
            "contract_coverage": round(float(self.contract_coverage), 4),
            "verifier_fail_reasons": list(self.verifier_fail_reasons),
            "dimension_scores": dict(self.dimension_scores),
        }


class ReasoningVerifierService:
    """Plan-level reasoning quality verifier for process supervision."""

    @staticmethod
    def verify(
        *,
        plan: ExecutablePlan | None,
        contract: dict[str, Any] | None,
    ) -> ReasoningVerificationResult:
        fail_reasons: list[str] = []
        normalized_contract = contract if isinstance(contract, dict) else {}

        goal_ok = _has_text(normalized_contract.get("goal"))
        constraints_ok = _has_nonempty_list(normalized_contract.get("constraints"))
        milestones_ok = _has_nonempty_list(normalized_contract.get("milestones"))
        acceptance_ok = _has_nonempty_list(normalized_contract.get("acceptance_criteria"))
        risks_ok = _has_nonempty_list(normalized_contract.get("risks"))

        contract_hits = sum(
            1
            for ok in (goal_ok, constraints_ok, milestones_ok, acceptance_ok, risks_ok)
            if ok
        )
        contract_coverage = contract_hits / 5.0

        if not goal_ok:
            fail_reasons.append("missing_goal")
        if not constraints_ok:
            fail_reasons.append("missing_constraints")
        if not milestones_ok:
            fail_reasons.append("missing_milestones")
        if not acceptance_ok:
            fail_reasons.append("missing_acceptance_criteria")
        if not risks_ok:
            fail_reasons.append("missing_risks")

        has_plan = plan is not None
        tool_count = len(plan.tool_calls) if plan else 0
        has_steps = tool_count > 0
        has_success_criteria = bool(plan and (plan.success_criteria or any(tc.success_criteria for tc in plan.tool_calls)))
        has_dependencies = bool(
            plan
            and (
                any(tc.depends_on for tc in plan.tool_calls)
                or (plan.execution_order and len(plan.execution_order) > 1)
                or tool_count <= 1
            )
        )
        confidence = float(plan.confidence or 0.0) if plan else 0.0
        confidence = max(0.0, min(confidence, 1.0))

        executability = 0.0
        if has_plan:
            if has_steps:
                executability += 0.5
            if has_success_criteria:
                executability += 0.3
            if tool_count <= 5:
                executability += 0.2
        executability = max(0.0, min(executability, 1.0))

        dependency_score = 1.0 if has_dependencies else 0.0
        acceptance_verifiability = _acceptance_verifiability(
            plan=plan,
            contract=normalized_contract,
        )
        time_budget_consistency = _time_budget_consistency(
            plan=plan,
            contract=normalized_contract,
        )
        verifier_ensemble_score = (
            0.45 * contract_coverage
            + 0.25 * executability
            + 0.15 * dependency_score
            + 0.1 * acceptance_verifiability
            + 0.05 * time_budget_consistency
        )
        verifier_ensemble_score = max(0.0, min(verifier_ensemble_score, 1.0))
        verifier_score = verifier_ensemble_score

        if not has_steps:
            fail_reasons.append("empty_plan")
        if not has_success_criteria:
            fail_reasons.append("missing_success_criteria")
        if not has_dependencies:
            fail_reasons.append("missing_dependency_relations")
        if acceptance_verifiability < 0.6:
            fail_reasons.append("low_acceptance_verifiability")
        if time_budget_consistency < 0.55:
            fail_reasons.append("time_budget_inconsistent")
        if confidence < 0.35:
            fail_reasons.append("low_plan_confidence")

        return ReasoningVerificationResult(
            verifier_score=verifier_score,
            verifier_ensemble_score=verifier_ensemble_score,
            contract_coverage=contract_coverage,
            verifier_fail_reasons=fail_reasons,
            dimension_scores={
                "contract_coverage": round(contract_coverage, 4),
                "executability": round(executability, 4),
                "dependency_score": round(dependency_score, 4),
                "acceptance_verifiability": round(acceptance_verifiability, 4),
                "time_budget_consistency": round(time_budget_consistency, 4),
                "confidence": round(confidence, 4),
            },
        )

    @staticmethod
    def should_block(result: ReasoningVerificationResult) -> bool:
        min_score = float(getattr(settings, "REASONING_VERIFIER_MIN_SCORE", 0.75))
        min_coverage = float(getattr(settings, "REASONING_VERIFIER_MIN_CONTRACT_COVERAGE", 0.85))
        return bool(result.verifier_score < min_score or result.contract_coverage < min_coverage)


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_nonempty_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return any(str(item).strip() for item in value)


def _acceptance_verifiability(*, plan: ExecutablePlan | None, contract: dict[str, Any]) -> float:
    score = 0.0
    acceptance = contract.get("acceptance_criteria")
    if isinstance(acceptance, list) and any(str(item).strip() for item in acceptance):
        score += 0.45
    if plan and plan.success_criteria:
        score += 0.35
    if plan and any(tc.success_criteria for tc in plan.tool_calls):
        score += 0.2
    return max(0.0, min(score, 1.0))


def _time_budget_consistency(*, plan: ExecutablePlan | None, contract: dict[str, Any]) -> float:
    constraints = contract.get("constraints")
    has_time_constraint = False
    if isinstance(constraints, list):
        for item in constraints:
            text = str(item).lower()
            if any(token in text for token in ("天", "周", "月", "小时", "分钟", "day", "week", "month", "hour", "minute", "deadline", "截止")):
                has_time_constraint = True
                break

    if plan is None:
        return 0.2 if has_time_constraint else 0.0

    avg_timeout_ms = 0.0
    if plan.tool_calls:
        avg_timeout_ms = sum(max(0, int(tc.timeout_ms or 0)) for tc in plan.tool_calls) / max(1, len(plan.tool_calls))
    timeout_score = 1.0 if avg_timeout_ms <= 30000 else max(0.3, 1.0 - (avg_timeout_ms - 30000) / 90000)
    layering_score = 1.0 if plan.execution_order and len(plan.execution_order) >= 1 else 0.65

    score = 0.4 * timeout_score + 0.35 * layering_score + (0.25 if has_time_constraint else 0.1)
    return max(0.0, min(score, 1.0))
