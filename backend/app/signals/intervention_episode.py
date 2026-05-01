"""
Core: execution / research
Phase: adapt
Stage: P4-0 — Evaluation-Grade Logging

Foundational evidence layer for all P4 research-grade capabilities.
Every strategy change produces an InterventionEpisode with full context,
candidate policies, selection probability, multi-dim outcome, and evidence quality.

Design principle:
  任何能改变用户下一步的策略，都必须先能被证据化、评估化、模拟化、风险分级化。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from loguru import logger


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. ContextSignature — 9-dim snapshot at decision time
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ContextSignature:
    """Frozen 9-dimension context snapshot at the moment of strategy selection.

    This is the matching key for counterfactual evaluation — each dimension
    narrows the comparison space.
    """
    goal_mode: str = ""                # "exam_rescue" | "standard_learning" | "project_delivery" | ...
    deadline_phase: str = ""            # "D-7" ~ "D-0"
    deadline_pressure: str = ""         # "low" | "medium" | "high" | "critical"
    knowledge_bottleneck: str = ""      # e.g. "cn.tcp.congestion_control"
    failure_type: str = ""              # "transfer_failure" | "knowledge_gap" | "timeout" | "overwhelm"
    cognitive_load: str = ""            # "low" | "medium" | "high"
    affective_pressure: str = ""        # "calm" | "tense" | "anxious" | "fatigued"
    relationship_stance: str = ""       # "trusted" | "neutral" | "strained" | "new"
    source_availability: str = ""       # "teacher_slides" | "past_exam" | "textbook" | "none"
    user_id: str = ""
    goal_id: str = ""
    timestamp: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_mode": self.goal_mode,
            "deadline_phase": self.deadline_phase,
            "deadline_pressure": self.deadline_pressure,
            "knowledge_bottleneck": self.knowledge_bottleneck,
            "failure_type": self.failure_type,
            "cognitive_load": self.cognitive_load,
            "affective_pressure": self.affective_pressure,
            "relationship_stance": self.relationship_stance,
            "source_availability": self.source_availability,
        }

    def distance_to(self, other: ContextSignature) -> float:
        """Compute normalized context distance (0-1) for matched evaluation.

        Each dimension contributes equally. Empty fields on both sides
        are treated as matching (no signal), but one-sided empty gets a penalty.
        """
        dims = [
            "goal_mode", "deadline_phase", "deadline_pressure",
            "failure_type", "cognitive_load", "affective_pressure",
            "relationship_stance", "source_availability",
        ]
        total = 0.0
        count = 0
        for dim in dims:
            a_val = getattr(self, dim, "")
            b_val = getattr(other, dim, "")
            count += 1
            if not a_val and not b_val:
                # Both empty → match (no signal to compare)
                total += 0.0
            elif a_val and b_val:
                total += 0.0 if a_val == b_val else 1.0
            else:
                # One has signal but the other doesn't → partial mismatch
                total += 0.5
        if count == 0:
            return 0.5
        return total / count

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextSignature:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════
# 2. OutcomeVector — 7-class multi-objective outcome
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ExecutionOutcome:
    started: bool = False
    completed: bool = False
    actual_duration_min: float = 0.0
    expected_duration_min: float = 0.0

    @property
    def time_overrun_ratio(self) -> float:
        if self.expected_duration_min <= 0:
            return 0.0
        return max(0.0, (self.actual_duration_min - self.expected_duration_min) / self.expected_duration_min)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started": self.started,
            "completed": self.completed,
            "actual_duration_min": self.actual_duration_min,
            "expected_duration_min": self.expected_duration_min,
        }


@dataclass
class LearningOutcome:
    quiz_accuracy: float = 0.0
    accuracy_delta_from_baseline: float = 0.0
    mistake_recurrence: bool = False
    transfer_success: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "quiz_accuracy": self.quiz_accuracy,
            "accuracy_delta_from_baseline": self.accuracy_delta_from_baseline,
            "mistake_recurrence": self.mistake_recurrence,
            "transfer_success": self.transfer_success,
        }


@dataclass
class GoalProgressOutcome:
    node_mastery_delta: float = 0.0
    exam_readiness_delta: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_mastery_delta": self.node_mastery_delta,
            "exam_readiness_delta": self.exam_readiness_delta,
        }


@dataclass
class AgencyOutcome:
    user_accepted_strategy: bool = True
    user_corrected_system: bool = False
    user_overrode_policy: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_accepted_strategy": self.user_accepted_strategy,
            "user_corrected_system": self.user_corrected_system,
            "user_overrode_policy": self.user_overrode_policy,
        }


@dataclass
class LoadOutcome:
    cognitive_load_after: str = ""     # "low" | "medium" | "high"
    affective_pressure_after: str = "" # "calm" | "tense" | "anxious"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cognitive_load_after": self.cognitive_load_after,
            "affective_pressure_after": self.affective_pressure_after,
        }


@dataclass
class TrustOutcome:
    explicit_negative_feedback: bool = False
    receipt_dismissed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "explicit_negative_feedback": self.explicit_negative_feedback,
            "receipt_dismissed": self.receipt_dismissed,
        }


@dataclass
class SustainabilityOutcome:
    returned_next_day: bool | None = None
    continued_sequence: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "returned_next_day": self.returned_next_day,
            "continued_sequence": self.continued_sequence,
        }


@dataclass
class OutcomeVector:
    """7-class multi-objective outcome.

    P4 evaluates strategies on ALL dimensions, not just task completion.
    This prevents the system from optimizing for "easy tasks completed."
    """
    execution: ExecutionOutcome = field(default_factory=ExecutionOutcome)
    learning: LearningOutcome = field(default_factory=LearningOutcome)
    goal_progress: GoalProgressOutcome = field(default_factory=GoalProgressOutcome)
    agency: AgencyOutcome = field(default_factory=AgencyOutcome)
    load: LoadOutcome = field(default_factory=LoadOutcome)
    trust: TrustOutcome = field(default_factory=TrustOutcome)
    sustainability: SustainabilityOutcome = field(default_factory=SustainabilityOutcome)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution": self.execution.to_dict(),
            "learning": self.learning.to_dict(),
            "goal_progress": self.goal_progress.to_dict(),
            "agency": self.agency.to_dict(),
            "load": self.load.to_dict(),
            "trust": self.trust.to_dict(),
            "sustainability": self.sustainability.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OutcomeVector:
        return cls(
            execution=ExecutionOutcome(**d.get("execution", {})),
            learning=LearningOutcome(**d.get("learning", {})),
            goal_progress=GoalProgressOutcome(**d.get("goal_progress", {})),
            agency=AgencyOutcome(**d.get("agency", {})),
            load=LoadOutcome(**d.get("load", {})),
            trust=TrustOutcome(**d.get("trust", {})),
            sustainability=SustainabilityOutcome(**d.get("sustainability", {})),
        )

    def compute_primary_reward(self, weights: dict[str, float] | None = None) -> float:
        """Compute weighted primary reward from multi-objective outcome.

        Default weights prioritize goal progress + learning over completion.
        """
        w = weights or {
            "goal_progress": 0.35,
            "learning": 0.25,
            "execution_completion": 0.15,
            "sustainability": 0.10,
            "trust": 0.10,
            "agency": 0.05,
        }
        score = 0.0
        score += w.get("goal_progress", 0.35) * (
            self.goal_progress.node_mastery_delta + self.goal_progress.exam_readiness_delta
        ) / 2.0
        score += w.get("learning", 0.25) * max(0.0, self.learning.accuracy_delta_from_baseline + 0.5)
        score += w.get("execution_completion", 0.15) * (1.0 if self.execution.completed else 0.0)
        score += w.get("sustainability", 0.10) * (1.0 if self.sustainability.continued_sequence else 0.0)
        score += w.get("trust", 0.10) * (0.0 if self.trust.explicit_negative_feedback else 1.0)
        score += w.get("agency", 0.05) * (0.0 if self.agency.user_corrected_system else 1.0)
        return round(score, 4)

    def has_guardrail_violation(self) -> tuple[bool, list[str]]:
        """Check if any guardrail metric violated (negative feedback, fatigue, agency loss, trust drop)."""
        violations = []
        if self.trust.explicit_negative_feedback:
            violations.append("negative_feedback")
        if self.load.cognitive_load_after == "high" or self.load.affective_pressure_after == "anxious":
            violations.append("fatigue_increased")
        if self.agency.user_corrected_system:
            violations.append("user_agency_loss")
        if self.trust.receipt_dismissed:
            violations.append("trust_drop")
        return len(violations) > 0, violations


# ═══════════════════════════════════════════════════════════════════════
# 3. EvidenceQuality
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class EvidenceQuality:
    """Meta-assessment of whether the episode data supports evaluation."""
    propensity_logged: bool = False
    counterfactual_candidates_logged: bool = False
    outcome_complete: bool = False
    user_feedback_present: bool = False

    @property
    def grade(self) -> int:
        """Evidence grade (0-4) based on what was logged.

        Grade 0: anecdotal (nothing logged)
        Grade 1: trace-supported (outcome only)
        Grade 2: matched-context (outcome + context)
        Grade 3: propensity-aware (+ selection_probability + candidates)
        Grade 4: doubly-robust-ready (all fields complete)
        """
        if not self.outcome_complete:
            return 0
        score = 1
        if self.user_feedback_present:
            score += 1
        if self.propensity_logged:
            score += 1
        if self.counterfactual_candidates_logged:
            score += 1
        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "propensity_logged": self.propensity_logged,
            "counterfactual_candidates_logged": self.counterfactual_candidates_logged,
            "outcome_complete": self.outcome_complete,
            "user_feedback_present": self.user_feedback_present,
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. InterventionEpisode — core evidence unit
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class InterventionEpisode:
    """The core research-grade evidence unit.

    Every strategic change produces one episode. This is the atomic record
    for counterfactual evaluation, policy comparison, and safe adaptation.

    iron_law: episodes without candidate_policies cannot support OPE (Grade < 3).
    """
    episode_id: str = ""
    user_id: str = ""
    goal_id: str = ""
    domain: str = ""                          # "exam_sprint" | "project_delivery" | ...
    timestamp: str = field(default_factory=_utcnow)

    context_signature: ContextSignature = field(default_factory=ContextSignature)
    candidate_policies: list[str] = field(default_factory=list)
    selected_policy: str = ""
    selection_reason: str = ""
    selection_mode: str = ""                 # "rule_based" | "learning_bias" | "shadow_experiment" | "bandit" | "human_override"
    selection_confidence: float = 0.0
    selection_probability: float = 1.0       # P(selected_policy | context) — required for IPS/SNIPS
    risk_level: str = "low"                  # "low" | "medium" | "high" | "critical"
    directive_ids: list[str] = field(default_factory=list)
    outcome_vector: OutcomeVector = field(default_factory=OutcomeVector)
    evidence_quality: EvidenceQuality = field(default_factory=EvidenceQuality)

    def __post_init__(self):
        if not self.episode_id:
            self.episode_id = _uid("ep")

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "user_id": self.user_id,
            "goal_id": self.goal_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "context_signature": self.context_signature.to_dict(),
            "candidate_policies": self.candidate_policies,
            "selected_policy": self.selected_policy,
            "selection_reason": self.selection_reason,
            "selection_mode": self.selection_mode,
            "selection_confidence": self.selection_confidence,
            "selection_probability": self.selection_probability,
            "risk_level": self.risk_level,
            "directive_ids": self.directive_ids,
            "outcome_vector": self.outcome_vector.to_dict(),
            "evidence_quality": self.evidence_quality.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> InterventionEpisode:
        return cls(
            episode_id=d.get("episode_id", ""),
            user_id=d.get("user_id", ""),
            goal_id=d.get("goal_id", ""),
            domain=d.get("domain", ""),
            timestamp=d.get("timestamp", ""),
            context_signature=ContextSignature.from_dict(d.get("context_signature", {})),
            candidate_policies=d.get("candidate_policies", []),
            selected_policy=d.get("selected_policy", ""),
            selection_reason=d.get("selection_reason", ""),
            selection_mode=d.get("selection_mode", ""),
            selection_confidence=d.get("selection_confidence", 0.0),
            selection_probability=d.get("selection_probability", 1.0),
            risk_level=d.get("risk_level", "low"),
            directive_ids=d.get("directive_ids", []),
            outcome_vector=OutcomeVector.from_dict(d.get("outcome_vector", {})),
            evidence_quality=EvidenceQuality(**d.get("evidence_quality", {})),
        )


# ═══════════════════════════════════════════════════════════════════════
# 5. InterventionEpisodeLedger — management layer
# ═══════════════════════════════════════════════════════════════════════


class InterventionEpisodeLedger:
    """Manage intervention episodes for research-grade evaluation.

    All operations are pure computation; persistence is via caller.
    """

    @staticmethod
    def validate_integrity(episode: InterventionEpisode) -> EvidenceQuality:
        """Validate episode data integrity and compute EvidenceQuality.

        Episodes missing candidate_policies or selection_probability
        cannot support OPE and are capped at grade < 3.
        """
        eq = EvidenceQuality()
        eq.propensity_logged = (
            episode.selection_probability < 1.0
            or len(episode.candidate_policies) > 1
        )
        eq.counterfactual_candidates_logged = len(episode.candidate_policies) > 0
        eq.outcome_complete = False  # No outcome yet at creation time
        eq.user_feedback_present = False

        # Iron law: episodes without candidate_policies cannot support OPE.
        # Force propensity_logged=False if no candidates exist.
        if not episode.candidate_policies:
            eq.propensity_logged = False
            eq.counterfactual_candidates_logged = False

        return eq

    @staticmethod
    def create_episode(
        *,
        user_id: str,
        goal_id: str,
        domain: str,
        context_signature: ContextSignature,
        candidate_policies: list[str],
        selected_policy: str,
        selection_reason: str = "",
        selection_mode: str = "rule_based",
        selection_confidence: float = 0.5,
        selection_probability: float = 1.0,
        risk_level: str = "low",
        directive_ids: list[str] | None = None,
    ) -> InterventionEpisode:
        """Create a new intervention episode at decision time.

        selection_probability is critical: it must reflect the true probability
        that this policy was selected from the candidate set. Without it,
        IPS/SNIPS offline evaluation is impossible.
        """
        episode = InterventionEpisode(
            episode_id=_uid("ep"),
            user_id=user_id,
            goal_id=goal_id,
            domain=domain,
            context_signature=context_signature,
            candidate_policies=candidate_policies,
            selected_policy=selected_policy,
            selection_reason=selection_reason,
            selection_mode=selection_mode,
            selection_confidence=selection_confidence,
            selection_probability=selection_probability,
            risk_level=risk_level,
            directive_ids=directive_ids or [],
        )

        logger.info(
            "InterventionEpisode: {} policy={} mode={} candidates={} risk={}",
            episode.episode_id, selected_policy, selection_mode,
            len(candidate_policies), risk_level,
        )
        return episode

    @staticmethod
    def record_outcome(
        episode: InterventionEpisode,
        outcome_vector: OutcomeVector,
    ) -> InterventionEpisode:
        """Record the measured outcome for an episode.

        After this call, the episode is evaluation-ready.
        """
        episode.outcome_vector = outcome_vector

        # Auto-grade evidence quality
        eq = EvidenceQuality()
        eq.propensity_logged = episode.selection_probability < 1.0 or len(episode.candidate_policies) > 1
        eq.counterfactual_candidates_logged = len(episode.candidate_policies) > 0
        eq.outcome_complete = (
            outcome_vector.execution.completed is not None
            or outcome_vector.learning.accuracy_delta_from_baseline != 0.0
            or outcome_vector.goal_progress.node_mastery_delta != 0.0
        )
        eq.user_feedback_present = (
            outcome_vector.agency.user_corrected_system
            or outcome_vector.trust.explicit_negative_feedback
        )
        episode.evidence_quality = eq

        logger.info(
            "InterventionEpisode {} outcome recorded — evidence_grade={}",
            episode.episode_id, eq.grade,
        )
        return episode

    @staticmethod
    def find_similar_episodes(
        target: InterventionEpisode,
        pool: list[InterventionEpisode],
        *,
        max_distance: float = 0.3,
        min_count: int = 1,
    ) -> list[InterventionEpisode]:
        """Find episodes with similar context_signature for matched evaluation."""
        matches = []
        for ep in pool:
            if ep.episode_id == target.episode_id:
                continue
            dist = target.context_signature.distance_to(ep.context_signature)
            if dist <= max_distance:
                matches.append((dist, ep))

        matches.sort(key=lambda x: x[0])
        result = [ep for _, ep in matches]
        return result if len(result) >= min_count else []

    @staticmethod
    def group_by_policy(
        episodes: list[InterventionEpisode],
    ) -> dict[str, list[InterventionEpisode]]:
        """Group episodes by selected_policy for stratified comparison."""
        groups: dict[str, list[InterventionEpisode]] = {}
        for ep in episodes:
            policy = ep.selected_policy
            if policy not in groups:
                groups[policy] = []
            groups[policy].append(ep)
        return groups

    @staticmethod
    def compute_policy_stats(
        episodes: list[InterventionEpisode],
    ) -> dict[str, Any]:
        """Compute aggregate statistics for a set of episodes sharing a policy."""
        if not episodes:
            return {"episode_count": 0}

        n = len(episodes)
        completion_rate = sum(1 for e in episodes if e.outcome_vector.execution.completed) / n
        avg_accuracy_delta = sum(
            e.outcome_vector.learning.accuracy_delta_from_baseline for e in episodes
        ) / n
        avg_mastery_delta = sum(
            e.outcome_vector.goal_progress.node_mastery_delta for e in episodes
        ) / n
        correction_rate = sum(1 for e in episodes if e.outcome_vector.agency.user_corrected_system) / n
        negative_feedback_rate = sum(
            1 for e in episodes if e.outcome_vector.trust.explicit_negative_feedback
        ) / n

        return {
            "episode_count": n,
            "completion_rate": round(completion_rate, 3),
            "avg_accuracy_delta": round(avg_accuracy_delta, 3),
            "avg_mastery_delta": round(avg_mastery_delta, 3),
            "correction_rate": round(correction_rate, 3),
            "negative_feedback_rate": round(negative_feedback_rate, 3),
        }

    @staticmethod
    def compute_stratified_stats(
        episodes: list[InterventionEpisode],
        *,
        stratify_by: str = "failure_type",
    ) -> dict[str, dict[str, Any]]:
        """Compute policy stats stratified by context dimension."""
        strata: dict[str, list[InterventionEpisode]] = {}
        for ep in episodes:
            key = getattr(ep.context_signature, stratify_by, "unknown") or "unknown"
            if key not in strata:
                strata[key] = []
            strata[key].append(ep)

        return {
            key: InterventionEpisodeLedger.compute_policy_stats(group)
            for key, group in strata.items()
        }

    @staticmethod
    def filter_grade(
        episodes: list[InterventionEpisode],
        min_grade: int = 2,
    ) -> list[InterventionEpisode]:
        """Filter episodes by minimum evidence grade."""
        return [e for e in episodes if e.evidence_quality.grade >= min_grade]

    @staticmethod
    def compute_effect_size(
        policy_a_episodes: list[InterventionEpisode],
        policy_b_episodes: list[InterventionEpisode],
        *,
        metric: str = "completion_rate",
    ) -> dict[str, Any]:
        """Compute raw effect size between two policies for a given metric."""
        stats_a = InterventionEpisodeLedger.compute_policy_stats(policy_a_episodes)
        stats_b = InterventionEpisodeLedger.compute_policy_stats(policy_b_episodes)

        if stats_a["episode_count"] == 0 or stats_b["episode_count"] == 0:
            return {"effect_size": 0.0, "confidence": 0.0, "reason": "insufficient_data"}

        metric_map = {
            "completion_rate": "completion_rate",
            "avg_accuracy_delta": "avg_accuracy_delta",
            "avg_mastery_delta": "avg_mastery_delta",
        }
        key = metric_map.get(metric, "completion_rate")
        delta = stats_a[key] - stats_b[key]

        # Simple confidence: higher when both sides have more episodes
        min_n = min(stats_a["episode_count"], stats_b["episode_count"])
        confidence = min(min_n / 30.0, 1.0)

        return {
            "metric": metric,
            "policy_a_value": stats_a[key],
            "policy_b_value": stats_b[key],
            "effect_size": round(delta, 4),
            "episodes_a": stats_a["episode_count"],
            "episodes_b": stats_b["episode_count"],
            "confidence": round(confidence, 3),
            "direction": "a_better" if delta > 0 else ("b_better" if delta < 0 else "no_difference"),
        }

    @staticmethod
    def estimate_required_samples(
        episodes: list[InterventionEpisode],
        *,
        min_effect_size: float = 0.1,
        power: float = 0.8,
    ) -> dict[str, Any]:
        """Estimate how many more episodes are needed for conclusive evaluation.

        Uses a simplified power analysis based on observed variance.
        """
        n = len(episodes)
        if n < 2:
            return {"current_episodes": n, "estimated_needed": max(30, int(2 / min_effect_size ** 2)), "sufficient": False}

        completions = [1.0 if e.outcome_vector.execution.completed else 0.0 for e in episodes]
        avg = sum(completions) / n
        variance = sum((x - avg) ** 2 for x in completions) / (n - 1) if n > 1 else 0.25

        # Simplified: n ≈ (z_α/2 + z_β)² * σ² / δ²
        # z_0.025 ≈ 1.96, z_0.2 ≈ 0.84 (for power=0.8)
        import math
        z_alpha = 1.96
        z_beta = 0.84
        if min_effect_size <= 0:
            needed = 1000
        else:
            needed = int(math.ceil((z_alpha + z_beta) ** 2 * variance / (min_effect_size ** 2)))

        return {
            "current_episodes": n,
            "estimated_needed": needed,
            "sufficient": n >= needed,
            "observed_variance": round(variance, 4),
            "min_effect_size": min_effect_size,
        }
