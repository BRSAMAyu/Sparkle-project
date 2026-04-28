"""Spine tests — test_pipeline_integration.py."""

from __future__ import annotations
from tests.unit.spine._helpers import FakeRedis, _make_redis_mock


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

# ── P2 Integration: SpineOrchestrator P1 wiring ─────────────────────

from unittest.mock import AsyncMock, MagicMock

from app.signals.spine_orchestrator import SpineOrchestrator


def _make_redis_mock():
    redis = AsyncMock()
    redis._store: dict[str, str] = {}
    redis._sets: dict[str, set] = {}

    async def _set(key, value, ex=None):
        redis._store[key] = value

    async def _get(key):
        return redis._store.get(key)

    async def _delete(key):
        redis._store.pop(key, None)

    async def _smembers(key):
        return redis._sets.get(key, set())

    async def _sadd(key, *members):
        s = redis._sets.setdefault(key, set())
        for m in members:
            s.add(m)

    async def _srem(key, *members):
        s = redis._sets.get(key, set())
        for m in members:
            s.discard(m)

    async def _incr(key):
        val = int(redis._store.get(key, "0")) + 1
        redis._store[key] = str(val)
        return val

    async def _expire(key, seconds):
        redis._store[f"__expire__{key}"] = str(seconds)

    redis.set = _set
    redis.get = _get
    redis.delete = _delete
    redis.smembers = _smembers
    redis.sadd = _sadd
    redis.srem = _srem
    redis.incr = _incr
    redis.expire = _expire
    redis.lpush = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.ltrim = AsyncMock()
    return redis


@pytest.fixture
def spine():
    return SpineOrchestrator(_make_redis_mock())


@pytest.mark.asyncio
async def test_spine_achievement_high_momentum_pipeline(spine):
    """on_achievement_event → high momentum → trace with policy。"""
    trace = await spine.on_achievement_event(
        user_id="u1",
        achievement_type="streak",
        achievement_id="seven_day_streak",
        recent_unlocks=3,
        active_streaks=2,
        in_progress_count=4,
    )
    assert trace is not None
    assert "achievement_seven_day_streak" in trace.raw_event_ids
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_achievement_moderate_no_trace(spine):
    """on_achievement_event → moderate momentum → no signal → None。"""
    trace = await spine.on_achievement_event(
        user_id="u1",
        achievement_type="task_complete",
        achievement_id="first_task",
        recent_unlocks=1,
        active_streaks=1,
        in_progress_count=2,
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_recall_undigested_pipeline(spine):
    """on_recall_check(undigested_material) → trace with policy。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="undigested_material",
        uploaded_files_count=3,
        diagnosed_files_count=1,
        hours_since_upload=2.0,
    )
    assert trace is not None
    assert "recall_undigested_material" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_recall_task_missed_pipeline(spine):
    """on_recall_check(task_missed) → trace with high urgency policy。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="task_missed",
        task_id="t1",
        deadline_hours=-3.0,
        is_completed=False,
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_recall_pre_exam_pipeline(spine):
    """on_recall_check(pre_exam_silence) → trace with hard constraints。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="pre_exam_silence",
        exam_deadline_days=1.0,
        hours_since_last_activity=6.0,
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_recall_no_trigger(spine):
    """on_recall_check with no trigger condition met → None。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="task_not_started",
        task_id="t1",
        hours_since_assignment=0.5,
        has_started=False,
    )
    assert trace is None


# ── P2 Extended Integration Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_spine_exam_rescue_pipeline(spine):
    """on_first_message → exam rescue → trace with policy。"""
    trace = await spine.on_first_message(
        user_id="u1",
        message="我7天后计网考试，零基础，想先别挂",
    )
    assert trace is not None
    assert "first_message_exam_rescue" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_exam_no_rescue(spine):
    """on_first_message → normal chat → None。"""
    trace = await spine.on_first_message(
        user_id="u1",
        message="你好，我想学一下编程",
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_stale_return(spine):
    """on_user_return → stale → trace。"""
    trace = await spine.on_user_return(
        user_id="u1",
        time_context={
            "now": "2026-04-27T12:00:00Z",
            "timezone": "Asia/Shanghai",
            "goal_deadline": None,
            "last_user_interaction_at": "2026-04-27T10:00:00Z",
            "elapsed_since_last_interaction_min": 120,
            "active_task_id": "t1",
            "deadline_phase": "normal_sprint",
        },
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_not_stale(spine):
    """on_user_return → not stale → None。"""
    trace = await spine.on_user_return(
        user_id="u1",
        time_context={
            "now": "2026-04-27T12:00:00Z",
            "timezone": "Asia/Shanghai",
            "goal_deadline": None,
            "last_user_interaction_at": "2026-04-27T11:30:00Z",
            "elapsed_since_last_interaction_min": 30,
            "active_task_id": "t1",
            "deadline_phase": "normal_sprint",
        },
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_build_state_packet(spine):
    """build_state_packet → ActionableStatePacket。"""
    packet = await spine.build_state_packet(user_id="u1")
    assert packet.user_id == "u1"
    assert isinstance(packet.top_states, list)


@pytest.mark.asyncio
async def test_spine_community_cohort_pipeline(spine):
    """on_community_cohort_data → pattern detected → trace。"""
    trace = await spine.on_community_cohort_data(
        user_id="u1",
        knowledge_node_id="tcp",
        subject="cn",
        mistake_type="confusion",
        cohort_size=10,
        error_count=7,
        common_misconception="test",
    )
    assert trace is not None
    assert "community_cohort_mistake" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_community_no_pipeline(spine):
    """on_community_cohort_data → too few peers → None。"""
    trace = await spine.on_community_cohort_data(
        user_id="u1",
        knowledge_node_id="tcp",
        subject="cn",
        mistake_type="confusion",
        cohort_size=3,
        error_count=2,
        common_misconception="test",
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_community_resource_pipeline(spine):
    """on_community_resource_data → resource recommended → trace。"""
    trace = await spine.on_community_resource_data(
        user_id="u1",
        resource_id="r1",
        resource_title="计网速通",
        subject="cn",
        peer_count=8,
        relevance_score=0.8,
    )
    assert trace is not None


def test_spine_aurora_wake_check(spine):
    """check_aurora_wake → eligible。"""
    result = spine.check_aurora_wake(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
        consecutive_negative_outcomes=3,
    )
    assert result.can_wake is True


def test_spine_aurora_wake_denied(spine):
    """check_aurora_wake → no reason → denied。"""
    result = spine.check_aurora_wake(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
    )
    assert result.can_wake is False


@pytest.mark.asyncio
async def test_spine_self_model_outcome(spine):
    """record_strategy_outcome → outcome recorded。"""
    claim = await spine.self_model.record_claim(
        user_id="u1", claim="test strategy", confidence=0.6, scope="current_sprint",
    )
    outcome = await spine.record_strategy_outcome(
        user_id="u1",
        directive_id="dir_001",
        claim_id=claim.claim_id,
        expected_outcome="user completes task",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    assert outcome.attribution["effect"] == "effective"


# ── P3: Production Wiring Tests ───────────────────────────────────────


def test_achievement_consumer_imports_spine():
    """Verify achievement_event_consumer has spine import path."""
    import ast
    import inspect
    from app.services.achievement_event_consumer import AchievementEventConsumer
    source = inspect.getsource(AchievementEventConsumer._handle_achievement_unlocked)
    assert "SpineOrchestrator" in source
    assert "on_achievement_event" in source


def test_orchestrator_imports_spine():
    """Verify orchestrator has spine exam rescue + stale guard wiring."""
    import inspect
    from app.orchestration.orchestrator import ChatOrchestrator
    source = inspect.getsource(ChatOrchestrator.process_stream)
    assert "on_first_message" in source
    assert "on_user_return" in source
    assert "SpineOrchestrator" in source


@pytest.mark.asyncio
async def test_spine_on_achievement_event_from_consumer():
    """Simulate achievement_event_consumer calling spine.on_achievement_event."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_achievement_event(
        user_id="u_ach",
        achievement_type="streak",
        achievement_id="ach_123",
        recent_unlocks=5,
        active_streaks=3,
        in_progress_count=2,
    )
    # High momentum (5 unlocks + 3 streaks) should produce a signal
    assert trace is not None
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_on_first_message_exam_rescue():
    """Simulate first-message exam rescue via spine."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_first_message(
        user_id="u_exam",
        message="我7天后计网考试，零基础，想先别挂",
    )
    assert trace is not None
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_on_user_return_stale():
    """Simulate user return after 2 hours."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_user_return(
        user_id="u_stale",
        time_context={
            "now": "2026-04-27T12:00:00",
            "elapsed_since_last_interaction_min": 120,
            "active_task_id": None,
        },
    )
    assert trace is not None
    assert "user_responded_to_stale_check" in trace.outcome_to_measure


