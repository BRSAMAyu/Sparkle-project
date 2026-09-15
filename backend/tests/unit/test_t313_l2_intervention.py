"""
Tests for T3.1.3: L2 Mid Aurora — escalation pattern detection and intervention.

Production scenario coverage:
- Pattern matching with real-world state combinations
- Boundary conditions (exact thresholds)
- User isolation (per-user-per-pattern cooldown)
- Redis failure graceful degradation
- Pattern priority ordering
- Malformed / missing state fields
- Value constraint enforcement
- Cooldown key format and TTL correctness
"""
import pytest
from unittest.mock import AsyncMock, call

from app.aurora.runtime_v1.l2_intervention import (
    L2InterventionEngine,
    _ESCALATION_PATTERNS,
    _L2_COOLDOWN_SECONDS,
)


def _state(key: str, confidence: float, value: str, scope: str = "session") -> dict:
    """Build a single state dict as StateRegister.get_active_states() would produce."""
    return {"state_key": key, "confidence": confidence, "value": value, "scope": scope}


def _states(*specs: tuple[str, float, str]) -> list[dict]:
    """Build multiple states from (key, confidence, value) tuples."""
    return [_state(k, c, v) for k, c, v in specs]


class TestPatternMatching:
    """Core pattern matching logic — the decision brain of L2."""

    @pytest.mark.asyncio
    async def test_knowledge_crisis_from_bottleneck(self):
        """Real scenario: student stuck on TCP congestion concept for 3 turns."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.82, "tcp_congestion", "session"),
            _state("cognitive_load", 0.65, "high", "session"),
        ])
        assert result is not None
        assert result["pattern_name"] == "knowledge_crisis"
        assert result["intervention"] == "error_replan_bridge"
        assert result["energy_level"] == "L2"
        assert "knowledge_bottleneck" in result["matched_states"]
        # cognitive_load is not part of this pattern
        assert "cognitive_load" not in result["matched_states"]

    @pytest.mark.asyncio
    async def test_knowledge_crisis_from_transfer_failure(self):
        """Real scenario: student can't apply learned concept to new problem type."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("transfer_failure", 0.75, "task_abandoned", "task"),
        ])
        assert result is not None
        assert result["pattern_name"] == "knowledge_crisis"
        assert "transfer_failure" in result["matched_states"]

    @pytest.mark.asyncio
    async def test_execution_collapse_needs_both_states(self):
        """execution_collapse requires execution_consistency AND growth_momentum."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        # Only one condition — should not trigger execution_collapse
        result = await engine.check_escalation("user_abc", [
            _state("execution_consistency", 0.85, "task_abandoned", "session"),
        ])
        # May trigger knowledge_crisis if value matches, but NOT execution_collapse
        assert result is None or result["pattern_name"] != "execution_collapse"

        # Both conditions present — should trigger
        result = await engine.check_escalation("user_abc", [
            _state("execution_consistency", 0.85, "task_abandoned", "session"),
            _state("growth_momentum", 0.72, "momentum_stalled", "session"),
        ])
        assert result is not None
        assert result["pattern_name"] == "execution_collapse"
        assert result["intervention"] == "adaptive_replan"

    @pytest.mark.asyncio
    async def test_execution_collapse_value_mismatch_blocks(self):
        """execution_collapse needs specific values — wrong value should not match."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        # execution_consistency with wrong value
        result = await engine.check_escalation("user_abc", [
            _state("execution_consistency", 0.85, "inconsistent_but_improving", "session"),
            _state("growth_momentum", 0.72, "momentum_stalled", "session"),
        ])
        assert result is None or result["pattern_name"] != "execution_collapse"

    @pytest.mark.asyncio
    async def test_exam_underwater_real_deadline(self):
        """Real scenario: exam in 3 days, execution dropping, student overwhelmed."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("deadline_pressure", 0.88, "approaching", "task"),
            _state("execution_consistency", 0.72, "task_abandoned", "session"),
        ])
        assert result is not None
        assert result["pattern_name"] == "exam_underwater"
        assert result["intervention"] == "adaptive_replan"

    @pytest.mark.asyncio
    async def test_burnout_risk_from_affective_pressure(self):
        """Real scenario: sustained high affective_pressure with burnout_risk value."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("affective_pressure", 0.81, "burnout_risk", "session"),
        ])
        assert result is not None
        assert result["pattern_name"] == "burnout_risk"
        assert result["intervention"] == "reduce_load"

    @pytest.mark.asyncio
    async def test_burnout_risk_wrong_value_no_trigger(self):
        """affective_pressure with non-burnout value should not trigger burnout_risk pattern."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("affective_pressure", 0.81, "frustrated_but_motivated", "session"),
        ])
        assert result is None


class TestBoundaryConditions:
    """Threshold precision — exact boundary values matter in production."""

    @pytest.mark.asyncio
    async def test_exact_threshold_triggers(self):
        """Confidence exactly at minimum threshold (0.7) should trigger."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.7, "tcp_congestion"),
        ])
        assert result is not None
        assert result["pattern_name"] == "knowledge_crisis"

    @pytest.mark.asyncio
    async def test_just_below_threshold_no_trigger(self):
        """Confidence 0.01 below threshold should not trigger."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.69, "tcp_congestion"),
        ])
        assert result is None

    @pytest.mark.asyncio
    async def test_exam_underwater_needs_high_deadline(self):
        """exam_underwater requires deadline_pressure ≥ 0.8 (higher than other patterns)."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        # deadline_pressure at 0.79 — should not trigger exam_underwater
        result = await engine.check_escalation("user_abc", [
            _state("deadline_pressure", 0.79, "approaching"),
            _state("execution_consistency", 0.7, "task_abandoned"),
        ])
        assert result is None or result["pattern_name"] != "exam_underwater"

        # At 0.80 — should trigger
        result = await engine.check_escalation("user_abc", [
            _state("deadline_pressure", 0.80, "approaching"),
            _state("execution_consistency", 0.7, "task_abandoned"),
        ])
        assert result is not None
        assert result["pattern_name"] == "exam_underwater"

    @pytest.mark.asyncio
    async def test_zero_confidence_no_trigger(self):
        """Zero confidence should never trigger."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.0, "tcp_congestion"),
        ])
        assert result is None


class TestPatternPriority:
    """First matching pattern wins — ordering matters in production."""

    @pytest.mark.asyncio
    async def test_first_pattern_wins_when_multiple_match(self):
        """If states match multiple patterns, the first in _ESCALATION_PATTERNS wins."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        # States that could match knowledge_crisis (knowledge_bottleneck)
        # AND burnout_risk (affective_pressure)
        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.8, "tcp_congestion"),
            _state("affective_pressure", 0.8, "burnout_risk"),
        ])
        assert result is not None
        # knowledge_crisis is listed first in _ESCALATION_PATTERNS
        assert result["pattern_name"] == "knowledge_crisis"

    @pytest.mark.asyncio
    async def test_pattern_order_follows_definition(self):
        """Verify knowledge_crisis < execution_collapse < exam_underwater < burnout_risk."""
        names = [p["name"] for p in _ESCALATION_PATTERNS]
        assert names == ["knowledge_crisis", "execution_collapse", "exam_underwater", "burnout_risk"]


class TestCooldown:
    """Redis-backed cooldown — prevents intervention spam in production."""

    @pytest.mark.asyncio
    async def test_cooldown_blocks_same_pattern(self):
        """Active cooldown for a pattern prevents re-triggering."""
        redis = AsyncMock()
        redis.get.return_value = b"1"
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.95, "critical"),
        ])
        assert result is None

    @pytest.mark.asyncio
    async def test_cooldown_key_format_per_user_per_pattern(self):
        """Cooldown key must include both user_id and pattern_name for isolation."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        await engine.check_escalation("user_123", [
            _state("knowledge_bottleneck", 0.8, "topic_x"),
        ])

        # Verify the cooldown was set with correct key format
        set_call = redis.set.call_args
        key = set_call[0][0]
        assert key == f"spine:l2_intervention:user_123:knowledge_crisis"
        assert set_call[1]["ex"] == _L2_COOLDOWN_SECONDS

    @pytest.mark.asyncio
    async def test_user_isolation_different_users_independent(self):
        """User A's cooldown should not block User B's intervention."""
        redis = AsyncMock()
        engine = L2InterventionEngine(redis)

        # User A has active cooldown
        async def get_side_effect(key):
            if "user_a" in key:
                return b"1"
            return None
        redis.get.side_effect = get_side_effect

        result_a = await engine.check_escalation("user_a", [
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result_a is None  # blocked by cooldown

        result_b = await engine.check_escalation("user_b", [
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result_b is not None  # different user, no cooldown

    @pytest.mark.asyncio
    async def test_cooldown_per_pattern_not_global(self):
        """Cooldown for one pattern does not block a different pattern."""
        redis = AsyncMock()

        async def get_side_effect(key):
            # Only knowledge_crisis is cooled down
            if "knowledge_crisis" in key:
                return b"1"
            return None
        redis.get.side_effect = get_side_effect
        engine = L2InterventionEngine(redis)

        # knowledge_crisis blocked, but burnout_risk should still trigger
        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.8, "topic"),
            _state("affective_pressure", 0.8, "burnout_risk"),
        ])
        assert result is not None
        assert result["pattern_name"] == "burnout_risk"


class TestResilience:
    """Production failure modes — Redis down, malformed data, etc."""

    @pytest.mark.asyncio
    async def test_redis_get_failure_allows_escalation(self):
        """If Redis cooldown check fails, allow intervention (fail-open for intervention)."""
        redis = AsyncMock()
        redis.get.side_effect = Exception("Redis connection refused")
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result is not None  # fail-open: intervention proceeds

    @pytest.mark.asyncio
    async def test_redis_set_failure_does_not_crash(self):
        """If Redis cooldown write fails, the escalation result is still returned."""
        redis = AsyncMock()
        redis.get.return_value = None
        redis.set.side_effect = Exception("Redis write failed")
        engine = L2InterventionEngine(redis)

        # Should not raise
        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result is not None

    @pytest.mark.asyncio
    async def test_malformed_state_missing_key(self):
        """State dict with missing state_key should be skipped, not crash."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            {"confidence": 0.8, "value": "something", "scope": "session"},  # no state_key
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result is not None
        assert result["pattern_name"] == "knowledge_crisis"

    @pytest.mark.asyncio
    async def test_malformed_state_missing_confidence(self):
        """State with missing confidence defaults to 0.0 — should not trigger."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            {"state_key": "knowledge_bottleneck", "value": "topic", "scope": "session"},
        ])
        assert result is None  # confidence defaults to 0, below threshold

    @pytest.mark.asyncio
    async def test_malformed_state_non_numeric_confidence(self):
        """Non-numeric confidence should be handled gracefully."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        # This will crash with ValueError in _build_state_map float() call
        # — that's expected; StateRegister always produces valid entries
        # but we verify the engine doesn't silently produce wrong results
        try:
            result = await engine.check_escalation("user_abc", [
                {"state_key": "knowledge_bottleneck", "confidence": "high", "value": "topic"},
            ])
            # If it somehow doesn't crash, it should not trigger
            assert result is None
        except (ValueError, TypeError):
            pass  # Expected — invalid confidence is a caller bug

    @pytest.mark.asyncio
    async def test_empty_states_returns_none(self):
        """No active states → no escalation."""
        redis = AsyncMock()
        engine = L2InterventionEngine(redis)
        result = await engine.check_escalation("user_abc", [])
        assert result is None

    @pytest.mark.asyncio
    async def test_irrelevant_states_no_trigger(self):
        """States that don't match any pattern should not trigger escalation."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("cognitive_load", 0.9, "high"),
            _state("material_utilization", 0.85, "low"),
        ])
        assert result is None


class TestResultCompleteness:
    """Every escalation result must have all required fields for downstream consumers."""

    @pytest.mark.asyncio
    async def test_result_has_all_required_fields(self):
        """Verify all fields that PolicyEngine/SpineOrchestrator expect."""
        redis = AsyncMock()
        redis.get.return_value = None
        engine = L2InterventionEngine(redis)

        result = await engine.check_escalation("user_abc", [
            _state("knowledge_bottleneck", 0.8, "topic"),
        ])
        assert result is not None
        required_fields = {"pattern_name", "intervention", "reason", "matched_states", "energy_level"}
        assert required_fields.issubset(set(result.keys()))
        assert result["energy_level"] == "L2"
        assert isinstance(result["matched_states"], list)
        assert len(result["matched_states"]) > 0
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0
