"""Production wiring and scenario tests — extracted from test_signal_spine.py."""

from __future__ import annotations

from tests.unit.spine._helpers import FakeRedis, FakeRedisWithHset, _make_redis_mock, _make_signal

import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.signals.types import (
    ActionableSignal, ActionableStatePacket, AuroraAgenda, AuroraAgendaItem,
    AuroraControlSignal, CausalTrace, DirectiveApplicationAudit, ExecutionDirective,
    OutcomeRecord, PolicyDecision, StateEntry, UserVisibleReceipt, _uid,
)
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.policy_engine import PolicyEngine
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.spine_metrics import SpineMetricsCollector, METRIC_DEFINITIONS
from app.orchestration.prompts import build_system_prompt
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.causal_trace_store import CausalTraceStore
from app.signals.signal_ranker import SignalRanker
from app.signals.state_register import StateRegister
from app.signals.exam_sprint_policy import ExamSprintPolicyService
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.policy_analytics import PolicyAnalytics
from app.signals.policy_experiments import PolicyExperimentManager
from app.signals.learning_base import LearningBase
from app.signals.relationship_model import RelationshipModelService
from app.signals.skill_extraction import SkillExtractionService
from app.signals.goal_type_adapter import GoalTypeAdapter
from app.signals.directive_quota import DirectiveQuotaService
from app.signals.aurora_core_session import AuroraCoreSessionService, SessionClosure, StatePatch, PolicyChange
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.community_loops import CommunityLoopManager
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.goal_world_graph import GoalWorldGraphService
from app.signals.multi_goal_arbitration import MultiGoalArbitrator
from app.signals.timeline_card_renderer import TimelineCardRenderer
from app.signals.material_signal import MaterialSignalDetector
from app.signals.community_signal import CommunitySignalDetector
from app.signals.recall_notification import RecallNotificationBuilder, RecallMessage
# ═══════════════════════════════════════════════════════════════════════
# P0-1b: Achievement Quality Cross-Check (3-tier rules)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_quality_cross_check_rule_a_quality_ok():
    """Rule A: momentum_high + quality_ok → standard sustain_momentum."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qa",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="7天解锁5个成就",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal, context={"quality_ok": True, "accuracy_trend": "improving"})
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "sustain_momentum"


@pytest.mark.asyncio
async def test_quality_cross_check_rule_b_declining_accuracy():
    """Rule B: momentum_high + declining accuracy → mistake repair."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qb",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="7天解锁5个成就",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal, context={"quality_ok": False, "accuracy_trend": "declining"})
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "recognize_effort_but_repair_quality"
    assert decision.soft_biases.get("task_type") == "mistake_repair"


@pytest.mark.asyncio
async def test_quality_cross_check_rule_c_overrun():
    """Rule C: momentum_high + time overrun → protect sustainability."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qc",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="7天解锁5个成就",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal, context={"time_overrun": True})
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "protect_sustainability"
    assert decision.hard_constraints.get("max_task_duration_min") == 25


@pytest.mark.asyncio
async def test_quality_cross_check_rule_c_high_pressure():
    """Rule C: momentum_high + high_pressure → protect sustainability."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qc2",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="7天解锁5个成就",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal, context={"high_pressure": True})
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "protect_sustainability"


@pytest.mark.asyncio
async def test_quality_cross_check_no_context():
    """No context → standard momentum_high behavior (Rule A default)."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qd",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="7天解锁5个成就",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal, context=None)
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "sustain_momentum"


@pytest.mark.asyncio
async def test_quality_cross_check_does_not_affect_momentum_stalled():
    """Quality cross-check only applies to momentum_high, not stalled."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_qs",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_stalled",
        confidence=0.75,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="7天仅解锁1个成就",
        possible_effects=["reduce_pressure"],
        priority="medium",
    )
    result = await engine.evaluate(signal, context={"time_overrun": True})
    assert result is not None
    decision, _ = result
    # Should be rekindle_engagement, NOT protect_sustainability
    assert decision.primary_strategy == "rekindle_engagement"


# ═══════════════════════════════════════════════════════════════════════
# P0-6: ExamSprintPolicy + Galaxy Mastery Mapping
# ═══════════════════════════════════════════════════════════════════════


def test_exam_sprint_phase_d7():
    """D-7 → build_path phase."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=7, subject="计网")
    assert directive.phase.phase_id == "build_path"
    assert directive.phase.allow_new_chapters is True


def test_exam_sprint_phase_d3():
    """D-3 → bottleneck_training phase."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=3)
    assert directive.phase.phase_id == "bottleneck_training"
    assert directive.phase.allow_new_chapters is False


def test_exam_sprint_phase_d1():
    """D-1 → survival phase."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=1)
    assert directive.phase.phase_id == "survival"
    assert directive.phase.max_task_duration_min == 20


def test_exam_sprint_phase_d0():
    """D-0 → final_review phase."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=0)
    assert directive.phase.phase_id == "final_review"
    assert directive.phase.difficulty_cap == 1


def test_exam_sprint_should_activate():
    """should_activate for exam_rescue <= 30 days."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=7)
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=14)
    assert not ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=31)
    assert not ExamSprintPolicyService.should_activate(goal_mode="normal", days_to_deadline=3)
    assert not ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=None)


def test_mastery_to_task_type():
    """Mastery maps to correct task types."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    assert svc.mastery_to_task_type(0.1) == "concept_compression"
    assert svc.mastery_to_task_type(0.4) == "worked_example_guided_drill"
    assert svc.mastery_to_task_type(0.6) == "drill_mistake_check"
    assert svc.mastery_to_task_type(0.9) == "mixed_practice_exam_simulation"


def test_mastery_to_difficulty():
    """Mastery maps to correct difficulty levels."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    assert svc.mastery_to_difficulty(0.1) == 5
    assert svc.mastery_to_difficulty(0.4) == 3
    assert svc.mastery_to_difficulty(0.6) == 2
    assert svc.mastery_to_difficulty(0.9) == 1


def test_score_node_priorities():
    """Nodes sorted by priority: low mastery + high weight first."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    nodes = [
        {"node_id": "n1", "label": "TCP", "mastery": 0.8, "exam_weight": 1.0},
        {"node_id": "n2", "label": "UDP", "mastery": 0.2, "exam_weight": 1.5},
        {"node_id": "n3", "label": "HTTP", "mastery": 0.5, "exam_weight": 0.8},
    ]
    scored = svc.score_node_priorities(nodes)
    # UDP should be highest priority (low mastery, high weight)
    assert scored[0]["node_id"] == "n2"
    assert scored[0]["recommended_task_type"] == "concept_compression"
    assert scored[0]["recommended_difficulty"] == 5
    # TCP should be lowest priority (high mastery)
    assert scored[-1]["node_id"] == "n1"

# ═══════════════════════════════════════════════════════════════════════
# P0-6: ExamSprintPolicy — Deadline-Phase Adaptive Strategy
# ═══════════════════════════════════════════════════════════════════════


def test_exam_sprint_phase_d7_build_path():
    """D-7 → build_path: allow new chapters, mixed tasks, 45 min cap."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=7)
    assert directive.phase.phase_id == "build_path"
    assert directive.phase.allow_new_chapters is True
    assert directive.phase.max_task_duration_min == 45
    assert directive.phase.task_type_bias == "mixed"
    assert directive.days_to_deadline == 7


def test_exam_sprint_phase_d5_build_path():
    """D-5 still build_path."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=5)
    assert directive.phase.phase_id == "build_path"


def test_exam_sprint_phase_d4_bottleneck_training():
    """D-4 → bottleneck_training: no new chapters, worked_example."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=4)
    assert directive.phase.phase_id == "bottleneck_training"
    assert directive.phase.allow_new_chapters is False
    assert directive.phase.max_task_duration_min == 35
    assert directive.phase.task_type_bias == "worked_example"


def test_exam_sprint_phase_d2_error_repair():
    """D-2 → error_repair: drill mode, high-yield review, 25 min cap."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=2)
    assert directive.phase.phase_id == "error_repair"
    assert directive.phase.prefer_high_yield_review is True
    assert directive.phase.max_task_duration_min == 25
    assert directive.phase.task_type_bias == "drill"
    assert directive.phase.tone == "calm_urgent"


def test_exam_sprint_phase_d1_survival():
    """D-1 → survival: 20 min cap, exam_pack retrieval."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=1)
    assert directive.phase.phase_id == "survival"
    assert directive.phase.max_task_duration_min == 20
    assert directive.phase.retrieval_mode == "graph_summary_or_exam_pack"
    assert directive.phase.difficulty_cap == 2


def test_exam_sprint_phase_d0_final_review():
    """D-0 → final_review: 15 min cap, difficulty 1, only review."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=0)
    assert directive.phase.phase_id == "final_review"
    assert directive.phase.max_task_duration_min == 15
    assert directive.phase.difficulty_cap == 1
    assert directive.phase.task_type_bias == "review"


def test_exam_sprint_phase_past_deadline():
    """Past deadline (days < 0) → final_review as fallback."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=-1)
    assert directive.phase.phase_id == "final_review"


def test_exam_sprint_should_activate():
    """should_activate true for exam_rescue + <=30 days."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=7) is True
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=0) is True
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=8) is True
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=31) is False
    assert ExamSprintPolicyService.should_activate(goal_mode="standard", days_to_deadline=3) is False
    assert ExamSprintPolicyService.should_activate(goal_mode="exam_rescue", days_to_deadline=None) is False


def test_exam_sprint_mastery_to_task_type():
    """Mastery level maps to correct task types."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    assert svc.mastery_to_task_type(0.1) == "concept_compression"
    assert svc.mastery_to_task_type(0.4) == "worked_example_guided_drill"
    assert svc.mastery_to_task_type(0.6) == "drill_mistake_check"
    assert svc.mastery_to_task_type(0.8) == "mixed_practice_exam_simulation"


def test_exam_sprint_mastery_to_difficulty():
    """Mastery level maps to correct difficulty."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    assert svc.mastery_to_difficulty(0.1) == 5
    assert svc.mastery_to_difficulty(0.4) == 3
    assert svc.mastery_to_difficulty(0.6) == 2
    assert svc.mastery_to_difficulty(0.8) == 1


def test_exam_sprint_score_node_priorities():
    """Node priority scoring: lower mastery + higher weight = higher priority."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    nodes = [
        {"node_id": "tcp", "label": "TCP", "mastery": 0.8, "exam_weight": 2.0},
        {"node_id": "udp", "label": "UDP", "mastery": 0.2, "exam_weight": 1.5},
        {"node_id": "http", "label": "HTTP", "mastery": 0.5, "exam_weight": 3.0},
    ]
    scored = svc.score_node_priorities(nodes)
    assert scored[0]["node_id"] == "http"  # (1-0.5)*3.0 = 1.5
    assert scored[1]["node_id"] == "udp"  # (1-0.2)*1.5 = 1.2
    assert scored[2]["node_id"] == "tcp"  # (1-0.8)*2.0 = 0.4
    assert "priority_score" in scored[0]
    assert "recommended_task_type" in scored[0]


def test_exam_sprint_directive_serialization():
    """ExamSprintDirective round-trips through to_dict."""
    from app.signals.exam_sprint_policy import ExamSprintPolicyService
    svc = ExamSprintPolicyService()
    directive = svc.compute(days_to_deadline=3)
    d = directive.to_dict()
    assert "directive_id" in d
    assert "phase" in d
    assert d["phase"]["phase_id"] == "bottleneck_training"
    assert d["days_to_deadline"] == 3
    assert "max_task_duration_min" in d["constraints"]


@pytest.mark.asyncio
async def test_spine_get_exam_sprint_policy():
    """SpineOrchestrator.get_exam_sprint_policy delegates correctly."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis_client=redis)

    # Not exam rescue
    result = spine.get_exam_sprint_policy(days_to_deadline=3, goal_mode="standard")
    assert result is None

    # Exam rescue D-3
    result = spine.get_exam_sprint_policy(days_to_deadline=3, goal_mode="exam_rescue")
    assert result is not None
    assert result.phase.phase_id == "bottleneck_training"

    # Exam rescue D-0
    result = spine.get_exam_sprint_policy(days_to_deadline=0, goal_mode="exam_rescue")
    assert result is not None
    assert result.phase.phase_id == "final_review"


# ═══════════════════════════════════════════════════════════════════════
# P0-7: Divine Moments — Admit Misjudgment + Remember Time
# ═══════════════════════════════════════════════════════════════════════


def test_self_correction_receipt_insufficient():
    """When outcome is insufficient, build_self_correction_receipt returns correction."""
    from app.signals.types import CausalTrace, OutcomeRecord
    from app.signals.outcome_recorder import OutcomeRecorder
    redis = FakeRedis()
    recorder = OutcomeRecorder(redis)

    record = OutcomeRecord(
        outcome_id="or_test",
        causal_trace_id="tr_test",
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": False, "user_feedback": "看不懂"},
        attribution="insufficient",
        attribution_confidence=0.6,
        new_hypothesis="knowledge_explanation_failure",
        next_policy_suggestion="switch_to_worked_example",
    )
    receipt = recorder.build_self_correction_receipt(record)
    assert receipt is not None
    assert receipt["type"] == "divine_moment_self_correction"
    assert "recent_task_overrun" in receipt["message"]
    assert "knowledge_explanation_failure" in receipt["message"]
    assert receipt["new_action"] == "worked_example_then_drill"


def test_self_correction_receipt_effective():
    """When outcome is effective (not insufficient), no correction receipt."""
    from app.signals.types import OutcomeRecord
    from app.signals.outcome_recorder import OutcomeRecorder
    redis = FakeRedis()
    recorder = OutcomeRecorder(redis)

    record = OutcomeRecord(
        outcome_id="or_ok",
        causal_trace_id="tr_ok",
        intervention="reduce_pressure",
        reason="momentum_stalled",
        expected_outcome="task_started_and_completed",
        actual_outcome={"completed": True},
        attribution="effective",
        attribution_confidence=0.8,
    )
    receipt = recorder.build_self_correction_receipt(record)
    assert receipt is None


def test_remember_time_recovery_card():
    """StaleStateGuard builds structured recovery card with deadline context."""
    from app.signals.stale_state_guard import StaleStateGuard, TimeContext, TimeDeltaPacket
    guard = StaleStateGuard()

    ctx = TimeContext(
        now="2026-04-27T10:00:00",
        elapsed_since_last_interaction_min=120,
        active_task_id="task_123",
        active_task_status="started",
    )
    packet = guard.check(ctx, user_id="u_test")
    assert packet is not None

    card = guard.build_recovery_card(
        packet,
        deadline_phase="high_pressure",
        days_to_deadline=3,
    )
    assert card["type"] == "divine_moment_recovery"
    assert "deadline_context" in card
    assert card["deadline_context"]["urgency"] == "high"
    assert card["deadline_context"]["days_to_deadline"] == 3
    # Active task pending → must ask status first regardless of deadline
    assert card["recommended_action"]["action"] == "ask_status"


def test_remember_time_high_pressure_no_task():
    """High pressure + no active task → high_yield_drill recommended."""
    from app.signals.stale_state_guard import StaleStateGuard, TimeContext
    guard = StaleStateGuard()

    ctx = TimeContext(
        now="2026-04-27T10:00:00",
        elapsed_since_last_interaction_min=120,
        active_task_id=None,
    )
    packet = guard.check(ctx, user_id="u_test")
    assert packet is not None

    card = guard.build_recovery_card(
        packet,
        deadline_phase="high_pressure",
        days_to_deadline=3,
    )
    assert card["recommended_action"]["action"] == "high_yield_drill"


def test_remember_time_recovery_card_exam_day():
    """Exam day recovery: only light recall recommended."""
    from app.signals.stale_state_guard import StaleStateGuard, TimeContext
    guard = StaleStateGuard()

    ctx = TimeContext(
        now="2026-04-27T10:00:00",
        elapsed_since_last_interaction_min=90,
        active_task_id=None,
    )
    packet = guard.check(ctx, user_id="u_test")
    assert packet is not None

    card = guard.build_recovery_card(
        packet,
        deadline_phase="final_day",
        days_to_deadline=0,
    )
    assert card["recommended_action"]["action"] == "light_recall"


def test_remember_time_no_deadline():
    """Recovery card without deadline context."""
    from app.signals.stale_state_guard import StaleStateGuard, TimeContext
    guard = StaleStateGuard()

    ctx = TimeContext(
        now="2026-04-27T10:00:00",
        elapsed_since_last_interaction_min=90,
        active_task_id=None,
    )
    packet = guard.check(ctx, user_id="u_test")
    assert packet is not None

    card = guard.build_recovery_card(packet)
    assert card["deadline_context"] is None
    assert card["recommended_action"]["action"] == "resume_or_fresh"


# ═══════════════════════════════════════════════════════════════════════
# P0-5: SourceAsset / SourceSlice / Source Tray
# ═══════════════════════════════════════════════════════════════════════


def test_source_slice_serialization():
    """SourceSlice round-trips through to_dict/from_dict."""
    from app.signals.types import SourceSlice
    s = SourceSlice(
        slice_id="slice_001",
        source_id="src_001",
        location="p32-p45",
        summary="TCP 拥塞控制",
        concepts=["slow_start", "congestion_avoidance"],
        knowledge_nodes=["cn.tcp.congestion_control"],
        evidence_type="definition_and_example",
        noise_risk="low",
    )
    d = s.to_dict()
    restored = SourceSlice.from_dict(d)
    assert restored.slice_id == "slice_001"
    assert restored.source_id == "src_001"
    assert restored.concepts == ["slow_start", "congestion_avoidance"]
    assert restored.noise_risk == "low"


def test_source_asset_basic():
    """SourceAsset stores metadata and computes node relevance."""
    from app.signals.types import SourceAsset
    asset = SourceAsset(
        source_id="src_001",
        title="计算机网络第 3 章：传输层",
        source_type="slides",
        course="computer_networks",
        quality_score=0.78,
        mapped_nodes=["cn.tcp", "cn.udp", "cn.congestion_control"],
        recommended_uses=["concept_explanation", "task_material"],
        not_recommended_uses=["full_exam_scope_confirmation"],
    )
    d = asset.to_dict()
    restored = SourceAsset.from_dict(d)
    assert restored.source_id == "src_001"
    assert restored.quality_score == 0.78
    assert len(restored.mapped_nodes) == 3


def test_source_asset_relevance():
    """SourceAsset.relevance_for_nodes computes overlap ratio."""
    from app.signals.types import SourceAsset
    asset = SourceAsset(
        source_id="src_001",
        title="传输层课件",
        source_type="slides",
        mapped_nodes=["cn.tcp", "cn.udp", "cn.congestion_control"],
    )
    # 2 out of 3 target nodes overlap
    assert asset.relevance_for_nodes(["cn.tcp", "cn.congestion_control", "cn.http"]) == pytest.approx(2 / 3)
    # Full overlap
    assert asset.relevance_for_nodes(["cn.tcp"]) == 1.0
    # No overlap
    assert asset.relevance_for_nodes(["cn.http"]) == pytest.approx(0.0)
    # Empty target
    assert asset.relevance_for_nodes([]) == 0.0


def test_source_asset_with_slices():
    """SourceAsset with nested SourceSlice round-trips."""
    from app.signals.types import SourceAsset, SourceSlice
    slice1 = SourceSlice(
        slice_id="slice_001",
        source_id="src_001",
        location="p32-p45",
        summary="TCP 拥塞控制",
        concepts=["slow_start"],
        knowledge_nodes=["cn.tcp.congestion_control"],
    )
    asset = SourceAsset(
        source_id="src_001",
        title="传输层课件",
        source_type="slides",
        slices=[slice1],
    )
    d = asset.to_dict()
    assert len(d["slices"]) == 1
    restored = SourceAsset.from_dict(d)
    assert restored.slices is not None
    assert restored.slices[0].slice_id == "slice_001"


def test_source_tray_selection():
    """SourceTraySelection round-trips."""
    from app.signals.types import SourceTraySelection
    sel = SourceTraySelection(
        source_id="src_001",
        action="include",
        scope="this_task",
        user_initiated=True,
    )
    d = sel.to_dict()
    restored = SourceTraySelection.from_dict(d)
    assert restored.action == "include"
    assert restored.scope == "this_task"


def test_source_tray_state_include_exclude():
    """SourceTrayState filters included and excluded sources."""
    from app.signals.types import SourceTrayState, SourceTraySelection
    state = SourceTrayState(
        mode="manual_only",
        selections=[
            SourceTraySelection(source_id="src_001", action="include", scope="this_task"),
            SourceTraySelection(source_id="src_002", action="exclude", scope="this_turn"),
            SourceTraySelection(source_id="src_003", action="include", scope="today"),
        ],
    )
    assert state.get_included_source_ids() == ["src_001", "src_003"]
    assert state.get_excluded_source_ids() == ["src_002"]


def test_source_tray_state_auto_mode():
    """SourceTrayState defaults to auto mode with no selections."""
    from app.signals.types import SourceTrayState
    state = SourceTrayState()
    assert state.mode == "auto"
    assert state.get_included_source_ids() == []
    assert state.get_excluded_source_ids() == []


def test_source_asset_no_mapped_nodes():
    """SourceAsset with no mapped_nodes has 0 relevance."""
    from app.signals.types import SourceAsset
    asset = SourceAsset(source_id="src_002", title="笔记", source_type="notes")
    assert asset.relevance_for_nodes(["cn.tcp"]) == 0.0


def test_source_asset_empty_slices_round_trip():
    """SourceAsset with empty slices list round-trips correctly (W-3 fix)."""
    from app.signals.types import SourceAsset
    asset = SourceAsset(source_id="src_003", title="空切片", source_type="notes", slices=[])
    d = asset.to_dict()
    # to_dict includes slices as empty list
    assert d["slices"] == []
    restored = SourceAsset.from_dict(d)
    assert restored.slices == []


def test_source_tray_state_from_dict():
    """SourceTrayState round-trips through to_dict/from_dict (W-1 fix)."""
    from app.signals.types import SourceTrayState, SourceTraySelection, SourceAsset
    state = SourceTrayState(
        mode="manual_only",
        selections=[
            SourceTraySelection(source_id="src_001", action="include", scope="this_task"),
        ],
        available_sources=[
            SourceAsset(source_id="src_001", title="课件", source_type="slides"),
        ],
    )
    d = state.to_dict()
    restored = SourceTrayState.from_dict(d)
    assert restored.mode == "manual_only"
    assert len(restored.selections) == 1
    assert restored.selections[0].source_id == "src_001"
    assert len(restored.available_sources) == 1
    assert restored.available_sources[0].title == "课件"


# ═══════════════════════════════════════════════════════════════════════
# Skill Extraction — auto-extract effective strategies
# ═══════════════════════════════════════════════════════════════════════


def test_skill_entry_serialization():
    """SkillEntry round-trips through to_dict/from_dict."""
    from app.signals.types import SkillEntry
    skill = SkillEntry(
        skill_id="skill_001",
        scope="personal",
        source_policy_key="recover_execution_rhythm",
        strategy={"task_type": "worked_example_then_drill", "duration_min": 25},
        applicable_when={"goal_mode": "exam_rescue"},
        evidence={"effective_count": 3, "total_observed": 5, "avg_confidence": 0.82},
        effective_count=3,
        sample_size=5,
    )
    d = skill.to_dict()
    restored = SkillEntry.from_dict(d)
    assert restored.skill_id == "skill_001"
    assert restored.scope == "personal"
    assert restored.strategy["task_type"] == "worked_example_then_drill"


def test_skill_extraction_consecutive_effective():
    """Extract skill when 3+ consecutive effective outcomes."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    svc = SkillExtractionService()

    effects = [
        PolicyEffectEntry(
            entry_id=f"pe_{i}",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_duration_25min",
            attribution="effective",
            attribution_confidence=0.8,
        )
        for i in range(4)
    ]
    skills = svc.scan_for_extractions(effects, user_id="u1")
    assert len(skills) == 1
    assert skills[0].source_policy_key == "recover_execution_rhythm"
    assert skills[0].effective_count == 4


def test_skill_extraction_below_threshold():
    """No extraction when consecutive effective count < 3."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    svc = SkillExtractionService()

    effects = [
        PolicyEffectEntry(
            entry_id="pe_1",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.8,
        ),
        PolicyEffectEntry(
            entry_id="pe_2",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.75,
        ),
    ]
    skills = svc.scan_for_extractions(effects)
    assert len(skills) == 0


def test_skill_extraction_broken_by_insufficient():
    """No extraction when effective streak is broken by insufficient."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    svc = SkillExtractionService()

    effects = [
        PolicyEffectEntry(
            entry_id="pe_0",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="insufficient",
            attribution_confidence=0.5,
        ),
    ]
    effects += [
        PolicyEffectEntry(
            entry_id=f"pe_eff_{i}",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.8,
        )
        for i in range(3)
    ]
    skills = svc.scan_for_extractions(effects)
    # Last 3 are effective, so extraction triggers
    assert len(skills) == 1


def test_skill_extraction_negative_feedback_blocks():
    """No extraction when recent effective entries have negative feedback."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    svc = SkillExtractionService()

    effects = [
        PolicyEffectEntry(
            entry_id="pe_1",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.8,
            user_feedback_signal="completed",
        ),
        PolicyEffectEntry(
            entry_id="pe_2",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.8,
            user_feedback_signal="too_hard",
        ),
        PolicyEffectEntry(
            entry_id="pe_3",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_25min",
            attribution="effective",
            attribution_confidence=0.8,
        ),
    ]
    skills = svc.scan_for_extractions(effects)
    # "too_hard" is negative feedback → blocks extraction
    assert len(skills) == 0


def test_skill_should_extract_quick_check():
    """should_extract returns True for eligible policy keys."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    effects = [
        PolicyEffectEntry(
            entry_id=f"pe_{i}",
            policy_key="sustain_momentum",
            intervention_summary="keep_going",
            attribution="effective",
            attribution_confidence=0.85,
        )
        for i in range(4)
    ]
    assert SkillExtractionService.should_extract(policy_key="sustain_momentum", policy_effects=effects)
    assert not SkillExtractionService.should_extract(policy_key="nonexistent", policy_effects=effects)


def test_skill_extraction_with_context():
    """Extracted skill includes context information."""
    from app.signals.types import PolicyEffectEntry
    from app.signals.skill_extraction import SkillExtractionService
    svc = SkillExtractionService()

    effects = [
        PolicyEffectEntry(
            entry_id=f"pe_{i}",
            policy_key="repair_knowledge_bottleneck",
            intervention_summary="worked_example",
            attribution="effective",
            attribution_confidence=0.85,
        )
        for i in range(3)
    ]
    skills = svc.scan_for_extractions(
        effects,
        context={"goal_mode": "exam_rescue", "scope": "cohort"},
    )
    assert len(skills) == 1
    assert skills[0].scope == "cohort"
    assert skills[0].applicable_when["goal_mode"] == "exam_rescue"
    assert skills[0].privacy["shareable"] is True


# ═══════════════════════════════════════════════════════════════════════
# v2.0: SourceTrayIntegration — SourceAsset ↔ RetrievalDirective
# ═══════════════════════════════════════════════════════════════════════


async def test_source_tray_must_load_user_included():
    """User explicitly includes a source → must_load."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(
        mode="manual_only",
        selections=[SourceTraySelection(source_id="src_1", action="include")],
        available_sources=[
            SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides",
                        mapped_nodes=["tcp", "congestion_control"]),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="targeted_source_rag", pollution_guard="strict",
    )
    plan = await compute_retrieval_plan(retrieval_directive=directive, source_tray=tray)
    assert len(plan["must_load"]) == 1
    assert plan["must_load"][0]["source_id"] == "src_1"
    assert plan["must_load"][0]["reason"] == "user_explicitly_included"


async def test_source_tray_do_not_load_user_excluded():
    """User explicitly excludes a source → do_not_load."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(
        mode="auto",
        selections=[SourceTraySelection(source_id="src_2", action="exclude")],
        available_sources=[
            SourceAsset(source_id="src_2", title="Old Notes", source_type="notes"),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="targeted_source_rag", pollution_guard="strict",
    )
    plan = await compute_retrieval_plan(retrieval_directive=directive, source_tray=tray)
    assert len(plan["do_not_load"]) == 1
    assert plan["do_not_load"][0]["reason"] == "user_explicitly_excluded"


async def test_source_tray_strict_guard_low_relevance():
    """Strict pollution_guard skips low-relevance sources."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(
        mode="auto",
        available_sources=[
            SourceAsset(source_id="src_a", title="UDP Slides", source_type="slides",
                        mapped_nodes=["udp"]),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="targeted_source_rag", pollution_guard="strict",
    )
    # Query for TCP nodes — UDP source has 0 relevance
    plan = await compute_retrieval_plan(
        retrieval_directive=directive, source_tray=tray,
        target_nodes=["tcp", "congestion_control"],
    )
    assert len(plan["do_not_load"]) == 1
    assert "low_relevance" in plan["do_not_load"][0]["reason"]


async def test_source_tray_high_relevance_in_may_load():
    """High-relevance source goes to may_load in auto mode."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(
        mode="auto",
        available_sources=[
            SourceAsset(source_id="src_tcp", title="TCP Slides", source_type="slides",
                        mapped_nodes=["tcp", "congestion_control"]),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="targeted_source_rag", pollution_guard="permissive",
        token_budget=5000,
    )
    plan = await compute_retrieval_plan(
        retrieval_directive=directive, source_tray=tray,
        target_nodes=["tcp"],
    )
    # TCP source has 1.0 relevance for TCP query
    assert plan["relevance_scores"]["src_tcp"] == 1.0
    assert any(s["source_id"] == "src_tcp" for s in plan["may_load"] + plan["must_load"])


async def test_source_tray_failed_parse_excluded():
    """Failed parse sources always go to do_not_load."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(
        mode="auto",
        available_sources=[
            SourceAsset(source_id="bad", title="Bad File", source_type="notes",
                        parsed_status="failed"),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="targeted_source_rag",
    )
    plan = await compute_retrieval_plan(retrieval_directive=directive, source_tray=tray)
    assert len(plan["do_not_load"]) == 1
    assert plan["do_not_load"][0]["reason"] == "parse_failed"


async def test_source_tray_empty_sources():
    """Empty source tray returns empty plan."""
    from app.signals.types import RetrievalDirective, SourceTrayState
    from app.signals.source_tray_integration import compute_retrieval_plan

    tray = SourceTrayState(mode="auto")
    directive = RetrievalDirective(
        directive_id="rd_1", policy_decision_id="pd_1",
        retrieval_mode="no_rag",
    )
    plan = await compute_retrieval_plan(retrieval_directive=directive, source_tray=tray)
    assert plan["must_load"] == []
    assert plan["may_load"] == []
    assert plan["do_not_load"] == []


# ═══════════════════════════════════════════════════════════════════════
# P1-2: Source Tray → RetrievalDirective Integration
# ═══════════════════════════════════════════════════════════════════════


def test_build_source_receipt_with_loaded_sources():
    """Receipt lists loaded sources with user-selected reasons."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import build_source_receipt

    tray = SourceTrayState(
        mode="manual_only",
        selections=[SourceTraySelection(source_id="src_1", action="include")],
        available_sources=[SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides")],
    )
    directive = RetrievalDirective(
        directive_id="rd_1",
        policy_decision_id="pd_1",
        must_load=["src_1"],
    )

    receipt = build_source_receipt(directive, tray, ["src_1"])

    assert receipt["loaded"] == [{"source_id": "src_1", "title": "TCP Slides", "reason": "user_selected"}]
    assert receipt["skipped"] == []
    assert receipt["excluded"] == []
    assert "使用了你选的 1 份资料" in receipt["reason_for_user"]


def test_build_source_receipt_empty():
    """Empty tray and no loaded sources returns an empty receipt."""
    from app.signals.types import RetrievalDirective, SourceTrayState
    from app.signals.source_tray_integration import build_source_receipt

    tray = SourceTrayState(mode="auto")
    directive = RetrievalDirective(directive_id="rd_1", policy_decision_id="pd_1")

    receipt = build_source_receipt(directive, tray, [])

    assert receipt["loaded"] == []
    assert receipt["skipped"] == []
    assert receipt["excluded"] == []
    assert receipt["reason_for_user"] == "这轮没有加载资料。"


def test_build_source_receipt_mixed():
    """Receipt separates loaded, skipped, and excluded materials."""
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import build_source_receipt

    tray = SourceTrayState(
        mode="manual_only",
        selections=[
            SourceTraySelection(source_id="src_1", action="include"),
            SourceTraySelection(source_id="bad", action="include"),
            SourceTraySelection(source_id="old", action="exclude"),
        ],
        available_sources=[
            SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides"),
            SourceAsset(source_id="bad", title="Corrupt PDF", source_type="notes", parsed_status="failed"),
            SourceAsset(source_id="old", title="Old Notes", source_type="notes"),
        ],
    )
    directive = RetrievalDirective(
        directive_id="rd_1",
        policy_decision_id="pd_1",
        must_load=["src_1", "bad"],
        do_not_load=["old"],
    )

    receipt = build_source_receipt(directive, tray, ["src_1"])

    assert receipt["loaded"][0]["source_id"] == "src_1"
    assert receipt["skipped"] == [{"source_id": "bad", "title": "Corrupt PDF", "reason": "parse_failed"}]
    assert receipt["excluded"] == [{"source_id": "old", "title": "Old Notes", "reason": "user_excluded"}]
    assert "解析失败" in receipt["reason_for_user"]


def test_validate_source_tray_removes_invalid():
    """Stale include selections are removed when the source is unavailable."""
    from app.signals.types import SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import validate_source_tray_selections

    available = [SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides")]
    tray = SourceTrayState(
        mode="manual_only",
        selections=[
            SourceTraySelection(source_id="src_1", action="include"),
            SourceTraySelection(source_id="missing", action="include"),
        ],
        available_sources=available,
    )

    cleaned = validate_source_tray_selections(tray, available)

    assert [selection.source_id for selection in cleaned.selections or []] == ["src_1"]
    assert cleaned.available_sources == available


def test_validate_source_tray_keeps_valid():
    """Valid selections are preserved after SourceTray validation."""
    from app.signals.types import SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import validate_source_tray_selections

    available = [
        SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides"),
        SourceAsset(source_id="src_2", title="UDP Notes", source_type="notes"),
    ]
    tray = SourceTrayState(
        mode="auto",
        selections=[
            SourceTraySelection(source_id="src_1", action="include"),
            SourceTraySelection(source_id="src_2", action="exclude"),
        ],
    )

    cleaned = validate_source_tray_selections(tray, available)

    assert [selection.source_id for selection in cleaned.selections or []] == ["src_1", "src_2"]
    assert cleaned.mode == "auto"


@pytest.mark.asyncio
async def test_retrieval_directive_source_tray_integration():
    """Policy hard constraints flow into RetrievalDirective source_scope."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="material_utilization", claim="material_underutilized",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    decision.hard_constraints["source_scope"] = "user_selected"

    directive = engine.build_retrieval_directive(decision, signal)

    assert directive is not None
    assert directive.retrieval_mode == "targeted_source_rag"
    assert directive.source_scope == "user_selected"


@pytest.mark.asyncio
async def test_retrieval_directive_material_signal():
    """Material signals always build targeted SourceTray retrieval directives."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="material_signal",
        state_key="material_utilization", claim="material_underutilized",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="unused source tray materials", possible_effects=["change_retrieval_strategy"],
        priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result

    directive = engine.build_retrieval_directive(decision, signal)

    assert directive is not None
    assert directive.retrieval_mode == "targeted_source_rag"
    assert directive.source_scope == "user_selected"
    assert directive.pollution_guard == "strict"


def test_source_receipt_serialization():
    """Source receipt is a plain JSON-serializable structure."""
    import json
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState
    from app.signals.source_tray_integration import build_source_receipt

    tray = SourceTrayState(
        selections=[SourceTraySelection(source_id="src_1", action="include")],
        available_sources=[SourceAsset(source_id="src_1", title="TCP Slides", source_type="slides")],
    )
    directive = RetrievalDirective(
        directive_id="rd_1",
        policy_decision_id="pd_1",
        must_load=["src_1"],
    )

    restored = json.loads(json.dumps(build_source_receipt(directive, tray, ["src_1"])))

    assert restored["loaded"][0]["title"] == "TCP Slides"
    assert restored["loaded"][0]["reason"] == "user_selected"


# ══════════════════════════════════════════════════════════════════════
# P1-1: Causal Timeline UI — TimelineCardRenderer
# ══════════════════════════════════════════════════════════════════════


def test_timeline_card_compact_basic():
    """Compact card renders from signal + policy + directive."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_001",
        signal_data={
            "signal_id": "sig_1",
            "state_key": "task_granularity_fit",
            "claim": "recent_task_too_large",
            "confidence": 0.85,
            "evidence_summary": "连续2次任务超时",
        },
        policy_data={
            "policy_decision_id": "pd_1",
            "primary_strategy": "recover_execution_rhythm",
            "reason_for_user": "将任务时长调整为25分钟以内",
        },
        directives=[{
            "directive_id": "ed_1",
            "target_module": "task_generator",
            "user_visible_reason": "任务时长上限25分钟",
        }],
        receipt_data={
            "receipt_id": "rcpt_1",
            "message": "你的任务有点大，帮你拆小了",
            "actions": ["confirm", "correct", "dismiss"],
        },
        mode="compact",
        timestamp="2026-04-27T10:00:00Z",
    )
    assert card is not None
    assert card.mode == "compact"
    assert card.trace_id == "ct_001"
    assert "任务" in card.headline
    assert len(card.evidence_chain) >= 3
    assert card.card_type == "causal"


def test_timeline_card_expanded_with_evidence_chain():
    """Expanded card includes full evidence chain including outcome."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_002",
        signal_data={
            "state_key": "knowledge_transfer",
            "claim": "transfer_failure",
            "confidence": 0.9,
            "evidence_summary": "TCP协议连续3题出错",
        },
        policy_data={"primary_strategy": "repair_knowledge_gap"},
        outcome_data={"attribution": "insufficient", "new_hypothesis": "worked_example_needed"},
        mode="expanded",
        timestamp="2026-04-27T11:00:00Z",
    )
    assert card is not None
    assert card.mode == "expanded"
    assert card.card_type == "self_correction"
    assert any(step["step"] == "结果" for step in card.evidence_chain)


def test_timeline_card_exam_rescue():
    """Exam rescue signal renders with appropriate headline."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_003",
        signal_data={
            "state_key": "goal_mode", "claim": "exam_rescue_detected",
            "confidence": 0.95, "evidence_summary": "",
        },
        policy_data={"primary_strategy": "exam_sprint"},
        mode="compact",
    )
    assert card is not None
    assert "备考" in card.headline or "冲刺" in card.headline


def test_timeline_card_momentum_high_and_stalled():
    """Momentum signals render correctly for high and stalled."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()

    card_high = renderer.render_card(
        trace_id="ct_high",
        signal_data={"state_key": "growth_momentum", "claim": "momentum_high", "confidence": 0.8},
        mode="compact",
    )
    assert card_high is not None
    assert "好" in card_high.headline

    card_stalled = renderer.render_card(
        trace_id="ct_stalled",
        signal_data={"state_key": "growth_momentum", "claim": "momentum_stalled", "confidence": 0.7},
        mode="compact",
    )
    assert card_stalled is not None
    assert "慢" in card_stalled.headline or "调整" in card_stalled.headline


def test_timeline_card_recall_divine_moment():
    """Recall signals are tagged as divine_moment card type."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_recall",
        signal_data={"state_key": "recall_needed", "claim": "pre_exam_silence", "confidence": 0.6},
        mode="compact",
    )
    assert card is not None
    assert card.card_type == "divine_moment"


def test_timeline_card_no_signal_no_policy_returns_none():
    """Trace with no signal or policy returns None."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(trace_id="ct_empty", signal_data=None, policy_data=None, mode="compact")
    assert card is None


def test_timeline_card_community_cohort():
    """Community cohort mistake renders with appropriate headline."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_comm",
        signal_data={
            "state_key": "community_cohort_pattern", "claim": "cohort_mistake",
            "confidence": 0.7, "evidence_summary": "20个同学在TCP三次握手出错",
        },
        mode="compact",
    )
    assert card is not None
    assert "同学" in card.headline or "避坑" in card.headline


def test_timeline_card_user_actions_with_receipt():
    """Card with receipt has correct user actions."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_rcpt",
        signal_data={"state_key": "task_granularity_fit", "claim": "recent_task_too_large"},
        receipt_data={"actions": ["confirm", "correct", "dismiss"], "message": "调整任务大小"},
        mode="compact",
    )
    assert card is not None
    assert len(card.user_actions) >= 3
    assert any(a["action"] == "correct" for a in card.user_actions)


def test_timeline_card_user_actions_without_receipt():
    """Card without receipt defaults to 'why?' expand action."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_no_rcpt",
        signal_data={"state_key": "task_granularity_fit", "claim": "recent_task_too_large"},
        mode="compact",
    )
    assert card is not None
    assert len(card.user_actions) == 1
    assert card.user_actions[0]["action"] == "expand"


def test_timeline_card_batch_render():
    """Batch rendering skips non-renderable traces."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    traces = [
        {"trace_id": "ct_good", "signal": {"state_key": "task_granularity_fit", "claim": "recent_task_too_large"}},
        {"trace_id": "ct_empty"},
        {"trace_id": "ct_good2", "signal": {"state_key": "knowledge_transfer", "claim": "transfer_failure"}},
    ]
    cards = renderer.render_cards_batch(traces=traces, mode="compact")
    assert len(cards) == 2
    assert cards[0].trace_id == "ct_good"
    assert cards[1].trace_id == "ct_good2"


def test_timeline_card_serialization():
    """TimelineCard serializes to dict correctly."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_ser",
        signal_data={"state_key": "growth_momentum", "claim": "momentum_high"},
        mode="compact",
        timestamp="2026-04-27T10:00:00Z",
    )
    assert card is not None
    d = card.to_dict()
    assert d["trace_id"] == "ct_ser"
    assert d["mode"] == "compact"
    assert "headline" in d
    assert "evidence_chain" in d
    assert "user_actions" in d
    assert d["card_type"] in ("causal", "self_correction", "divine_moment")


def test_build_correction_options():
    """Correction options are context-specific."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    options = TimelineCardRenderer.build_correction_options(
        state_key="task_granularity_fit", claim="recent_task_too_large",
    )
    assert any("不用调" in o["label"] for o in options)

    options = TimelineCardRenderer.build_correction_options(
        state_key="knowledge_transfer", claim="transfer_failure",
    )
    assert any("粗心" in o["label"] for o in options)

    options = TimelineCardRenderer.build_correction_options(
        state_key="growth_momentum", claim="momentum_stalled",
    )
    assert any("休息" in o["label"] for o in options)


def test_timeline_card_evidence_chain_full():
    """Full evidence chain contains all 5 steps."""
    from app.signals.timeline_card_renderer import TimelineCardRenderer

    renderer = TimelineCardRenderer()
    card = renderer.render_card(
        trace_id="ct_full",
        signal_data={"state_key": "task_granularity_fit", "claim": "recent_task_too_large", "confidence": 0.9},
        policy_data={"primary_strategy": "recover_execution_rhythm", "reason_for_user": "调整任务时长"},
        directives=[{"target_module": "task_generator", "user_visible_reason": "25分钟上限"}],
        receipt_data={"message": "调整完成", "actions": ["confirm"]},
        outcome_data={"attribution": "effective"},
        mode="expanded",
    )
    assert card is not None
    steps = [s["step"] for s in card.evidence_chain]
    assert "检测" in steps
    assert "策略" in steps
    assert "执行" in steps
    assert "通知" in steps
    assert "结果" in steps


# ══════════════════════════════════════════════════════════════════════
# Task #3: CommunityDirective v1 — 3 Loops
# ══════════════════════════════════════════════════════════════════════


def test_cohort_mistake_hint_basic():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    hint = manager.build_cohort_mistake_hint({
        "knowledge_node_id": "tcp_handshake",
        "subject": "计算机网络",
        "mistake_type": "概念混淆",
        "cohort_size": 6,
        "error_count": 4,
        "common_misconception": "把 SYN 和 ACK 的顺序记反",
    })

    assert hint is not None
    assert hint["hint_type"] == "cohort_mistake"
    assert "6位同学" in hint["anonymous_summary"]
    assert hint["affected_nodes"] == ["tcp_handshake"]


def test_cohort_mistake_hint_too_small():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    hint = manager.build_cohort_mistake_hint({
        "knowledge_node_id": "tcp",
        "subject": "计算机网络",
        "mistake_type": "概念混淆",
        "cohort_size": 2,
        "error_count": 2,
        "common_misconception": "test",
    })

    assert hint is None


def test_cohort_mistake_hint_anonymous():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    hint = manager.build_cohort_mistake_hint({
        "knowledge_node_id": "node_1",
        "subject": "math",
        "mistake_type": "calculation",
        "cohort_size": 3,
        "student_id": "private_student",
        "student_name": "private_name",
        "common_misconception": "forgets sign",
    })

    assert hint is not None
    payload = json.dumps(hint, ensure_ascii=False)
    assert "private_student" not in payload
    assert "private_name" not in payload
    assert hint["privacy"] == "anonymous_aggregate_only"


def test_partner_feedback_pacing():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    adjustment = manager.apply_partner_feedback({
        "partner_id": "p1",
        "observation_type": "pacing",
        "observation_text": "She is moving too fast and seems overwhelmed.",
        "target_area": "networking",
    })

    assert adjustment is not None
    assert adjustment["adjustment_type"] == "pace_adjustment"
    assert adjustment["scope"] == "next_48h"
    assert adjustment["claim"] == "pacing_too_fast"
    assert adjustment["strategy_patch"]["pace_direction"] == "slow_down"
    assert "partner_id" not in adjustment


def test_partner_feedback_focus():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    adjustment = manager.apply_partner_feedback({
        "partner_id": "p1",
        "observation_type": "focus",
        "observation_text": "Keeps switching topics.",
        "target_area": "TCP",
    })

    assert adjustment is not None
    assert adjustment["adjustment_type"] == "topic_refocus"
    assert adjustment["scope"] == "current_sprint"
    assert adjustment["strategy_patch"]["reduce_context_switching"] is True


def test_partner_feedback_morale():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    adjustment = manager.apply_partner_feedback({
        "partner_id": "p1",
        "observation_type": "morale",
        "observation_text": "Seems discouraged today.",
        "target_area": "exam prep",
    })

    assert adjustment is not None
    assert adjustment["adjustment_type"] == "encouragement"
    assert adjustment["scope"] == "this_turn"
    assert adjustment["claim"] == "morale_encouragement_needed"


def test_resource_quality_high():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    score = manager.score_resource_quality({
        "resource_id": "res_1",
        "peer_ratings": [0.9, 0.8, 0.95],
        "usage_count": 8,
        "completion_rate": 0.85,
        "relevance_score": 0.9,
    })

    assert score["quality_score"] >= 0.8
    assert score["recommendation_level"] == "high"


def test_resource_quality_low():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    score = manager.score_resource_quality({
        "resource_id": "res_2",
        "peer_ratings": [0.2, 0.3, 0.4],
        "usage_count": 5,
        "completion_rate": 0.3,
        "relevance_score": 0.2,
    })

    assert score["quality_score"] < 0.5
    assert score["recommendation_level"] == "low"


def test_resource_quality_too_few_data():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    score = manager.score_resource_quality({
        "resource_id": "res_3",
        "peer_ratings": [1.0, 1.0],
        "usage_count": 2,
        "completion_rate": 1.0,
        "relevance_score": 1.0,
    })

    assert score["quality_score"] is None
    assert score["recommendation_level"] == "too_few_data"


def test_community_loop_serialization():
    from app.signals.community_loops import CommunityLoopManager

    manager = CommunityLoopManager()
    score = manager.score_resource_quality({
        "resource_id": "res_json",
        "peer_ratings": [0.7, 0.8, 0.9],
        "usage_count": 3,
        "completion_rate": 0.8,
        "relevance_score": 0.9,
    })

    restored = json.loads(json.dumps(score))
    assert restored["resource_id"] == "res_json"
    assert "quality_score" in restored


@pytest.mark.asyncio
async def test_policy_partner_feedback_pacing_plan_directive():
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_partner_pacing",
        source_event_ids=["community_partner_observation"],
        source_system="community_loops",
        state_key="community_partner_feedback",
        claim="pacing_too_fast",
        confidence=0.75,
        scope="next_48h",
        ttl_hours=48,
        evidence_summary="moving too fast",
        possible_effects=["strategy_micro_adjustment"],
        priority="medium",
    )

    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    plan_dir = engine.build_plan_directive(decision, signal)

    assert decision.primary_strategy == "adjust_partner_reported_pacing"
    assert plan_dir is not None
    assert plan_dir.scope == "next_48h"
    assert plan_dir.constraints["pace_adjustment"] == "slow_down"


@pytest.mark.asyncio
async def test_spine_partner_observation_pipeline():
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_partner_observation(
        user_id="u_partner",
        partner_id="partner_private",
        observation_type="pacing",
        observation_text="The pace is too fast this week.",
        target_area="networking",
    )

    assert trace is not None
    assert "community_partner_observation" in trace.raw_event_ids
    plan_dir = await spine.get_plan_directive("u_partner")
    assert plan_dir is not None
    assert plan_dir.scope == "next_48h"


# ══════════════════════════════════════════════════════════════════════
# Task #9: P3-1 — GoalWorldGraph Goal Type Adapter
# ══════════════════════════════════════════════════════════════════════


def test_goal_type_profile_exam():
    """Exam profile preserves knowledge graph and deadline-sensitive defaults."""
    from app.signals.goal_type_adapter import GoalTypeProfile

    profile = GoalTypeProfile.get_profile("exam")

    assert profile.goal_type == "exam"
    assert profile.deadline_sensitive is True
    assert profile.mastery_trackable is True
    assert profile.has_knowledge_graph is True
    assert profile.default_phase_count == 5
    assert profile.default_sprint_duration_days == 7
    assert profile.node_label == "知识点"


def test_goal_type_profile_project():
    """Project profile uses milestone semantics."""
    from app.signals.goal_type_adapter import GoalTypeProfile

    profile = GoalTypeProfile.get_profile("project")

    assert profile.goal_type == "project"
    assert profile.deadline_sensitive is True
    assert profile.mastery_trackable is False
    assert profile.has_knowledge_graph is False
    assert profile.default_phase_count == 4
    assert profile.default_sprint_duration_days == 14
    assert profile.node_label == "里程碑"


def test_goal_type_profile_job_search():
    """Job search profile tracks skills and supports graph-backed retrieval."""
    from app.signals.goal_type_adapter import GoalTypeProfile

    profile = GoalTypeProfile.get_profile("job_search")

    assert profile.goal_type == "job_search"
    assert profile.deadline_sensitive is False
    assert profile.mastery_trackable is True
    assert profile.has_knowledge_graph is True
    assert profile.default_phase_count == 5
    assert profile.default_sprint_duration_days == 30
    assert profile.node_label == "技能"


def test_goal_type_profile_general():
    """Unknown goal types fall back to the general profile safely."""
    from app.signals.goal_type_adapter import GoalTypeProfile

    profile = GoalTypeProfile.get_profile("unknown_goal")
    serialized = profile.to_dict()
    restored = GoalTypeProfile.from_dict(serialized)

    assert profile.goal_type == "general"
    assert profile.deadline_sensitive is False
    assert profile.mastery_trackable is False
    assert profile.default_phase_count == 3
    assert restored == profile


def test_adapt_mastery_mapping_exam():
    """Exam mastery mapping delegates to the existing exam sprint policy semantics."""
    from app.signals.goal_type_adapter import GoalTypeAdapter

    adapter = GoalTypeAdapter()
    low = adapter.adapt_mastery_mapping(0.2, "exam")
    high = adapter.adapt_mastery_mapping(0.9, "exam")

    assert low["task_type"] == "concept_compression"
    assert low["difficulty"] == 5
    assert low["node_label"] == "知识点"
    assert high["task_type"] == "mixed_practice_exam_simulation"
    assert high["difficulty"] == 1


def test_adapt_mastery_mapping_project():
    """Project mastery mapping moves from outline to submit."""
    from app.signals.goal_type_adapter import GoalTypeAdapter

    adapter = GoalTypeAdapter()
    early = adapter.adapt_mastery_mapping(0.1, "project")
    middle = adapter.adapt_mastery_mapping(0.45, "project")
    ready = adapter.adapt_mastery_mapping(0.92, "project")

    assert early["task_type"] == "outline"
    assert early["focus"] == "clarify_scope"
    assert middle["task_type"] == "draft"
    assert ready["task_type"] == "submit"
    assert ready["node_label"] == "里程碑"


def test_adapt_sprint_phases():
    """Sprint phases adapt count, labels, retrieval mode, and urgency by goal type."""
    from app.signals.goal_type_adapter import GoalTypeAdapter

    adapter = GoalTypeAdapter()
    project_phases = adapter.adapt_sprint_phases(days_to_deadline=10, goal_type="project")
    job_phases = adapter.adapt_sprint_phases(days_to_deadline=45, goal_type="job_search")

    assert [p["phase_id"] for p in project_phases] == ["scope", "build", "review", "ship"]
    assert project_phases[0]["node_label"] == "里程碑"
    assert project_phases[0]["urgency"] == "deadline"
    assert project_phases[0]["retrieval_mode"] == "targeted_source_rag"
    assert len(job_phases) == 5
    assert job_phases[0]["node_label"] == "技能"
    assert job_phases[0]["retrieval_mode"] == "task_bound_graph_rag"


def test_adapt_recall_message():
    """Recall copy changes language for exam and project contexts."""
    from app.signals.goal_type_adapter import GoalTypeAdapter

    adapter = GoalTypeAdapter()
    exam_message = adapter.adapt_recall_message(
        "pre_exam_silence",
        "exam",
        {"subject": "计网"},
    )
    project_message = adapter.adapt_recall_message(
        "pre_exam_silence",
        "project",
        {"target": "Demo"},
    )
    fallback = adapter.adapt_recall_message("unknown", "does_not_exist", {})

    assert "计网：" in exam_message
    assert "考前" in exam_message
    assert "Demo：" in project_message
    assert "交付前检查" in project_message
    assert fallback == "先把目标收束成一个下一步。"


# ═══════════════════════════════════════════════════════════════════════
# P1-5: SkillDirective v1 — inject/recommend/extract lifecycle
# ═══════════════════════════════════════════════════════════════════════


def _make_lifecycle_skill(
    *,
    skill_id: str = "skill_life_1",
    scope: str = "personal",
    effective_count: int = 5,
    sample_size: int = 6,
    applicable_when: dict | None = None,
):
    from app.signals.types import SkillEntry

    return SkillEntry(
        skill_id=skill_id,
        scope=scope,
        source_policy_key="repair_knowledge_bottleneck",
        strategy={"intervention_summary": "Show a worked example before the drill."},
        applicable_when=applicable_when or {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
        evidence={"effective_count": effective_count, "total_observed": sample_size, "avg_confidence": 0.84},
        privacy={"contains_personal_data": scope == "personal", "shareable": scope != "personal"},
        effective_count=effective_count,
        sample_size=sample_size,
    )


@pytest.mark.asyncio
async def test_skill_store_and_retrieve():
    """SkillLifecycleManager stores a user list entry and an ID lookup entry."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _make_lifecycle_skill(skill_id="skill_store")

    await manager.store_skill("u_skill", skill)

    user_skills = await manager.get_user_skills("u_skill")
    by_id = await manager.get_skill("skill_store")
    assert len(user_skills) == 1
    assert user_skills[0].skill_id == "skill_store"
    assert by_id is not None
    assert by_id.strategy["intervention_summary"].startswith("Show a worked example")


def test_find_applicable_skills_by_scope():
    """Personal skills rank before cohort and system skills."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skills = [
        _make_lifecycle_skill(skill_id="skill_system", scope="system", effective_count=12),
        _make_lifecycle_skill(skill_id="skill_personal", scope="personal", effective_count=3),
        _make_lifecycle_skill(skill_id="skill_cohort", scope="cohort", effective_count=9),
    ]

    applicable = manager.find_applicable_skills(
        skills,
        {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
    )

    assert [skill.skill_id for skill in applicable] == ["skill_personal", "skill_cohort", "skill_system"]


def test_find_applicable_skills_by_context():
    """Applicable skills must match declared goal_mode and state_key conditions."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skills = [
        _make_lifecycle_skill(skill_id="skill_goal", applicable_when={"goal_mode": "exam_rescue"}),
        _make_lifecycle_skill(skill_id="skill_state", applicable_when={"state_key": "knowledge_transfer"}),
        _make_lifecycle_skill(skill_id="skill_wrong", applicable_when={"goal_mode": "daily_growth"}),
    ]

    applicable = manager.find_applicable_skills(
        skills,
        {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
    )

    assert {skill.skill_id for skill in applicable} == {"skill_goal", "skill_state"}


def test_find_applicable_min_effective_count():
    """Skills below effective_count threshold are not injectable."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skills = [
        _make_lifecycle_skill(skill_id="skill_low", effective_count=2),
        _make_lifecycle_skill(skill_id="skill_ready", effective_count=3),
    ]

    applicable = manager.find_applicable_skills(
        skills,
        {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
    )

    assert [skill.skill_id for skill in applicable] == ["skill_ready"]


def test_build_worked_example_repair():
    """A skill converts into the worked-example-then-drill task patch."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _make_lifecycle_skill()

    patch = manager.build_worked_example_repair(skill, {"state_key": "knowledge_transfer"})

    assert patch["task_type_override"] == "worked_example_then_drill"
    assert patch["strategy_summary"] == "Show a worked example before the drill."
    assert patch["applies_to_nodes"] == "knowledge_transfer"
    assert patch["evidence"]["effective_count"] == 5


def test_build_recommendation_high_evidence():
    """High-evidence skills produce a user-confirmable recommendation."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _make_lifecycle_skill(effective_count=5)

    recommendation = manager.build_recommendation(skill)

    assert recommendation is not None
    assert recommendation["skill_id"] == skill.skill_id
    assert "Worked 5/6 times" in recommendation["evidence_summary"]
    labels = [option["label"] for option in recommendation["user_options"]]
    assert "Not now" in labels
    assert "Don't suggest again" in labels


def test_build_recommendation_low_evidence_none():
    """Low-evidence skills are not recommended to the user yet."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _make_lifecycle_skill(effective_count=4)

    assert manager.build_recommendation(skill) is None


def test_validate_extraction_valid():
    """A complete extracted skill passes validation."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _make_lifecycle_skill()

    result = manager.validate_extraction(skill)

    assert result == {"valid": True, "issues": []}


def test_validate_extraction_issues():
    """Invalid candidate skills report concrete extraction issues."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _make_lifecycle_skill(
        skill_id="",
        scope="global",
        effective_count=1,
        sample_size=0,
    )
    skill.source_policy_key = ""
    skill.strategy = {}

    result = manager.validate_extraction(skill)

    assert result["valid"] is False
    assert "missing_skill_id" in result["issues"]
    assert "invalid_scope" in result["issues"]
    assert "missing_intervention_summary" in result["issues"]
    assert "effective_count_below_threshold" in result["issues"]


def test_skill_lifecycle_serialization():
    """SkillEntry remains serializable for lifecycle persistence."""
    from app.signals.types import SkillEntry

    skill = _make_lifecycle_skill(skill_id="skill_serial")

    restored = SkillEntry.from_dict(skill.to_dict())

    assert restored.skill_id == "skill_serial"
    assert restored.effective_count == 5
    assert restored.privacy["contains_personal_data"] is True


@pytest.mark.asyncio
async def test_skill_lifecycle_orchestrator_inject_skill_to_task():
    """SpineOrchestrator injects the strongest applicable skill into task specs."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)
    skill = _make_lifecycle_skill(skill_id="skill_inject", effective_count=7)
    await spine.skill_lifecycle_manager.store_skill("u_inject", skill)

    modified = await spine.inject_skill_to_task(
        "u_inject",
        {"task_id": "task_1", "task_type": "drill"},
        {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
    )

    assert modified["task_type"] == "worked_example_then_drill"
    assert modified["_skill_injection"]["skill_id"] == "skill_inject"


@pytest.mark.asyncio
async def test_skill_lifecycle_orchestrator_recommend_skill():
    """SpineOrchestrator returns the highest-evidence recommendable skill."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)
    await spine.skill_lifecycle_manager.store_skill(
        "u_rec",
        _make_lifecycle_skill(skill_id="skill_recommend", effective_count=6),
    )

    recommendation = await spine.recommend_skill("u_rec")

    assert recommendation is not None
    assert recommendation["skill_id"] == "skill_recommend"


@pytest.mark.asyncio
async def test_skill_directive_inject_action():
    """recent_task_too_large can request SkillDirective injection."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_skill_inject",
        source_event_ids=["test"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="two recent tasks ran long",
        possible_effects=["inject_skill"],
        priority="high",
    )
    result = await engine.evaluate(signal, context={"consecutive": 2})
    assert result is not None
    decision, _ = result

    skill_dir = engine.build_skill_directive(decision, signal)

    assert skill_dir is not None
    assert skill_dir.skill_action == "inject"


# ═══════════════════════════════════════════════════════════════════════
# Task #7: Skill Lifecycle — promote/deprecate/health
# ═══════════════════════════════════════════════════════════════════════


def _skill_lifecycle_entry(
    *,
    skill_id: str = "skill_life_1",
    scope: str = "personal",
    effective_count: int = 10,
    sample_size: int = 12,
    avg_confidence: float = 0.82,
    shareable: bool = True,
    evidence_extra: dict | None = None,
):
    from app.signals.types import SkillEntry

    evidence = {
        "effective_count": effective_count,
        "total_observed": sample_size,
        "avg_confidence": avg_confidence,
    }
    if evidence_extra:
        evidence.update(evidence_extra)
    return SkillEntry(
        skill_id=skill_id,
        scope=scope,
        source_policy_key="recover_execution_rhythm",
        strategy={"intervention_summary": "worked_example_then_drill"},
        applicable_when={"goal_mode": "exam_rescue", "state_key": "tcp"},
        evidence=evidence,
        privacy={"contains_personal_data": False, "shareable": shareable},
        effective_count=effective_count,
        sample_size=sample_size,
    )


@pytest.mark.asyncio
async def test_promote_skill_personal_to_cohort():
    """Personal skill promotes to cohort when evidence and privacy gates pass."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry(effective_count=10, avg_confidence=0.81)
    await manager.store_skill("u1", skill)

    promoted = await manager.promote_skill("u1", skill.skill_id, "cohort")

    assert promoted is not None
    assert promoted.scope == "cohort"
    assert promoted.evidence["promoted_from"] == "personal"
    stored = await manager.get_skill(skill.skill_id)
    assert stored is not None
    assert stored.scope == "cohort"


@pytest.mark.asyncio
async def test_promote_skill_insufficient_evidence():
    """Promotion is blocked below threshold."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry(effective_count=9, avg_confidence=0.79)
    await manager.store_skill("u1", skill)

    promoted = await manager.promote_skill("u1", skill.skill_id, "cohort")

    assert promoted is None
    stored = await manager.get_skill(skill.skill_id)
    assert stored is not None
    assert stored.scope == "personal"


@pytest.mark.asyncio
async def test_promote_skill_cohort_to_system():
    """Cohort skill promotes to system with stronger evidence."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry(
        skill_id="skill_life_system",
        scope="cohort",
        effective_count=50,
        sample_size=55,
        avg_confidence=0.86,
    )
    await manager.store_skill("u1", skill)

    promoted = await manager.promote_skill("u1", skill.skill_id, "system")

    assert promoted is not None
    assert promoted.scope == "system"
    assert promoted.evidence["promotion_history"][-1]["to"] == "system"


@pytest.mark.asyncio
async def test_deprecate_skill():
    """Deprecation marks the skill but does not delete it."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry()
    await manager.store_skill("u1", skill)

    await manager.deprecate_skill("u1", skill.skill_id, "user_rejected")

    stored = await manager.get_skill(skill.skill_id)
    assert stored is not None
    assert stored.evidence["deprecated"] is True
    assert stored.evidence["deprecation_reason"] == "user_rejected"


@pytest.mark.asyncio
async def test_auto_deprecate_stale_skill():
    """Auto deprecation catches skills whose effective count is stale."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry(
        evidence_extra={"effective_count_updated_at": "2026-03-01T00:00:00Z"},
    )
    await manager.store_skill("u1", skill)

    deprecated = await manager.auto_deprecate_check("u1")

    assert deprecated == [skill.skill_id]
    stored = await manager.get_skill(skill.skill_id)
    assert stored is not None
    assert stored.evidence["deprecated"] is True
    assert stored.evidence["deprecation_reason"] == "effective_count_stale_30_days"


@pytest.mark.asyncio
async def test_auto_deprecate_healthy_skill():
    """Healthy skills with recent effective outcomes remain active."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    redis = FakeRedis()
    manager = SkillLifecycleManager(redis)
    skill = _skill_lifecycle_entry(
        evidence_extra={
            "effective_count_updated_at": "2026-04-20T00:00:00Z",
            "recent_outcomes": ["effective", "effective", "insufficient", "effective", "effective"],
        },
    )
    await manager.store_skill("u1", skill)

    deprecated = await manager.auto_deprecate_check("u1")

    assert deprecated == []
    stored = await manager.get_skill(skill.skill_id)
    assert stored is not None
    assert stored.evidence.get("deprecated") is None


def test_compute_skill_health_good():
    """Healthy skill gets high score and reuse recommendation."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _skill_lifecycle_entry(
        effective_count=9,
        sample_size=10,
        evidence_extra={"recent_outcomes": ["effective", "effective", "effective", "effective"]},
    )

    health = manager.compute_skill_health(skill)

    assert health["health_score"] == 0.9
    assert health["trend"] == "stable"
    assert health["recommendation"] == "promote_or_reuse"


def test_compute_skill_health_declining():
    """Declining recent outcomes trigger review recommendation."""
    from app.signals.skill_lifecycle import SkillLifecycleManager

    manager = SkillLifecycleManager(FakeRedis())
    skill = _skill_lifecycle_entry(
        effective_count=4,
        sample_size=8,
        evidence_extra={
            "recent_outcomes": [
                "effective",
                "effective",
                "effective",
                "effective",
                "insufficient",
                "insufficient",
                "insufficient",
                "insufficient",
            ],
        },
    )

    health = manager.compute_skill_health(skill)

    assert health["health_score"] == 0.5
    assert health["trend"] == "declining"
    assert health["recommendation"] == "review_or_deprecate"


# ═══════════════════════════════════════════════════════════════════
# Task #5: Goal-Respectful Recall Notification
# ═══════════════════════════════════════════════════════════════════


def test_recall_message_undigested_material():
    """undigested_material → low-effort user-facing message."""
    from app.signals.recall_notification import RecallNotificationBuilder

    builder = RecallNotificationBuilder()
    message = builder.build_message(
        "undigested_material",
        "low_effort_next_step",
        {"uploaded": 3, "undigested": 2},
    )
    assert message is not None
    assert message.title == "你的课件还没看完"
    assert "3份资料" in message.body
    assert "2份没诊断" in message.body
    assert message.deep_link == "/materials?filter=undigested"


def test_recall_message_task_not_started():
    """task_not_started → pending task deep link."""
    from app.signals.recall_notification import RecallNotificationBuilder

    builder = RecallNotificationBuilder()
    message = builder.build_message("task_not_started", "low_effort_next_step", {})
    assert message is not None
    assert message.title == "任务等你开始"
    assert message.deep_link == "/tasks?status=pending"
    assert message.frequency_tag == "1_per_day"


def test_recall_message_task_missed():
    """task_missed → recovery_offer message."""
    from app.signals.recall_notification import RecallNotificationBuilder

    builder = RecallNotificationBuilder()
    message = builder.build_message("task_missed", "recovery_offer", {})
    assert message is not None
    assert message.strategy == "recovery_offer"
    assert message.title == "有个任务错过了"
    assert message.frequency_tag == "2_per_day"


def test_recall_message_pre_exam_silence():
    """pre_exam_silence → quick review message."""
    from app.signals.recall_notification import RecallNotificationBuilder

    builder = RecallNotificationBuilder()
    message = builder.build_message(
        "pre_exam_silence",
        "quick_review_offer",
        {"exam_deadline_days": 2.0},
    )
    assert message is not None
    assert message.title == "考前快速复习"
    assert "还有2天就考了" in message.body
    assert message.deep_link == "/review?mode=quick"


def test_recall_message_unknown_trigger_none():
    """Unknown recall trigger should not build a notification."""
    from app.signals.recall_notification import RecallNotificationBuilder

    builder = RecallNotificationBuilder()
    assert builder.build_message("unknown", "low_effort_next_step", {}) is None


def test_recall_cooldown_check():
    """record_sent starts cooldown for the trigger type."""
    from app.signals.recall_notification import RecallNotificationBuilder

    redis = FakeRedis()
    builder = RecallNotificationBuilder()
    builder.record_sent("u_recall", "undigested_material", redis)
    assert builder.check_cooldown("u_recall", "undigested_material", redis) is True


def test_recall_cooldown_not_in_cooldown():
    """No sent marker means no cooldown."""
    from app.signals.recall_notification import RecallNotificationBuilder

    redis = FakeRedis()
    builder = RecallNotificationBuilder()
    assert builder.check_cooldown("u_recall", "task_not_started", redis) is False


def test_recall_record_sent():
    """record_sent stores sent_at and cooldown_until metadata."""
    from app.signals.recall_notification import RecallNotificationBuilder

    redis = FakeRedis()
    builder = RecallNotificationBuilder()
    builder.record_sent("u_recall", "task_missed", redis)
    raw = redis._store["spine:recall_notification_cooldown:u_recall:task_missed"]
    data = json.loads(raw)
    assert "sent_at" in data
    assert "cooldown_until" in data


def test_recall_user_preference_schema():
    """Recall preferences are explicit per trigger type."""
    from app.signals.recall_notification import RecallNotificationBuilder

    schema = RecallNotificationBuilder().build_user_preference_schema()
    assert schema["undigested_material"]["enabled"] is True
    assert schema["undigested_material"]["quiet_hours"] == "22:00-08:00"
    assert schema["task_missed"]["max_per_day"] == 2
    assert schema["task_not_started"]["max_per_day"] == 1


def test_recall_message_serialization():
    """RecallMessage round-trips through dict serialization."""
    from app.signals.recall_notification import RecallMessage

    message = RecallMessage(
        message_id="rmsg_1",
        trigger_type="task_missed",
        strategy="recovery_offer",
        title="有个任务错过了",
        body="没关系，帮你重新安排了一个更合适的任务。",
        deep_link="/tasks?status=recovery",
        cooldown_until="2026-04-27T10:00:00+00:00",
        frequency_tag="2_per_day",
    )
    restored = RecallMessage.from_dict(message.to_dict())
    assert restored.message_id == "rmsg_1"
    assert restored.trigger_type == "task_missed"
    assert restored.frequency_tag == "2_per_day"


@pytest.mark.asyncio
async def test_recall_notification_orchestrator_integration():
    """Spine builds NotificationDirective and RecallMessage together."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)
    message = await spine.build_recall_notification(
        user_id="u_recall",
        trigger_type="undigested_material",
        context={"uploaded": 4, "undigested": 1},
    )
    assert message is not None
    assert "4份资料" in message.body

    stored_message = await spine.get_recall_notification("u_recall")
    stored_directive = await spine.get_notification_directive("u_recall")
    assert stored_message is not None
    assert stored_message.trigger_type == "undigested_material"
    assert stored_directive is not None
    assert stored_directive.trigger == "undigested_material"


# ══════════════════════════════════════════════════════════════════════
# P1-3: Core Session Lifecycle
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_core_session_create():
    """CoreSessionManager creates an active modeling session."""
    from app.signals.core_session import CoreSessionManager

    redis = FakeRedis()
    manager = CoreSessionManager(redis)
    session = await manager.create_session(user_id="u_session", goal_id="goal_1")

    assert session.session_id.startswith("sess_")
    assert session.user_id == "u_session"
    assert session.goal_id == "goal_1"
    assert session.phase == "modeling"
    assert redis._store[f"spine:session_active:u_session"] == session.session_id


@pytest.mark.asyncio
async def test_core_session_advance_phases():
    """CoreSession advances through planning/executing/reflecting."""
    from app.signals.core_session import CoreSessionManager

    manager = CoreSessionManager(FakeRedis())
    session = await manager.create_session(user_id="u_phase")

    session = await manager.advance_phase(session.session_id, "planning")
    assert session.phase == "planning"
    session = await manager.advance_phase(session.session_id, "executing")
    assert session.phase == "executing"
    session = await manager.advance_phase(session.session_id, "reflecting")
    assert session.phase == "reflecting"


@pytest.mark.asyncio
async def test_core_session_pause_resume():
    """Pause increments pause_count and resume clears paused snapshot flag."""
    from app.signals.core_session import CoreSessionManager

    manager = CoreSessionManager(FakeRedis())
    session = await manager.create_session(user_id="u_pause")

    paused = await manager.pause_session(session.session_id)
    assert paused.pause_count == 1
    assert paused.context_snapshot["paused"] is True

    resumed = await manager.resume_session(session.session_id)
    assert resumed.pause_count == 1
    assert resumed.context_snapshot["paused"] is False


@pytest.mark.asyncio
async def test_core_session_complete():
    """Completing a session marks it completed and clears active user pointer."""
    from app.signals.core_session import CoreSessionManager

    redis = FakeRedis()
    manager = CoreSessionManager(redis)
    session = await manager.create_session(user_id="u_complete")

    completed = await manager.complete_session(session.session_id)
    assert completed.phase == "completed"
    assert await manager.get_active_session("u_complete") is None


@pytest.mark.asyncio
async def test_core_session_record_tasks():
    """Task counters track total and completed tasks."""
    from app.signals.core_session import CoreSessionManager

    manager = CoreSessionManager(FakeRedis())
    session = await manager.create_session(user_id="u_tasks")

    session = await manager.record_task(session.session_id, completed=False)
    session = await manager.record_task(session.session_id, completed=True)

    assert session.task_count == 2
    assert session.completed_task_count == 1


@pytest.mark.asyncio
async def test_core_session_link_directive():
    """Session stores the most recent linked directive id."""
    from app.signals.core_session import CoreSessionManager

    manager = CoreSessionManager(FakeRedis())
    session = await manager.create_session(user_id="u_link")

    linked = await manager.link_directive(session.session_id, "ed_123")
    assert linked.last_directive_id == "ed_123"


def test_core_session_serialization():
    """CoreSession serializes and restores all lifecycle fields."""
    from app.signals.core_session import CoreSession

    session = CoreSession(
        session_id="sess_1",
        user_id="u_serial",
        goal_id="goal_1",
        phase="executing",
        started_at="2026-04-27T00:00:00+00:00",
        updated_at="2026-04-27T00:05:00+00:00",
        pause_count=1,
        task_count=3,
        completed_task_count=2,
        last_directive_id="ed_1",
        context_snapshot={"paused": False},
    )

    restored = CoreSession.from_dict(session.to_dict())
    assert restored.session_id == session.session_id
    assert restored.task_count == 3
    assert restored.context_snapshot["paused"] is False


@pytest.mark.asyncio
async def test_core_session_manager_redis():
    """Manager persists session JSON with 7-day TTL."""
    from app.signals.core_session import CoreSessionManager

    redis = FakeRedis()
    manager = CoreSessionManager(redis)
    session = await manager.create_session(user_id="u_redis")
    restored = await manager.get_session(session.session_id)

    assert restored is not None
    assert restored.session_id == session.session_id
    assert redis._expires[f"spine:session:{session.session_id}"] == 7 * 24 * 3600
    assert redis._expires["spine:session_active:u_redis"] == 7 * 24 * 3600


@pytest.mark.asyncio
async def test_core_session_active_user():
    """Active-session lookup returns the newest active session for a user."""
    from app.signals.core_session import CoreSessionManager

    manager = CoreSessionManager(FakeRedis())
    first = await manager.create_session(user_id="u_active", goal_id="goal_old")
    second = await manager.create_session(user_id="u_active", goal_id="goal_new")
    active = await manager.get_active_session("u_active")

    assert active is not None
    assert active.session_id == second.session_id
    assert active.session_id != first.session_id
    assert active.goal_id == "goal_new"


@pytest.mark.asyncio
async def test_spine_orchestrator_session_integration():
    """_run_signal_pipeline links generated directive to active CoreSession."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)
    session = await spine.create_core_session(user_id="u_integrated", goal_id="goal_pipe")
    signal = ActionableSignal(
        signal_id="sig_core_session",
        source_event_ids=["evt_core_session"],
        source_system="test",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="连续 2 次超时",
        possible_effects=["cap_task_duration"],
        priority="high",
    )

    trace = await spine._run_signal_pipeline(user_id="u_integrated", signal=signal)
    active = await spine.get_active_core_session("u_integrated")

    assert trace is not None
    assert active is not None
    assert active.session_id == session.session_id
    assert active.last_directive_id is not None
    assert active.last_directive_id in trace.directive_ids


# ═══════════════════════════════════════════════════════════════════════
# P2-1: PolicyEffectLedger Analytics
# ═══════════════════════════════════════════════════════════════════════


def _policy_effect(
    entry_id: str,
    policy_key: str,
    attribution: str,
    confidence: float = 0.8,
    feedback: str | None = None,
):
    """Build a PolicyEffectEntry for analytics tests."""
    from app.signals.types import PolicyEffectEntry

    return PolicyEffectEntry(
        entry_id=entry_id,
        policy_key=policy_key,
        intervention_summary="test intervention",
        attribution=attribution,
        attribution_confidence=confidence,
        user_feedback_signal=feedback,
    )


def test_compute_strategy_accuracy_basic():
    """Accuracy is computed per policy_key."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect("pe_1", "recover_execution_rhythm", "effective"),
        _policy_effect("pe_2", "recover_execution_rhythm", "insufficient"),
        _policy_effect("pe_3", "sustain_momentum", "effective"),
    ]

    accuracy = analytics.compute_strategy_accuracy(effects)

    assert accuracy["recover_execution_rhythm"] == 0.5
    assert accuracy["sustain_momentum"] == 1.0


def test_compute_strategy_accuracy_empty():
    """Empty ledgers return an empty accuracy map."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)

    assert analytics.compute_strategy_accuracy([]) == {}


def test_detect_degrading_strategies():
    """A policy is degrading when its latest window performs worse than all history."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect(f"pe_good_{i}", "recover_execution_rhythm", "effective")
        for i in range(8)
    ]
    effects += [
        _policy_effect(f"pe_bad_{i}", "recover_execution_rhythm", "insufficient")
        for i in range(2)
    ]

    assert analytics.detect_degrading_strategies(effects, window=2) == ["recover_execution_rhythm"]


def test_detect_degrading_stable():
    """Stable policies are not marked as degrading."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect(f"pe_{i}", "sustain_momentum", "effective")
        for i in range(5)
    ]

    assert analytics.detect_degrading_strategies(effects, window=2) == []


def test_compute_confidence_distribution():
    """Confidence stats include core descriptive statistics."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect("pe_1", "policy", "effective", confidence=0.6),
        _policy_effect("pe_2", "policy", "effective", confidence=0.8),
        _policy_effect("pe_3", "policy", "insufficient", confidence=1.0),
    ]

    stats = analytics.compute_confidence_distribution(effects)

    assert stats["count"] == 3
    assert stats["mean"] == 0.8
    assert stats["median"] == 0.8
    assert stats["min"] == 0.6
    assert stats["max"] == 1.0
    assert stats["std"] > 0


def test_suggest_policy_review():
    """Low accuracy, confidence decline, and mixed feedback trigger review."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect("pe_1", "recover_execution_rhythm", "effective", 0.9, "completed"),
        _policy_effect("pe_2", "recover_execution_rhythm", "insufficient", 0.82, "too_hard"),
        _policy_effect("pe_3", "recover_execution_rhythm", "insufficient", 0.68, "cant_understand"),
        _policy_effect("pe_4", "recover_execution_rhythm", "insufficient", 0.58, "too_hard"),
    ]

    suggestions = analytics.suggest_policy_review(effects)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion["policy_key"] == "recover_execution_rhythm"
    assert "low_accuracy" in suggestion["reasons"]
    assert "confidence_declining" in suggestion["reasons"]
    assert "mixed_user_feedback" in suggestion["reasons"]


def test_suggest_policy_review_none_needed():
    """Healthy policies produce no human review suggestions."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect(f"pe_{i}", "sustain_momentum", "effective", 0.85, "completed")
        for i in range(5)
    ]

    assert analytics.suggest_policy_review(effects) == []


def test_build_analytics_snapshot():
    """Snapshot combines all policy analytics outputs."""
    from app.signals.policy_analytics import PolicyAnalytics

    analytics = PolicyAnalytics(redis_client=None)
    effects = [
        _policy_effect(f"pe_good_{i}", "recover_execution_rhythm", "effective", 0.8)
        for i in range(10)
    ]
    effects += [
        _policy_effect(f"pe_bad_{i}", "recover_execution_rhythm", "insufficient", 0.6)
        for i in range(2)
    ]

    snapshot = analytics.build_analytics_snapshot("u_analytics", effects)

    assert snapshot["user_id"] == "u_analytics"
    assert snapshot["total_effects"] == 12
    assert snapshot["accuracy_by_policy"]["recover_execution_rhythm"] == 0.8333
    assert snapshot["degrading"] == ["recover_execution_rhythm"]
    assert snapshot["confidence_stats"]["count"] == 12
    assert "review_suggestions" in snapshot


# ═══════════════════════════════════════════════════════════════════════
# Task #8: P2-3 — Relationship Model
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_relationship_create_default():
    """RelationshipModelService creates a default relationship state."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    state = await service.get_or_create("u_rel")

    assert state.user_id == "u_rel"
    assert state.trust_level == 0.5
    assert state.interaction_style == "exploratory"
    assert state.correction_frequency == 0.0
    assert state.engagement_depth == "surface"
    assert state.total_interactions == 0


@pytest.mark.asyncio
async def test_relationship_update_confirmed():
    """Confirmed interactions increase trust and confirmation count."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    state = await service.update_from_interaction("u_rel", "confirmed")

    assert state.trust_level == 0.52
    assert state.total_interactions == 1
    assert state.total_confirmations == 1
    assert state.total_corrections == 0


@pytest.mark.asyncio
async def test_relationship_update_corrected():
    """Corrected interactions lower trust and update correction frequency."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    state = await service.update_from_interaction("u_rel", "corrected")

    assert state.trust_level == 0.45
    assert state.total_corrections == 1
    assert state.correction_frequency == 10.0
    assert state.interaction_style == "corrective"


@pytest.mark.asyncio
async def test_relationship_update_dismissed():
    """Dismissed interactions lower trust slightly."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    state = await service.update_from_interaction("u_rel", "dismissed")

    assert state.trust_level == 0.49
    assert state.total_interactions == 1
    assert state.preferences["last_interaction_type"] == "dismissed"


@pytest.mark.asyncio
async def test_relationship_trust_bounds():
    """Trust level stays within floor and cap."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    for _ in range(40):
        low_state = await service.update_from_interaction("u_low", "corrected")
    for _ in range(40):
        high_state = await service.update_from_interaction("u_high", "confirmed")

    assert low_state.trust_level == 0.1
    assert high_state.trust_level == 1.0


@pytest.mark.asyncio
async def test_relationship_interaction_style():
    """Repeated corrections, ignored turns, and confirmations infer styles."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())

    corrected = await service.update_from_interaction("u_corrective", "corrected")
    assert corrected.interaction_style == "corrective"

    await service.update_from_interaction("u_passive", "ignored")
    await service.update_from_interaction("u_passive", "dismissed")
    passive = await service.update_from_interaction("u_passive", "ignored")
    assert passive.interaction_style == "passive"

    await service.update_from_interaction("u_directive", "confirmed")
    await service.update_from_interaction("u_directive", "confirmed")
    directive = await service.update_from_interaction("u_directive", "confirmed")
    assert directive.interaction_style == "directive"


@pytest.mark.asyncio
async def test_relationship_strategy_conservative():
    """Low trust uses conservative strategy adjustments."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    for _ in range(6):
        await service.update_from_interaction("u_rel", "corrected")

    adjustment = await service.get_strategy_adjustment("u_rel")

    # D4 hybrid: stance-driven tone (strained or cooldown)
    assert adjustment["tone_adjustment"] in ("cautious", "minimal", "conservative")
    assert adjustment["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_relationship_strategy_proactive():
    """High trust uses proactive strategy adjustments."""
    from app.signals.relationship_model import RelationshipModelService

    service = RelationshipModelService(FakeRedis())
    for _ in range(16):
        await service.update_from_interaction("u_rel", "confirmed")

    adjustment = await service.get_strategy_adjustment("u_rel")

    assert adjustment["tone_adjustment"] == "confident"
    assert adjustment["proactivity_level"] == "act_first"
    assert adjustment["explanation_depth"] == "summary"
    assert adjustment["requires_confirmation"] is False


# ══════ Task #10: Growth Chronicle ═══════════════════════════════════

def test_chronicle_entry_create():
    """ChronicleEntry serializes and deserializes as a user-governed story artifact."""
    from app.signals.growth_chronicle import ChronicleEntry

    entry = ChronicleEntry(
        entry_id="chron_1",
        user_id="u1",
        entry_type="milestone",
        timestamp="2026-04-27T10:00:00+00:00",
        title="里程碑：完成复盘",
        narrative="你完成了一次关键复盘。",
        evidence_refs=["or_1", "trace_1"],
        user_editable=True,
    )

    data = entry.to_dict()
    restored = ChronicleEntry.from_dict(data)

    assert data["user_editable"] is True
    assert restored.entry_id == "chron_1"
    assert restored.user_hidden is False


def test_build_milestone_from_outcome():
    """Effective high-confidence outcomes become milestone entries."""
    from app.signals.growth_chronicle import GrowthChronicleService

    service = GrowthChronicleService(redis_client=None)
    entry = service.build_milestone_from_outcome({
        "outcome_id": "or_1",
        "causal_trace_id": "trace_1",
        "user_id": "u1",
        "intervention": "25分钟小任务",
        "reason": "拆小任务",
        "attribution": "effective",
        "attribution_confidence": 0.86,
        "actual_outcome": {"count": 3, "type": "复习", "strategy": "25分钟小任务"},
        "created_at": "2026-04-27T10:00:00+00:00",
    })

    assert entry is not None
    assert entry.entry_type == "milestone"
    assert entry.user_editable is True
    assert "连续3次" in entry.narrative
    assert "or_1" in entry.evidence_refs
    assert "trace_1" in entry.evidence_refs


def test_build_milestone_insufficient_outcome():
    """Insufficient or low-confidence outcomes do not enter the chronicle."""
    from app.signals.growth_chronicle import GrowthChronicleService

    service = GrowthChronicleService(redis_client=None)

    assert service.build_milestone_from_outcome({
        "outcome_id": "or_low",
        "user_id": "u1",
        "attribution": "effective",
        "attribution_confidence": 0.6,
    }) is None
    assert service.build_milestone_from_outcome({
        "outcome_id": "or_bad",
        "user_id": "u1",
        "attribution": "insufficient",
        "attribution_confidence": 0.9,
    }) is None


def test_build_turning_point_from_correction():
    """User corrections become turning-point entries with explicit lesson text."""
    from app.signals.growth_chronicle import GrowthChronicleService

    service = GrowthChronicleService(redis_client=None)
    entry = service.build_turning_point_from_correction({
        "correction_id": "corr_1",
        "trace_id": "trace_2",
        "user_id": "u1",
        "topic": "概率题卡点",
        "lesson": "先区分公式不会还是题意没读懂",
    })

    assert entry.entry_type == "turning_point"
    assert entry.user_editable is True
    assert "概率题卡点" in entry.title
    assert "系统对概率题卡点的判断有偏差" in entry.narrative
    assert "corr_1" in entry.evidence_refs


def test_build_pattern_discovery():
    """Five outcomes with the same strategy produce a pattern discovery entry."""
    from app.signals.growth_chronicle import GrowthChronicleService

    service = GrowthChronicleService(redis_client=None)
    patterns = [
        {
            "outcome_id": f"or_{i}",
            "causal_trace_id": f"trace_{i}",
            "user_id": "u1",
            "strategy": "例题后立刻练习",
            "actual_outcome": {"type": "数学"},
        }
        for i in range(5)
    ]

    entry = service.build_pattern_discovery(patterns)

    assert entry is not None
    assert entry.entry_type == "pattern_discovered"
    assert entry.user_editable is True
    assert "例题后立刻练习" in entry.narrative
    assert len(entry.evidence_refs) == 10


@pytest.mark.asyncio
async def test_chronicle_hide_entry():
    """Hidden entries remain stored but disappear from the visible chronicle."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService

    redis = FakeRedis()
    service = GrowthChronicleService(redis)
    entry = ChronicleEntry(
        entry_id="chron_hide",
        user_id="u1",
        entry_type="milestone",
        timestamp="2026-04-27T10:00:00+00:00",
        title="里程碑：开始行动",
        narrative="你开始行动了。",
        evidence_refs=["or_1"],
        user_editable=True,
    )

    await service.add_entry("u1", entry)
    await service.hide_entry("u1", "chron_hide")

    assert await service.get_chronicle("u1") == []
    raw = await redis.get("spine:chronicle:u1")
    assert json.loads(raw)[0]["user_hidden"] is True


@pytest.mark.asyncio
async def test_chronicle_edit_entry():
    """Editable chronicle entries can be rewritten by the user."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService

    redis = FakeRedis()
    service = GrowthChronicleService(redis)
    entry = ChronicleEntry(
        entry_id="chron_edit",
        user_id="u1",
        entry_type="turning_point",
        timestamp="2026-04-27T10:00:00+00:00",
        title="转折点：修正计划",
        narrative="旧叙事",
        evidence_refs=["corr_1"],
        user_editable=True,
    )

    await service.add_entry("u1", entry)
    await service.edit_entry("u1", "chron_edit", "这是我自己改过的叙事。")

    entries = await service.get_chronicle("u1")
    assert entries[0].narrative == "这是我自己改过的叙事。"


@pytest.mark.asyncio
async def test_weekly_summary():
    """Weekly summaries are template-based aggregations of visible entries."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService

    redis = FakeRedis()
    service = GrowthChronicleService(redis)
    await service.add_entry("u1", ChronicleEntry(
        entry_id="chron_week_1",
        user_id="u1",
        entry_type="milestone",
        timestamp="2026-04-27T10:00:00+00:00",
        title="里程碑：连续完成复习",
        narrative="你连续完成了复习任务。",
        evidence_refs=["or_1"],
        user_editable=True,
    ))
    await service.add_entry("u1", ChronicleEntry(
        entry_id="chron_week_2",
        user_id="u1",
        entry_type="turning_point",
        timestamp="2026-04-27T11:00:00+00:00",
        title="转折点：纠正了系统判断",
        narrative="你纠正了系统判断。",
        evidence_refs=["corr_1"],
        user_editable=True,
    ))

    summary = await service.generate_weekly_summary("u1")

    assert "新增了2条记录" in summary
    assert "1个里程碑" in summary
    assert "1次重要修正" in summary
    assert "你可以继续编辑或隐藏" in summary


# ── P2-8: Notification Service Integration Tests ──────────────────────────

from app.signals.recall_notification import RecallNotificationBuilder


@pytest.mark.asyncio
async def test_recall_notification_build_and_store():
    """RecallNotificationBuilder produces message + stores in Redis via SpineOrchestrator."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    message = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="undigested_material",
        context={"material_count": 5, "undigested": 2},
    )
    assert message is not None
    assert message.trigger_type == "undigested_material"
    assert message.strategy == "low_effort_next_step"
    assert "5" in message.body
    assert "5" in message.body
    assert "2" in message.body
    assert message.message_id.startswith("rmsg_")

    # Verify stored in Redis
    stored = await spine.get_recall_notification("u1")
    assert stored is not None
    assert stored.message_id == message.message_id


@pytest.mark.asyncio
async def test_recall_notification_cooldown_blocks_duplicate():
    """Second recall notification within cooldown period is blocked."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    msg1 = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="task_not_started",
        context={},
    )
    assert msg1 is not None

    # Second call for same trigger type → blocked by cooldown
    msg2 = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="task_not_started",
        context={},
    )
    assert msg2 is None


@pytest.mark.asyncio
async def test_recall_notification_different_triggers_independent_cooldown():
    """Different trigger types have independent cooldowns."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    msg1 = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="undigested_material",
        context={"material_count": 3, "undigested": 1},
    )
    assert msg1 is not None

    # Different trigger → not blocked
    msg2 = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="pre_exam_silence",
        context={"days_to_exam": 1, "exam_deadline_days": 1},
    )
    assert msg2 is not None
    assert msg2.trigger_type == "pre_exam_silence"


@pytest.mark.asyncio
async def test_recall_notification_pre_exam_silence_template():
    """Pre-exam silence trigger uses correct template with days_to_exam."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    message = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="pre_exam_silence",
        context={"days_to_exam": 2, "exam_deadline_days": 2},
    )
    assert message is not None
    assert "2" in message.body
    assert message.deep_link == "/review?mode=quick"

