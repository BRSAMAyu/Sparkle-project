from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.evidence import BeliefState, EvidenceDirection, EvidenceSourceType, EvidenceTarget, FusionEngine
from app.services.evidence.unified_evidence import UnifiedEvidence


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.expirations[key] = ttl

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        self.lists[key] = self.lists.get(key, [])[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        return self.lists.get(key, [])[start : end + 1]

    async def lset(self, key: str, index: int, value: str) -> None:
        self.lists[key][index] = value

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    async def incr(self, key: str) -> int:
        current = int(self.store.get(key, "0") or 0) + 1
        self.store[key] = str(current)
        return current


def _evidence(
    *,
    target: EvidenceTarget,
    direction: EvidenceDirection = EvidenceDirection.INCREASE,
    strength: float = 0.8,
    confidence: float = 0.9,
    timestamp: datetime | None = None,
) -> UnifiedEvidence:
    return UnifiedEvidence(
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT,
        target_latent_variable=target,
        direction=direction,
        strength=strength,
        confidence=confidence,
        evidence_text="这个任务看着就烦，我有点头晕。",
        timestamp=timestamp or datetime.now(UTC).replace(tzinfo=None),
    )


def _scoped_evidence(plan_id: str, strength: float) -> UnifiedEvidence:
    evidence = _evidence(target=EvidenceTarget.TASK_AVERSION, strength=strength, confidence=0.9)
    evidence.scope = {"plan_id": plan_id}
    return evidence


def _turn_evidence(target: EvidenceTarget, *, turn_index: int = 1, confidence: float = 0.95) -> UnifiedEvidence:
    evidence = _evidence(target=target, strength=0.9, confidence=confidence)
    evidence.scope = {"conversation_id": "conv-1", "turn_index": turn_index}
    evidence.metadata["extractor"] = "llm"
    return evidence


def test_fusion_engine_high_confidence_evidence_moves_mean_and_reduces_variance() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")

    updated = engine.fuse_evidence(state, _evidence(target=EvidenceTarget.EMOTIONAL_BLOCK))
    variable = updated.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)

    assert variable.mean > 0.75
    assert variable.variance < 0.05
    assert variable.evidence_count == 1
    assert variable.confidence > 0.8


def test_heuristic_fallback_evidence_gets_confidence_discount() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    evidence = _evidence(target=EvidenceTarget.COGNITIVE_LOAD, strength=0.95, confidence=0.95)
    evidence.source_type = EvidenceSourceType.HEURISTIC_FALLBACK
    evidence.metadata["extractor"] = "rule_fallback"

    updated = engine.fuse_evidence(state, evidence)
    variable = updated.get_variable(EvidenceTarget.COGNITIVE_LOAD)

    assert evidence.metadata["confidence_discount_applied"] is True
    assert evidence.metadata["min_observation_variance"] == 0.15
    assert variable.variance >= 0.09


def test_same_turn_same_source_evidence_gets_correlation_discount() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    evidence_items = [
        _turn_evidence(EvidenceTarget.EMOTIONAL_BLOCK),
        _turn_evidence(EvidenceTarget.TASK_AVERSION),
        _turn_evidence(EvidenceTarget.COGNITIVE_LOAD),
    ]

    engine.fuse_many(state, evidence_items)
    summary = engine.summarize_evidence_metadata(evidence_items)

    assert evidence_items[0].metadata["same_source_group_size"] == 3
    assert evidence_items[0].metadata["same_source_group_index"] == 0
    assert "same_source_correlation_discount_applied" not in evidence_items[0].metadata
    assert evidence_items[1].metadata["same_source_correlation_discount_applied"] is True
    assert evidence_items[2].metadata["same_source_correlation_discount_applied"] is True
    assert evidence_items[1].metadata["effective_confidence"] < 0.95
    assert evidence_items[1].metadata["min_observation_variance"] == 0.08
    assert summary["same_source_correlation_discount_count"] == 2
    assert summary["same_source_correlation_group_count"] == 1
    assert summary["same_source_correlation_max_group_size"] == 3


def test_different_turn_evidence_does_not_get_correlation_discount() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    evidence_items = [
        _turn_evidence(EvidenceTarget.EMOTIONAL_BLOCK, turn_index=1),
        _turn_evidence(EvidenceTarget.TASK_AVERSION, turn_index=2),
    ]

    engine.fuse_many(state, evidence_items)
    summary = engine.summarize_evidence_metadata(evidence_items)

    assert "same_source_correlation_discount_applied" not in evidence_items[0].metadata
    assert "same_source_correlation_discount_applied" not in evidence_items[1].metadata
    assert summary["same_source_correlation_discount_count"] == 0
    assert summary["same_source_correlation_group_count"] == 0


def test_belief_state_temporal_decay_increases_uncertainty_and_reverts_toward_neutral() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    now = datetime.now(UTC).replace(tzinfo=None)
    updated = engine.fuse_evidence(
        state,
        _evidence(target=EvidenceTarget.TASK_AVERSION, strength=1.0, confidence=0.95, timestamp=now),
    )
    variable = updated.get_variable(EvidenceTarget.TASK_AVERSION)
    mean_after_update = variable.mean
    variance_after_update = variable.variance

    updated.apply_temporal_decay(now=now + timedelta(hours=24))
    decayed = updated.get_variable(EvidenceTarget.TASK_AVERSION)

    assert decayed.variance > variance_after_update
    assert decayed.mean < mean_after_update
    assert decayed.mean > 0.5


def test_belief_state_temporal_decay_uses_true_half_life_semantics() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    state = BeliefState(user_id="u1")
    variable = state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    variable.mean = 0.9
    variable.unbounded_mean = 0.9
    variable.variance = 0.05
    variable.last_updated = now

    variable.apply_temporal_decay(
        now=now + timedelta(hours=12),
        uncertainty_half_life_hours=12,
        mean_reversion_strength=1.0,
    )

    assert variable.variance == pytest.approx(0.15)
    assert variable.mean == pytest.approx(0.7)


def test_belief_variable_preserves_unbounded_gaussian_mean_before_projection() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    state = BeliefState(user_id="u1")
    variable = state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    variable.mean = 1.0
    variable.unbounded_mean = 1.2
    variable.variance = 0.05
    variable.last_updated = now

    variable.update_from_evidence(
        observed_mean=1.0,
        confidence=0.95,
        observed_at=now,
        evidence_id="e-overflow",
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT.value,
    )

    assert variable.unbounded_mean is not None
    assert variable.unbounded_mean > 1.0
    assert variable.mean == 1.0
    assert variable.projection_applied is True
    diagnostics = state.projection_diagnostics()
    assert diagnostics["projected_target_count"] == 1
    assert diagnostics["projected_targets"]["emotional_block"]["projected_mean"] == 1.0


def test_temporal_decay_reverts_unbounded_mean_before_projection() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    state = BeliefState(user_id="u1")
    variable = state.get_variable(EvidenceTarget.TASK_AVERSION)
    variable.mean = 1.0
    variable.unbounded_mean = 1.2
    variable.variance = 0.05
    variable.last_updated = now

    variable.apply_temporal_decay(
        now=now + timedelta(hours=12),
        uncertainty_half_life_hours=12,
        mean_reversion_strength=1.0,
    )

    assert variable.unbounded_mean == pytest.approx(0.85)
    assert variable.mean == pytest.approx(0.85)
    assert variable.projection_applied is False


def test_router_shadow_projection_marks_support_pressure() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    updated = engine.fuse_many(
        state,
        [
            _evidence(target=EvidenceTarget.EMOTIONAL_BLOCK, strength=0.9, confidence=0.9),
            _evidence(target=EvidenceTarget.TASK_AVERSION, strength=0.7, confidence=0.85),
        ],
    )

    projection = engine.project_router_signals(updated)

    assert projection["signals"]["emotional_block_detected"] is True
    assert projection["signals"]["procrastination_pattern"] is True
    assert projection["shadow_mode"] == "cognitive_first"


def test_fusion_engine_maps_decrease_to_inverse_strength() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    updated = engine.fuse_evidence(
        state,
        _evidence(
            target=EvidenceTarget.COGNITIVE_LOAD,
            direction=EvidenceDirection.DECREASE,
            strength=0.8,
            confidence=0.9,
        ),
    )

    variable = updated.get_variable(EvidenceTarget.COGNITIVE_LOAD)
    assert variable.mean < 0.25


def test_router_shadow_projection_includes_system_dissatisfaction() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    updated = engine.fuse_evidence(
        state,
        _evidence(target=EvidenceTarget.SYSTEM_DISSATISFACTION, strength=0.9, confidence=0.9),
    )

    projection = engine.project_router_signals(updated)

    assert projection["signals"]["system_dissatisfaction"] is True
    assert projection["shadow_mode"] == "cognitive_first"
    assert projection["target_router_mapping"]["system_dissatisfaction"]["impacts_mode"] is True


def test_generate_rl_trace_contains_state_action_projection_and_outcome() -> None:
    state = BeliefState(user_id="u1")
    engine = FusionEngine("u1")
    updated = engine.fuse_evidence(state, _evidence(target=EvidenceTarget.GOAL_CLARITY))

    trace = engine.generate_rl_trace(
        updated,
        action_taken={"mode": "execution_first"},
        actual_router_mode="execution_first",
        outcome="unknown",
        router_snapshot={"mode": "execution_first"},
    )

    assert trace["schema_version"] == "rl_ready_trace.v1"
    assert trace["action_taken"]["mode"] == "execution_first"
    assert trace["actual_router_mode"] == "execution_first"
    assert trace["outcome"] == "unknown"
    assert "goal_clarity_mean" in trace["belief_state_vector"]
    assert trace["belief_source_breakdown"]["total"]["conversational_implicit"] == 1
    assert trace["belief_variable_evidence_counts"]["goal_clarity"] == 1
    assert "router_shadow_projection" in trace
    assert trace["belief_projection_diagnostics"]["projected_target_count"] == 0


@pytest.mark.asyncio
async def test_fusion_engine_persists_state_and_trace_to_redis() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")

    state = await engine.update_user_state(
        redis,
        user_id="u1",
        evidence_items=[_evidence(target=EvidenceTarget.COGNITIVE_LOAD, strength=0.6, confidence=0.8)],
    )
    trace = engine.generate_rl_trace(state, action_taken={"mode": "balanced"})
    await engine.append_trace(redis, user_id="u1", trace=trace)

    saved = await engine.load_state(redis, "u1")
    assert saved.get_variable(EvidenceTarget.COGNITIVE_LOAD).mean > 0.57
    assert redis.lists[engine.BELIEF_TRACE_KEY.format(user_id="u1")]


@pytest.mark.asyncio
async def test_fusion_engine_writes_goal_or_plan_scoped_belief_without_polluting_other_scope() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")

    plan_a = await engine.update_user_state(redis, user_id="u1", evidence_items=[_scoped_evidence("plan-a", 0.95)])
    await engine.update_user_state(redis, user_id="u1", evidence_items=[_scoped_evidence("plan-b", 0.10)])

    scoped_a = await engine.load_state(redis, "u1", scope_level="plan", scope_id="plan-a")
    scoped_b = await engine.load_state(redis, "u1", scope_level="plan", scope_id="plan-b")

    assert plan_a.scope_metadata["belief_scope_level"] == "plan"
    assert scoped_a.get_variable(EvidenceTarget.TASK_AVERSION).mean > 0.80
    assert scoped_b.get_variable(EvidenceTarget.TASK_AVERSION).mean < 0.25


@pytest.mark.asyncio
async def test_fusion_engine_binds_outcome_to_matching_unknown_trace() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")
    state = engine.fuse_evidence(BeliefState(user_id="u1"), _evidence(target=EvidenceTarget.GOAL_CLARITY))
    trace = engine.generate_rl_trace(
        state,
        action_taken={"mode": "execution_first", "routing_trace_id": "rt-1"},
        actual_router_mode="execution_first",
        router_snapshot={"routing_trace_id": "rt-1"},
    )
    await engine.append_trace(redis, user_id="u1", trace=trace)

    updated = await engine.bind_outcome_to_recent_trace(
        redis,
        user_id="u1",
        outcome="task_completion",
        reward={"signal_type": "task.completed", "total_reward": 1.0},
        match={"routing_trace_id": "rt-1"},
    )

    assert updated is not None
    assert updated["outcome"] == "task_completion"
    assert updated["training_eligible"] is True
    assert updated["outcome_binding"]["matched_fields"] == ["routing_trace_id"]


@pytest.mark.asyncio
async def test_fusion_engine_binds_weak_heuristic_as_non_training_label() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")
    state = engine.fuse_evidence(BeliefState(user_id="u1"), _evidence(target=EvidenceTarget.GOAL_CLARITY))
    trace = engine.generate_rl_trace(
        state,
        action_taken={"mode": "balanced", "routing_trace_id": "rt-weak"},
        actual_router_mode="balanced",
        router_snapshot={"routing_trace_id": "rt-weak"},
    )
    await engine.append_trace(redis, user_id="u1", trace=trace)

    updated = await engine.bind_outcome_to_recent_trace(
        redis,
        user_id="u1",
        outcome="weak_routing_success",
        reward={"signal_type": "routing.weak_heuristic", "outcome_strength": "weak_heuristic"},
        match={"routing_trace_id": "rt-weak"},
    )

    assert updated is not None
    assert updated["training_eligible"] is False
    assert updated["outcome_binding"]["outcome_strength"] == "weak_heuristic"


@pytest.mark.asyncio
async def test_fusion_engine_diagnoses_outcome_binding_id_overlap() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")
    state = engine.fuse_evidence(BeliefState(user_id="u1"), _evidence(target=EvidenceTarget.GOAL_CLARITY))
    trace = engine.generate_rl_trace(
        state,
        action_taken={"mode": "execution_first", "routing_trace_id": "rt-1"},
        actual_router_mode="execution_first",
        router_snapshot={
            "routing_trace_id": "rt-1",
            "route_history_decision_id": "decision-1",
            "task_id": "task-1",
        },
    )
    await engine.append_trace(redis, user_id="u1", trace=trace)

    diagnostics = await engine.diagnose_outcome_binding(
        redis,
        user_id="u1",
        match={"routing_trace_id": "rt-1", "task_id": "task-1"},
    )

    assert diagnostics["schema_version"] == "outcome_binding_diagnostics.v1"
    assert diagnostics["bindable"] is True
    assert diagnostics["best_match_score"] == 7
    assert diagnostics["best_matched_fields"] == ["routing_trace_id", "task_id"]
    assert diagnostics["trace_id_coverage"]["routing_trace_id"] == 1
    assert diagnostics["trace_id_coverage"]["route_history_decision_id"] == 1
    assert diagnostics["blockers"] == []


@pytest.mark.asyncio
async def test_fusion_engine_diagnoses_unbindable_outcome_event() -> None:
    redis = FakeRedis()
    engine = FusionEngine("u1")
    state = engine.fuse_evidence(BeliefState(user_id="u1"), _evidence(target=EvidenceTarget.GOAL_CLARITY))
    trace = engine.generate_rl_trace(
        state,
        action_taken={"mode": "execution_first", "routing_trace_id": "rt-1"},
        actual_router_mode="execution_first",
        router_snapshot={"routing_trace_id": "rt-1"},
    )
    await engine.append_trace(redis, user_id="u1", trace=trace)

    diagnostics = await engine.diagnose_outcome_binding(
        redis,
        user_id="u1",
        match={"task_id": "task-missing"},
    )

    assert diagnostics["bindable"] is False
    assert diagnostics["best_match_score"] == 0
    assert diagnostics["blockers"] == ["no_trace_id_overlap"]
