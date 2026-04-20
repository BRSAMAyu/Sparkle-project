"""Experiment planner: proposes parameter changes based on diagnostic hypotheses.

Maps DiagnosticHypothesis objects to concrete parameter adjustments
and produces ExperimentPlan objects for the meta-orchestrator.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .diagnostic_agent import DiagnosticHypothesis


@dataclass
class ParameterChange:
    """A single parameter adjustment."""
    parameter: str
    current_value: Any
    proposed_value: Any
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "rationale": self.rationale,
        }


@dataclass
class ExperimentPlan:
    """A concrete plan for the next iteration with parameter changes."""
    plan_id: str
    parent_run_id: str
    hypotheses: list[str]               # hypothesis_ids addressed
    parameter_changes: list[ParameterChange]
    expected_outcome: str
    priority: str = "normal"            # "urgent" | "high" | "normal" | "low"
    status: str = "proposed"            # "proposed" | "accepted" | "running" | "completed" | "rejected"
    result_run_id: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "parent_run_id": self.parent_run_id,
            "hypotheses": self.hypotheses,
            "parameter_changes": [pc.to_dict() for pc in self.parameter_changes],
            "expected_outcome": self.expected_outcome,
            "priority": self.priority,
            "status": self.status,
            "result_run_id": self.result_run_id,
            "created_at": self.created_at,
        }


# Parameter adjustment rules: map hypothesis_id -> list of (parameter, adjustment_fn)
_ADJUSTMENT_RULES: dict[str, list[tuple[str, Any]]] = {
    "high_soft_violation_rate": [
        ("soft_violation_threshold", lambda v: round(min(v + 0.05, 0.95), 2)),
    ],
    "low_authenticity_mean": [
        ("turn_target", lambda v: max(v, 10)),
        ("audit_sample_rate", lambda v: round(min(v + 0.05, 0.5), 2)),
    ],
    "high_authenticity_failure_rate": [
        ("authenticity_sample_rate", lambda v: round(min(v + 0.10, 0.5), 2)),
    ],
    "low_session_completion_rate": [
        ("claude_timeout_seconds", lambda v: min(v + 15, 120)),
        ("claude_failure_backoff_seconds", lambda v: min(v + 10, 120)),
    ],
    "hard_violations_present": [
        # Cannot auto-fix hard violations - needs human review
    ],
    "low_turn_volume": [
        ("turn_target", lambda v: min(v + 2, 20)),
    ],
}


class ExperimentPlanner:
    """Proposes parameter changes based on diagnostic hypotheses."""

    def __init__(self, current_config: dict[str, Any]):
        self.current_config = current_config

    def plan(self, hypotheses: list[DiagnosticHypothesis], parent_run_id: str) -> ExperimentPlan | None:
        """Generate an ExperimentPlan from diagnostic hypotheses."""
        if not hypotheses:
            return None

        changes: list[ParameterChange] = []
        addressed_hypotheses: list[str] = []
        max_severity = "low"

        severity_order = {"critical": 0, "major": 1, "minor": 2, "low": 3}

        for hypothesis in sorted(hypotheses, key=lambda h: severity_order.get(h.severity, 3)):
            if hypothesis.hypothesis_id.startswith("regression_"):
                # Regression hypotheses need manual review
                addressed_hypotheses.append(hypothesis.hypothesis_id)
                if severity_order.get(hypothesis.severity, 3) < severity_order.get(max_severity, 3):
                    max_severity = hypothesis.severity
                continue

            rules = _ADJUSTMENT_RULES.get(hypothesis.hypothesis_id, [])
            for param_name, adjust_fn in rules:
                current = self.current_config.get(param_name)
                if current is None:
                    continue
                proposed = adjust_fn(current)
                if proposed != current:
                    changes.append(
                        ParameterChange(
                            parameter=param_name,
                            current_value=current,
                            proposed_value=proposed,
                            rationale=hypothesis.description,
                        )
                    )
            addressed_hypotheses.append(hypothesis.hypothesis_id)
            if severity_order.get(hypothesis.severity, 3) < severity_order.get(max_severity, 3):
                max_severity = hypothesis.severity

        if not changes and not any(h.hypothesis_id.startswith("regression_") for h in hypotheses):
            return None

        priority_map = {"critical": "urgent", "major": "high", "minor": "normal", "low": "low"}
        priority = priority_map.get(max_severity, "normal")

        # Build expected outcome description
        change_desc = "; ".join(
            f"{c.parameter}: {c.current_value} -> {c.proposed_value}" for c in changes
        )
        expected = f"Applying changes: {change_desc}" if change_desc else "Review required (no auto-adjustable parameters)"

        return ExperimentPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            parent_run_id=parent_run_id,
            hypotheses=addressed_hypotheses,
            parameter_changes=changes,
            expected_outcome=expected,
            priority=priority,
        )

    def apply_plan(self, plan: ExperimentPlan) -> dict[str, Any]:
        """Apply experiment plan to a copy of current config, return new config."""
        new_config = dict(self.current_config)
        for change in plan.parameter_changes:
            new_config[change.parameter] = change.proposed_value
        return new_config
