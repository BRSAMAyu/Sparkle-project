"""Rollout gate implementation: offline validation → shadow → canary → full.

Enforces the four-stage rollout process defined in docs/sgw/05_rollout_gates.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .spec import (
    Action, StateVector, validate_action, clamp_amplitude,
    check_config_novelty, check_direction_history,
    compute_config_hash, ACTION_SPECS,
)


class RolloutStage(str, Enum):
    OFFLINE = "offline"
    SHADOW = "shadow"
    CANARY = "canary"
    FULL = "full"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class GateResult:
    """Result of a rollout gate check."""
    stage: RolloutStage
    passed: bool
    violations: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class RolloutGate:
    """Four-stage rollout gate for RL policy changes.

    Usage:
        gate = RolloutGate(current_config)
        result = gate.validate_offline(action)
        if result.passed:
            # Run shadow...
    """

    def __init__(
        self,
        current_config: dict[str, Any],
        *,
        recent_config_hashes: list[str] | None = None,
        direction_history: list[dict[str, Any]] | None = None,
        canary_ratio: float = 0.1,
        canary_duration_hours: float = 1.0,
    ):
        self.current_config = current_config
        self.recent_hashes = recent_config_hashes or []
        self.direction_history = direction_history or []
        self.canary_ratio = canary_ratio
        self.canary_duration_hours = canary_duration_hours

    def validate_offline(self, action: Action) -> GateResult:
        """Stage 1: Offline validation of the proposed action."""
        violations: list[str] = []

        # 1. Action structural validation
        violations.extend(validate_action(action))

        # 2. Config novelty (Guardrail 1)
        new_config = dict(self.current_config)
        new_config.update(action.changes)
        new_hash = compute_config_hash(new_config)
        if not check_config_novelty(new_hash, self.recent_hashes):
            violations.append(f"Config hash {new_hash} duplicates recent iteration")

        # 3. Direction history (Guardrail 2)
        for param, value in action.changes.items():
            current = self.current_config.get(param, 0)
            direction = 1 if value > current else -1
            if not check_direction_history(param, direction, self.direction_history):
                violations.append(f"Parameter {param} moved {direction} too many times consecutively")

        # 4. Amplitude check (Guardrail 3)
        for param, proposed in action.changes.items():
            current = self.current_config.get(param)
            if current is not None and param in ACTION_SPECS:
                clamped = clamp_amplitude(param, current, proposed)
                if abs(clamped - proposed) > 0.001:
                    violations.append(f"Parameter {param} amplitude exceeds 15% limit")

        passed = len(violations) == 0
        return GateResult(
            stage=RolloutStage.OFFLINE,
            passed=passed,
            violations=violations,
            details={"new_config_hash": new_hash, "changes": action.changes},
        )

    def evaluate_shadow(
        self,
        shadow_summary: dict[str, Any],
        baseline_summary: dict[str, Any],
        *,
        max_hard_violations: int = 0,
        max_soft_rate_multiplier: float = 1.5,
    ) -> GateResult:
        """Stage 2: Evaluate shadow run results."""
        violations: list[str] = []

        # Hard violations check
        if shadow_summary.get("hard_violations", 0) > max_hard_violations:
            violations.append(
                f"Shadow run has {shadow_summary.get('hard_violations', 0)} hard violations"
            )

        # Soft violation rate comparison
        shadow_soft = shadow_summary.get("soft_violation_rate", 0)
        baseline_soft = baseline_summary.get("soft_violation_rate", 0)
        if baseline_soft > 0 and shadow_soft > baseline_soft * max_soft_rate_multiplier:
            violations.append(
                f"Shadow soft rate {shadow_soft:.4f} > {baseline_soft:.4f} × {max_soft_rate_multiplier}"
            )

        # Authenticity check
        shadow_auth = shadow_summary.get("authenticity_mean", 0)
        baseline_auth = baseline_summary.get("authenticity_mean", 1.0)
        if shadow_auth < baseline_auth * 0.9:
            violations.append(
                f"Shadow authenticity {shadow_auth:.4f} < {baseline_auth:.4f} × 0.9"
            )

        passed = len(violations) == 0
        return GateResult(
            stage=RolloutStage.SHADOW,
            passed=passed,
            violations=violations,
            details={"shadow_summary": shadow_summary, "baseline_summary": baseline_summary},
        )

    def evaluate_canary(
        self,
        canary_summary: dict[str, Any],
        control_summary: dict[str, Any],
    ) -> GateResult:
        """Stage 3: Evaluate canary run (10% traffic A/B test)."""
        violations: list[str] = []

        # Hard violations
        if canary_summary.get("hard_violations", 0) > 0:
            violations.append("Canary has hard violations")

        # Soft violation rate ≤ 1.2 × control
        canary_soft = canary_summary.get("soft_violation_rate", 0)
        control_soft = control_summary.get("soft_violation_rate", 0)
        if control_soft > 0 and canary_soft > control_soft * 1.2:
            violations.append(
                f"Canary soft rate {canary_soft:.4f} > control {control_soft:.4f} × 1.2"
            )

        # Authenticity ≥ 0.95 × control
        canary_auth = canary_summary.get("authenticity_mean", 0)
        control_auth = control_summary.get("authenticity_mean", 1.0)
        if canary_auth < control_auth * 0.95:
            violations.append(
                f"Canary authenticity {canary_auth:.4f} < control {control_auth:.4f} × 0.95"
            )

        passed = len(violations) == 0
        return GateResult(
            stage=RolloutStage.CANARY,
            passed=passed,
            violations=violations,
            details={"canary_summary": canary_summary, "control_summary": control_summary},
        )

    def approve_full_rollout(
        self,
        final_summary: dict[str, Any],
        shadow_summary: dict[str, Any],
    ) -> GateResult:
        """Stage 4: Approve full rollout after monitoring period."""
        violations: list[str] = []

        # Final hard check
        if final_summary.get("hard_violations", 0) > 0:
            violations.append("Hard violations detected in final rollout")

        # Soft rate vs shadow
        final_soft = final_summary.get("soft_violation_rate", 0)
        shadow_soft = shadow_summary.get("soft_violation_rate", 0)
        if shadow_soft > 0 and final_soft > shadow_soft * 1.5:
            violations.append(
                f"Final soft rate {final_soft:.4f} > shadow {shadow_soft:.4f} × 1.5"
            )

        passed = len(violations) == 0
        return GateResult(
            stage=RolloutStage.FULL,
            passed=passed,
            violations=violations,
            details={"final_summary": final_summary},
        )
