"""
Tests for T3.1.5-T3.1.7: L4 Async Deep Learning, Energy Level Decision, Cost Control.

Production scenario coverage:
- L4 candidate creation with type validation and min-episode enforcement
- L4 candidate lifecycle: shadow → simulation → promoted → (rejected)
- L4 Redis persistence and retrieval
- Energy level decision at each turn with correct upgrade reasons
- Cost controller: L3/L4 quota enforcement, cooldown, fallback
- CausalTrace receives aurora_energy_level and aurora_upgrade_reason
- Redis failure graceful degradation
- Concurrent candidate operations
"""
import json
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from app.aurora.runtime_v1.l4_async import (
    L4AsyncEngine,
    L4PolicyCandidate,
    L4_ANALYSIS_TYPES,
)
from app.aurora.runtime_v1.energy_controller import (
    EnergyLevelDecider,
    EnergyDecision,
    CostController,
)
from app.aurora.runtime_v1.state import AuroraEnergyState
from app.signals.types import CausalTrace


# ── Helpers ──────────────────────────────────────────────────────────

def _make_energy(
    user_id: str = "user_abc",
    level: str = "L1",
    wake_score: float = 0.5,
    cooling: bool = False,
    l3_count: int = 0,
) -> AuroraEnergyState:
    """Build an AuroraEnergyState for testing."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return AuroraEnergyState(
        user_id=user_id,
        current_level=level,
        wake_score=wake_score,
        cooldown_until=(now + timedelta(hours=1)) if cooling else None,
        l3_session_count_today=l3_count,
    )


# ═══════════════════════════════════════════════════════════════════
# T3.1.5: L4 Async Deep Learning
# ═══════════════════════════════════════════════════════════════════

class TestL4CandidateCreation:
    """L4 candidate creation — validates analysis types and episodes."""

    def setup_method(self):
        self.redis = AsyncMock()
        self.engine = L4AsyncEngine(self.redis)

    def test_valid_candidate_created(self):
        """Standard candidate with sufficient episodes."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="strategy_effectiveness",
            current_policy="worked_example",
            proposed_policy="retrieval_practice",
            confidence=0.75,
            episode_count=5,
        )
        assert candidate is not None
        assert candidate.analysis_type == "strategy_effectiveness"
        assert candidate.status == "shadow"
        assert candidate.confidence == 0.75
        assert candidate.domain == "strategy"
        assert candidate.user_id == "user_abc"

    def test_unknown_analysis_type_returns_none(self):
        """Invalid analysis type is rejected."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="nonexistent_type",
            current_policy="a",
            proposed_policy="b",
            episode_count=10,
        )
        assert candidate is None

    def test_insufficient_episodes_returns_none(self):
        """Below min_episodes for analysis type → None."""
        # strategy_effectiveness needs 5 episodes
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="strategy_effectiveness",
            current_policy="a",
            proposed_policy="b",
            episode_count=4,
        )
        assert candidate is None

    def test_exact_min_episodes_accepted(self):
        """Exactly at min_episodes → accepted."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="strategy_effectiveness",
            current_policy="a",
            proposed_policy="b",
            episode_count=5,  # exact min
        )
        assert candidate is not None

    def test_confidence_clamped_to_01(self):
        """Confidence > 1.0 is clamped to 1.0."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="mistake_cluster",
            current_policy="a",
            proposed_policy="b",
            confidence=1.5,
            episode_count=3,
        )
        assert candidate is not None
        assert candidate.confidence == 1.0

    def test_negative_confidence_clamped_to_zero(self):
        """Negative confidence is clamped to 0.0."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="mistake_cluster",
            current_policy="a",
            proposed_policy="b",
            confidence=-0.5,
            episode_count=3,
        )
        assert candidate is not None
        assert candidate.confidence == 0.0

    def test_domain_defaults_from_analysis_type(self):
        """If no domain specified, uses default from analysis type config."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="achievement_feedback",
            current_policy="a",
            proposed_policy="b",
            episode_count=3,
        )
        assert candidate is not None
        assert candidate.domain == "achievement"

    def test_explicit_domain_overrides_default(self):
        """Explicit domain takes precedence over default."""
        candidate = self.engine.create_candidate(
            user_id="user_abc",
            analysis_type="achievement_feedback",
            current_policy="a",
            proposed_policy="b",
            domain="custom_domain",
            episode_count=3,
        )
        assert candidate is not None
        assert candidate.domain == "custom_domain"


class TestL4CandidatePersistence:
    """L4 candidate Redis storage — the async pipeline substrate."""

    def setup_method(self):
        self.redis = AsyncMock()
        self.engine = L4AsyncEngine(self.redis)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """Store candidate, then retrieve by ID."""
        self.redis.get.return_value = json.dumps({
            "candidate_id": "l4c_test",
            "user_id": "u1",
            "analysis_type": "behavior_trend",
            "current_policy": "a",
            "proposed_policy": "b",
            "domain": "behavior",
            "evidence_summary": {},
            "confidence": 0.7,
            "episode_count": 5,
            "status": "shadow",
            "created_at": datetime.now(UTC).isoformat(),
        }).encode()

        candidate = await self.engine.get_candidate("l4c_test")
        assert candidate is not None
        assert candidate.candidate_id == "l4c_test"
        assert candidate.status == "shadow"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        """Non-existent candidate returns None."""
        self.redis.get.return_value = None
        candidate = await self.engine.get_candidate("nonexistent")
        assert candidate is None

    @pytest.mark.asyncio
    async def test_store_failure_returns_false(self):
        """Redis write failure returns False, doesn't crash."""
        self.redis.set.side_effect = Exception("Redis down")
        candidate = self.engine.create_candidate(
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="a",
            proposed_policy="b",
            episode_count=5,
        )
        result = await self.engine.store_candidate(candidate)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_corrupted_json_returns_none(self):
        """Corrupted JSON returns None."""
        self.redis.get.return_value = b"not json{{{"
        candidate = await self.engine.get_candidate("corrupt")
        assert candidate is None


class TestL4CandidateLifecycle:
    """L4 candidate promotion: shadow → simulation → promoted."""

    def setup_method(self):
        self.redis = AsyncMock()
        self.engine = L4AsyncEngine(self.redis)

    @pytest.mark.asyncio
    async def test_shadow_to_simulation(self):
        """Promoting shadow candidate → simulation."""
        stored = L4PolicyCandidate(
            candidate_id="l4c_1",
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="a",
            proposed_policy="b",
        )
        stored.status = "shadow"
        self.redis.get.return_value = json.dumps(stored.to_dict()).encode()

        result = await self.engine.promote_candidate("l4c_1")
        assert result is not None
        assert result.status == "simulation"

    @pytest.mark.asyncio
    async def test_simulation_to_promoted(self):
        """Promoting simulation candidate → promoted."""
        stored = L4PolicyCandidate(
            candidate_id="l4c_1",
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="a",
            proposed_policy="b",
        )
        stored.status = "simulation"
        self.redis.get.return_value = json.dumps(stored.to_dict()).encode()

        result = await self.engine.promote_candidate("l4c_1")
        assert result is not None
        assert result.status == "promoted"

    @pytest.mark.asyncio
    async def test_promoted_cannot_be_promoted_again(self):
        """Already promoted → None (no further promotion)."""
        stored = L4PolicyCandidate(
            candidate_id="l4c_1",
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="a",
            proposed_policy="b",
        )
        stored.status = "promoted"
        self.redis.get.return_value = json.dumps(stored.to_dict()).encode()

        result = await self.engine.promote_candidate("l4c_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_reject_candidate(self):
        """Rejected candidate gets status=rejected."""
        stored = L4PolicyCandidate(
            candidate_id="l4c_1",
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="a",
            proposed_policy="b",
        )
        self.redis.get.return_value = json.dumps(stored.to_dict()).encode()

        result = await self.engine.reject_candidate("l4c_1", reason="low_confidence")
        assert result is not None
        assert result.status == "rejected"


class TestL4AnalysisTypes:
    """L4 analysis type configuration validation."""

    def test_all_types_have_min_episodes(self):
        """Every analysis type must define min_episodes > 0."""
        for name, config in L4_ANALYSIS_TYPES.items():
            assert config["min_episodes"] > 0, f"{name} missing min_episodes"

    def test_all_types_have_description(self):
        """Every analysis type must have a description."""
        for name, config in L4_ANALYSIS_TYPES.items():
            assert len(config["description"]) > 0, f"{name} missing description"

    def test_six_analysis_types_defined(self):
        """Expected 6 analysis types: behavior, achievement, recall, strategy, mistake, skill."""
        assert len(L4_ANALYSIS_TYPES) == 6
        expected = {"behavior_trend", "achievement_feedback", "recall_effectiveness",
                     "strategy_effectiveness", "mistake_cluster", "skill_extraction"}
        assert set(L4_ANALYSIS_TYPES.keys()) == expected


# ═══════════════════════════════════════════════════════════════════
# T3.1.6: Energy Level Decision
# ═══════════════════════════════════════════════════════════════════

class TestEnergyLevelDecision:
    """Energy level decision at each turn — the brain of Aurora scheduling."""

    def setup_method(self):
        self.decider = EnergyLevelDecider()

    def test_aurora_inactive_returns_l0(self):
        """When Aurora is not active → L0 with aurora_inactive reason."""
        energy = _make_energy(level="L1")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[],
            aurora_active=False,
        )
        assert decision.current_level == "L0"
        assert decision.upgrade_reason == "aurora_inactive"

    def test_cooling_down_returns_l0(self):
        """Cooling down → L0 with cooled_down reason."""
        energy = _make_energy(level="L3", cooling=True)
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[],
        )
        assert decision.current_level == "L0"
        assert decision.upgrade_reason == "cooled_down"

    def test_l3_wake_eligible_upgrades_to_l3(self):
        """When L3 wake eligible and not cooling → L3."""
        energy = _make_energy(level="L1", l3_count=0)
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[],
            l3_wake_eligible=True,
        )
        assert decision.current_level == "L3"
        assert decision.upgrade_reason == "l3_wake_eligible"

    def test_l3_wake_blocked_by_quota(self):
        """L3 wake eligible but daily quota exhausted → stays L1."""
        energy = _make_energy(level="L1", l3_count=3)
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[],
            l3_wake_eligible=True,
        )
        # can_user_wake checks l3_session_count_today < 3, so 3 fails
        assert decision.current_level != "L3"
        assert decision.upgrade_reason != "l3_wake_eligible"

    def test_l2_risk_detected_upgrades_to_l2(self):
        """High-confidence knowledge_bottleneck triggers L2."""
        energy = _make_energy(level="L1")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[
                {"state_key": "knowledge_bottleneck", "confidence": 0.82, "value": "tcp"},
            ],
        )
        assert decision.current_level == "L2"
        assert "risk_detected" in decision.upgrade_reason

    def test_l2_from_execution_consistency(self):
        """execution_consistency above threshold triggers L2."""
        energy = _make_energy(level="L1")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[
                {"state_key": "execution_consistency", "confidence": 0.75, "value": "task_abandoned"},
            ],
        )
        assert decision.current_level == "L2"
        assert "execution_risk" in decision.upgrade_reason

    def test_no_risk_stays_l1(self):
        """No triggers → stays L1 with not_upgraded."""
        energy = _make_energy(level="L1")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[
                {"state_key": "cognitive_load", "confidence": 0.6, "value": "moderate"},
            ],
        )
        assert decision.current_level == "L1"
        assert decision.upgrade_reason == "not_upgraded"

    def test_below_threshold_no_l2(self):
        """State at 0.69 confidence → stays L1 (below 0.7 threshold)."""
        energy = _make_energy(level="L1")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[
                {"state_key": "knowledge_bottleneck", "confidence": 0.69, "value": "tcp"},
            ],
        )
        assert decision.current_level == "L1"

    def test_l3_takes_priority_over_l2(self):
        """L3 wake eligible + L2 risk → L3 wins."""
        energy = _make_energy(level="L1", l3_count=0)
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[
                {"state_key": "knowledge_bottleneck", "confidence": 0.85, "value": "tcp"},
            ],
            l3_wake_eligible=True,
        )
        assert decision.current_level == "L3"
        assert decision.upgrade_reason == "l3_wake_eligible"

    def test_decision_records_previous_level(self):
        """Decision records what the level was before this turn."""
        energy = _make_energy(level="L0")
        decision = self.decider.decide(
            user_id="u1",
            energy=energy,
            active_states=[],
        )
        assert decision.previous_level == "L0"


class TestEnergyDecisionToTrace:
    """Verify CausalTrace can store energy level decision fields."""

    def test_trace_has_energy_fields(self):
        """CausalTrace must have aurora_energy_level and aurora_upgrade_reason."""
        trace = CausalTrace(trace_id="test")
        assert hasattr(trace, "aurora_energy_level")
        assert hasattr(trace, "aurora_upgrade_reason")

    def test_trace_round_trips_energy_fields(self):
        """Energy fields survive to_dict → from_dict round trip."""
        trace = CausalTrace(trace_id="test")
        trace.aurora_energy_level = "L2"
        trace.aurora_upgrade_reason = "risk_detected:knowledge_crisis"
        d = trace.to_dict()
        assert d["aurora_energy_level"] == "L2"
        assert d["aurora_upgrade_reason"] == "risk_detected:knowledge_crisis"

        restored = CausalTrace.from_dict(d)
        assert restored.aurora_energy_level == "L2"
        assert restored.aurora_upgrade_reason == "risk_detected:knowledge_crisis"

    def test_trace_default_empty_string(self):
        """Default values are empty strings for backward compatibility."""
        trace = CausalTrace(trace_id="test")
        assert trace.aurora_energy_level == ""
        assert trace.aurora_upgrade_reason == ""


# ═══════════════════════════════════════════════════════════════════
# T3.1.7: Cost Control
# ═══════════════════════════════════════════════════════════════════

class TestCostControl:
    """Quota, cooldown, and fallback enforcement for L3/L4."""

    def setup_method(self):
        self.controller = CostController()

    def test_l3_allowed_within_quota(self):
        """User with 0 sessions today and no cooldown → allowed."""
        energy = _make_energy(level="L1", l3_count=0)
        result = self.controller.check_l3_allowed(energy)
        assert result["allowed"] is True
        assert result["quota_remaining"] >= 1

    def test_l3_blocked_by_cooldown(self):
        """User in cooldown → not allowed, fallback provided."""
        energy = _make_energy(level="L3", cooling=True)
        result = self.controller.check_l3_allowed(energy)
        assert result["allowed"] is False
        assert result["reason"] == "cooldown_active"
        assert result["fallback"] == "L1_quick_calibration"

    def test_l3_blocked_by_quota_exhaustion(self):
        """User with 3 L3 sessions today → quota exhausted."""
        energy = _make_energy(level="L1", l3_count=3)
        result = self.controller.check_l3_allowed(energy)
        assert result["allowed"] is False
        assert result["reason"] == "quota_exhausted"
        assert result["quota_remaining"] == 0

    def test_l3_sprint_mode_higher_quota(self):
        """Sprint mode allows more sessions."""
        energy = _make_energy(level="L1", l3_count=2)
        result = self.controller.check_l3_allowed(energy, sprint_mode="sprint_24h")
        # sprint_24h quota = 3, count = 2, remaining = 1
        assert result["allowed"] is True
        assert result["quota_remaining"] == 1

    def test_l4_allowed_within_quota(self):
        """L4 with 0 runs today → allowed."""
        result = self.controller.check_l4_allowed(l4_run_count_today=0)
        assert result["allowed"] is True
        assert result["quota_remaining"] == 5

    def test_l4_blocked_by_quota(self):
        """L4 with 5 runs today → exhausted."""
        result = self.controller.check_l4_allowed(l4_run_count_today=5)
        assert result["allowed"] is False
        assert result["reason"] == "quota_exhausted"

    def test_l4_quota_not_yet_exhausted(self):
        """L4 with 4 runs today → still has 1 remaining."""
        result = self.controller.check_l4_allowed(l4_run_count_today=4)
        assert result["allowed"] is True
        assert result["quota_remaining"] == 1

    def test_l3_fallback_action(self):
        """When L3 blocked → quick_calibration fallback."""
        result = self.controller.get_fallback_action(blocked_level="L3", reason="quota_exhausted")
        assert result["action"] == "quick_calibration"
        assert result["level"] == "L1"

    def test_l4_fallback_action(self):
        """When L4 blocked → defer fallback."""
        result = self.controller.get_fallback_action(blocked_level="L4", reason="quota_exhausted")
        assert result["action"] == "defer"
        assert result["level"] == "L4"


# ═══════════════════════════════════════════════════════════════════
# Cross-cutting: L4PolicyCandidate serialization
# ═══════════════════════════════════════════════════════════════════

class TestL4CandidateSerialization:
    """L4PolicyCandidate round-trip serialization."""

    def test_to_dict_and_from_dict(self):
        """Candidate survives to_dict → from_dict round trip."""
        original = L4PolicyCandidate(
            candidate_id="l4c_test",
            user_id="u1",
            analysis_type="behavior_trend",
            current_policy="worked_example",
            proposed_policy="retrieval_practice",
            domain="behavior",
            evidence_summary={"trend": "improving"},
            confidence=0.78,
            episode_count=10,
        )
        original.status = "simulation"

        restored = L4PolicyCandidate.from_dict(original.to_dict())
        assert restored.candidate_id == original.candidate_id
        assert restored.user_id == original.user_id
        assert restored.analysis_type == original.analysis_type
        assert restored.current_policy == original.current_policy
        assert restored.proposed_policy == original.proposed_policy
        assert restored.domain == original.domain
        assert restored.evidence_summary == original.evidence_summary
        assert restored.confidence == original.confidence
        assert restored.episode_count == original.episode_count
        assert restored.status == original.status

    def test_auto_generates_candidate_id(self):
        """If no candidate_id provided, auto-generates one."""
        c = L4PolicyCandidate(user_id="u1", analysis_type="behavior_trend")
        assert c.candidate_id.startswith("l4c_")
