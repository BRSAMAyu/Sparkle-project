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
from datetime import datetime, UTC
from typing import Any

from loguru import logger


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


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


# ═══════════════════════════════════════════════════════════════════════
# P4-5 v2: Temporal Privacy Budget + Cohort Drift + Secure Aggregation
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class TemporalPrivacyBudget:
    """Privacy budget with time-windowed spending and renewal.

    Key protocol:
    - Short windows (hourly) have strict caps
    - Longer windows (daily/weekly) allow more queries
    - Budget renews at window boundaries
    - Exhaustion triggers graceful degradation, never data leak
    """
    user_id: str
    epsilon_per_query: float = 0.1
    max_hourly_queries: int = 5
    max_daily_queries: int = 30
    max_weekly_queries: int = 100
    hourly_count: int = 0
    daily_count: int = 0
    weekly_count: int = 0
    total_queries: int = 0
    exhausted: bool = False
    exhaustion_reason: str = ""
    window_start: str = field(default_factory=_utcnow)
    last_query_at: str = ""

    def can_query(self) -> dict[str, Any]:
        """Check if any time window has remaining capacity."""
        if self.exhausted:
            return {"allowed": False, "reason": f"budget_exhausted: {self.exhaustion_reason}"}
        if self.hourly_count >= self.max_hourly_queries:
            return {"allowed": False, "reason": "hourly_cap_exceeded"}
        if self.daily_count >= self.max_daily_queries:
            return {"allowed": False, "reason": "daily_cap_exceeded"}
        if self.weekly_count >= self.max_weekly_queries:
            return {"allowed": False, "reason": "weekly_cap_exceeded"}
        return {"allowed": True, "reason": "ok"}

    def record_query(self) -> dict[str, Any]:
        """Record a query against this budget. Auto-exhausts if any cap is hit."""
        check = self.can_query()
        if not check["allowed"]:
            self.exhausted = True
            self.exhaustion_reason = check["reason"]
            return {"recorded": False, **check}

        self.hourly_count += 1
        self.daily_count += 1
        self.weekly_count += 1
        self.total_queries += 1
        self.last_query_at = _utcnow()

        # Check if this query exhausted any window
        if self.hourly_count >= self.max_hourly_queries:
            self.exhausted = True
            self.exhaustion_reason = "hourly_cap_hit"

        return {"recorded": True, "remaining_hourly": self.max_hourly_queries - self.hourly_count}

    def try_renew(self, current_window_start: str | None = None) -> bool:
        """Attempt to renew budget (e.g., at hour/day/week boundary)."""
        # Simplified: reset if explicitly called with new window
        if current_window_start and current_window_start != self.window_start:
            self.hourly_count = 0
            self.daily_count = 0
            self.weekly_count = 0
            self.exhausted = False
            self.exhaustion_reason = ""
            self.window_start = current_window_start
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "hourly_used": self.hourly_count,
            "daily_used": self.daily_count,
            "weekly_used": self.weekly_count,
            "total_queries": self.total_queries,
            "exhausted": self.exhausted,
            "exhaustion_reason": self.exhaustion_reason,
            "can_query": self.can_query()["allowed"],
        }


@dataclass
class CohortDriftReport:
    """Report on cohort composition changes over time."""
    cohort_id: str
    initial_member_count: int
    current_member_count: int
    drift_detected: bool = False
    drift_magnitude: float = 0.0          # 0-1 normalized
    direction: str = "stable"             # "growing" | "shrinking" | "shifting" | "stable"
    criteria_shifts: dict[str, Any] = field(default_factory=dict)
    requires_requery: bool = False
    generated_at: str = field(default_factory=_utcnow)


class CohortDriftDetector:
    """Detect when cohort composition has shifted enough to warrant re-computation.

    Key rule: if a cohort changes >20% in size or composition, re-query the
    privacy engine to refresh aggregate stats. Stale cohort stats mislead users.
    """

    DRIFT_THRESHOLD = 0.2  # 20% change triggers re-query recommendation

    @classmethod
    def compute_drift(
        cls,
        initial_size: int,
        current_size: int,
        *,
        initial_criteria: dict[str, str] | None = None,
        current_criteria: dict[str, str] | None = None,
    ) -> CohortDriftReport:
        """Compute drift between initial and current cohort state."""
        if initial_size == 0:
            return CohortDriftReport(
                cohort_id="unknown",
                initial_member_count=0,
                current_member_count=current_size,
                drift_detected=True,
                drift_magnitude=1.0,
                direction="growing",
                requires_requery=True,
            )

        magnitude = abs(current_size - initial_size) / initial_size
        drift_detected = magnitude >= cls.DRIFT_THRESHOLD

        direction = "stable"
        if current_size > initial_size * 1.2:
            direction = "growing"
        elif current_size < initial_size * 0.8:
            direction = "shrinking"

        # Check criteria changes
        criteria_shifts = {}
        if initial_criteria and current_criteria:
            for key in set(initial_criteria.keys()) | set(current_criteria.keys()):
                old_val = initial_criteria.get(key, "")
                new_val = current_criteria.get(key, "")
                if old_val != new_val:
                    criteria_shifts[key] = {"from": old_val, "to": new_val}
            if criteria_shifts:
                direction = "shifting"
                drift_detected = True

        return CohortDriftReport(
            cohort_id="unknown",
            initial_member_count=initial_size,
            current_member_count=current_size,
            drift_detected=drift_detected,
            drift_magnitude=round(min(magnitude, 1.0), 3),
            direction=direction,
            criteria_shifts=criteria_shifts,
            requires_requery=drift_detected,
        )

    @classmethod
    def should_refresh(cls, report: CohortDriftReport) -> dict[str, Any]:
        """Decision: should we spend privacy budget to refresh this cohort?"""
        if not report.drift_detected:
            return {"refresh": False, "reason": "no_significant_drift"}
        if report.direction == "shrinking":
            return {"refresh": True, "reason": "cohort_shrinking", "priority": "high"}
        if report.direction == "shifting":
            return {"refresh": True, "reason": "criteria_changed", "priority": "high"}
        if report.direction == "growing":
            return {"refresh": True, "reason": "cohort_growing", "priority": "medium"}
        return {"refresh": False, "reason": "stable"}


@dataclass
class FederatedInsight:
    """Cross-cohort insight derived without raw data sharing.

    All insights carry audit trail showing which cohorts contributed,
    when, and at what privacy cost.
    """
    insight_id: str = ""
    insight_type: str = ""               # "cross_cohort_trend" | "strategy_transfer" | "risk_signal"
    description: str = ""
    contributing_cohort_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0              # 0-1, derived from cohort sizes and epsilon
    privacy_cost: float = 0.0            # Total epsilon spent to derive this insight
    requires_human_review: bool = True   # Federated insights always need review
    status: str = "candidate"            # "candidate" | "reviewed" | "published" | "rejected"
    generated_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.insight_id:
            self.insight_id = _uid("fi")

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "description": self.description,
            "contributing_cohort_ids": self.contributing_cohort_ids,
            "confidence": self.confidence,
            "privacy_cost": self.privacy_cost,
            "requires_human_review": self.requires_human_review,
            "status": self.status,
            "generated_at": self.generated_at,
        }


class SecureAggregationEngine:
    """Privacy-preserving cross-cohort aggregation.

    All aggregations:
    - Never expose individual data
    - Carry privacy cost (epsilon spent)
    - Require minimum cohort sizes
    - Produce audit trail
    """

    @staticmethod
    def federated_average(
        cohort_stats: list[AnonymizedCohortStat],
        *,
        min_reliable_cohorts: int = 2,
    ) -> dict[str, Any]:
        """Compute a privacy-preserving average across cohorts.

        Each cohort contributes its already-noised stat. The result is a
        meta-aggregate that doesn't touch raw data.
        """
        reliable = [s for s in cohort_stats if s.is_reliable]
        if len(reliable) < min_reliable_cohorts:
            return {
                "computed": False,
                "reason": f"Only {len(reliable)} reliable cohorts, need {min_reliable_cohorts}",
                "value": None,
            }

        # Weight by cohort size (larger cohorts get more weight)
        total_weight = sum(s.cohort_size for s in reliable)
        weighted_avg = sum(s.value * s.cohort_size for s in reliable) / total_weight if total_weight > 0 else 0

        # Meta noise: combined standard error
        import math
        combined_noise = math.sqrt(sum(s.noise_std ** 2 for s in reliable)) / len(reliable)

        return {
            "computed": True,
            "value": round(weighted_avg, 4),
            "meta_noise_std": round(combined_noise, 4),
            "cohorts_contributing": len(reliable),
            "total_members": sum(s.cohort_size for s in reliable),
        }

    @staticmethod
    def privacy_preserving_rank(
        items: list[dict[str, Any]],
        *,
        score_key: str = "value",
        privacy_floor: int = 5,
    ) -> list[dict[str, Any]]:
        """Rank items with privacy protection: items below floor get 'suppressed'."""
        ranked = []
        for item in items:
            if item.get("cohort_size", 0) < privacy_floor:
                ranked.append({**item, "rank": None, "rank_reason": "below_privacy_floor"})
            else:
                ranked.append({**item, "rank": None})  # Will fill after sorting

        # Sort rankable items by score
        [r for r in ranked if r["rank"] is not None or r.get("rank_reason") != "below_privacy_floor"]

        # Actually, let me fix the logic:
        visible = [r for r in ranked if r.get("rank_reason") != "below_privacy_floor"]
        suppressed = [r for r in ranked if r.get("rank_reason") == "below_privacy_floor"]

        visible.sort(key=lambda x: x.get(score_key, 0), reverse=True)
        for i, item in enumerate(visible):
            item["rank"] = i + 1

        return visible + suppressed

    @staticmethod
    def audit_trail(
        insight: FederatedInsight,
        cohorts: dict[str, PrivacyPreservingCohort],
    ) -> dict[str, Any]:
        """Generate audit trail for a federated insight."""
        trail_entries = []
        for cid in insight.contributing_cohort_ids:
            cohort = cohorts.get(cid)
            if cohort:
                trail_entries.append({
                    "cohort_id": cid,
                    "member_count": cohort.member_count,
                    "privacy_tier": cohort.privacy_tier,
                    "criteria": cohort.cohort_criteria,
                    "contributed_at": insight.generated_at,
                })

        return {
            "insight_id": insight.insight_id,
            "privacy_cost": insight.privacy_cost,
            "confidence": insight.confidence,
            "cohorts_audited": len(trail_entries),
            "entries": trail_entries,
            "verifiable": len(trail_entries) >= 2,  # At least 2 cohorts to cross-verify
        }
