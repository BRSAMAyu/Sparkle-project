from __future__ import annotations

from dataclasses import dataclass, field

from app.orchestration.schemas import ExecutablePlan


@dataclass
class PlanSimulationResult:
    simulated_risk_score: float
    risk_factors: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    simulated_failure_paths: list[dict[str, str]] = field(default_factory=list)
    preemptive_actions: list[str] = field(default_factory=list)


class PlanSimulatorService:
    """Lightweight pre-execution simulator for planning risk control."""

    @staticmethod
    def simulate(
        *,
        plan: ExecutablePlan | None,
        selected_experts: list[str] | None,
        uncertainty_score: float,
        route_confidence: float,
    ) -> PlanSimulationResult:
        if plan is None:
            return PlanSimulationResult(
                simulated_risk_score=0.8,
                risk_factors=["missing_plan"],
                suggested_actions=["fallback_single_expert"],
                simulated_failure_paths=[
                    {
                        "path": "missing_plan",
                        "trigger": "planner_output_empty",
                        "impact": "high",
                    }
                ],
                preemptive_actions=["fallback_single_expert"],
            )

        experts = [str(item).strip() for item in (selected_experts or []) if str(item).strip()]
        step_count = len(plan.tool_calls)
        layer_count = len(plan.execution_order) if plan.execution_order else (1 if step_count > 0 else 0)
        has_dependencies = any(tc.depends_on for tc in plan.tool_calls)
        avg_timeout = (
            sum(max(0, int(tc.timeout_ms or 0)) for tc in plan.tool_calls) / max(1, step_count)
            if step_count > 0
            else 0.0
        )
        confidence = max(0.0, min(float(plan.confidence or 0.0), 1.0))
        uncertainty = max(0.0, min(float(uncertainty_score), 1.0))
        route = max(0.0, min(float(route_confidence), 1.0))

        risk = (
            0.2 * min(step_count / 8.0, 1.0)
            + 0.15 * min(max(layer_count - 1, 0) / 4.0, 1.0)
            + 0.12 * (0.0 if has_dependencies else 1.0)
            + 0.13 * min(max(len(experts) - 1, 0) / 3.0, 1.0)
            + 0.12 * min(avg_timeout / 60000.0, 1.0)
            + 0.16 * uncertainty
            + 0.12 * (1.0 - route)
            + 0.1 * (1.0 - confidence)
        )
        risk = max(0.0, min(risk, 1.0))

        risk_factors: list[str] = []
        actions: list[str] = []
        if step_count >= 7:
            risk_factors.append("high_step_count")
            actions.append("reduce_expert_count")
        if len(experts) >= 3:
            risk_factors.append("high_expert_parallelism")
            actions.append("degrade_parallelism")
        if not has_dependencies and step_count > 1:
            risk_factors.append("weak_dependency_graph")
            actions.append("tighten_dependency_order")
        if uncertainty >= 0.62:
            risk_factors.append("high_uncertainty")
            actions.append("require_minimal_clarification")
        if avg_timeout >= 45000:
            risk_factors.append("timeout_pressure")
            actions.append("degrade_to_single_expert")

        dedup_actions: list[str] = []
        for action in actions:
            if action not in dedup_actions:
                dedup_actions.append(action)

        failure_paths: list[dict[str, str]] = []
        if "high_step_count" in risk_factors:
            failure_paths.append(
                {
                    "path": "critical_path_overload",
                    "trigger": "too_many_serial_steps",
                    "impact": "medium",
                }
            )
        if "high_expert_parallelism" in risk_factors:
            failure_paths.append(
                {
                    "path": "parallel_coordination_failure",
                    "trigger": "fanout_too_high",
                    "impact": "medium",
                }
            )
        if "weak_dependency_graph" in risk_factors:
            failure_paths.append(
                {
                    "path": "dependency_break",
                    "trigger": "missing_dep_bindings",
                    "impact": "high",
                }
            )
        if "high_uncertainty" in risk_factors:
            failure_paths.append(
                {
                    "path": "intent_mismatch",
                    "trigger": "clarity_insufficient",
                    "impact": "high",
                }
            )
        if "timeout_pressure" in risk_factors:
            failure_paths.append(
                {
                    "path": "timeout_chain_reaction",
                    "trigger": "tool_timeout_pressure",
                    "impact": "medium",
                }
            )

        return PlanSimulationResult(
            simulated_risk_score=round(risk, 4),
            risk_factors=risk_factors,
            suggested_actions=dedup_actions[:3],
            simulated_failure_paths=failure_paths[:4],
            preemptive_actions=dedup_actions[:3],
        )
