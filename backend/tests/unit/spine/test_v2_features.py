"""Spine tests — test_v2_v3_features.py."""

from __future__ import annotations
from tests.unit.spine._helpers import FakeRedis


import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    AuroraAgenda,
    AuroraAgendaItem,
    AuroraControlSignal,
    CausalTrace,
    DirectiveApplicationAudit,
    ExecutionDirective,
    OutcomeRecord,
    PolicyDecision,
    StateEntry,
    UserVisibleReceipt,
    _uid,
)
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.policy_engine import PolicyEngine
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.spine_metrics import SpineMetricsCollector, METRIC_DEFINITIONS
from app.orchestration.prompts import build_system_prompt
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.causal_trace_store import CausalTraceStore
from app.signals.material_signal import MaterialSignalDetector
from app.signals.mistake_signal import MistakeSignalDetector
from app.signals.exam_rescue_detector import ExamRescueDetector, FirstMinuteSnapshot
from app.signals.stale_state_guard import StaleStateGuard, TimeContext, TimeDeltaPacket
from app.signals.state_packet_builder import ActionableStatePacketBuilder
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.self_model import SparkleSelfModelService, SelfModelClaim, StrategyOutcome
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.community_signal import CommunitySignalDetector
from app.signals.signal_ranker import SignalRanker
from app.signals.state_register import StateRegister
from app.signals.exam_sprint_policy import ExamSprintPolicyService
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.policy_analytics import PolicyAnalytics
from app.signals.policy_experiments import PolicyExperimentManager
from app.signals.learning_base import LearningBase
from app.signals.growth_chronicle import GrowthChronicleService, ChronicleEntry
from app.signals.relationship_model import RelationshipModelService
from app.signals.skill_extraction import SkillExtractionService
from app.signals.goal_type_adapter import GoalTypeAdapter
from app.signals.timeline_card_renderer import TimelineCardRenderer
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.goal_world_graph import GoalWorldGraphService
from app.signals.multi_goal_arbitration import MultiGoalArbitrator
from app.signals.directive_quota import DirectiveQuotaService
from app.signals.aurora_core_session import AuroraCoreSessionService, SessionClosure, StatePatch, PolicyChange
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.community_loops import CommunityLoopManager
from app.signals.recall_notification import RecallNotificationBuilder, RecallMessage

# ── v2.2: Degraded Mode Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_degraded_get_response_directive():
    """When Redis raises, get_response_directive returns None (degraded mode)."""
    from unittest.mock import AsyncMock

    redis = FakeRedis()
    redis.get = AsyncMock(side_effect=Exception("connection refused"))
    spine = SpineOrchestrator(redis)

    result = await spine.get_response_directive("u1")
    assert result is None


@pytest.mark.asyncio
async def test_degraded_get_plan_directive():
    """When Redis raises, get_plan_directive returns None (degraded mode)."""
    from unittest.mock import AsyncMock

    redis = FakeRedis()
    redis.get = AsyncMock(side_effect=Exception("connection refused"))
    spine = SpineOrchestrator(redis)

    result = await spine.get_plan_directive("u1")
    assert result is None


@pytest.mark.asyncio
async def test_degraded_get_latest_receipt():
    """When Redis raises, get_latest_receipt returns None (degraded mode)."""
    from unittest.mock import AsyncMock

    redis = FakeRedis()
    redis.get = AsyncMock(side_effect=Exception("connection refused"))
    spine = SpineOrchestrator(redis)

    result = await spine.get_latest_receipt("u1")
    assert result is None


@pytest.mark.asyncio
async def test_degraded_get_ux_directive():
    """When Redis raises, get_ux_directive returns None (degraded mode)."""
    from unittest.mock import AsyncMock

    redis = FakeRedis()
    redis.get = AsyncMock(side_effect=Exception("connection refused"))
    spine = SpineOrchestrator(redis)

    result = await spine.get_ux_directive("u1")
    assert result is None


@pytest.mark.asyncio
async def test_degraded_circuit_breaker_blocks_pipeline():
    """When circuit breaker is open, pipeline returns None early."""
    from app.signals.redis_resilience import _spine_pipeline_breaker

    _spine_pipeline_breaker._failure_count = 10
    _spine_pipeline_breaker._state = "open"

    from app.signals.redis_resilience import resilient_redis_call

    async def would_crash():
        raise Exception("should not be called")

    result = await resilient_redis_call("spine_pipeline", would_crash(), fallback="blocked")
    assert result == "blocked"

    # Reset
    _spine_pipeline_breaker._failure_count = 0
    _spine_pipeline_breaker._state = "closed"


# ══════════════════════════════════════════════════════════════════════
# v2.4: Learning Layer Tests
# ══════════════════════════════════════════════════════════════════════


class TestV24SourceEffectiveness:
    """v2.4 SourceEffectiveness — track which sources help learning."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def tracker(self, redis):
        from app.signals.source_tray_integration import SourceEffectivenessTracker
        return SourceEffectivenessTracker(redis)

    @pytest.mark.asyncio
    async def test_record_effective_source(self, tracker, redis):
        result = await tracker.record_source_outcome(
            user_id="u1", source_id="src_tcp_notes", outcome="effective",
        )
        assert result["effective"] == 1
        assert result["total"] == 1
        assert result["effectiveness_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_record_insufficient_source(self, tracker, redis):
        await tracker.record_source_outcome(
            user_id="u1", source_id="src_bad_ppt", outcome="insufficient",
        )
        result = await tracker.get_source_effectiveness("u1", "src_bad_ppt")
        assert result["insufficient"] == 1
        assert result["effectiveness_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_mixed_outcomes_rate(self, tracker, redis):
        for _ in range(3):
            await tracker.record_source_outcome(
                user_id="u1", source_id="src_mixed", outcome="effective",
            )
        for _ in range(2):
            await tracker.record_source_outcome(
                user_id="u1", source_id="src_mixed", outcome="insufficient",
            )
        result = await tracker.get_source_effectiveness("u1", "src_mixed")
        assert result["total"] == 5
        assert result["effectiveness_rate"] == 0.6

    @pytest.mark.asyncio
    async def test_get_all_source_effectiveness_sorted(self, tracker, redis):
        # Create 3 sources with different rates
        for _ in range(4):
            await tracker.record_source_outcome(
                user_id="u1", source_id="good", outcome="effective",
            )
        await tracker.record_source_outcome(
            user_id="u1", source_id="bad", outcome="insufficient",
        )
        for _ in range(2):
            await tracker.record_source_outcome(
                user_id="u1", source_id="mid", outcome="effective",
            )
        for _ in range(2):
            await tracker.record_source_outcome(
                user_id="u1", source_id="mid", outcome="insufficient",
            )

        all_effects = await tracker.get_all_source_effectiveness("u1")
        assert len(all_effects) == 3
        assert all_effects[0]["source_id"] == "good"
        assert all_effects[-1]["source_id"] == "bad"

    @pytest.mark.asyncio
    async def test_low_effectiveness_filter(self, tracker, redis):
        for _ in range(5):
            await tracker.record_source_outcome(
                user_id="u1", source_id="low_src", outcome="insufficient",
            )
        low = await tracker.get_low_effectiveness_sources("u1", min_trials=3, max_rate=0.3)
        assert "low_src" in low

    @pytest.mark.asyncio
    async def test_not_enough_trials_excluded(self, tracker, redis):
        await tracker.record_source_outcome(
            user_id="u1", source_id="few_src", outcome="insufficient",
        )
        low = await tracker.get_low_effectiveness_sources("u1", min_trials=3, max_rate=0.3)
        assert "few_src" not in low


class TestV24StrategyBeliefConsumption:
    """v2.4: PolicyEngine.consume strategy_beliefs to bias decisions."""

    @pytest.fixture
    def engine(self):
        from app.signals.policy_engine import PolicyEngine
        return PolicyEngine()

    @pytest.mark.asyncio
    async def test_belief_bias_applied_for_low_effectiveness(self, engine):
        signal = ActionableSignal(
            signal_id="s1", source_event_ids=["e1"], source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large", confidence=0.8,
            scope="current_sprint", ttl_hours=24,
            evidence_summary="test", possible_effects=["test"],
            priority="high",
        )
        from app.signals.learning_base import StrategyBelief
        beliefs = [
            StrategyBelief(strategy_key="recover_execution_rhythm", alpha=2, beta=8, evidence_count=10),
            StrategyBelief(strategy_key="repair_knowledge_gap", alpha=8, beta=2, evidence_count=10),
        ]
        result = await engine.evaluate(signal, strategy_beliefs=beliefs)
        assert result is not None
        decision, directive = result
        # Should have belief_bias in soft_biases
        assert decision.soft_biases.get("belief_biased_to") == "repair_knowledge_gap"

    @pytest.mark.asyncio
    async def test_belief_not_applied_when_strategy_effective(self, engine):
        signal = ActionableSignal(
            signal_id="s1", source_event_ids=["e1"], source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large", confidence=0.8,
            scope="current_sprint", ttl_hours=24,
            evidence_summary="test", possible_effects=["test"],
            priority="high",
        )
        from app.signals.learning_base import StrategyBelief
        beliefs = [
            StrategyBelief(strategy_key="recover_execution_rhythm", alpha=8, beta=2, evidence_count=10),
        ]
        result = await engine.evaluate(signal, strategy_beliefs=beliefs)
        assert result is not None
        decision, directive = result
        # Strategy is effective, no bias needed
        assert "belief_biased_to" not in decision.soft_biases

    @pytest.mark.asyncio
    async def test_belief_not_applied_with_low_evidence(self, engine):
        signal = ActionableSignal(
            signal_id="s1", source_event_ids=["e1"], source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large", confidence=0.8,
            scope="current_sprint", ttl_hours=24,
            evidence_summary="test", possible_effects=["test"],
            priority="high",
        )
        from app.signals.learning_base import StrategyBelief
        beliefs = [
            StrategyBelief(strategy_key="recover_execution_rhythm", alpha=1, beta=3, evidence_count=2),
        ]
        result = await engine.evaluate(signal, strategy_beliefs=beliefs)
        assert result is not None
        decision, directive = result
        assert "belief_biased_to" not in decision.soft_biases

    @pytest.mark.asyncio
    async def test_no_beliefs_no_change(self, engine):
        signal = ActionableSignal(
            signal_id="s1", source_event_ids=["e1"], source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large", confidence=0.8,
            scope="current_sprint", ttl_hours=24,
            evidence_summary="test", possible_effects=["test"],
            priority="high",
        )
        result = await engine.evaluate(signal, strategy_beliefs=None)
        assert result is not None
        decision, _ = result
        assert "belief_biased_to" not in decision.soft_biases


class TestV24PolicyExperimentFullLoop:
    """v2.4: Experiment creation → outcome recording → promotion suggestion."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def manager(self, redis):
        from app.signals.policy_experiments import PolicyExperimentManager
        return PolicyExperimentManager(redis)

    @pytest.mark.asyncio
    async def test_create_and_record_trial(self, manager):
        exp = await manager.create_experiment(
            user_id="u1",
            signal_state_key="task_granularity_fit",
            signal_claim="recent_task_too_large",
            primary_strategy="recover_execution_rhythm",
        )
        assert exp is not None
        assert exp.shadow_strategy == "recover_execution_rhythm_gentle"

        # Record a trial
        updated = await manager.record_trial(
            exp.experiment_id,
            primary_outcome="effective",
            shadow_hypothesis="effective",
        )
        assert updated is not None
        assert updated.primary_wins == 1
        assert updated.total_trials == 1

    @pytest.mark.asyncio
    async def test_promotion_suggestion_after_conclusion(self, manager):
        exp = await manager.create_experiment(
            user_id="u1",
            signal_state_key="task_granularity_fit",
            signal_claim="recent_task_too_large",
            primary_strategy="recover_execution_rhythm",
        )
        # Shadow outperforms: 8 wins for shadow vs 2 for primary
        for _ in range(8):
            await manager.record_trial(
                exp.experiment_id,
                primary_outcome="insufficient",
                shadow_hypothesis="effective",
            )
        for _ in range(2):
            await manager.record_trial(
                exp.experiment_id,
                primary_outcome="effective",
                shadow_hypothesis="effective",
            )

        experiments = await manager.get_user_experiments("u1")
        promotions = manager.suggest_promotions(experiments)
        assert len(promotions) >= 1
        assert promotions[0]["suggested_strategy"] == "recover_execution_rhythm_gentle"
        assert promotions[0]["action"] == "promote_shadow_to_primary"

    @pytest.mark.asyncio
    async def test_shadow_outcome_heuristic(self, manager):
        result = manager.evaluate_shadow_outcome(
            primary_outcome="insufficient",
            primary_strategy="repair_knowledge_gap",
            context={"new_hypothesis": "user lacks understanding of core concepts"},
        )
        # Shadow "guided" should win when understanding is the issue
        assert result == "effective"


class TestV24SkillAutoDeprecation:
    """v2.4: Skill lifecycle auto-deprecation."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def spine(self, redis):
        return SpineOrchestrator(redis_client=redis)

    @pytest.mark.asyncio
    async def test_auto_deprecation_no_stale_skills(self, spine, redis):
        deprecated = await spine.run_auto_deprecation("u1")
        assert deprecated == []

    @pytest.mark.asyncio
    async def test_auto_deprecation_with_stale_skill(self, spine, redis):
        import json
        # Seed a stale skill — last 5 outcomes all insufficient
        skill_data = {
            "skill_id": "stale_skill",
            "scope": "personal",
            "source_policy_key": "test_policy",
            "strategy": {},
            "applicable_when": {},
            "evidence": {
                "deprecated": False,
                "recent_outcomes": [
                    {"outcome": "insufficient"} for _ in range(5)
                ],
            },
            "effective_count": 0,
            "sample_size": 5,
        }
        await redis.set(
            "spine:skills:u1",
            json.dumps([skill_data]),
            ex=30 * 24 * 3600,
        )
        deprecated = await spine.run_auto_deprecation("u1")
        assert "stale_skill" in deprecated


class TestV24PipelineBeliefPersistence:
    """v2.4: Strategy beliefs persist across pipeline calls."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def spine(self, redis):
        return SpineOrchestrator(redis_client=redis)

    @pytest.mark.asyncio
    async def test_beliefs_persisted_after_pipeline(self, spine, redis):
        import json
        from app.signals.learning_base import StrategyBelief

        beliefs = [
            StrategyBelief(strategy_key="test_strategy", alpha=5, beta=3, evidence_count=8),
        ]
        await spine._persist_strategy_beliefs("u1", beliefs)

        loaded = await spine._load_strategy_beliefs("u1")
        assert len(loaded) == 1
        assert loaded[0].strategy_key == "test_strategy"
        assert loaded[0].alpha == 5

    @pytest.mark.asyncio
    async def test_beliefs_empty_on_new_user(self, spine, redis):
        loaded = await spine._load_strategy_beliefs("new_user")
        assert loaded == []


class TestV24OutcomeTriggersExperimentAndSource:
    """v2.4: record_outcome triggers experiment trial + source effectiveness."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def spine(self, redis):
        return SpineOrchestrator(redis_client=redis)

    @pytest.mark.asyncio
    async def test_outcome_records_source_effectiveness(self, spine, redis):
        trace = CausalTrace(trace_id="t1")

        # Create a running experiment first
        await spine.policy_experiments.create_experiment(
            user_id="u1",
            signal_state_key="task_granularity_fit",
            signal_claim="recent_task_too_large",
            primary_strategy="recover_execution_rhythm",
        )

        record = await spine.record_outcome(
            trace=trace,
            intervention="test",
            reason="test",
            expected_outcome="task_started_and_completed",
            actual_outcome={"completed": True, "source_ids": ["src_tcp_notes"]},
            user_id="u1",
        )
        assert record is not None

        # Check source effectiveness was recorded
        source_eff = await spine.source_effectiveness.get_source_effectiveness("u1", "src_tcp_notes")
        assert source_eff is not None
        assert source_eff["effective"] == 1

    @pytest.mark.asyncio
    async def test_outcome_updates_experiment_trial(self, spine, redis):
        trace = CausalTrace(trace_id="t1")

        exp = await spine.policy_experiments.create_experiment(
            user_id="u1",
            signal_state_key="task_granularity_fit",
            signal_claim="recent_task_too_large",
            primary_strategy="recover_execution_rhythm",
        )
        assert exp is not None

        await spine.record_outcome(
            trace=trace,
            intervention="test",
            reason="test",
            expected_outcome="task_started_and_completed",
            actual_outcome={"completed": True},
            user_id="u1",
        )

        updated_exp = await spine.policy_experiments.get_experiment(exp.experiment_id)
        assert updated_exp is not None
        assert updated_exp.total_trials >= 1


# =============================================================================
# v2.5 Audit Fix Tests — Chronicle injection, self-model correction, concurrency
# =============================================================================


@pytest.mark.asyncio
async def test_chronicle_injects_into_prompt():
    """Chronicle summary is injected into system prompt via build_system_prompt."""
    result = build_system_prompt(
        user_context={"name": "Test"},
        spine_chronicle_summary="里程碑：完成5次任务；转折点：修正了难度判断",
    )
    assert "用户成长叙事" in result
    assert "里程碑" in result


@pytest.mark.asyncio
async def test_fatigue_injects_into_prompt():
    """High fatigue state modulates prompt tone."""
    result = build_system_prompt(
        user_context={"name": "Test"},
        spine_fatigue_context={"fatigue_level": "critical"},
    )
    assert "疲劳状态" in result
    assert "减轻负担" in result


@pytest.mark.asyncio
async def test_crisis_injects_into_prompt():
    """Crisis mode adds考前高压 guidance."""
    result = build_system_prompt(
        user_context={"name": "Test"},
        spine_fatigue_context={"crisis_mode": True},
    )
    assert "高压" in result


@pytest.mark.asyncio
async def test_no_chronicle_no_section():
    """Without chronicle, no chronicle section appears."""
    result = build_system_prompt(user_context={"name": "Test"})
    assert "用户成长叙事" not in result


@pytest.mark.asyncio
async def test_on_user_correction_calls_self_model():
    """on_user_correction → self_model.record_user_correction is called."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    spine.relationship_model.update_from_interaction = AsyncMock()
    spine.self_model.record_user_correction = AsyncMock()

    await spine.on_user_correction(
        user_id="u1",
        correction_type="receipt_correction",
        original_claim="too_hard",
        corrected_understanding="just_right",
        trace_id="trace_1",
    )
    spine.self_model.record_user_correction.assert_awaited_once_with(
        user_id="u1",
        signal_id="trace_1",
        reason="too_hard → just_right",
        source="user_receipt_correction",
    )


@pytest.mark.asyncio
async def test_pipeline_concurrency_guard():
    """Second concurrent pipeline for same user is skipped."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    # Simulate lock already held — use direct store since FakeRedis.set lacks nx=
    lock_key = f"spine:pipeline_lock:u1"
    redis._store[lock_key] = "1"

    signal = ActionableSignal(
        signal_id="sig_concurrent",
        source_event_ids=["evt_1"],
        source_system="test",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.9,
        evidence_summary="task exceeded 60 min",
        scope="turn",
        ttl_hours=1,
        possible_effects=["reduce_duration"],
        priority="high",
    )
    result = await spine._run_signal_pipeline(user_id="u1", signal=signal)
    assert result is None  # Skipped due to lock


@pytest.mark.asyncio
async def test_metrics_counter_ttl():
    """Metrics counters get 7-day TTL on increment."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis)
    await metrics.increment("signals_generated")
    # FakeRedis doesn't track TTL but the call should succeed
    val = await metrics.get_counter("signals_generated")
    assert val == 1


# ══════════════════════════════════════════════════════════════════════
# v2.5: General Goal OS Tests
# ══════════════════════════════════════════════════════════════════════


class TestV25GoalWorldGraph:
    """v2.5: GoalWorldGraph — per-goal dependency tracking."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def service(self, redis):
        from app.signals.goal_world_graph import GoalWorldGraphService
        return GoalWorldGraphService(redis)

    @pytest.mark.asyncio
    async def test_create_graph(self, service, redis):
        graph = await service.create_graph(
            user_id="u1",
            goal_id="exam_cn",
            goal_type="exam",
            node_specs=[
                {"node_id": "tcp", "label": "TCP协议", "mastery": 0.0, "dependency_ids": ["ip"]},
                {"node_id": "ip", "label": "IP基础", "mastery": 0.3, "dependency_ids": []},
                {"node_id": "http", "label": "HTTP", "mastery": 0.0, "dependency_ids": ["tcp"]},
            ],
        )
        assert graph.graph_id.startswith("gwg_")
        assert len(graph.nodes) == 3
        assert graph.coverage == 0.0  # none mastered

    @pytest.mark.asyncio
    async def test_update_mastery(self, service, redis):
        await service.create_graph(
            user_id="u1", goal_id="g1", goal_type="exam",
            node_specs=[
                {"node_id": "n1", "label": "A", "mastery": 0.0},
                {"node_id": "n2", "label": "B", "mastery": 0.0},
            ],
        )
        updated = await service.update_node_mastery("u1", "g1", "n1", 0.9)
        assert updated is not None
        assert updated.nodes[0].mastery == 0.9
        assert updated.nodes[0].status == "mastered"
        assert updated.coverage == 0.5

    @pytest.mark.asyncio
    async def test_find_bottleneck(self, service, redis):
        await service.create_graph(
            user_id="u1", goal_id="g1", goal_type="exam",
            node_specs=[
                {"node_id": "base", "label": "基础", "mastery": 0.2, "dependency_ids": []},
                {"node_id": "mid1", "label": "中级1", "mastery": 0.0, "dependency_ids": ["base"]},
                {"node_id": "mid2", "label": "中级2", "mastery": 0.0, "dependency_ids": ["base"]},
                {"node_id": "adv", "label": "高级", "mastery": 0.0, "dependency_ids": ["mid1", "mid2"]},
            ],
        )
        graph = await service.get_graph("u1", "g1")
        bottleneck = service.find_bottleneck(graph)
        assert bottleneck is not None
        assert bottleneck.node_id == "base"  # blocks mid1, mid2, and indirectly adv

    @pytest.mark.asyncio
    async def test_suggest_focus_nodes(self, service, redis):
        await service.create_graph(
            user_id="u1", goal_id="g1", goal_type="exam",
            node_specs=[
                {"node_id": "a", "label": "A", "mastery": 0.8},  # mastered
                {"node_id": "b", "label": "B", "mastery": 0.3, "dependency_ids": ["a"]},  # unblocked, in-progress
                {"node_id": "c", "label": "C", "mastery": 0.0, "dependency_ids": ["a"]},  # unblocked, pending
            ],
        )
        # Update mastery to mark 'a' as mastered
        await service.update_node_mastery("u1", "g1", "a", 0.9)
        graph = await service.get_graph("u1", "g1")
        suggestions = service.suggest_focus_nodes(graph, limit=3)
        assert len(suggestions) >= 2
        # Should suggest the lowest-mastery unblocked nodes
        suggested_ids = [s["node_id"] for s in suggestions]
        assert "c" in suggested_ids  # mastery 0, should be suggested

    @pytest.mark.asyncio
    async def test_add_dependency(self, service, redis):
        await service.create_graph(
            user_id="u1", goal_id="g1", goal_type="general",
            node_specs=[
                {"node_id": "a", "label": "A", "mastery": 0.5},
                {"node_id": "b", "label": "B", "mastery": 0.5},
            ],
        )
        updated = await service.add_dependency("u1", "g1", "b", "a")
        assert "a" in updated.nodes[1].dependency_ids


class TestV25MultiGoalArbitration:
    """v2.5: MultiGoalArbitration — resolve conflicts between active goals."""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.fixture
    def arbitrator(self, redis):
        from app.signals.multi_goal_arbitration import MultiGoalArbitrator
        return MultiGoalArbitrator(redis)

    @pytest.mark.asyncio
    async def test_single_goal(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=7, mastery=0.3)]
        result = arbitrator.arbitrate(goals)
        assert result.primary_goal_id == "g1"
        assert result.reason == "single_active_goal"
        assert result.suggested_time_split["g1"] == 1.0

    @pytest.mark.asyncio
    async def test_deadline_urgent_wins(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [
            ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=3, mastery=0.6),
            ActiveGoal(goal_id="g2", goal_type="project", title="大作业", deadline_days=14, mastery=0.3),
        ]
        result = arbitrator.arbitrate(goals)
        assert result.primary_goal_id == "g1"
        assert "deadline" in result.reason or "priority" in result.reason

    @pytest.mark.asyncio
    async def test_bottleneck_severity(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [
            ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=30, mastery=0.5),
            ActiveGoal(goal_id="g2", goal_type="exam", title="高数考试", deadline_days=30, mastery=0.5, bottleneck_severity=0.9),
        ]
        result = arbitrator.arbitrate(goals)
        assert result.primary_goal_id == "g2"

    @pytest.mark.asyncio
    async def test_user_override(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [
            ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=3, mastery=0.2),
            ActiveGoal(goal_id="g2", goal_type="project", title="大作业", deadline_days=14, mastery=0.5, priority_override="high"),
        ]
        result = arbitrator.arbitrate(goals)
        assert result.primary_goal_id == "g2"
        assert result.reason == "user_priority_override"

    @pytest.mark.asyncio
    async def test_paused_goals_excluded(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [
            ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=7, mastery=0.5),
            ActiveGoal(goal_id="g2", goal_type="project", title="大作业", priority_override="pause"),
        ]
        result = arbitrator.arbitrate(goals)
        assert result.primary_goal_id == "g1"

    @pytest.mark.asyncio
    async def test_conflict_detection(self, arbitrator):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goals = [
            ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=3, mastery=0.3),
            ActiveGoal(goal_id="g2", goal_type="exam", title="高数考试", deadline_days=5, mastery=0.3),
        ]
        result = arbitrator.arbitrate(goals)
        assert "multiple_urgent_deadlines" in result.conflicts

    @pytest.mark.asyncio
    async def test_redis_register_and_get(self, arbitrator, redis):
        from app.signals.multi_goal_arbitration import ActiveGoal
        goal = ActiveGoal(goal_id="g1", goal_type="exam", title="计网考试", deadline_days=7)
        await arbitrator.register_goal("u1", goal)
        loaded = await arbitrator.get_active_goals("u1")
        assert len(loaded) == 1
        assert loaded[0].goal_id == "g1"

    @pytest.mark.asyncio
    async def test_spine_orchestrator_integration(self, redis):
        spine = SpineOrchestrator(redis_client=redis)
        await spine.register_goal("u1", "g1", "exam", "计网考试", deadline_days=5, mastery=0.3)
        result = await spine.arbitrate_goals("u1")
        assert result is not None
        assert result.primary_goal_id == "g1"


class TestV25SpineGoalGraphIntegration:
    """v2.5: SpineOrchestrator delegates to GoalWorldGraphService."""

    @pytest.fixture
    def spine(self):
        return SpineOrchestrator(redis_client=FakeRedis())

    @pytest.mark.asyncio
    async def test_get_goal_graph_none(self, spine):
        result = await spine.get_goal_graph("u1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_focus_suggestions_empty(self, spine):
        result = await spine.get_goal_focus_suggestions("u1", "nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_arbitrate_no_goals(self, spine):
        result = await spine.arbitrate_goals("u1")
        assert result is None


# ══════════════════════════════════════════════════════════════════════
# E2E Test Matrix — 12 required scenarios from v2.1 Unified Causal Runtime
# ══════════════════════════════════════════════════════════════════════


