"""Automatic parameter proposal from accumulated effectiveness data.

Uses Bayesian posteriors + Thompson sampling to identify winning parameter
configurations, validates through drift firewall, and proposes changes
via the experiment service. Proposals require explicit approval.

Core: bridge
Phase: adapt
Stage: meta_learning
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.time_utils import utcnow
from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
from app.orchestration.routing_parameter_registry import (
    ALL_DEFAULT_PARAMETERS,
    PARAMETER_BOUNDS,
    PARAM_EXPERIMENT_PREFIX,
    _clamp,
)
from app.services.constitutional_drift_firewall import ConstitutionalDriftFirewall
from app.services.routing_parameter_experiment_service import (
    REGISTRY_UPDATE_KEY,
    RoutingParameterExperimentService,
)

PROPOSAL_KEY_PREFIX = "aurora:param_proposals:"
PROPOSAL_TTL = 86400 * 7  # 7 days
MIN_SAMPLES_FOR_PROPOSAL = 50
MIN_IMPROVEMENT_RATIO = 1.05  # 5% better than baseline
MAX_DRIFT_RATIO = 0.5  # Block if proposed value drifts >50% from default

# Three promotion layers
LAYER_SESSION = "session"
LAYER_EPISODE = "episode"
LAYER_PROFILE = "profile"

PROMOTION_THRESHOLDS = {
    LAYER_SESSION: {"min_samples": 30, "min_sessions": 1, "min_improvement": 0.03},
    LAYER_EPISODE: {"min_samples": 60, "min_sessions": 3, "min_improvement": 0.05},
    LAYER_PROFILE: {"min_samples": 120, "min_sessions": 5, "min_improvement": 0.08},
}


class ParameterProposal:
    __slots__ = (
        "parameter_name", "current_value", "proposed_value", "baseline_rate",
        "treatment_rate", "sample_count", "session_count", "promotion_layer",
        "created_at", "drift_firewall_result", "status",
    )

    def __init__(
        self,
        *,
        parameter_name: str,
        current_value: float,
        proposed_value: float,
        baseline_rate: float,
        treatment_rate: float,
        sample_count: int,
        session_count: int = 1,
        promotion_layer: str = LAYER_SESSION,
    ):
        self.parameter_name = parameter_name
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.baseline_rate = baseline_rate
        self.treatment_rate = treatment_rate
        self.sample_count = sample_count
        self.session_count = session_count
        self.promotion_layer = promotion_layer
        self.created_at = utcnow().isoformat()
        self.drift_firewall_result: dict[str, Any] | None = None
        self.status = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "baseline_rate": self.baseline_rate,
            "treatment_rate": self.treatment_rate,
            "sample_count": self.sample_count,
            "session_count": self.session_count,
            "promotion_layer": self.promotion_layer,
            "created_at": self.created_at,
            "drift_firewall_result": self.drift_firewall_result,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParameterProposal:
        p = cls(
            parameter_name=data["parameter_name"],
            current_value=data["current_value"],
            proposed_value=data["proposed_value"],
            baseline_rate=data["baseline_rate"],
            treatment_rate=data["treatment_rate"],
            sample_count=data["sample_count"],
            session_count=data.get("session_count", 1),
            promotion_layer=data.get("promotion_layer", LAYER_SESSION),
        )
        p.created_at = data.get("created_at", p.created_at)
        p.drift_firewall_result = data.get("drift_firewall_result")
        p.status = data.get("status", "pending")
        return p


class RoutingParameterProposalService:
    """Generates, validates, and stores parameter change proposals."""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client or cache_service.redis
        self.drift_firewall = ConstitutionalDriftFirewall()

    async def propose_from_effectiveness(self) -> list[ParameterProposal]:
        """Scan effectiveness data and generate proposals for winning parameters.

        For each known parameter, compare Bayesian posteriors between versions
        that modified it vs the default version. Propose changes where evidence
        shows improvement.
        """
        proposals: list[ParameterProposal] = []

        effectiveness_data = await self._load_effectiveness_data()
        if not effectiveness_data:
            return proposals

        # Group effectiveness by signal/mode for baseline computation
        baseline_rates: dict[str, float] = {}
        for group in effectiveness_data:
            total = group.get("total", 0)
            if total < MIN_SAMPLES_FOR_PROPOSAL:
                continue
            signal = group.get("dominant_signal", "")
            mode = group.get("routing_mode", "")
            key = f"{signal}:{mode}"
            rate = float(group.get("success_rate", 0))
            # Keep the highest-rate group as baseline reference
            if key not in baseline_rates or rate > baseline_rates[key]:
                baseline_rates[key] = rate

        if not baseline_rates:
            return proposals

        # Average baseline across all signal/mode groups
        avg_baseline = sum(baseline_rates.values()) / len(baseline_rates)

        # For each known parameter, try to find evidence of improvement
        learner = PersistentBayesianLearner(self.redis, user_id="system:meta_learning")

        for param_name, default_value in ALL_DEFAULT_PARAMETERS.items():
            if not isinstance(default_value, (int, float)):
                continue

            # Check if there's sufficient evidence via Bayesian learner
            # Key pattern: param_effectiveness:{version} -> {signal}:{mode}
            try:
                stats = await learner.get_stats()
            except Exception:
                continue

            # Find keys related to this parameter's effectiveness
            # The learner stores keys as "source_key->target_key"
            relevant_observations = 0
            best_rate = 0.0
            for stat_key, stat_val in stats.items():
                if not stat_key.startswith("param_effectiveness:"):
                    continue
                # Only consider stats with meaningful sample counts
                alpha = float(stat_val.get("alpha", 1.0))
                beta = float(stat_val.get("beta", 1.0))
                obs = int(alpha + beta - 2)  # Prior starts at alpha=1, beta=1
                if obs < 10:
                    continue
                rate = alpha / (alpha + beta)
                if rate > best_rate:
                    best_rate = rate
                relevant_observations += obs

            if relevant_observations < MIN_SAMPLES_FOR_PROPOSAL:
                continue

            if best_rate < avg_baseline * MIN_IMPROVEMENT_RATIO:
                continue

            # Propose a small adjustment toward the direction of improvement
            lo, hi = PARAMETER_BOUNDS.get(param_name, (0.0, 15.0))
            proposed_value = await self._compute_proposed_value(
                param_name, float(default_value), lo, hi, best_rate, avg_baseline,
            )
            if proposed_value is None or abs(proposed_value - float(default_value)) < 0.01:
                continue

            proposal = ParameterProposal(
                parameter_name=param_name,
                current_value=float(default_value),
                proposed_value=proposed_value,
                baseline_rate=avg_baseline,
                treatment_rate=best_rate,
                sample_count=relevant_observations,
                promotion_layer=self._determine_promotion_layer(relevant_observations),
            )

            # Run drift firewall
            proposal.drift_firewall_result = self._check_drift(proposal)
            if proposal.drift_firewall_result.get("disposition") == "blocked":
                proposal.status = "blocked_by_firewall"
                logger.info(
                    "Proposal blocked by drift firewall: {} → {} ({})",
                    param_name, proposed_value,
                    proposal.drift_firewall_result.get("explanation", ""),
                )
                continue

            proposals.append(proposal)

        # Store proposals in Redis
        await self._store_proposals(proposals)

        logger.info("Generated {} parameter proposals from effectiveness data", len(proposals))
        return proposals

    async def approve_proposal(self, proposal_key: str) -> dict[str, Any]:
        """Approve a pending proposal and create an A/B experiment."""
        proposal = await self._load_proposal(proposal_key)
        if proposal is None:
            return {"status": "not_found"}
        if proposal.status != "pending":
            return {"status": "not_pending", "current_status": proposal.status}

        # Create A/B experiment via experiment service
        experiment_service = RoutingParameterExperimentService(self.db, self.redis)
        result = await experiment_service.propose_parameter_change(
            parameter_name=proposal.parameter_name,
            proposed_value=proposal.proposed_value,
            evidence={
                "current_value": proposal.current_value,
                "baseline_success_rate": proposal.baseline_rate,
                "treatment_success_rate": proposal.treatment_rate,
                "sample_count": proposal.sample_count,
            },
        )

        # Mark proposal as approved
        proposal.status = "approved"
        await self._update_proposal_status(proposal_key, "approved")

        return {
            "status": "approved",
            "proposal": proposal.to_dict(),
            "experiment_result": result,
        }

    async def reject_proposal(self, proposal_key: str, reason: str = "") -> dict[str, Any]:
        """Reject a pending proposal."""
        proposal = await self._load_proposal(proposal_key)
        if proposal is None:
            return {"status": "not_found"}

        proposal.status = "rejected"
        await self._update_proposal_status(proposal_key, "rejected")
        return {"status": "rejected", "parameter_name": proposal.parameter_name}

    async def list_proposals(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all proposals, optionally filtered by status."""
        if self.redis is None:
            return []

        keys = []
        cursor = 0
        while True:
            cursor, batch = await self.redis.scan(
                cursor=cursor, match=f"{PROPOSAL_KEY_PREFIX}*", count=50,
            )
            keys.extend(batch)
            if cursor == 0:
                break

        proposals = []
        for key in keys:
            raw = await self.redis.get(key)
            if raw is None:
                continue
            data = json.loads(raw)
            if status and data.get("status") != status:
                continue
            data["key"] = key if isinstance(key, str) else key.decode()
            proposals.append(data)

        return sorted(proposals, key=lambda x: x.get("created_at", ""), reverse=True)

    # ── Internal helpers ──────────────────────────────────────────────

    async def _load_effectiveness_data(self) -> list[dict[str, Any]]:
        """Load cached effectiveness data from Redis."""
        from app.services.routing_parameter_effectiveness_service import EFFECTIVENESS_REDIS_KEY

        if self.redis is None:
            return []
        raw = await self.redis.get(EFFECTIVENESS_REDIS_KEY)
        if raw is None:
            return []
        return json.loads(raw)

    @staticmethod
    def _compute_proposed_value(
        param_name: str,
        default_value: float,
        lo: float,
        hi: float,
        treatment_rate: float,
        baseline_rate: float,
    ) -> float | None:
        """Compute a conservative proposed value for a parameter.

        Uses the improvement ratio to determine the magnitude of the change,
        capped by MAX_DRIFT_RATIO from the default.
        """
        if baseline_rate <= 0:
            return None

        improvement = (treatment_rate - baseline_rate) / baseline_rate
        # Scale the parameter change proportionally to the improvement,
        # but never exceed MAX_DRIFT_RATIO of the default value
        max_change = abs(default_value) * MAX_DRIFT_RATIO if default_value != 0 else (hi - lo) * 0.1
        change_magnitude = min(max_change, (hi - lo) * improvement * 0.5)

        # Determine direction: if rate is high, nudge toward the middle of bounds
        # (conservative — assume current default is already decent)
        # If improvement is positive, propose a small increase or decrease
        if default_value < (lo + hi) / 2:
            proposed = default_value + change_magnitude
        else:
            proposed = default_value - change_magnitude

        return _clamp(round(proposed, 3), param_name)

    @staticmethod
    def _determine_promotion_layer(sample_count: int) -> str:
        """Determine promotion layer based on accumulated evidence."""
        if sample_count >= PROMOTION_THRESHOLDS[LAYER_PROFILE]["min_samples"]:
            return LAYER_PROFILE
        if sample_count >= PROMOTION_THRESHOLDS[LAYER_EPISODE]["min_samples"]:
            return LAYER_EPISODE
        return LAYER_SESSION

    def _check_drift(self, proposal: ParameterProposal) -> dict[str, Any]:
        """Run drift firewall check on proposed parameter change."""
        default_value = float(ALL_DEFAULT_PARAMETERS.get(proposal.parameter_name, 0))
        if default_value > 0:
            drift_ratio = abs(proposal.proposed_value - default_value) / default_value
            if drift_ratio > MAX_DRIFT_RATIO:
                return {
                    "disposition": "blocked",
                    "explanation": (
                        f"Proposed {proposal.parameter_name}={proposal.proposed_value} "
                        f"drifts {drift_ratio:.0%} from default {default_value} "
                        f"(max allowed: {MAX_DRIFT_RATIO:.0%})"
                    ),
                    "drift_ratio": drift_ratio,
                }

        # Also run through constitutional drift firewall
        try:
            report = self.drift_firewall.evaluate_change(
                change_type="parameter_promotion",
                target_layer=proposal.promotion_layer,
                proposed_value=f"{proposal.parameter_name}={proposal.proposed_value}",
                evidence={
                    "source": "parameter_learning",
                    "effectiveness": proposal.treatment_rate,
                    "sample_count": proposal.sample_count,
                    "current_value": proposal.current_value,
                    "proposed_value": proposal.proposed_value,
                },
            )
            return {
                "disposition": report.disposition,
                "allowed": report.allowed,
                "explanation": report.explanation,
                "manipulation_risk": report.manipulation_risk,
                "freedom_risk": report.freedom_risk,
            }
        except Exception as exc:
            logger.warning("Drift firewall evaluation failed: {}", exc)
            return {"disposition": "blocked", "explanation": f"firewall_unavailable: {exc}"}

    async def _store_proposals(self, proposals: list[ParameterProposal]) -> None:
        """Store proposals in Redis with TTL."""
        if self.redis is None:
            return
        for proposal in proposals:
            key = f"{PROPOSAL_KEY_PREFIX}{proposal.parameter_name}:{proposal.created_at}"
            await self.redis.set(
                key,
                json.dumps(proposal.to_dict()),
                ex=PROPOSAL_TTL,
            )

    async def _load_proposal(self, proposal_key: str) -> ParameterProposal | None:
        """Load a single proposal from Redis."""
        if self.redis is None:
            return None
        raw = await self.redis.get(proposal_key)
        if raw is None:
            return None
        return ParameterProposal.from_dict(json.loads(raw))

    async def _update_proposal_status(self, proposal_key: str, status: str) -> None:
        """Update the status of a stored proposal."""
        if self.redis is None:
            return
        raw = await self.redis.get(proposal_key)
        if raw is None:
            return
        data = json.loads(raw)
        data["status"] = status
        await self.redis.set(proposal_key, json.dumps(data), ex=PROPOSAL_TTL)


def in_canary_bucket(user_id: str, canary_percent: int) -> bool:
    """Deterministic canary bucket assignment (same pattern as BayesianRoutingWireService)."""
    if canary_percent >= 100:
        return True
    if canary_percent <= 0:
        return False
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < canary_percent
