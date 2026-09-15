from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.analytics.user_state_model import (
    RoutingMode,
    SimulatedOutcome,
    UserArchetype,
    UserStateModel,
)


class UserStateModelAuditor:
    """Batch self-checks for the simulation wind tunnel.

    This audit does not claim a policy is good for real users. It only checks
    whether the stochastic dynamics are internally sane across archetypes and
    stress policies before we use the simulator for boundary testing.
    """

    DEFAULT_POLICIES: tuple[str, ...] = ("execution_stress", "balanced", "support_recovery")

    def run(
        self,
        *,
        samples_per_archetype: int = 100,
        steps: int = 100,
        seed: int = 17,
        archetypes: list[UserArchetype] | None = None,
        policies: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        resolved_archetypes = archetypes or list(UserArchetype)
        resolved_policies = policies or self.DEFAULT_POLICIES
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for archetype_index, archetype in enumerate(resolved_archetypes):
            for policy_index, policy in enumerate(resolved_policies):
                for sample_index in range(samples_per_archetype):
                    run_seed = seed + archetype_index * 100_000 + policy_index * 10_000 + sample_index
                    model = UserStateModel.from_archetype(archetype, rng_seed=run_seed)
                    outcomes: list[str] = []
                    consistency_failures = 0
                    for step_index in range(steps):
                        action = self._action_for_policy(policy, step_index)
                        report = model.step(action)
                        outcomes.append(report.outcome.value)
                        if not report.consistency.passed:
                            consistency_failures += 1
                        if report.absorbed:
                            break
                    groups[(archetype.value, policy)].append(
                        {
                            "seed": run_seed,
                            "steps_run": len(outcomes),
                            "absorbed": model.absorbed,
                            "final_outcome": outcomes[-1] if outcomes else SimulatedOutcome.CONTINUE.value,
                            "consistency_failures": consistency_failures,
                            "final_state": model.state.to_dict(),
                        }
                    )

        summaries = {
            f"{archetype}:{policy}": self._summarize_runs(runs)
            for (archetype, policy), runs in sorted(groups.items())
        }
        return {
            "schema_version": "user_state_model_audit.v1",
            "samples_per_archetype": samples_per_archetype,
            "steps": steps,
            "seed": seed,
            "summaries": summaries,
            "warnings": self._warnings(summaries),
        }

    @staticmethod
    def _action_for_policy(policy: str, step_index: int) -> RoutingMode:
        if policy == "execution_stress":
            return RoutingMode.EXECUTION_FIRST
        if policy == "support_recovery":
            return RoutingMode.COGNITIVE_FIRST
        if policy == "balanced":
            return RoutingMode.BALANCED
        if policy == "cycle":
            return (RoutingMode.EXECUTION_FIRST, RoutingMode.BALANCED, RoutingMode.COGNITIVE_FIRST)[step_index % 3]
        raise ValueError(f"unknown audit policy: {policy}")

    @staticmethod
    def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
        total = max(1, len(runs))
        final_states = [run["final_state"] for run in runs]
        outcome_counts: dict[str, int] = {}
        for run in runs:
            outcome = str(run["final_outcome"])
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        return {
            "runs": len(runs),
            "absorption_rate": round(sum(1 for run in runs if run["absorbed"]) / total, 4),
            "collapse_rate": round(
                sum(1 for run in runs if run["final_outcome"] == SimulatedOutcome.FORCED_ABANDON.value) / total,
                4,
            ),
            "abandon_rate": round(
                sum(1 for run in runs if run["final_outcome"] == SimulatedOutcome.TASK_ABANDONED.value) / total,
                4,
            ),
            "completion_rate": round(
                sum(1 for run in runs if run["final_outcome"] == SimulatedOutcome.TASK_COMPLETED.value) / total,
                4,
            ),
            "avg_steps_run": round(sum(float(run["steps_run"]) for run in runs) / total, 4),
            "consistency_failure_rate": round(
                sum(1 for run in runs if int(run["consistency_failures"]) > 0) / total,
                4,
            ),
            "outcome_counts": outcome_counts,
            "avg_final_state": {
                key: round(sum(float(state[key]) for state in final_states) / total, 4)
                for key in sorted(final_states[0])
            }
            if final_states
            else {},
        }

    @staticmethod
    def _warnings(summaries: dict[str, dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        fragile_exec = summaries.get("fragile:execution_stress", {})
        resilient_exec = summaries.get("resilient:execution_stress", {})
        pressure_exec = summaries.get("pressure_driven:execution_stress", {})
        if fragile_exec and resilient_exec:
            if float(fragile_exec.get("collapse_rate", 0.0)) <= float(resilient_exec.get("collapse_rate", 0.0)):
                warnings.append("fragile execution_stress collapse_rate is not above resilient; check trait separation.")
        if pressure_exec and fragile_exec:
            pressure_capacity = float(pressure_exec.get("avg_final_state", {}).get("execution_capacity", 0.0))
            fragile_capacity = float(fragile_exec.get("avg_final_state", {}).get("execution_capacity", 0.0))
            if pressure_capacity <= fragile_capacity:
                warnings.append("pressure_driven execution capacity is not above fragile under execution_stress.")
        for key, summary in summaries.items():
            if float(summary.get("consistency_failure_rate", 0.0)) > 0.05:
                warnings.append(f"{key} consistency_failure_rate exceeds 5%.")
        return warnings
