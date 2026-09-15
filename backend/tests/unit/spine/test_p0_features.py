"""Spine tests — test_p0_features.py."""

from __future__ import annotations

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

# ── P0-1: FirstMinuteSnapshot / ExamRescueDetector Tests ─────────────

from app.signals.exam_rescue_detector import ExamRescueDetector, FirstMinuteSnapshot


def test_exam_rescue_detects_7_day_urgent():
    """E4: '我 7 天后计网考试，零基础，想先别挂' → exam_rescue."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")

    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.path_mode == "minimum_pass"
    assert snapshot.deadline_days == 7
    assert snapshot.baseline == "near_zero"
    assert snapshot.subject == "computer_networks"
    assert snapshot.confidence >= 0.6
    assert "抢救" in snapshot.first_user_visible_hypothesis


def test_exam_rescue_detects_english_exam():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我后天英语四六级考试，基本不会")

    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.subject == "english_cet"
    assert snapshot.baseline == "near_zero"


def test_exam_rescue_high_score_target():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 14 天后高数考试，零基础，想冲高分")

    assert snapshot is not None
    assert snapshot.path_mode == "high_score"


def test_exam_rescue_no_signal_for_normal_chat():
    """Normal chat should not trigger exam rescue."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("你好，我想了解一下这个产品")

    assert snapshot is None


def test_exam_rescue_no_signal_for_empty():
    detector = ExamRescueDetector()
    assert detector.analyze_first_message("") is None


def test_exam_rescue_to_actionable_signal():
    """Snapshot → ActionableSignal conversion."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")

    signal = detector.to_actionable_signal(snapshot, user_id="u1", message_id="msg_001")
    assert signal is not None
    assert signal.state_key == "goal_mode"
    assert signal.claim == "exam_rescue_detected"
    assert signal.confidence >= 0.5
    assert signal.priority == "high"
    assert snapshot.signal_id == signal.signal_id


def test_exam_rescue_no_signal_for_build_mode():
    """exam_build mode should not generate ActionableSignal."""
    detector = ExamRescueDetector()
    snapshot = FirstMinuteSnapshot(
        detected_mode="exam_build",
        path_mode="solid_pass",
        deadline_days=30,
        baseline="unknown",
        subject=None,
        next_best_action="standard_onboarding",
        first_user_visible_hypothesis="test",
        confidence=0.5,
    )
    signal = detector.to_actionable_signal(snapshot, user_id="u1")
    assert signal is None


@pytest.mark.asyncio
async def test_exam_rescue_policy_rule():
    """PolicyEngine has exam_rescue rule."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["msg_001"],
        source_system="first_minute",
        state_key="goal_mode",
        claim="exam_rescue_detected",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=168,
        evidence_summary="新用户首次消息检测到 7 天计网考试抢救",
        possible_effects=["exam_rescue_mode"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "exam_rescue_sprint"
    assert directive.hard_constraints["sprint_policy"] == "seven_day_survival"
    assert directive.hard_constraints["defer_low_roi_topics"] is True


def test_exam_rescue_deadline_extraction():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我还有3天就考线代了什么都不会")
    assert snapshot is not None
    assert snapshot.deadline_days == 3
    assert snapshot.subject == "linear_algebra"


def test_exam_rescue_relative_date_houtian():
    """Chinese relative date '后天' should give deadline_days=2."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我后天考高数，什么都不会")
    assert snapshot is not None
    assert snapshot.deadline_days == 2
    assert snapshot.confidence >= 0.5


def test_exam_rescue_relative_date_xiazhou():
    """Chinese relative date '下周' should give deadline_days=7."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我下周考数据结构，零基础")
    assert snapshot is not None
    assert snapshot.deadline_days == 7


def test_exam_rescue_no_false_positive_no_exam():
    """弱基础没有考试意图不触发 exam_rescue (C2 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我零基础，想学一下计网")
    assert snapshot is None


def test_exam_rescue_english_subject():
    """English subject names should be detected (C3 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("I have a calculus exam in 5 days, I know nothing")
    assert snapshot is not None
    assert snapshot.subject == "calculus"
    assert snapshot.deadline_days == 5


@pytest.mark.asyncio
async def test_first_minute_to_policy_pipeline():
    """E2E: Detector → Signal → PolicyEngine must produce result (W2 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")
    signal = detector.to_actionable_signal(snapshot, user_id="u1")
    assert signal is not None
    assert signal.confidence >= 0.5, f"Confidence {signal.confidence} below policy threshold 0.5"

    engine = PolicyEngine()
    result = await engine.evaluate(signal)
    assert result is not None, "Signal was rejected by PolicyEngine (below threshold?)"
    decision, directive = result
    assert decision.primary_strategy == "exam_rescue_sprint"
    assert "seven_day_survival" in str(directive.hard_constraints)


# ── P0-2: TimeContext + StaleStateGuard Tests ─────────────────────────

from app.signals.stale_state_guard import StaleStateGuard, TimeContext, TimeDeltaPacket


def test_stale_guard_triggers_after_2_hours():
    """E5: 用户离开 2 小时 → TimeDeltaPacket."""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        last_user_interaction_at="2026-04-26T20:00:00+08:00",
        elapsed_since_last_interaction_min=120,
        active_task_id="task_tcp_001",
        active_task_status="no_completion",
    )
    packet = guard.check(ctx, user_id="u1")

    assert packet is not None
    assert packet.elapsed_since_last_seen_min == 120
    assert packet.pending_task_status == "expected_finished_but_no_feedback"
    assert len(packet.resume_options) == 4
    assert packet.message_template != ""


def test_stale_guard_no_trigger_under_threshold():
    """用户只离开 30 分钟，不触发。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T20:30:00+08:00",
        elapsed_since_last_interaction_min=30,
    )
    packet = guard.check(ctx)
    assert packet is None


def test_stale_guard_no_active_task():
    """离开时间长但没有活跃任务。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=120,
    )
    packet = guard.check(ctx)

    assert packet is not None
    assert packet.pending_task_status == "no_active_task"
    assert packet.resume_options[0]["value"] == "continue"


def test_stale_guard_resume_options_format():
    """恢复选项必须包含 4 个标准选项。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=130,
        active_task_id="task_001",
        active_task_status="started",
    )
    packet = guard.check(ctx)

    assert packet is not None
    labels = [opt["label"] for opt in packet.resume_options]
    assert "做完了，补记录" in labels
    assert "做了一半，卡住了" in labels
    assert "没开始" in labels
    assert "换个小任务" in labels


def test_stale_guard_message_contains_time():
    """返回消息必须包含时间信息。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=130,
        active_task_id="task_001",
        active_task_status="no_completion",
    )
    packet = guard.check(ctx)

    assert packet is not None
    assert "2 小时" in packet.message_template
    assert "任务" in packet.message_template


def test_stale_guard_time_context_serialization():
    """TimeContext to_dict round-trip."""
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=120,
        active_task_id="task_001",
        deadline_phase="high_pressure",
    )
    d = ctx.to_dict()
    assert d["deadline_phase"] == "high_pressure"
    assert d["active_task_id"] == "task_001"


# ── P0-3: ActionableStatePacket v1 Tests ─────────────────────────

from app.signals.state_packet_builder import ActionableStatePacketBuilder


def test_state_packet_builds_from_signals():
    """从活跃信号构建 ActionableStatePacket。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="task_service",
            state_key="task_granularity_fit", claim="recent_task_too_large",
            confidence=0.72, scope="current_sprint", ttl_hours=72,
            evidence_summary="连续 2 次超时", possible_effects=["cap_duration"],
            priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.user_id == "u1"
    assert len(packet.top_states) == 1
    assert packet.top_states[0].state_key == "task_granularity_fit"
    assert packet.top_states[0].confidence == 0.72
    assert "task_granularity_fit:recent_task_too_large" in packet.risk_flags


def test_state_packet_with_directive():
    """有活跃 directive 时 next_best_action 应该引用它。"""
    builder = ActionableStatePacketBuilder()
    directive = ExecutionDirective(
        directive_id="ed_001", policy_decision_id="pd_001",
        target_module="task_generator", scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    packet = builder.build(user_id="u1", active_directive=directive)

    assert packet.next_best_action is not None
    assert packet.next_best_action["type"] == "apply_directive"
    assert packet.next_best_action["directive_id"] == "ed_001"
    assert "task_duration_capped:25min" in packet.risk_flags


def test_state_packet_deduplicates_state_keys():
    """多个同 state_key 的信号只保留一个。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="task_service",
            state_key="task_granularity_fit", claim="too_large",
            confidence=0.6, scope="sprint", ttl_hours=72,
            evidence_summary="test", possible_effects=[], priority="high",
        ),
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e2"], source_system="task_service",
            state_key="task_granularity_fit", claim="too_large_v2",
            confidence=0.8, scope="sprint", ttl_hours=72,
            evidence_summary="test2", possible_effects=[], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert len(packet.top_states) == 1


def test_state_packet_bottleneck_from_mistake():
    """知识迁移失败信号应该产生瓶颈。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="error_book",
            state_key="knowledge_transfer", claim="transfer_failure",
            confidence=0.8, scope="current_sprint", ttl_hours=72,
            evidence_summary="知识节点 cn.tcp.congestion_control 连续 3 次出错",
            possible_effects=["avoid_new_chapter"], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.current_bottleneck is not None
    assert packet.current_bottleneck["type"] == "transfer_failure"
    assert packet.current_bottleneck["node_id"] == "cn.tcp.congestion_control"


def test_state_packet_goal_frame_from_exam_rescue():
    """exam_rescue 信号应该填充 goal_frame。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["m1"], source_system="first_minute",
            state_key="goal_mode", claim="exam_rescue_detected",
            confidence=0.85, scope="current_sprint", ttl_hours=168,
            evidence_summary="7 天计网抢救", possible_effects=["exam_rescue_mode"],
            priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.goal_frame.get("mode") == "exam_rescue"
    assert packet.goal_frame.get("target") == "minimum_pass"


def test_state_packet_empty_inputs():
    """无信号无 directive 应该产生空包。"""
    builder = ActionableStatePacketBuilder()
    packet = builder.build(user_id="u1")

    assert packet.user_id == "u1"
    assert len(packet.top_states) == 0
    assert len(packet.risk_flags) == 0
    assert packet.current_bottleneck is None
    assert packet.next_best_action is None


def test_state_packet_serialization():
    """ActionableStatePacket to_dict 可序列化。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_001", source_event_ids=[], source_system="test",
            state_key="test_key", claim="test_claim",
            confidence=0.5, scope="test", ttl_hours=1,
            evidence_summary="test", possible_effects=[], priority="low",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    d = packet.to_dict()

    assert d["user_id"] == "u1"
    assert len(d["top_states"]) == 1
    assert d["top_states"][0]["state_key"] == "test_key"


# ── P0-3 v1.1: ActionableStatePacket 3 new fields ──────────────────

def test_state_packet_time_context_from_signals():
    """time_context populated from goal_mode and task_granularity_fit signals."""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_gm", source_event_ids=[], source_system="goal_service",
            state_key="goal_mode", claim="exam_rescue_detected",
            confidence=0.9, scope="current_sprint", ttl_hours=24,
            evidence_summary="考试倒计时 < 7 天", possible_effects=[], priority="high",
        ),
        ActionableSignal(
            signal_id="sig_tg", source_event_ids=[], source_system="task_service",
            state_key="task_granularity_fit", claim="recent_task_too_large",
            confidence=0.8, scope="current_sprint", ttl_hours=24,
            evidence_summary="连续 2 次任务超时", possible_effects=[], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert packet.time_context["deadline_phase"] == "urgent"
    assert packet.time_context["task_stale_status"] == "overrun"


def test_state_packet_time_context_passthrough():
    """time_context parameter passed through to packet."""
    builder = ActionableStatePacketBuilder()
    tc = {
        "last_interaction_at": "2026-04-27T10:00:00Z",
        "elapsed_since_last_interaction_min": 120,
        "active_task_expected_end_at": "2026-04-27T09:00:00Z",
        "quiet_hours_active": False,
    }
    packet = builder.build(user_id="u1", time_context=tc)
    assert packet.time_context["last_interaction_at"] == "2026-04-27T10:00:00Z"
    assert packet.time_context["elapsed_since_last_interaction_min"] == 120


def test_state_packet_execution_pattern():
    """execution_pattern populated from signal types."""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_tg", source_event_ids=[], source_system="task_service",
            state_key="task_granularity_fit", claim="recent_task_too_large",
            confidence=0.8, scope="current_sprint", ttl_hours=24,
            evidence_summary="超时", possible_effects=[], priority="high",
        ),
        ActionableSignal(
            signal_id="sig_kt", source_event_ids=[], source_system="knowledge_service",
            state_key="knowledge_transfer", claim="transfer_failure",
            confidence=0.7, scope="current_sprint", ttl_hours=24,
            evidence_summary="迁移失败", possible_effects=[], priority="medium",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert packet.execution_pattern["task_size_tendency"] == "oversized"
    assert packet.execution_pattern["transfer_tendency"] == "failure"
    assert packet.execution_pattern["signal_density"] == 2


def test_state_packet_execution_pattern_momentum():
    """execution_pattern captures momentum claim."""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_gm", source_event_ids=[], source_system="achievement",
            state_key="growth_momentum", claim="momentum_high",
            confidence=0.8, scope="current_sprint", ttl_hours=24,
            evidence_summary="7连胜", possible_effects=[], priority="low",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert packet.execution_pattern["momentum"] == "momentum_high"


def test_state_packet_context_recommendation_with_directive():
    """context_recommendation populated from directive constraints."""
    builder = ActionableStatePacketBuilder()
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"avoid_new_chapter": True, "max_task_duration_min": 25},
        user_visible_reason="任务超时",
    )
    packet = builder.build(user_id="u1", active_directive=directive)
    assert packet.context_recommendation["retrieval_hint"] == "targeted"


def test_state_packet_context_recommendation_material():
    """context_recommendation detects material underutilization."""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_mu", source_event_ids=[], source_system="retrieval",
            state_key="material_utilization", claim="material_underutilized",
            confidence=0.7, scope="current_sprint", ttl_hours=24,
            evidence_summary="课件未被使用", possible_effects=[], priority="medium",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert packet.context_recommendation["material_mode"] == "underutilized"


def test_state_packet_empty_fields_default_to_empty_dict():
    """Empty packet has empty dict defaults for all 3 new fields."""
    builder = ActionableStatePacketBuilder()
    packet = builder.build(user_id="u1")
    assert packet.time_context == {}
    assert packet.execution_pattern == {}
    assert packet.context_recommendation == {}


def test_state_packet_to_dict_includes_new_fields():
    """to_dict() includes all 3 new fields."""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_gm", source_event_ids=[], source_system="goal_service",
            state_key="goal_mode", claim="exam_rescue_detected",
            confidence=0.9, scope="current_sprint", ttl_hours=24,
            evidence_summary="考试", possible_effects=[], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    d = packet.to_dict()
    assert "time_context" in d
    assert "execution_pattern" in d
    assert "context_recommendation" in d
    assert d["time_context"]["deadline_phase"] == "urgent"


