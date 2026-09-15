"""Spine tests — test_types_and_detectors.py."""

from __future__ import annotations
from tests.unit.spine._helpers import FakeRedis, FakeRedisWithHset


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

# ── Test 1: Types serialization round-trip ─────────────────────────────

def test_actionable_signal_roundtrip():
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["evt_001"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.72,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="连续 2 次任务超时",
        possible_effects=["cap_task_duration"],
        priority="high",
    )
    d = signal.to_dict()
    restored = ActionableSignal.from_dict(d)
    assert restored.signal_id == signal.signal_id
    assert restored.state_key == "task_granularity_fit"
    assert restored.confidence == 0.72


def test_causal_trace_roundtrip():
    trace = CausalTrace(trace_id=_uid("ct"), raw_event_ids=["evt_001"])
    d = trace.to_dict()
    restored = CausalTrace.from_dict(d)
    assert restored.trace_id == trace.trace_id
    assert restored.raw_event_ids == ["evt_001"]


# ── Test 2: TaskTimeoutDetector — no timeout ───────────────────────────

@pytest.mark.asyncio
async def test_no_timeout_no_signal(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)
    signal = await detector.on_task_completed(
        user_id="u1",
        task_id="t1",
        estimated_minutes=30,
        actual_minutes=25,  # within threshold
    )
    assert signal is None


# ── Test 3: TaskTimeoutDetector — single timeout, no trigger ───────────

@pytest.mark.asyncio
async def test_single_timeout_no_trigger(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)
    signal = await detector.on_task_completed(
        user_id="u1",
        task_id="t1",
        estimated_minutes=30,
        actual_minutes=50,  # > 140% = 42min
    )
    assert signal is None  # Need 2 consecutive


# ── Test 4: TaskTimeoutDetector — two consecutive timeouts → signal ────

@pytest.mark.asyncio
async def test_two_consecutive_timeouts_triggers_signal(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)

    # First timeout
    s1 = await detector.on_task_completed(
        user_id="u1", task_id="t1",
        estimated_minutes=30, actual_minutes=50,
    )
    assert s1 is None  # Not yet

    # Second timeout
    s2 = await detector.on_task_completed(
        user_id="u1", task_id="t2",
        estimated_minutes=45, actual_minutes=65,
    )
    assert s2 is not None
    assert s2.state_key == "task_granularity_fit"
    assert s2.claim == "recent_task_too_large"
    assert s2.confidence >= 0.5
    assert s2.priority == "high"


# ── Test 5: PolicyEngine — rule match ──────────────────────────────────

@pytest.mark.asyncio
async def test_policy_engine_matches_timeout_signal():
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["t1"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.72,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="连续 2 次超时",
        possible_effects=["cap_task_duration"],
        priority="high",
    )
    result = await engine.evaluate(signal, context={"consecutive": 2})
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "recover_execution_rhythm"
    assert directive.hard_constraints["max_task_duration_min"] == 25
    assert directive.hard_constraints["avoid_new_chapter"] is True
    assert directive.target_module == "task_generator"


# ── Test 6: DirectiveApplier — duration cap ────────────────────────────

def test_directive_caps_duration():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=directive,
        estimated_minutes=60,
    )
    assert capped == 25
    assert applied is True


def test_directive_no_cap_when_below():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=directive,
        estimated_minutes=20,
    )
    assert capped == 20
    assert applied is True


def test_directive_no_cap_when_no_directive():
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=None,
        estimated_minutes=60,
    )
    assert capped == 60
    assert applied is False


# ── Test 7: DirectiveAuditor — pass ────────────────────────────────────

def test_audit_passes_when_constraints_met():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25, "required_task_type": "worked_example_then_drill"},
        user_visible_reason="test",
    )
    audit = DirectiveAuditor.audit(
        directive=directive,
        generated_task={
            "task_id": "task_001",
            "estimated_minutes": 23,
            "task_kind": "worked_example_then_drill",
            "is_new_chapter": False,
        },
    )
    assert audit.applied is True
    assert len(audit.violations) == 0


# ── Test 8: DirectiveAuditor — fail (duration violation) ──────────────

def test_audit_fails_on_duration_violation():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    audit = DirectiveAuditor.audit(
        directive=directive,
        generated_task={
            "task_id": "task_002",
            "estimated_minutes": 40,
            "task_kind": "retrieval_drill",
        },
    )
    assert audit.applied is False
    assert len(audit.violations) == 1
    assert audit.violations[0]["constraint"] == "max_task_duration_min"


# ── Test 9: Full pipeline (E1 acceptance) ──────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_e1_acceptance(fake_redis):
    """E1: 连续2次超时 → signal → policy → directive ≤ 25min → audit pass → receipt"""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.causal_trace_store import CausalTraceStore

    spine = SpineOrchestrator(fake_redis)

    # Task 1: timeout (30 est → 50 actual)
    trace1 = await spine.on_task_completed(
        user_id="u1", task_id="t1",
        estimated_minutes=30, actual_minutes=50,
    )
    assert trace1 is not None
    # Only 1 timeout → no signal generated
    assert len(trace1.signal_ids) == 0

    # Task 2: timeout (45 est → 65 actual)
    trace2 = await spine.on_task_completed(
        user_id="u1", task_id="t2",
        estimated_minutes=45, actual_minutes=65,
    )
    assert trace2 is not None
    # 2 consecutive → signal + policy + directive
    assert len(trace2.signal_ids) >= 1
    assert trace2.policy_decision_id is not None
    assert len(trace2.directive_ids) >= 1
    assert len(trace2.receipt_ids) >= 1

    # Verify active directive exists
    directive = await spine.get_active_directive("u1")
    assert directive is not None
    assert directive.hard_constraints["max_task_duration_min"] == 25

    # Apply directive to a task spec
    task_spec = {"estimated_minutes": 60, "task_kind": "retrieval_drill"}
    modified_spec, audit = await spine.apply_directive_to_task_spec("u1", task_spec)

    assert modified_spec["estimated_minutes"] <= 25
    assert audit is not None
    assert audit.applied is True
    assert len(audit.violations) == 0

    # Verify receipt exists
    receipt = await spine.get_latest_receipt("u1")
    assert receipt is not None
    assert "25" in receipt.message or "超时" in receipt.message

    # After consumption, directive should be cleared
    directive2 = await spine.get_active_directive("u1")
    assert directive2 is None


# ── M2: Material Signal Tests ────────────────────────────────────────

from app.signals.material_signal import MaterialSignalDetector


class FakeRedisWithHset(FakeRedis):
    """Extended fake Redis with hash operations for M2 tests."""

    def __init__(self):
        super().__init__()
        self._hashes: dict[str, dict[str, str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {})


@pytest.mark.asyncio
async def test_material_signal_no_files():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)
    signal = await detector.on_turn_completed(user_id="u1", context_receipt=None)
    assert signal is None


@pytest.mark.asyncio
async def test_material_signal_underutilized_after_threshold():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)

    # Register uploaded file
    await detector.register_uploaded_file(
        user_id="u1", file_id="f1", filename="计网传输层.pdf", node_ids=["cn.tcp"]
    )

    # 3 turns with no usage
    for _ in range(3):
        signal = await detector.on_turn_completed(
            user_id="u1", context_receipt={"used_count": 0, "decision_reason": "graph_only"}
        )

    # After 3 turns: signal should be generated
    assert signal is not None
    assert signal.state_key == "material_utilization"
    assert signal.claim == "material_underutilized"
    assert "计网传输层" in signal.evidence_summary


@pytest.mark.asyncio
async def test_material_signal_resets_when_used():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)

    await detector.register_uploaded_file(user_id="u1", file_id="f1", filename="test.pdf")

    # 2 turns unused
    for _ in range(2):
        await detector.on_turn_completed(user_id="u1", context_receipt={"used_count": 0})

    # 1 turn with usage → should NOT trigger
    signal = await detector.on_turn_completed(
        user_id="u1", context_receipt={"used_count": 3}
    )
    assert signal is None


# ── M2: Retrieval Override Test ──────────────────────────────────────

def test_retrieval_intent_respects_spine_override_when_upgrading():
    from app.orchestration.retrieval_intent import build_retrieval_decision

    # Test with a simple greeting where normal classifier returns graph_only or no_retrieval
    # Spine override should upgrade to targeted_source_rag
    decision = build_retrieval_decision(
        message="你好",
        context={
            "spine_retrieval_override": {
                "retrieval_mode": "targeted_source_rag",
                "source_scope": "user_selected",
            }
        },
    )
    assert decision.retrieval_mode == "targeted_source_rag"
    assert decision.source_scope == "user_selected"
    assert decision.should_retrieve is True
    assert "课件" in decision.reason_for_user


def test_retrieval_intent_normal_without_override():
    from app.orchestration.retrieval_intent import build_retrieval_decision

    decision = build_retrieval_decision(
        message="TCP 拥塞控制是什么？",
        context={},
    )
    # Should follow normal classification (not spine override)
    assert decision.retrieval_mode != "no_retrieval" or decision.reason != "spine_material_directive"


# ── M3: Mistake Signal Tests ─────────────────────────────────────────

from app.signals.mistake_signal import MistakeSignalDetector


@pytest.mark.asyncio
async def test_mistake_no_signal_below_threshold():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)
    signals = await detector.on_error_created(
        user_id="u1", error_id="e1",
        linked_node_ids=["cn.tcp.congestion_control"],
    )
    assert len(signals) == 0  # Need 3 consecutive


@pytest.mark.asyncio
async def test_mistake_signal_after_three_errors():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)

    all_signals = []
    for i in range(3):
        signals = await detector.on_error_created(
            user_id="u1", error_id=f"e{i+1}",
            linked_node_ids=["cn.tcp.congestion_control"],
            error_type="concept_confusion",
        )
        all_signals.extend(signals)

    assert len(all_signals) == 1
    sig = all_signals[0]
    assert sig.state_key == "knowledge_transfer"
    assert sig.claim == "transfer_failure"
    assert sig.priority == "high"


@pytest.mark.asyncio
async def test_mistake_no_duplicate_signal():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)

    # 3 errors → first signal
    for i in range(3):
        await detector.on_error_created(
            user_id="u1", error_id=f"e{i+1}",
            linked_node_ids=["cn.tcp.congestion_control"],
        )
    # 4th error → should NOT generate duplicate signal
    signals = await detector.on_error_created(
        user_id="u1", error_id="e4",
        linked_node_ids=["cn.tcp.congestion_control"],
    )
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_mistake_policy_generates_avoid_new_chapter():
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["e1"],
        source_system="error_book",
        state_key="knowledge_transfer",
        claim="transfer_failure",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="TCP 拥塞控制连续 3 次出错",
        possible_effects=["avoid_new_chapter"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "repair_knowledge_bottleneck"
    assert directive.hard_constraints["avoid_new_chapter"] is True
    assert directive.hard_constraints["required_task_type"] == "worked_example_then_drill"

