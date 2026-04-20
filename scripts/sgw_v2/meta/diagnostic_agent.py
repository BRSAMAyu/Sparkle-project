"""Diagnostic agent: identifies failure patterns from run data.

Analyzes SQLite run data to produce DiagnosticHypothesis objects that
attribute failures to specific system parameters.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..storage.db import RunDB


@dataclass
class DiagnosticHypothesis:
    """A specific, testable hypothesis about why failures occurred."""
    hypothesis_id: str
    category: str               # "compliance" | "authenticity" | "performance" | "coverage"
    severity: str               # "critical" | "major" | "minor"
    description: str
    evidence: list[str]
    suggested_action: str
    affected_parameters: list[str]
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "affected_parameters": self.affected_parameters,
            "confidence": self.confidence,
        }


# Pre-defined diagnostic rules (rule-based, no LLM)
_DIAGNOSTIC_RULES: list[dict[str, Any]] = [
    {
        "id": "high_soft_violation_rate",
        "category": "compliance",
        "severity": "critical",
        "trigger": lambda s: s.get("soft_violation_rate", 0) > 0.15,
        "description": "Soft violation rate exceeds 15% threshold",
        "evidence_fn": lambda s: [f"soft_violation_rate={s.get('soft_violation_rate', 0):.4f}"],
        "action": "Lower soft_violation_threshold or improve persona prompt constraints",
        "parameters": ["soft_violation_threshold", "persona_prompt_template"],
    },
    {
        "id": "low_authenticity_mean",
        "category": "authenticity",
        "severity": "major",
        "trigger": lambda s: s.get("authenticity_mean", 1.0) < 0.65,
        "description": "Authenticity mean score below 0.65",
        "evidence_fn": lambda s: [f"authenticity_mean={s.get('authenticity_mean', 0):.4f}"],
        "action": "Review state machine arc templates or increase persona diversity",
        "parameters": ["arc_templates", "persona_library", "authenticity_threshold"],
    },
    {
        "id": "high_authenticity_failure_rate",
        "category": "authenticity",
        "severity": "major",
        "trigger": lambda s: (
            s.get("authenticity_total", 0) > 5
            and s.get("authenticity_failures", 0) / max(s.get("authenticity_total", 1), 1) > 0.30
        ),
        "description": "More than 30% of authenticity audits fail",
        "evidence_fn": lambda s: [
            f"auth_failures={s.get('authenticity_failures', 0)}/{s.get('authenticity_total', 0)}"
        ],
        "action": "Investigate arc_progression and linguistic_naturalness dimensions",
        "parameters": ["arc_templates", "expression_prompt"],
    },
    {
        "id": "low_session_completion_rate",
        "category": "performance",
        "severity": "major",
        "trigger": lambda s: (
            s.get("sessions_total", 0) > 10
            and s.get("sessions_completed", 0) / max(s.get("sessions_total", 1), 1) < 0.70
        ),
        "description": "Less than 70% of sessions complete",
        "evidence_fn": lambda s: [
            f"sessions_completed={s.get('sessions_completed', 0)}/{s.get('sessions_total', 0)}"
        ],
        "action": "Check for rate limiting, quota exhaustion, or WebSocket failures",
        "parameters": ["claude_max_parallel", "claude_timeout_seconds", "websocket_url"],
    },
    {
        "id": "hard_violations_present",
        "category": "compliance",
        "severity": "critical",
        "trigger": lambda s: s.get("hard_violations", 0) > 0,
        "description": "Hard violations detected",
        "evidence_fn": lambda s: [f"hard_violations={s.get('hard_violations', 0)}"],
        "action": "Review hard violation logs and fix underlying compliance issue",
        "parameters": ["hard_violation_rules"],
    },
    {
        "id": "low_turn_volume",
        "category": "coverage",
        "severity": "minor",
        "trigger": lambda s: s.get("turns_total", 0) < 100 and s.get("sessions_completed", 0) > 5,
        "description": "Average turns per session is low",
        "evidence_fn": lambda s: [
            f"avg_turns={s.get('turns_total', 0) / max(s.get('sessions_completed', 1), 1):.1f}"
        ],
        "action": "Increase turn_target or check for premature session termination",
        "parameters": ["turn_target", "session_turn_slice"],
    },
]


class DiagnosticAgent:
    """Rule-based diagnostic agent that analyzes run data and produces hypotheses."""

    def __init__(self, run_db: RunDB):
        self.run_db = run_db

    def diagnose(self, run_id: str) -> list[DiagnosticHypothesis]:
        """Analyze a run and return diagnostic hypotheses."""
        summary = self.run_db.run_summary(run_id)
        if not summary:
            return []

        hypotheses: list[DiagnosticHypothesis] = []
        for rule in _DIAGNOSTIC_RULES:
            if rule["trigger"](summary):
                hypotheses.append(
                    DiagnosticHypothesis(
                        hypothesis_id=rule["id"],
                        category=rule["category"],
                        severity=rule["severity"],
                        description=rule["description"],
                        evidence=rule["evidence_fn"](summary),
                        suggested_action=rule["action"],
                        affected_parameters=rule["parameters"],
                        confidence=self._compute_confidence(rule, summary),
                    )
                )

        return hypotheses

    def _compute_confidence(self, rule: dict[str, Any], summary: dict[str, Any]) -> float:
        """Compute confidence based on sample size and effect size."""
        # More samples = higher confidence
        sessions = summary.get("sessions_completed", 0)
        sample_confidence = min(1.0, sessions / 100)

        # Stronger effect = higher confidence
        effect_confidence = 0.5
        if rule["severity"] == "critical":
            effect_confidence = 0.8
        elif rule["severity"] == "major":
            effect_confidence = 0.6

        return round(min(1.0, (sample_confidence + effect_confidence) / 2), 2)

    def compare_and_diagnose(self, run_id_a: str, run_id_b: str) -> list[DiagnosticHypothesis]:
        """Compare two runs and diagnose which got worse."""
        diff = self.run_db.compare_runs(run_id_a, run_id_b)
        summary_b = self.run_db.run_summary(run_id_b)
        hypotheses = self.diagnose(run_id_b)

        # Add regression hypotheses for metrics that got worse
        for key, vals in diff.items():
            if not isinstance(vals, dict) or "delta" not in vals:
                continue
            delta = vals["delta"]
            if key == "soft_violation_rate" and delta > 0.05:
                hypotheses.append(
                    DiagnosticHypothesis(
                        hypothesis_id=f"regression_{key}",
                        category="compliance",
                        severity="major",
                        description=f"{key} regressed by {delta:.4f}",
                        evidence=[f"before={vals['a']:.4f} after={vals['b']:.4f}"],
                        suggested_action=f"Revert changes that affected {key}",
                        affected_parameters=["unknown"],
                        confidence=0.7,
                    )
                )
            elif key == "authenticity_mean" and delta < -0.05:
                hypotheses.append(
                    DiagnosticHypothesis(
                        hypothesis_id=f"regression_{key}",
                        category="authenticity",
                        severity="major",
                        description=f"{key} regressed by {delta:.4f}",
                        evidence=[f"before={vals['a']:.4f} after={vals['b']:.4f}"],
                        suggested_action="Review arc template or persona changes",
                        affected_parameters=["arc_templates", "persona_library"],
                        confidence=0.7,
                    )
                )

        return hypotheses
