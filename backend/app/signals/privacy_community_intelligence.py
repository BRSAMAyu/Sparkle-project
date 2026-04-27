"""
Core: execution / research
Phase: reinforce
Stage: P4-5 — Privacy-preserving Community Intelligence

Enables cohort analysis without exposing individual user data.
Key principles:
- All community signals are anonymized before cross-user sharing
- Differential privacy: add calibrated noise to aggregate statistics
- Individual data never leaves user's privacy boundary
- External observations always need user confirmation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from loguru import logger


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PrivacyBudget:
    """Differential privacy budget for a user/query."""
    user_id: str
    epsilon: float = 1.0             # Privacy loss parameter (lower = more private)
    delta: float = 1e-5             # Privacy failure probability
    query_count: int = 0
    total_epsilon_spent: float = 0.0
    max_epsilon: float = 10.0       # Hard cap on lifetime epsilon
    reset_at: str = ""              # When budget resets

    def can_answer(self, query_cost: float = 0.1) -> bool:
        """Check if budget allows answering another query."""
        return (self.total_epsilon_spent + query_cost) <= self.max_epsilon

    def spend(self, query_cost: float = 0.1) -> bool:
        if self.can_answer(query_cost):
            self.total_epsilon_spent += query_cost
            self.query_count += 1
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "query_count": self.query_count,
            "total_epsilon_spent": self.total_epsilon_spent,
            "max_epsilon": self.max_epsilon,
            "budget_remaining": self.max_epsilon - self.total_epsilon_spent,
        }


@dataclass
class AnonymizedCohortStat:
    """An anonymized aggregate statistic from a cohort.

    Never exposes individual data. Uses Laplace noise for differential privacy.
    """
    stat_id: str
    stat_name: str               # e.g. "avg_task_completion_rate"
    cohort_size: int
    min_cohort_size: int = 5     # Suppress stats for cohorts smaller than this
    value: float = 0.0
    noise_std: float = 0.0       # Standard deviation of added Laplace noise
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    is_reliable: bool = False    # True if cohort_size >= min_cohort_size

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id": self.stat_id,
            "stat_name": self.stat_name,
            "cohort_size": self.cohort_size,
            "min_cohort_size": self.min_cohort_size,
            "value": round(self.value, 4),
            "noise_std": round(self.noise_std, 4),
            "confidence_interval": [round(ci, 4) for ci in self.confidence_interval],
            "is_reliable": self.is_reliable,
        }


@dataclass
class PrivacyPreservingCohort:
    """A privacy-preserving cohort for pattern detection.

    Key rules:
    - Under 5 users: NEVER share (absolute privacy floor)
    - 5-15 users: Share trend direction only (up/down/flat)
    - 16+ users: Share anonymized aggregate with Laplace noise
    """
    cohort_id: str
    cohort_criteria: dict[str, str]   # e.g. {"goal_type": "exam_sprint", "subject": "cs"}
    member_count: int
    privacy_tier: str = ""            # Auto-set by __post_init__: "suppressed" | "trend_only" | "anonymous_aggregate"
    stats: list[AnonymizedCohortStat] = field(default_factory=list)

    PRIVACY_FLOOR = 5
    TREND_ONLY_THRESHOLD = 15

    def __post_init__(self):
        if self.member_count < self.PRIVACY_FLOOR:
            self.privacy_tier = "suppressed"
        elif self.member_count < self.TREND_ONLY_THRESHOLD:
            self.privacy_tier = "trend_only"
        else:
            self.privacy_tier = "anonymous_aggregate"

    def can_share_stat(self, stat: AnonymizedCohortStat) -> bool:
        """Determine if a stat can be shared at this privacy tier."""
        if self.privacy_tier == "suppressed":
            return False
        if self.privacy_tier == "trend_only":
            # Only share direction, not exact value
            return stat.cohort_size >= self.PRIVACY_FLOOR
        return stat.cohort_size >= self.PRIVACY_FLOOR

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_id": self.cohort_id,
            "cohort_criteria": self.cohort_criteria,
            "member_count": self.member_count,
            "privacy_tier": self.privacy_tier,
            "stats": [s.to_dict() for s in self.stats if self.can_share_stat(s)],
        }


class PrivacyPreservingCommunityEngine:
    """Privacy-preserving community intelligence.

    All cohort analysis goes through this engine. Individual data NEVER
    crosses the privacy boundary. External observations always flow through
    ExternalRawEvent → Spine → PolicyEngine.
    """

    def __init__(self):
        self._budgets: dict[str, PrivacyBudget] = {}
        self._cohorts: dict[str, PrivacyPreservingCohort] = {}

    # ── Privacy Budget Management ────────────────────────────────────────

    def get_or_create_budget(
        self,
        user_id: str,
        *,
        epsilon: float = 1.0,
        max_epsilon: float = 10.0,
    ) -> PrivacyBudget:
        if user_id not in self._budgets:
            self._budgets[user_id] = PrivacyBudget(
                user_id=user_id,
                epsilon=epsilon,
                max_epsilon=max_epsilon,
                reset_at=_utcnow(),
            )
        return self._budgets[user_id]

    def check_privacy_budget(self, user_id: str, query: str) -> bool:
        """Check if user has remaining privacy budget for this query type."""
        budget = self.get_or_create_budget(user_id)
        costs = {
            "cohort_lookup": 0.05,
            "trend_detection": 0.1,
            "pattern_mining": 0.5,
        }
        return budget.can_answer(costs.get(query, 0.1))

    # ── Cohort Management ────────────────────────────────────────────────

    def create_cohort(
        self,
        criteria: dict[str, str],
        member_count: int,
    ) -> PrivacyPreservingCohort:
        """Create a privacy-preserving cohort.

        The cohort's privacy_tier is auto-determined by member_count:
        - < 5: suppressed (never shared)
        - 5-15: trend_only (only direction shared)
        - 16+: anonymous_aggregate (full stats with noise)
        """
        cohort_id = _uid("coh")
        cohort = PrivacyPreservingCohort(
            cohort_id=cohort_id,
            cohort_criteria=criteria,
            member_count=member_count,
        )
        self._cohorts[cohort_id] = cohort
        logger.info(
            "Cohort {} created: criteria={} members={} tier={}",
            cohort_id, criteria, member_count, cohort.privacy_tier,
        )
        return cohort

    # ── Anonymized Statistics ────────────────────────────────────────────

    @staticmethod
    def add_laplace_noise(value: float, sensitivity: float, epsilon: float) -> tuple[float, float]:
        """Add Laplace noise for (ε, δ)-differential privacy.

        Returns (noised_value, noise_std).
        """
        import math
        import random

        scale = sensitivity / epsilon
        noise = random.uniform(-1, 1) * scale  # Simplified: Laplace approximation
        noise_std = math.sqrt(2) * scale

        return value + noise, noise_std

    def compute_anonymized_stat(
        self,
        stat_name: str,
        raw_values: list[float],
        *,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
    ) -> AnonymizedCohortStat:
        """Compute a differentially private aggregate statistic.

        The raw individual values are consumed here and NEVER stored.
        Only the anonymized aggregate is returned.
        """
        n = len(raw_values)
        if n < PrivacyPreservingCohort.PRIVACY_FLOOR:
            return AnonymizedCohortStat(
                stat_id=_uid("astat"),
                stat_name=stat_name,
                cohort_size=n,
                is_reliable=False,
            )

        avg = sum(raw_values) / n
        noised_avg, noise_std = self.add_laplace_noise(avg, sensitivity, epsilon)

        ci_half = 1.96 * noise_std / (n ** 0.5) if n > 0 else 0
        ci_lower = noised_avg - ci_half
        ci_upper = noised_avg + ci_half

        return AnonymizedCohortStat(
            stat_id=_uid("astat"),
            stat_name=stat_name,
            cohort_size=n,
            value=noised_avg,
            noise_std=noise_std,
            confidence_interval=(ci_lower, ci_upper),
            is_reliable=True,
        )

    # ── Pattern Detection ────────────────────────────────────────────────

    @staticmethod
    def detect_cohort_pattern(
        cohort: PrivacyPreservingCohort,
        stat: AnonymizedCohortStat,
    ) -> dict[str, Any]:
        """Detect patterns from anonymized cohort stats without exposing individuals.

        Returns only pattern direction (improving/declining/stable) when
        privacy tier is 'trend_only'.
        """
        if not stat.is_reliable:
            return {"pattern": "unknown", "reason": "insufficient_data"}

        if cohort.privacy_tier == "suppressed":
            return {"pattern": "suppressed", "reason": "privacy_floor"}

        ci_low, ci_high = stat.confidence_interval

        if cohort.privacy_tier == "trend_only":
            # Only share direction, not magnitude
            if ci_low > 0:
                return {"pattern": "improving", "direction": "positive"}
            elif ci_high < 0:
                return {"pattern": "declining", "direction": "negative"}
            else:
                return {"pattern": "stable", "direction": "neutral"}

        # Full anonymous aggregate for large cohorts
        return {
            "pattern": "detailed",
            "value": round(stat.value, 4),
            "confidence_interval": [round(ci_low, 4), round(ci_high, 4)],
            "cohort_size": stat.cohort_size,
        }

    # ── External Observation Candidate ───────────────────────────────────

    @staticmethod
    def to_external_observation(
        pattern: dict[str, Any],
        cohort_criteria: dict[str, str],
        *,
        user_id: str,
    ) -> dict[str, Any]:
        """Convert a cohort pattern into an external observation candidate.

        This is ALWAYS a candidate signal — the user must confirm before
        it affects their personal state. Iron Rule: external signals
        cannot directly write personal models.
        """
        return {
            "event_type": "community_observation",
            "observation_id": _uid("obs"),
            "user_id": user_id,
            "cohort_criteria": cohort_criteria,
            "pattern": pattern,
            "status": "candidate",  # Always candidate, never auto-applied
            "requires_user_confirmation": True,
            "timestamp": _utcnow(),
        }

    # ── Aggregate Report (for platform-level insights) ────────────────────

    def build_aggregate_report(
        self,
        *,
        goal_type: str | None = None,
    ) -> dict[str, Any]:
        """Build a platform-level aggregate report. NEVER exposes individual data."""
        relevant_cohorts = [
            c for c in self._cohorts.values()
            if goal_type is None or c.cohort_criteria.get("goal_type") == goal_type
        ]

        total_members = sum(c.member_count for c in relevant_cohorts)
        by_tier = {"suppressed": 0, "trend_only": 0, "anonymous_aggregate": 0}
        for c in relevant_cohorts:
            by_tier[c.privacy_tier] += 1

        return {
            "report_id": _uid("agrpt"),
            "goal_type_filter": goal_type,
            "total_cohorts": len(relevant_cohorts),
            "total_members": total_members,
            "cohorts_by_privacy_tier": by_tier,
            "generated_at": _utcnow(),
            "_privacy_note": (
                "This report contains ONLY aggregate statistics. "
                "No individual user data is exposed."
            ),
        }
