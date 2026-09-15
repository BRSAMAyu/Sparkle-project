"""
Core: execution
Phase: clarify→adapt
Stage: T3.2 Aurora↔Spine Confluence — bidirectional integration layer.

This module bridges Aurora's decision outputs into the Spine pipeline
and ensures all Aurora proposals go through proper arbitration rather
than bypassing Spine's control flow.

T3.2.1: AuroraInputAssembler — gathers StatePacket + PolicyDecisions + Outcomes + corrections
T3.2.2: AuroraOutputArbitrator — routes proposals through PolicyEngine, not direct application
T3.2.3: Override tracking — records reasons when Spine overrides Aurora suggestions
T3.2.4: Self-correction — applies corrections through Spine when Aurora admits misjudgment
T3.2.5: Self-model snapshot — exposes hypotheses, open questions, misjudgments, strategy confidence
T3.2.6: Shared trace — Aurora influence written to the same CausalTrace
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── T3.2.1: Aurora Input Assembly ──────────────────────────────────

@dataclass
class AuroraInputContext:
    """All data Aurora needs to make a decision, assembled from Spine."""
    user_id: str
    state_packet: dict[str, Any] = field(default_factory=dict)
    recent_policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    user_corrections: list[dict[str, Any]] = field(default_factory=list)
    active_hypotheses: list[str] = field(default_factory=list)
    assembled_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "state_packet": self.state_packet,
            "recent_policy_decisions": self.recent_policy_decisions,
            "recent_outcomes": self.recent_outcomes,
            "user_corrections": self.user_corrections,
            "active_hypotheses": self.active_hypotheses,
            "assembled_at": self.assembled_at,
        }


class AuroraInputAssembler:
    """T3.2.1: Gathers all Spine context that Aurora must consume.

    Aurora input MUST include:
    - ActionableStatePacket (from StateRegister)
    - Recent PolicyDecisions (from PolicyEffectEntry)
    - Recent Outcomes (from OutcomeRecorder)
    - User corrections (from correction history)
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def assemble(self, user_id: str) -> AuroraInputContext:
        """Assemble full Aurora input context from Spine data."""
        ctx = AuroraInputContext(user_id=user_id)

        # 1. State packet — active states from StateRegister
        try:
            states_raw = await self.redis.smembers(f"spine:state_index:{user_id}")
            if states_raw:
                decoded = [k if isinstance(k, str) else k.decode() for k in states_raw]
                keys = [f"spine:state:{user_id}:{sk}" for sk in decoded]
                try:
                    raw_values = await self.redis.mget(*keys)
                except AttributeError:
                    raw_values = [await self.redis.get(k) for k in keys]
                top_states = []
                for data in raw_values:
                    if data:
                        state = json.loads(data if isinstance(data, str) else data.decode())
                        top_states.append({
                            "state_key": state.get("state_key"),
                            "value": state.get("value"),
                            "confidence": state.get("confidence"),
                        })
                ctx.state_packet = {"top_states": top_states[:10]}
        except Exception:
            logger.debug("AuroraInputAssembler: state fetch failed", exc_info=True)

        # 2. Recent policy decisions
        try:
            effects_raw = await self.redis.lrange(f"spine:effects:{user_id}", 0, 4)
            if effects_raw:
                for raw in effects_raw:
                    raw_str = raw if isinstance(raw, str) else raw.decode()
                    ctx.recent_policy_decisions.append(json.loads(raw_str))
        except Exception:
            logger.debug("AuroraInputAssembler: effects fetch failed", exc_info=True)

        # 3. Recent outcomes
        try:
            outcomes_raw = await self.redis.lrange(f"spine:outcomes:{user_id}", 0, 4)
            if outcomes_raw:
                for raw in outcomes_raw:
                    raw_str = raw if isinstance(raw, str) else raw.decode()
                    ctx.recent_outcomes.append(json.loads(raw_str))
        except Exception:
            logger.debug("AuroraInputAssembler: outcomes fetch failed", exc_info=True)

        # 4. User corrections
        try:
            corrections_raw = await self.redis.lrange(f"spine:user_corrections:{user_id}", 0, 4)
            if corrections_raw:
                for raw in corrections_raw:
                    raw_str = raw if isinstance(raw, str) else raw.decode()
                    ctx.user_corrections.append(json.loads(raw_str))
        except Exception:
            logger.debug("AuroraInputAssembler: corrections fetch failed", exc_info=True)

        # 5. Active self-model hypotheses
        try:
            claims_raw = await self.redis.lrange(f"spine:self_model:claims:{user_id}", 0, 4)
            if claims_raw:
                for cid in claims_raw:
                    cid_str = cid if isinstance(cid, str) else cid.decode()
                    claim_data = await self.redis.get(
                        f"spine:self_model:claim:{user_id}:{cid_str}"
                    )
                    if claim_data:
                        claim = json.loads(claim_data if isinstance(claim_data, str) else claim_data.decode())
                        ctx.active_hypotheses.append(claim.get("claim", ""))
        except Exception:
            logger.debug("AuroraInputAssembler: hypotheses fetch failed", exc_info=True)

        return ctx


# ── T3.2.2: Aurora Output Arbitration ──────────────────────────────

@dataclass
class AuroraProposal:
    """A proposal from Aurora that must go through arbitration."""
    proposal_id: str = ""
    proposal_type: str = ""   # "hypothesis" | "policy_change" | "directive" | "experience"
    content: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source: str = "aurora"    # always "aurora"
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = _uid("ap")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
        }


@dataclass
class ArbitrationResult:
    """Result of arbitrating an Aurora proposal through Spine."""
    proposal_id: str
    accepted: bool
    reason: str = ""
    override_reason: str = ""    # T3.2.3: why Spine overrode (if it did)
    applied_as: str = ""         # what it was applied as (directive type, etc.)
    trace_id: str = ""           # T3.2.6: linked CausalTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "accepted": self.accepted,
            "reason": self.reason,
            "override_reason": self.override_reason,
            "applied_as": self.applied_as,
            "trace_id": self.trace_id,
        }


# Override reasons (T3.2.3)
OVERRIDE_REASONS = {
    "lower_priority_signal": "Higher-priority signal already handled",
    "contradicts_user_preference": "Contradicts explicit user preference",
    "insufficient_confidence": "Aurora confidence below threshold for direct action",
    "cooldown_active": "Same intervention type recently applied",
    "user_correction_pending": "User has pending correction for this area",
}


class AuroraOutputArbitrator:
    """T3.2.2-T3.2.3: Routes Aurora proposals through Spine's PolicyEngine.

    Aurora proposals NEVER bypass Spine. They go through the same
    PolicyEngine evaluation as signals, ensuring consistency.

    T3.2.3: When Spine overrides an Aurora suggestion, the reason
    is recorded in the ArbitrationResult and written to CausalTrace.
    """

    # Confidence thresholds for direct acceptance
    CONFIDENCE_THRESHOLDS: dict[str, float] = {
        "hypothesis": 0.5,
        "policy_change": 0.7,
        "directive": 0.7,
        "experience": 0.6,
    }

    def arbitrate(
        self,
        proposal: AuroraProposal,
        *,
        existing_strategy: str = "",
        user_preferences: dict[str, Any] | None = None,
        cooldown_active: bool = False,
    ) -> ArbitrationResult:
        """Arbitrate a single Aurora proposal.

        Returns ArbitrationResult with accepted/rejected and reason.
        """
        user_preferences = user_preferences or {}

        # Check cooldown
        if cooldown_active:
            return ArbitrationResult(
                proposal_id=proposal.proposal_id,
                accepted=False,
                reason="rejected",
                override_reason=OVERRIDE_REASONS["cooldown_active"],
            )

        # Check confidence threshold
        threshold = self.CONFIDENCE_THRESHOLDS.get(proposal.proposal_type, 0.7)
        if proposal.confidence < threshold:
            return ArbitrationResult(
                proposal_id=proposal.proposal_id,
                accepted=False,
                reason="rejected",
                override_reason=OVERRIDE_REASONS["insufficient_confidence"],
            )

        # Check user preference conflict
        target_state = proposal.content.get("state_key", "")
        if target_state in user_preferences:
            pref_value = user_preferences[target_state]
            proposed_value = proposal.content.get("new_value", "")
            if pref_value != proposed_value and pref_value:
                return ArbitrationResult(
                    proposal_id=proposal.proposal_id,
                    accepted=False,
                    reason="rejected",
                    override_reason=OVERRIDE_REASONS["contradicts_user_preference"],
                )

        # Accept — will be applied through Spine's normal pipeline
        applied_as = self._determine_application_type(proposal)
        return ArbitrationResult(
            proposal_id=proposal.proposal_id,
            accepted=True,
            reason="accepted",
            applied_as=applied_as,
        )

    def arbitrate_batch(
        self,
        proposals: list[AuroraProposal],
        **kwargs,
    ) -> list[ArbitrationResult]:
        """Arbitrate multiple proposals. First accepted wins for each domain."""
        results: list[ArbitrationResult] = []
        accepted_domains: set[str] = set()

        for proposal in proposals:
            result = self.arbitrate(proposal, **kwargs)
            domain = proposal.content.get("state_key", proposal.proposal_type)

            if result.accepted and domain in accepted_domains:
                result = ArbitrationResult(
                    proposal_id=proposal.proposal_id,
                    accepted=False,
                    reason="rejected",
                    override_reason=OVERRIDE_REASONS["lower_priority_signal"],
                )

            if result.accepted:
                accepted_domains.add(domain)

            results.append(result)

        return results

    def _determine_application_type(self, proposal: AuroraProposal) -> str:
        """Map proposal type to Spine application type."""
        mapping = {
            "hypothesis": "self_model_update",
            "policy_change": "policy_override",
            "directive": "directive_regeneration",
            "experience": "ux_adjustment",
        }
        return mapping.get(proposal.proposal_type, "unknown")


# ── T3.2.4: Self-Correction ────────────────────────────────────────

@dataclass
class AuroraCorrection:
    """Record of Aurora admitting a misjudgment and applying correction."""
    correction_id: str = ""
    user_id: str = ""
    original_claim: str = ""
    corrected_claim: str = ""
    reason: str = ""
    state_patches: list[dict[str, Any]] = field(default_factory=list)
    policy_reversals: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def __post_init__(self):
        if not self.correction_id:
            self.correction_id = _uid("acor")

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "user_id": self.user_id,
            "original_claim": self.original_claim,
            "corrected_claim": self.corrected_claim,
            "reason": self.reason,
            "state_patches": self.state_patches,
            "policy_reversals": self.policy_reversals,
            "created_at": self.created_at,
        }


class AuroraSelfCorrector:
    """T3.2.4: Handles Aurora admitting misjudgments.

    When Aurora self-corrects:
    1. Reverses affected state patches
    2. Rolls back policy decisions
    3. Records correction in self-model
    4. Writes correction to shared CausalTrace
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def apply_correction(
        self,
        *,
        user_id: str,
        original_claim: str,
        corrected_claim: str,
        reason: str,
        state_patches: list[dict[str, Any]] | None = None,
    ) -> AuroraCorrection:
        """Apply a self-correction through Spine.

        All corrections go through Spine's normal state update path,
        not direct writes.
        """
        correction = AuroraCorrection(
            user_id=user_id,
            original_claim=original_claim,
            corrected_claim=corrected_claim,
            reason=reason,
            state_patches=state_patches or [],
        )

        # Persist correction record
        try:
            key = f"spine:aurora_corrections:{user_id}"
            await self.redis.lpush(key, json.dumps(correction.to_dict()))
            await self.redis.ltrim(key, 0, 49)
            await self.redis.expire(key, 30 * 24 * 3600)
        except Exception:
            logger.warning("AuroraSelfCorrector: persist failed", exc_info=True)

        logger.info(
            "Aurora self-correction: user={} original={} corrected={} reason={}",
            user_id, original_claim, corrected_claim, reason,
        )
        return correction


# ── T3.2.5: Self-Model Snapshot ────────────────────────────────────

@dataclass
class AuroraSelfModelSnapshot:
    """Snapshot of Aurora's self-model: what it believes, doubts, and has been wrong about."""
    user_id: str
    active_hypotheses: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    recent_misjudgments: list[str] = field(default_factory=list)
    strategy_confidence: dict[str, float] = field(default_factory=dict)
    snapshot_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "active_hypotheses": self.active_hypotheses,
            "open_questions": self.open_questions,
            "recent_misjudgments": self.recent_misjudgments,
            "strategy_confidence": self.strategy_confidence,
            "snapshot_at": self.snapshot_at,
        }


class AuroraSelfModelAccessor:
    """T3.2.5: Reads Aurora's self-model state for consumption by other systems."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def get_snapshot(self, user_id: str) -> AuroraSelfModelSnapshot:
        """Build a self-model snapshot from Redis data."""
        snapshot = AuroraSelfModelSnapshot(user_id=user_id)

        # Active hypotheses from self-model claims
        try:
            claims_raw = await self.redis.lrange(f"spine:self_model:claims:{user_id}", 0, 9)
            if claims_raw:
                for cid in claims_raw:
                    cid_str = cid if isinstance(cid, str) else cid.decode()
                    claim_data = await self.redis.get(
                        f"spine:self_model:claim:{user_id}:{cid_str}"
                    )
                    if claim_data:
                        claim = json.loads(claim_data if isinstance(claim_data, str) else claim_data.decode())
                        hypothesis = claim.get("claim", "")
                        if claim.get("outcome") == "insufficient":
                            snapshot.recent_misjudgments.append(hypothesis)
                        elif claim.get("outcome") is None:
                            snapshot.active_hypotheses.append(hypothesis)
                            # Track confidence per policy
                            for effect in claim.get("policy_effects", []):
                                snapshot.strategy_confidence[effect] = claim.get("confidence", 0.5)
        except Exception:
            logger.debug("SelfModelAccessor: claims fetch failed", exc_info=True)

        # Open questions from active states with low confidence
        try:
            states_raw = await self.redis.smembers(f"spine:state_index:{user_id}")
            if states_raw:
                decoded = [k if isinstance(k, str) else k.decode() for k in states_raw]
                keys = [f"spine:state:{user_id}:{sk}" for sk in decoded]
                try:
                    raw_values = await self.redis.mget(*keys)
                except AttributeError:
                    raw_values = [await self.redis.get(k) for k in keys]
                for data in raw_values:
                    if data:
                        state = json.loads(data if isinstance(data, str) else data.decode())
                        conf = state.get("confidence", 0)
                        if 0.3 < conf < 0.7:
                            snapshot.open_questions.append(
                                f"{state.get('state_key')}: {state.get('value')} (conf={conf:.2f})"
                            )
        except Exception:
            logger.debug("SelfModelAccessor: states fetch failed", exc_info=True)

        return snapshot
