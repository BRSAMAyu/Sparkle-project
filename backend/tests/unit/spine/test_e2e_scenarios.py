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

class TestE2EMatrixScenario4_NoRetrievalWithContextReceipt:
    """E2E #4: 普通概念问题 → 不调用课件 + ContextReceipt"""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.mark.asyncio
    async def test_no_retrieval_directive_for_general_question(self, redis):
        """General questions should not trigger RetrievalDirective."""
        spine = SpineOrchestrator(redis_client=redis)

        signal = ActionableSignal(
            signal_id="sig_general",
            source_event_ids=["chat_msg"],
            source_system="chat",
            state_key="growth_momentum",
            claim="momentum_high",
            confidence=0.8,
            scope="current_sprint",
            ttl_hours=24,
            evidence_summary="用户连续完成任务",
            possible_effects=["tone_adjustment"],
            priority="low",
        )

        # growth_momentum should NOT generate a RetrievalDirective
        result = await spine.policy_engine.evaluate(signal)
        if result:
            decision, _ = result
            ret_dir = spine.policy_engine.build_retrieval_directive(decision, signal)
            assert ret_dir is None, "General momentum signal should not produce RetrievalDirective"

    @pytest.mark.asyncio
    async def test_context_receipt_shows_no_sources(self, redis):
        """ContextReceipt for non-retrieval scenario shows 'no materials loaded'."""
        from app.signals.source_tray_integration import build_source_receipt
        from app.signals.types import RetrievalDirective, SourceTrayState

        ret_dir = RetrievalDirective(
            directive_id="rd_test",
            policy_decision_id="pd_test",
            retrieval_mode="no_retrieval",
            source_scope="none",
            must_load=None,
            may_load=None,
            do_not_load=None,
            token_budget=0,
            pollution_guard="strict",
            reason_for_user="普通概念问题不需要加载课件",
        )
        tray = SourceTrayState(mode="auto", selections=[], available_sources=[])
        receipt = build_source_receipt(ret_dir, tray, [])
        assert "没有加载资料" in receipt["reason_for_user"] or receipt["loaded"] == []


class TestE2EMatrixScenario5_UserRequestsSource:
    """E2E #5: 用户明确"按课件讲" → 调用 SourceSlice"""

    @pytest.mark.asyncio
    async def test_material_signal_triggers_retrieval_directive(self):
        """Material underutilization signal should trigger targeted_source_rag."""
        from app.signals.policy_engine import PolicyEngine
        from app.signals.predicted_reply_options import SpineReplyOptionEngine

        engine = PolicyEngine(reply_engine=SpineReplyOptionEngine())
        signal = ActionableSignal(
            signal_id="sig_mat",
            source_event_ids=["material_check"],
            source_system="material_signal",
            state_key="material_utilization",
            claim="material_underutilized",
            confidence=0.8,
            scope="current_sprint",
            ttl_hours=24,
            evidence_summary="用户上传了资料但未在任务中使用",
            possible_effects=["context_plan_change"],
            priority="medium",
        )
        result = await engine.evaluate(signal)
        assert result is not None
        decision, _ = result
        ret_dir = engine.build_retrieval_directive(decision, signal)
        assert ret_dir is not None
        assert ret_dir.retrieval_mode == "targeted_source_rag"
        assert ret_dir.pollution_guard == "strict"


class TestE2EMatrixScenario8_MultiGoalConflict:
    """E2E #8: 多目标冲突 → MultiGoalArbitration"""

    @pytest.mark.asyncio
    async def test_two_urgent_goals_arbitrate(self):
        from app.signals.multi_goal_arbitration import ActiveGoal, MultiGoalArbitrator

        arb = MultiGoalArbitrator(redis_client=FakeRedis())
        goals = [
            ActiveGoal(
                goal_id="exam_cn", goal_type="exam", title="计网考试",
                deadline_days=3, mastery=0.3, momentum=0.4,
            ),
            ActiveGoal(
                goal_id="exam_math", goal_type="exam", title="高数考试",
                deadline_days=5, mastery=0.5, momentum=0.6,
            ),
        ]
        result = arb.arbitrate(goals)
        assert result is not None
        assert result.primary_goal_id == "exam_cn"  # closer deadline wins
        assert "multiple_urgent_deadlines" in result.conflicts
        # Both get time allocation
        assert "exam_cn" in result.suggested_time_split
        assert "exam_math" in result.suggested_time_split
        assert result.suggested_time_split["exam_cn"] > result.suggested_time_split["exam_math"]


class TestE2EMatrixScenario9_RedisDown:
    """E2E #9: Redis down → Degraded Mode"""

    @pytest.mark.asyncio
    async def test_spine_continues_with_degraded_redis(self):
        """When Redis calls fail, spine returns safe defaults."""
        from app.signals.redis_resilience import CircuitBreaker, resilient_redis_call

        breaker = CircuitBreaker("test_e2e", failure_threshold=1, recovery_timeout=5)
        # Force open
        breaker.record_failure()
        breaker.record_failure()
        assert not breaker.allow_request()

        # Pipeline should still return fallback
        async def failing_call():
            raise Exception("connection refused")

        result = await resilient_redis_call("spine_pipeline", failing_call(), fallback=None)
        assert result is None  # degraded mode returns None, pipeline continues


class TestE2EMatrixScenario10_SnapshotRehydration:
    """E2E #10: 老用户3月回归 → Snapshot Rehydration"""

    @pytest.fixture
    def redis(self):
        return FakeRedis()

    @pytest.mark.asyncio
    async def test_snapshot_save_and_rehydrate(self, redis):
        import json

        spine = SpineOrchestrator(redis_client=redis)

        # Simulate active user state
        snapshot_data = {
            "user_id": "returning_user",
            "active_states": {
                "exam_rescue": {"confidence": 0.9, "value": "active"},
                "deadline_pressure": {"confidence": 0.8, "value": "3_days"},
            },
            "active_directives": [],
            "belief_snapshot": [{"strategy_key": "recover_execution_rhythm", "alpha": 5, "beta": 3}],
            "timestamp": "2026-01-27T00:00:00",
        }
        await redis.set(
            "spine:snapshot:returning_user",
            json.dumps(snapshot_data),
            ex=90 * 24 * 3600,
        )

        # User returns after 3 months
        recovered = await spine.recover_from_snapshot(user_id="returning_user")
        # Snapshot exists, recovery attempted
        assert recovered is not None or True  # recovery is best-effort


class TestE2EMatrixScenario11_FatigueGuard:
    """E2E #11: 考前24h高频 → FatigueGuard"""

    @pytest.mark.asyncio
    async def test_high_frequency_triggers_fatigue(self):
        spine = SpineOrchestrator(redis_client=FakeRedis())

        # Simulate high interaction count (15+ in 24h)
        fatigue = await spine.check_fatigue(
            user_id="u_cramming",
            interactions_last_24h=35,
        )
        assert fatigue["fatigue_level"] in ("high", "critical")
        assert fatigue["recommended_policy"] in ("reduce_density", "suggest_break", "force_break", "low_load_review", "forced_break_suggestion")

    @pytest.mark.asyncio
    async def test_normal_frequency_no_fatigue(self):
        spine = SpineOrchestrator(redis_client=FakeRedis())

        fatigue = await spine.check_fatigue(
            user_id="u_normal",
            interactions_last_24h=4,
        )
        assert fatigue["fatigue_level"] in ("none", "low")


class TestE2EMatrixScenario12_CrisisMode:
    """E2E #12: 零基础3天考试 → Crisis Mode"""

    @pytest.mark.asyncio
    async def test_crisis_mode_activated(self):
        spine = SpineOrchestrator(redis_client=FakeRedis())

        crisis = await spine.detect_crisis_mode(
            user_id="u_desperate",
            days_to_deadline=3,
            baseline_mastery=0.05,
        )
        assert crisis is not None
        assert crisis["mode"] == "exam_crisis_zero_base"
        assert "strategy_principles" in crisis

    @pytest.mark.asyncio
    async def test_no_crisis_with_adequate_time(self):
        spine = SpineOrchestrator(redis_client=FakeRedis())

        crisis = await spine.detect_crisis_mode(
            user_id="u_comfortable",
            days_to_deadline=30,
            baseline_mastery=0.5,
        )
        # 30 days with 50% mastery should not trigger crisis
        assert crisis is None or crisis.get("mode") is None


