"""
Tests for T3.2.1-T3.2.6: Aurora↔Spine Confluence.

Production scenario coverage:
- T3.2.1: Input assembler gathers state packet + policy decisions + outcomes + corrections
- T3.2.2: Output arbitrator routes proposals through arbitration, not direct
- T3.2.3: Override reasons recorded when Spine rejects Aurora proposals
- T3.2.4: Self-correction applies through Spine pipeline
- T3.2.5: Self-model snapshot exposes hypotheses, doubts, misjudgments
- T3.2.6: Shared trace integration (via CausalTrace fields)
- Redis failure graceful degradation
"""
import json
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from app.aurora.runtime_v1.aurora_spine_confluence import (
    AuroraInputAssembler,
    AuroraInputContext,
    AuroraOutputArbitrator,
    AuroraProposal,
    ArbitrationResult,
    AuroraSelfCorrector,
    AuroraCorrection,
    AuroraSelfModelAccessor,
    AuroraSelfModelSnapshot,
    OVERRIDE_REASONS,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.lpush.return_value = True
    redis.ltrim.return_value = True
    redis.expire.return_value = True
    redis.lrange.return_value = []
    redis.smembers.return_value = set()
    return redis


def _make_state(state_key: str, value: str, confidence: float) -> str:
    return json.dumps({
        "state_key": state_key,
        "value": value,
        "confidence": confidence,
        "scope": "session",
    })


def _make_claim(claim: str, confidence: float, outcome: str | None = None) -> str:
    return json.dumps({
        "claim": claim,
        "confidence": confidence,
        "scope": "current_sprint",
        "evidence": [],
        "counter_evidence": [],
        "policy_effects": ["strategy_a"],
        "outcome": outcome,
    })


# ═══════════════════════════════════════════════════════════════════
# T3.2.1: Input Assembler
# ═══════════════════════════════════════════════════════════════════

class TestInputAssembler:
    """AuroraInputAssembler — gathering all Spine context for Aurora."""

    @pytest.mark.asyncio
    async def test_assembles_state_packet(self):
        """Active states are gathered into state_packet.top_states."""
        redis = _make_redis()
        redis.smembers.return_value = {b"knowledge_bottleneck", b"cognitive_load"}
        redis.mget.return_value = [
            _make_state("knowledge_bottleneck", "tcp", 0.82),
            _make_state("cognitive_load", "high", 0.65),
        ]

        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert len(ctx.state_packet.get("top_states", [])) == 2
        assert ctx.state_packet["top_states"][0]["state_key"] == "knowledge_bottleneck"

    @pytest.mark.asyncio
    async def test_assembles_recent_effects(self):
        """Recent policy effects are included."""
        redis = _make_redis()
        redis.lrange.return_value = [json.dumps({"strategy_key": "worked_example", "effectiveness": 0.7})]

        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert len(ctx.recent_policy_decisions) == 1
        assert ctx.recent_policy_decisions[0]["strategy_key"] == "worked_example"

    @pytest.mark.asyncio
    async def test_assembles_user_corrections(self):
        """User corrections are included."""
        redis = _make_redis()

        async def lrange_side_effect(key, start, end):
            if "corrections" in key:
                return [json.dumps({"state_key": "knowledge_bottleneck", "correction": "not a bottleneck"})]
            return []

        redis.lrange.side_effect = lrange_side_effect
        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert len(ctx.user_corrections) == 1

    @pytest.mark.asyncio
    async def test_assembles_hypotheses_from_self_model(self):
        """Active self-model hypotheses are included."""
        redis = _make_redis()

        async def lrange_side_effect(key, start, end):
            if "self_model:claims" in key:
                return [b"smc_123"]
            return []

        redis.lrange.side_effect = lrange_side_effect

        async def get_side_effect(key):
            if "smc_123" in key:
                return _make_claim("User benefits from worked examples", 0.8)
            return None

        redis.get.side_effect = get_side_effect
        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert len(ctx.active_hypotheses) == 1
        assert "worked examples" in ctx.active_hypotheses[0]

    @pytest.mark.asyncio
    async def test_empty_data_returns_valid_context(self):
        """No data in Redis returns empty but valid context."""
        redis = _make_redis()
        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert ctx.user_id == "user_abc"
        assert ctx.state_packet == {}
        assert ctx.recent_policy_decisions == []
        assert ctx.recent_outcomes == []

    @pytest.mark.asyncio
    async def test_redis_failure_returns_valid_context(self):
        """Redis failure returns empty context, doesn't crash."""
        redis = _make_redis()
        redis.smembers.side_effect = Exception("Redis down")
        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert ctx.user_id == "user_abc"
        assert ctx.state_packet == {}

    @pytest.mark.asyncio
    async def test_limits_top_states_to_10(self):
        """State packet is capped at 10 states."""
        redis = _make_redis()
        redis.smembers.return_value = {f"state_{i}".encode() for i in range(15)}
        redis.mget.return_value = [_make_state(f"state_{i}", "val", 0.5) for i in range(15)]

        assembler = AuroraInputAssembler(redis)
        ctx = await assembler.assemble("user_abc")

        assert len(ctx.state_packet.get("top_states", [])) <= 10


# ═══════════════════════════════════════════════════════════════════
# T3.2.2: Output Arbitrator
# ═══════════════════════════════════════════════════════════════════

class TestOutputArbitrator:
    """AuroraOutputArbitrator — proposals go through arbitration, not direct."""

    def setup_method(self):
        self.arbitrator = AuroraOutputArbitrator()

    def test_high_confidence_policy_accepted(self):
        """Policy change at 0.8 confidence → accepted."""
        proposal = AuroraProposal(
            proposal_type="policy_change",
            content={"state_key": "execution_strategy", "new_value": "worked_example"},
            confidence=0.8,
        )
        result = self.arbitrator.arbitrate(proposal)
        assert result.accepted is True
        assert result.applied_as == "policy_override"

    def test_low_confidence_policy_rejected(self):
        """Policy change at 0.5 confidence (< 0.7 threshold) → rejected."""
        proposal = AuroraProposal(
            proposal_type="policy_change",
            content={"state_key": "execution_strategy", "new_value": "retrieval"},
            confidence=0.5,
        )
        result = self.arbitrator.arbitrate(proposal)
        assert result.accepted is False
        assert "confidence" in result.override_reason.lower() or "threshold" in result.override_reason.lower()

    def test_hypothesis_lower_threshold(self):
        """Hypotheses have lower threshold (0.5) than policies (0.7)."""
        proposal = AuroraProposal(
            proposal_type="hypothesis",
            content={"claim": "User prefers morning study"},
            confidence=0.55,
        )
        result = self.arbitrator.arbitrate(proposal)
        assert result.accepted is True
        assert result.applied_as == "self_model_update"

    def test_cooldown_blocks_all(self):
        """Cooldown active → any proposal rejected."""
        proposal = AuroraProposal(
            proposal_type="directive",
            content={"directive_type": "ExecutionDirective"},
            confidence=0.95,
        )
        result = self.arbitrator.arbitrate(proposal, cooldown_active=True)
        assert result.accepted is False
        assert "recently" in result.override_reason.lower() or "applied" in result.override_reason.lower()

    def test_user_preference_override(self):
        """Aurora proposal contradicting user preference → rejected."""
        proposal = AuroraProposal(
            proposal_type="policy_change",
            content={"state_key": "task_granularity", "new_value": "small"},
            confidence=0.85,
        )
        result = self.arbitrator.arbitrate(
            proposal,
            user_preferences={"task_granularity": "standard"},
        )
        assert result.accepted is False
        assert "preference" in result.override_reason.lower()

    def test_user_preference_no_conflict_accepted(self):
        """Proposal that doesn't conflict with preference → accepted."""
        proposal = AuroraProposal(
            proposal_type="policy_change",
            content={"state_key": "execution_strategy", "new_value": "worked_example"},
            confidence=0.8,
        )
        result = self.arbitrator.arbitrate(
            proposal,
            user_preferences={"task_granularity": "standard"},
        )
        assert result.accepted is True

    def test_batch_first_accepted_wins_per_domain(self):
        """Batch arbitration: first accepted per domain wins, rest rejected."""
        proposals = [
            AuroraProposal(
                proposal_type="policy_change",
                content={"state_key": "knowledge_bottleneck", "new_value": "a"},
                confidence=0.8,
            ),
            AuroraProposal(
                proposal_type="policy_change",
                content={"state_key": "knowledge_bottleneck", "new_value": "b"},
                confidence=0.9,
            ),
        ]
        results = self.arbitrator.arbitrate_batch(proposals)
        assert results[0].accepted is True
        assert results[1].accepted is False
        assert "priority" in results[1].override_reason.lower()

    def test_batch_different_domains_both_accepted(self):
        """Batch: different state_keys → both accepted."""
        proposals = [
            AuroraProposal(
                proposal_type="policy_change",
                content={"state_key": "knowledge_bottleneck", "new_value": "a"},
                confidence=0.8,
            ),
            AuroraProposal(
                proposal_type="policy_change",
                content={"state_key": "execution_consistency", "new_value": "b"},
                confidence=0.8,
            ),
        ]
        results = self.arbitrator.arbitrate_batch(proposals)
        assert results[0].accepted is True
        assert results[1].accepted is True


# ═══════════════════════════════════════════════════════════════════
# T3.2.3: Override Reasons
# ═══════════════════════════════════════════════════════════════════

class TestOverrideReasons:
    """Verify all override reasons are defined and meaningful."""

    def test_all_override_reasons_have_descriptions(self):
        """Every override reason must have a non-empty description."""
        for key, desc in OVERRIDE_REASONS.items():
            assert len(desc) > 0, f"{key} missing description"

    def test_expected_override_reasons_exist(self):
        """The 5 standard override reasons must exist."""
        expected = {"lower_priority_signal", "contradicts_user_preference",
                    "insufficient_confidence", "cooldown_active",
                    "user_correction_pending"}
        assert set(OVERRIDE_REASONS.keys()) == expected

    def test_arbitration_result_records_override(self):
        """ArbitrationResult stores override_reason when rejected."""
        result = ArbitrationResult(
            proposal_id="test",
            accepted=False,
            reason="rejected",
            override_reason=OVERRIDE_REASONS["insufficient_confidence"],
        )
        assert "threshold" in result.override_reason.lower() or "confidence" in result.override_reason.lower()


# ═══════════════════════════════════════════════════════════════════
# T3.2.4: Self-Correction
# ═══════════════════════════════════════════════════════════════════

class TestSelfCorrection:
    """AuroraSelfCorrector — admitting misjudgments through Spine."""

    def setup_method(self):
        self.redis = _make_redis()
        self.corrector = AuroraSelfCorrector(self.redis)

    @pytest.mark.asyncio
    async def test_correction_applied_and_recorded(self):
        """Self-correction is persisted and has all required fields."""
        correction = await self.corrector.apply_correction(
            user_id="user_abc",
            original_claim="User prefers morning study",
            corrected_claim="User prefers evening study",
            reason="User explicitly stated preference for evening",
            state_patches=[{"state_key": "study_time_pref", "old_value": "morning", "new_value": "evening"}],
        )

        assert correction.correction_id.startswith("acor_")
        assert correction.user_id == "user_abc"
        assert correction.original_claim == "User prefers morning study"
        assert correction.corrected_claim == "User prefers evening study"
        assert len(correction.state_patches) == 1

    @pytest.mark.asyncio
    async def test_correction_without_patches(self):
        """Correction with no state patches is valid (e.g., belief revision only)."""
        correction = await self.corrector.apply_correction(
            user_id="user_abc",
            original_claim="Task was too large",
            corrected_claim="Task was fine, user had knowledge gap",
            reason="User feedback revealed knowledge gap, not granularity issue",
        )

        assert len(correction.state_patches) == 0
        assert "knowledge gap" in correction.corrected_claim

    @pytest.mark.asyncio
    async def test_redis_failure_correction_still_returns(self):
        """Redis failure during correction persist doesn't crash."""
        redis = _make_redis()
        redis.lpush.side_effect = Exception("Redis down")
        corrector = AuroraSelfCorrector(redis)

        correction = await corrector.apply_correction(
            user_id="user_abc",
            original_claim="a",
            corrected_claim="b",
            reason="test",
        )
        assert correction is not None
        assert correction.correction_id.startswith("acor_")

    @pytest.mark.asyncio
    async def test_correction_serialization(self):
        """Correction survives to_dict round trip."""
        correction = await self.corrector.apply_correction(
            user_id="u1",
            original_claim="a",
            corrected_claim="b",
            reason="test",
        )
        d = correction.to_dict()
        assert d["correction_id"] == correction.correction_id
        assert d["user_id"] == "u1"


# ═══════════════════════════════════════════════════════════════════
# T3.2.5: Self-Model Snapshot
# ═══════════════════════════════════════════════════════════════════

class TestSelfModelSnapshot:
    """AuroraSelfModelAccessor — exposing Aurora's self-model state."""

    def setup_method(self):
        self.redis = _make_redis()
        self.accessor = AuroraSelfModelAccessor(self.redis)

    @pytest.mark.asyncio
    async def test_empty_snapshot_valid(self):
        """No data returns valid snapshot with empty fields."""
        snapshot = await self.accessor.get_snapshot("user_abc")
        assert snapshot.user_id == "user_abc"
        assert snapshot.active_hypotheses == []
        assert snapshot.recent_misjudgments == []
        assert snapshot.strategy_confidence == {}

    @pytest.mark.asyncio
    async def test_active_hypotheses_from_claims(self):
        """Claims with no outcome → active hypotheses."""
        redis = _make_redis()

        async def lrange_side_effect(key, start, end):
            if "self_model:claims" in key:
                return [b"smc_1"]
            return []

        redis.lrange.side_effect = lrange_side_effect

        async def get_side_effect(key):
            if "smc_1" in key:
                return _make_claim("User benefits from spaced repetition", 0.8, outcome=None)
            return None

        redis.get.side_effect = get_side_effect
        accessor = AuroraSelfModelAccessor(redis)
        snapshot = await accessor.get_snapshot("user_abc")

        assert len(snapshot.active_hypotheses) == 1
        assert "spaced repetition" in snapshot.active_hypotheses[0]

    @pytest.mark.asyncio
    async def test_misjudgments_from_failed_claims(self):
        """Claims with outcome=insufficient → recent misjudgments."""
        redis = _make_redis()

        async def lrange_side_effect(key, start, end):
            if "self_model:claims" in key:
                return [b"smc_1"]
            return []

        redis.lrange.side_effect = lrange_side_effect

        async def get_side_effect(key):
            if "smc_1" in key:
                return _make_claim("User prefers morning study", 0.6, outcome="insufficient")
            return None

        redis.get.side_effect = get_side_effect
        accessor = AuroraSelfModelAccessor(redis)
        snapshot = await accessor.get_snapshot("user_abc")

        assert len(snapshot.recent_misjudgments) == 1
        assert "morning study" in snapshot.recent_misjudgments[0]

    @pytest.mark.asyncio
    async def test_open_questions_from_uncertain_states(self):
        """States with confidence 0.3-0.7 → open questions."""
        redis = _make_redis()

        async def smembers_side_effect(key):
            return {b"cognitive_load"}

        redis.smembers.side_effect = smembers_side_effect
        redis.mget.return_value = [_make_state("cognitive_load", "moderate", 0.45)]

        accessor = AuroraSelfModelAccessor(redis)
        snapshot = await accessor.get_snapshot("user_abc")

        assert len(snapshot.open_questions) == 1
        assert "cognitive_load" in snapshot.open_questions[0]

    @pytest.mark.asyncio
    async def test_redis_failure_returns_empty_snapshot(self):
        """Redis failure returns empty snapshot, doesn't crash."""
        redis = _make_redis()
        redis.lrange.side_effect = Exception("Redis down")
        accessor = AuroraSelfModelAccessor(redis)
        snapshot = await accessor.get_snapshot("user_abc")

        assert snapshot.user_id == "user_abc"
        assert snapshot.active_hypotheses == []


# ═══════════════════════════════════════════════════════════════════
# T3.2.6: Shared Trace Integration
# ═══════════════════════════════════════════════════════════════════

class TestSharedTrace:
    """Verify Aurora influence writes to the same CausalTrace structure."""

    def test_arbitration_result_has_trace_id(self):
        """ArbitrationResult must carry a trace_id for shared tracing."""
        result = ArbitrationResult(
            proposal_id="test",
            accepted=True,
            reason="accepted",
            trace_id="ct_123",
        )
        d = result.to_dict()
        assert d["trace_id"] == "ct_123"

    def test_correction_has_timestamp(self):
        """Correction has created_at for trace linkage."""
        c = AuroraCorrection(user_id="u1", original_claim="a", corrected_claim="b")
        assert len(c.created_at) > 0

    def test_input_context_has_timestamp(self):
        """Input context has assembled_at for trace linkage."""
        ctx = AuroraInputContext(user_id="u1")
        assert len(ctx.assembled_at) > 0


# ═══════════════════════════════════════════════════════════════════
# Cross-cutting: Proposal Serialization
# ═══════════════════════════════════════════════════════════════════

class TestProposalSerialization:
    """AuroraProposal round-trip serialization."""

    def test_auto_generates_proposal_id(self):
        """If no proposal_id provided, auto-generates one."""
        p = AuroraProposal(proposal_type="hypothesis", confidence=0.7)
        assert p.proposal_id.startswith("ap_")

    def test_source_always_aurora(self):
        """Proposal source is always 'aurora'."""
        p = AuroraProposal(proposal_type="policy_change", confidence=0.8)
        assert p.source == "aurora"

    def test_to_dict_round_trip(self):
        """Proposal survives to_dict."""
        p = AuroraProposal(
            proposal_id="ap_test",
            proposal_type="directive",
            content={"directive_type": "ExecutionDirective"},
            confidence=0.9,
        )
        d = p.to_dict()
        assert d["proposal_id"] == "ap_test"
        assert d["proposal_type"] == "directive"
        assert d["confidence"] == 0.9
        assert d["source"] == "aurora"
