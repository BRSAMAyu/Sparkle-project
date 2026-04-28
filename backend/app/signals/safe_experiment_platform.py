"""
Core: execution / research
Phase: adapt
Stage: P4-2 — Safe Adaptive Experiment Platform

Risk-aware policy experiment platform. Extends policy_experiments.py with:
- 7-stage lifecycle (draft→shadow→canary→safe_live→paused→concluded→deprecated)
- SafeBanditController with human-in-the-loop exploration
- Multi-objective reward model (primary + guardrail weights)
- Experiment guardrails with auto-stop
- Experiment rollback mechanism
- Promotion gate with minimum thresholds

Iron Laws:
  1. Never experiment on high-risk users (D-0, fatigue_critical, user_opted_out)
  2. Shadow first, canary second, then constrained bandit — never skip stages
  3. Guardrails must auto-stop experiments (negative feedback, fatigue, agency loss)
  4. Every experiment must have rollback plan
  5. Multi-objective reward prevents "easy tasks" optimization
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.signals.intervention_episode import ContextSignature, OutcomeVector


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. Multi-objective Reward Model
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class RewardModel:
    """Multi-objective reward prevents optimizing for "completion only."

    The system MUST optimize for goal progress + learning, not just task completion.
    Guardrail metrics are constraints — they must not increase.
    """
    primary: dict[str, float] = field(default_factory=lambda: {
        "goal_progress": 0.35,
        "learning_gain": 0.25,
        "execution_completion": 0.15,
    })
    guardrails: dict[str, str] = field(default_factory=lambda: {
        "negative_feedback": "must_not_increase",
        "fatigue": "must_not_increase",
        "user_agency_loss": "must_not_increase",
        "trust_drop": "must_not_increase",
    })
    secondary: dict[str, float] = field(default_factory=lambda: {
        "next_day_return": 0.10,
        "source_effectiveness": 0.05,
        "relationship_trust": 0.10,
    })

    def compute_reward(self, outcome: OutcomeVector) -> dict[str, Any]:
        """Compute multi-objective reward from an OutcomeVector."""
        primary_score = 0.0
        primary_score += self.primary.get("goal_progress", 0.35) * (
            outcome.goal_progress.node_mastery_delta + outcome.goal_progress.exam_readiness_delta
        ) / 2.0
        primary_score += self.primary.get("learning_gain", 0.25) * max(
            0.0, outcome.learning.accuracy_delta_from_baseline + 0.5,
        )
        primary_score += self.primary.get("execution_completion", 0.15) * (
            1.0 if outcome.execution.completed else 0.0
        )

        secondary_score = 0.0
        secondary_score += self.secondary.get("next_day_return", 0.10) * (
            1.0 if outcome.sustainability.returned_next_day else 0.5
        )
        secondary_score += self.secondary.get("relationship_trust", 0.10) * (
            0.0 if outcome.trust.explicit_negative_feedback else 1.0
        )

        guardrail_violations, violations_list = outcome.has_guardrail_violation()

        return {
            "primary_score": round(primary_score, 4),
            "secondary_score": round(secondary_score, 4),
            "total_score": round(primary_score + secondary_score, 4),
            "guardrail_violations": violations_list,
            "guardrail_clean": not guardrail_violations,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "guardrails": self.guardrails,
            "secondary": self.secondary,
        }


# ═══════════════════════════════════════════════════════════════════════
# 2. Experiment Guardrails
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ExperimentGuardrails:
    """Auto-stop guardrails for safe experimentation."""
    max_negative_feedback_rate: float = 0.05
    max_user_correction_rate: float = 0.18
    max_fatigue_rate: float = 0.10
    max_trust_drop_rate: float = 0.10
    fatigue_guard_required: bool = True
    stop_if_trust_drop: bool = True
    no_new_chapter_when_deadline_high: bool = True
    excluded_contexts: list[str] = field(default_factory=lambda: [
        "D0_exam_day", "fatigue_critical", "user_opted_out_experiments",
    ])

    def check(
        self,
        outcomes: list[OutcomeVector],
    ) -> dict[str, Any]:
        """Check guardrails against recent outcomes. Returns status + violations."""
        if not outcomes:
            return {"status": "ok", "violations": []}

        n = len(outcomes)
        violations = []

        neg_fb_rate = sum(1 for o in outcomes if o.trust.explicit_negative_feedback) / n
        if neg_fb_rate > self.max_negative_feedback_rate:
            violations.append({
                "guardrail": "negative_feedback",
                "threshold": self.max_negative_feedback_rate,
                "actual": round(neg_fb_rate, 3),
                "action": "pause_experiment",
            })

        correction_rate = sum(1 for o in outcomes if o.agency.user_corrected_system) / n
        if correction_rate > self.max_user_correction_rate:
            violations.append({
                "guardrail": "user_correction",
                "threshold": self.max_user_correction_rate,
                "actual": round(correction_rate, 3),
                "action": "pause_experiment",
            })

        fatigue_rate = sum(
            1 for o in outcomes
            if o.load.cognitive_load_after == "high" or o.load.affective_pressure_after == "anxious"
        ) / n
        if fatigue_rate > self.max_fatigue_rate:
            violations.append({
                "guardrail": "fatigue",
                "threshold": self.max_fatigue_rate,
                "actual": round(fatigue_rate, 3),
                "action": "pause_experiment",
            })

        trust_drop_rate = sum(1 for o in outcomes if o.trust.receipt_dismissed) / n
        if trust_drop_rate > self.max_trust_drop_rate:
            violations.append({
                "guardrail": "trust_drop",
                "threshold": self.max_trust_drop_rate,
                "actual": round(trust_drop_rate, 3),
                "action": "stop_and_rollback",
            })

        return {
            "status": "ok" if not violations else "violated",
            "violations": violations,
            "requires_stop": any(
                v["action"] == "stop_and_rollback" for v in violations
            ),
            "requires_pause": any(
                v["action"] == "pause_experiment" for v in violations
            ),
        }

    def is_context_eligible(
        self,
        context: ContextSignature,
    ) -> tuple[bool, str]:
        """Check if context is eligible for experimentation."""
        if context.deadline_phase in self.excluded_contexts:
            return False, f"deadline_phase {context.deadline_phase} is excluded"
        if context.affective_pressure in self.excluded_contexts:
            return False, f"affective_pressure {context.affective_pressure} is excluded"
        return True, "eligible"

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_negative_feedback_rate": self.max_negative_feedback_rate,
            "max_user_correction_rate": self.max_user_correction_rate,
            "max_fatigue_rate": self.max_fatigue_rate,
            "max_trust_drop_rate": self.max_trust_drop_rate,
            "excluded_contexts": self.excluded_contexts,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. SafePolicyExperiment — 7-stage lifecycle
# ═══════════════════════════════════════════════════════════════════════

EXPERIMENT_STAGES = [
    "draft",        # Design review — not running
    "shadow",       # Log hypothetical outcomes, don't affect users
    "canary",       # Run on low-risk, small sample, reversible
    "safe_live",    # Run on eligible users with guardrails active
    "paused",       # Temporarily paused (guardrail trigger)
    "concluded",    # Analysis complete, awaiting promotion/rollback
    "deprecated",   # Archived, no longer active
]

VALID_TRANSITIONS = {
    "draft": ["shadow"],
    "shadow": ["canary", "deprecated"],
    "canary": ["safe_live", "paused", "deprecated"],
    "safe_live": ["paused", "concluded", "deprecated"],
    "paused": ["canary", "safe_live", "deprecated"],
    "concluded": ["deprecated"],
    "deprecated": [],  # Terminal
}


@dataclass
class SafePolicyExperiment:
    """A risk-aware policy experiment with full lifecycle management."""
    experiment_id: str = ""
    name: str = ""
    hypothesis: str = ""
    domain: str = ""                            # "exam_sprint" | "project_delivery" | ...
    status: str = "draft"                       # 7-stage lifecycle
    eligible_context: dict[str, Any] = field(default_factory=dict)
    excluded_context: list[str] = field(default_factory=list)
    policies: list[dict[str, Any]] = field(default_factory=list)
    assignment_mode: str = "shadow"             # "shadow" | "constrained_bandit" | "manual_review"
    reward_model: RewardModel = field(default_factory=RewardModel)
    guardrails: ExperimentGuardrails = field(default_factory=ExperimentGuardrails)
    min_episodes: int = 50
    min_distinct_users: int = 15
    evidence_grade_required: int = 3
    current_episodes: int = 0
    distinct_users: list[str] = field(default_factory=list)
    outcome_history: list[dict[str, Any]] = field(default_factory=list)
    rollback_version: str = ""
    previous_versions: list[dict[str, Any]] = field(default_factory=list)
    kill_switch_key: str = ""
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = _uid("spexp")
        if not self.kill_switch_key:
            self.kill_switch_key = f"exp_{self.experiment_id}"

    def can_transition_to(self, target: str) -> bool:
        return target in VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, target: str) -> tuple[bool, str]:
        """Attempt to transition experiment to a new stage."""
        if not self.can_transition_to(target):
            return False, f"Invalid transition: {self.status} → {target}"

        if target == "shadow" and self.status == "draft":
            if not self.policies or len(self.policies) < 2:
                return False, "Need at least 2 policies for shadow experiment"
            if not self.hypothesis:
                return False, "Hypothesis required"

        if target == "canary" and self.status == "shadow":
            if self.current_episodes < 10:
                return False, "Need at least 10 shadow episodes before canary"

        if target == "safe_live" and self.status == "canary":
            if self.current_episodes < self.min_episodes:
                return False, f"Need {self.min_episodes} episodes, have {self.current_episodes}"
            if len(self.distinct_users) < self.min_distinct_users:
                return False, f"Need {self.min_distinct_users} users, have {len(self.distinct_users)}"

        old_status = self.status
        self.status = target
        self.updated_at = _utcnow()
        logger.info("Experiment {} {} → {}", self.experiment_id, old_status, target)
        return True, f"Transitioned {old_status} → {target}"

    def pause(self, reason: str) -> None:
        """Pause experiment (guardrail trigger)."""
        if self.status in ("canary", "safe_live"):
            self.status = "paused"
            self.updated_at = _utcnow()
            logger.warning("Experiment {} paused: {}", self.experiment_id, reason)

    def rollback(self, target_version: str | None = None) -> dict[str, Any]:
        """Rollback experiment to a previous version."""
        if target_version and self.previous_versions:
            for v in self.previous_versions:
                if v.get("version") == target_version:
                    rollback_data = {
                        "rolled_back_to": target_version,
                        "previous_status": self.status,
                        "timestamp": _utcnow(),
                    }
                    self.rollback_version = target_version
                    self.status = "deprecated"
                    self.updated_at = _utcnow()
                    logger.warning(
                        "Experiment {} rolled back to {}",
                        self.experiment_id, target_version,
                    )
                    return rollback_data

        self.rollback_version = self.rollback_version or "v0"
        self.status = "deprecated"
        self.updated_at = _utcnow()
        return {
            "rolled_back_to": self.rollback_version,
            "previous_status": self.status,
            "timestamp": _utcnow(),
        }

    def record_outcome(self, user_id: str, outcome: OutcomeVector) -> dict[str, Any]:
        """Record an outcome for this experiment."""
        self.current_episodes += 1
        if user_id not in self.distinct_users:
            self.distinct_users.append(user_id)
        self.outcome_history.append(outcome.to_dict())
        self.updated_at = _utcnow()

        guardrail_result = self.guardrails.check(
            [OutcomeVector.from_dict(o) for o in self.outcome_history[-20:]],
        )

        if guardrail_result["requires_stop"] or guardrail_result["requires_pause"]:
            self.pause("guardrail_triggered")

        return guardrail_result

    def is_promotable(self) -> tuple[bool, list[str]]:
        """Check if experiment meets promotion criteria."""
        reasons = []
        if self.current_episodes < self.min_episodes:
            reasons.append(f"episodes: {self.current_episodes}/{self.min_episodes}")
        if len(self.distinct_users) < self.min_distinct_users:
            reasons.append(f"users: {len(self.distinct_users)}/{self.min_distinct_users}")
        if self.status not in ("concluded",):
            reasons.append(f"status: {self.status} (need concluded)")
        if reasons:
            return False, reasons
        return True, []

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "hypothesis": self.hypothesis,
            "domain": self.domain,
            "status": self.status,
            "eligible_context": self.eligible_context,
            "excluded_context": self.excluded_context,
            "policies": self.policies,
            "assignment_mode": self.assignment_mode,
            "reward_model": self.reward_model.to_dict(),
            "guardrails": self.guardrails.to_dict(),
            "min_episodes": self.min_episodes,
            "min_distinct_users": self.min_distinct_users,
            "evidence_grade_required": self.evidence_grade_required,
            "current_episodes": self.current_episodes,
            "distinct_users": self.distinct_users,
            "kill_switch_key": self.kill_switch_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. SafeBanditController
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class BanditActionStats:
    """Stats for a candidate action in the bandit."""
    action_key: str
    mean_reward: float = 0.0
    variance: float = 0.0
    pull_count: int = 0
    risk_score: float = 0.0             # 0-1, higher = riskier
    confidence: float = 0.0             # 0-1, higher = more certain

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_key": self.action_key,
            "mean_reward": round(self.mean_reward, 4),
            "variance": round(self.variance, 4),
            "pull_count": self.pull_count,
            "risk_score": round(self.risk_score, 3),
            "confidence": round(self.confidence, 3),
        }


class SafeBanditController:
    """Risk-aware, human-in-the-loop contextual bandit.

    Key principle: exploration budget is gated by risk level. High-risk
    contexts → conservative policy only. Low-risk + high confidence → automatic.
    Low-risk + low confidence → explore with guardrails.

    This is NOT a greedy reward-maximization bandit. It's a safe,
    user-agency-preserving bandit that prioritizes user trust over
    statistical efficiency.
    """

    RISK_THRESHOLDS = {
        "low": {"auto_select": True, "explore_allowed": True, "min_confidence": 0.4},
        "medium": {"auto_select": True, "explore_allowed": True, "min_confidence": 0.6},
        "high": {"auto_select": True, "explore_allowed": False, "min_confidence": 0.8},
        "critical": {"auto_select": False, "explore_allowed": False, "min_confidence": 1.0},
    }

    def __init__(self):
        self.action_stats: dict[str, BanditActionStats] = {}

    def select_action(
        self,
        candidate_actions: list[str],
        *,
        context: ContextSignature,
        risk_level: str = "low",
        user_preference: str | None = None,
    ) -> dict[str, Any]:
        """Select best action given context risk and current knowledge.

        Args:
            candidate_actions: Available policy action keys
            context: Current context signature
            risk_level: "low" | "medium" | "high" | "critical"
            user_preference: Explicit user preference (overrides bandit)

        Returns:
            Decision with selected action, reason, exploration_allowed flag
        """
        # User preference always wins
        if user_preference and user_preference in candidate_actions:
            return {
                "selected_action": user_preference,
                "reason": "user_preference",
                "exploration_allowed": False,
                "confidence": 1.0,
            }

        thresholds = self.RISK_THRESHOLDS.get(risk_level, self.RISK_THRESHOLDS["low"])

        # Critical risk: always conservative
        if risk_level == "critical":
            return {
                "selected_action": candidate_actions[0] if candidate_actions else "",
                "reason": "critical_risk_conservative",
                "exploration_allowed": False,
                "confidence": 0.3,
            }

        # No stats yet → uniform random with low confidence
        if not self.action_stats:
            import random
            selected = random.choice(candidate_actions) if len(candidate_actions) > 1 else candidate_actions[0]
            return {
                "selected_action": selected,
                "reason": "cold_start_uniform",
                "exploration_allowed": thresholds["explore_allowed"],
                "confidence": 0.2,
            }

        # Get stats for candidates
        candidate_stats = [
            self.action_stats.get(a, BanditActionStats(action_key=a))
            for a in candidate_actions
        ]

        # Find best action by UCB (upper confidence bound) for exploration
        best_action = None
        best_score = float("-inf")
        for stats in candidate_stats:
            if stats.pull_count == 0:
                score = float("inf")  # Always explore unpulled actions
            else:
                # UCB1: mean + sqrt(2 * ln(total_pulls) / pulls)
                import math
                total_pulls = sum(s.pull_count for s in candidate_stats)
                exploration_bonus = math.sqrt(2 * math.log(max(total_pulls, 1)) / stats.pull_count)
                score = stats.mean_reward + exploration_bonus

            if score > best_score:
                best_score = score
                best_action = stats

        # Check confidence threshold
        if best_action and best_action.confidence >= thresholds["min_confidence"]:
            return {
                "selected_action": best_action.action_key,
                "reason": f"ucb_select_confidence_{best_action.confidence:.2f}",
                "exploration_allowed": thresholds["explore_allowed"],
                "confidence": best_action.confidence,
            }
        elif best_action and thresholds["explore_allowed"]:
            return {
                "selected_action": best_action.action_key,
                "reason": "explore_low_confidence",
                "exploration_allowed": True,
                "confidence": best_action.confidence,
            }
        else:
            # High risk + low confidence → conservative default
            return {
                "selected_action": candidate_actions[0] if candidate_actions else "",
                "reason": "high_risk_low_confidence_default",
                "exploration_allowed": False,
                "confidence": 0.3,
            }

    def update(
        self,
        action_key: str,
        reward: float,
        *,
        risk_level: str = "low",
    ) -> None:
        """Update action stats with a new observation."""
        if action_key not in self.action_stats:
            self.action_stats[action_key] = BanditActionStats(action_key=action_key)

        stats = self.action_stats[action_key]
        stats.pull_count += 1

        # Online mean/variance update (Welford)
        old_mean = stats.mean_reward
        stats.mean_reward += (reward - old_mean) / stats.pull_count
        if stats.pull_count > 1:
            stats.variance = (
                (stats.pull_count - 2) * stats.variance / (stats.pull_count - 1)
                + (reward - old_mean) * (reward - stats.mean_reward)
                / (stats.pull_count - 1)
            )

        # Confidence: higher with more pulls, penalized by variance
        stats.confidence = min(
            stats.pull_count / (stats.pull_count + 10),
            0.95,
        )
        if stats.variance > 0.1:
            stats.confidence *= 0.5

        # Risk score from variance + inverse confidence
        stats.risk_score = min(stats.variance + (1 - stats.confidence) * 0.5, 1.0)

    def get_best_action(self) -> dict[str, Any] | None:
        """Get the current best action by mean reward (≥5 pulls)."""
        qualified = [
            s for s in self.action_stats.values()
            if s.pull_count >= 5
        ]
        if not qualified:
            return None
        best = max(qualified, key=lambda s: s.mean_reward)
        return best.to_dict()

    def reset(self) -> None:
        """Reset all action stats."""
        self.action_stats.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": [s.to_dict() for s in self.action_stats.values()],
        }


# ═══════════════════════════════════════════════════════════════════════
# 5. SafeExperimentRegistry
# ═══════════════════════════════════════════════════════════════════════


class SafeExperimentRegistry:
    """Manage and audit safe experiments."""

    def __init__(self):
        self._experiments: dict[str, SafePolicyExperiment] = {}

    def register(self, experiment: SafePolicyExperiment) -> None:
        self._experiments[experiment.experiment_id] = experiment
        logger.info(
            "Experiment registered: {} status={} policies={}",
            experiment.experiment_id, experiment.status, len(experiment.policies),
        )

    def get(self, experiment_id: str) -> SafePolicyExperiment | None:
        return self._experiments.get(experiment_id)

    def list_by_status(self, status: str) -> list[SafePolicyExperiment]:
        return [e for e in self._experiments.values() if e.status == status]

    def list_active(self) -> list[SafePolicyExperiment]:
        return [
            e for e in self._experiments.values()
            if e.status in ("shadow", "canary", "safe_live")
        ]

    def list_by_domain(self, domain: str) -> list[SafePolicyExperiment]:
        return [e for e in self._experiments.values() if e.domain == domain]

    def pause_all_for_user_context(
        self,
        *,
        deadline_pressure: str = "critical",
    ) -> list[str]:
        """Pause all active experiments when user enters critical context."""
        paused_ids = []
        for exp in self.list_active():
            excluded = exp.excluded_context
            if "critical" in excluded or "D0" in excluded:
                exp.pause(f"critical_context: {deadline_pressure}")
                paused_ids.append(exp.experiment_id)
        return paused_ids

    def check_all_guardrails(
        self,
    ) -> dict[str, list[dict[str, Any]]]:
        """Check guardrails on all active experiments."""
        violations: dict[str, list[dict[str, Any]]] = {}
        for exp in self.list_active():
            recent_outcomes = [
                OutcomeVector.from_dict(o)
                for o in exp.outcome_history[-20:]
            ]
            result = exp.guardrails.check(recent_outcomes)
            if result["violations"]:
                violations[exp.experiment_id] = result["violations"]
        return violations

    def get_promotion_candidates(self) -> list[SafePolicyExperiment]:
        """Get all experiments ready for promotion."""
        return [
            e for e in self._experiments.values()
            if e.status == "concluded" and e.is_promotable()[0]
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_experiments": len(self._experiments),
            "by_status": {
                status: len(self.list_by_status(status))
                for status in EXPERIMENT_STAGES
            },
            "active_count": len(self.list_active()),
            "promotion_candidates": len(self.get_promotion_candidates()),
        }


# ═══════════════════════════════════════════════════════════════════════
# 6. Experiment Design Validator
# ═══════════════════════════════════════════════════════════════════════


class ExperimentDesignValidator:
    """Validate experiment design before it can start."""

    @staticmethod
    def validate(experiment: SafePolicyExperiment) -> dict[str, Any]:
        """Validate experiment design. Returns issues + eligibility."""
        issues = []

        if not experiment.name:
            issues.append("missing_name")
        if not experiment.hypothesis:
            issues.append("missing_hypothesis")
        if not experiment.domain:
            issues.append("missing_domain")
        if len(experiment.policies) < 2:
            issues.append("need_at_least_2_policies")

        for i, policy in enumerate(experiment.policies):
            if not policy.get("policy_key"):
                issues.append(f"policy_{i}_missing_key")
            if not policy.get("risk_level"):
                issues.append(f"policy_{i}_missing_risk_level")

        if not experiment.excluded_context:
            issues.append("no_excluded_context — safety concern")

        if not experiment.guardrails.fatigue_guard_required:
            issues.append("fatigue_guard_disabled")

        if not experiment.kill_switch_key:
            issues.append("missing_kill_switch")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "can_proceed_to_shadow": len(issues) == 0,
        }

    @staticmethod
    def check_risk_safety(
        experiment: SafePolicyExperiment,
        user_context: ContextSignature,
    ) -> dict[str, Any]:
        """Check if experiment is safe for a specific user context."""
        eligible, reason = experiment.guardrails.is_context_eligible(user_context)
        high_risk_policies = [
            p for p in experiment.policies
            if p.get("risk_level") in ("high", "critical")
        ]
        return {
            "safe_for_user": eligible,
            "reason": reason,
            "high_risk_policy_count": len(high_risk_policies),
            "recommendation": (
                "avoid" if high_risk_policies and user_context.deadline_pressure == "critical"
                else ("cautious" if high_risk_policies else "safe")
            ),
        }
