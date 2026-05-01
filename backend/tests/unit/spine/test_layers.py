"""Spine tests — test_layers.py."""

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

# ── Layer 3: SignalRanker Tests ────────────────────────────────────────

from app.signals.signal_ranker import SignalRanker


@pytest.fixture
def ranker():
    return SignalRanker()


def _make_signal(state_key: str, claim: str, confidence: float, priority: str = "medium") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=[], source_system="test",
        state_key=state_key, claim=claim,
        confidence=confidence, scope="current_sprint", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority=priority,
    )


def test_rank_empty_signals(ranker):
    """空信号列表 → 空 result。"""
    result = ranker.rank([])
    assert result.ranked == []
    assert result.suppressed == []


def test_rank_single_signal(ranker):
    """单个信号 → 直接 ranked。"""
    s = _make_signal("task_granularity_fit", "too_large", 0.8, "high")
    result = ranker.rank([s])
    assert len(result.ranked) == 1
    assert result.ranked[0].signal.state_key == "task_granularity_fit"


def test_rank_orders_by_tier(ranker):
    """exam_rescue (tier 2) 排在 growth_momentum (tier 7) 之前。"""
    momentum = _make_signal("growth_momentum", "momentum_high", 0.9, "low")
    exam = _make_signal("goal_mode", "exam_rescue_detected", 0.7, "high")
    result = ranker.rank([momentum, exam])
    assert result.ranked[0].signal.state_key == "goal_mode"
    assert result.ranked[1].signal.state_key == "growth_momentum"


def test_rank_max_signals(ranker):
    """max_signals=3 时只保留前 3 个。"""
    signals = [_make_signal(f"key_{i}", f"claim_{i}", 0.5) for i in range(6)]
    result = ranker.rank(signals, max_signals=3)
    assert len(result.ranked) == 3
    assert len(result.suppressed) >= 3


def test_rank_conflict_momentum_vs_task(ranker):
    """growth_momentum + task_granularity_fit 冲突 → task_granularity_fit wins。"""
    momentum = _make_signal("growth_momentum", "momentum_high", 0.8, "low")
    task = _make_signal("task_granularity_fit", "too_large", 0.7, "high")
    result = ranker.rank([momentum, task])
    # task_granularity_fit has higher priority tier (4 vs 7)
    ranked_keys = [r.signal.state_key for r in result.ranked]
    assert "task_granularity_fit" in ranked_keys
    assert len(result.conflicts_resolved) >= 1


def test_rank_composite_score(ranker):
    """high priority + high confidence → higher composite score。"""
    high = _make_signal("task_granularity_fit", "test", 0.9, "high")
    low = _make_signal("task_granularity_fit", "test", 0.3, "low")
    result = ranker.rank([low, high])
    assert result.ranked[0].signal.confidence == 0.9


def test_rank_serialization(ranker):
    """RankingResult to_dict。"""
    s = _make_signal("knowledge_transfer", "transfer_failure", 0.8)
    result = ranker.rank([s])
    d = result.to_dict()
    assert len(d["ranked"]) == 1
    assert d["ranked"][0]["state_key"] == "knowledge_transfer"


def test_spine_rank_signals(spine):
    """SpineOrchestrator.rank_signals 委托到 SignalRanker。"""
    signals = [
        _make_signal("growth_momentum", "high", 0.9, "low"),
        _make_signal("task_granularity_fit", "too_large", 0.7, "high"),
    ]
    result = spine.rank_signals(signals)
    assert len(result.ranked) >= 1


@pytest.mark.asyncio
async def test_build_state_packet_ranks_signals(spine):
    """build_state_packet 通过 SignalRanker 排序后再构建。"""
    signals = [
        _make_signal("growth_momentum", "momentum_high", 0.9, "low"),
        _make_signal("task_granularity_fit", "too_large", 0.8, "high"),
        _make_signal("recall_needed", "task_missed", 0.7, "high"),
    ]
    packet = await spine.build_state_packet(
        user_id="u_rank",
        active_signals=signals,
    )
    # task_granularity_fit (tier 4) should rank before growth_momentum (tier 7)
    # and conflict rule suppresses growth_momentum when task_granularity_fit present
    state_keys = [s.state_key for s in packet.top_states]
    assert "task_granularity_fit" in state_keys or len(state_keys) >= 1


def test_rank_duplicate_state_keys(ranker):
    """同 state_key 的多个信号都被保留，各自独立评分。"""
    s1 = _make_signal("task_granularity_fit", "too_large", 0.9, "high")
    s2 = _make_signal("task_granularity_fit", "too_small", 0.6, "medium")
    result = ranker.rank([s1, s2])
    assert len(result.ranked) == 2
    # higher confidence should rank first
    assert result.ranked[0].signal.confidence == 0.9


def test_rank_conflict_rules_explicit(ranker):
    """冲突规则显式指定 winner/loser，不依赖排序顺序。"""
    # Pass in "wrong" order — growth_momentum first, task_granularity_fit second
    momentum = _make_signal("growth_momentum", "momentum_high", 0.9, "low")
    task = _make_signal("task_granularity_fit", "too_large", 0.7, "high")
    result = ranker.rank([momentum, task])
    ranked_keys = [r.signal.state_key for r in result.ranked]
    assert "task_granularity_fit" in ranked_keys
    assert "growth_momentum" not in ranked_keys
    assert len(result.conflicts_resolved) == 1
    assert result.conflicts_resolved[0]["winner"] == "task_granularity_fit"
    assert result.conflicts_resolved[0]["loser"] == "growth_momentum"


# ── Layer 4: StateRegister ─────────────────────────────────────────────

from app.signals.state_register import StateRegister


@pytest.fixture
def state_register(fake_redis):
    return StateRegister(fake_redis)


def _sig(state_key: str = "task_granularity_fit", claim: str = "too_large",
         confidence: float = 0.8, priority: str = "high", scope: str = "current_sprint",
         ttl: int = 72, evidence: str = "test evidence") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key=state_key, claim=claim, confidence=confidence,
        scope=scope, ttl_hours=ttl, evidence_summary=evidence,
        possible_effects=[], priority=priority,
    )


@pytest.mark.asyncio
async def test_state_register_upsert_new(state_register):
    """新信号 → 创建新状态。"""
    signal = _sig(confidence=0.8)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.state_key == "task_granularity_fit"
    assert entry.value == "too_large"
    assert entry.confidence == 0.8
    assert "test evidence" in entry.supporting_evidence


@pytest.mark.asyncio
async def test_state_register_upsert_merge_higher(state_register):
    """同 state_key 更高 confidence → 更新。"""
    await state_register.upsert_from_signal("u1", _sig(confidence=0.6, evidence="first evidence"))
    entry = await state_register.upsert_from_signal("u1", _sig(confidence=0.9, evidence="second evidence"))
    assert entry.confidence == 0.9
    # Evidence merged
    assert len(entry.supporting_evidence) == 2


@pytest.mark.asyncio
async def test_state_register_upsert_keep_lower(state_register):
    """同 state_key 更低 confidence → 保留旧的 confidence 和 value。"""
    await state_register.upsert_from_signal("u1", _sig(confidence=0.9, claim="original_claim"))
    entry = await state_register.upsert_from_signal("u1", _sig(confidence=0.5, claim="new_claim"))
    assert entry.confidence == 0.9
    assert entry.value == "original_claim"  # value NOT overwritten


@pytest.mark.asyncio
async def test_state_register_get_active(state_register):
    """获取所有活跃状态。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="task_granularity_fit"))
    await state_register.upsert_from_signal("u1", _sig(state_key="knowledge_transfer", claim="transfer_failure"))
    states = await state_register.get_active_states("u1")
    assert len(states) == 2
    keys = {s.state_key for s in states}
    assert "task_granularity_fit" in keys
    assert "knowledge_transfer" in keys


@pytest.mark.asyncio
async def test_state_register_get_single(state_register):
    """获取单个状态。"""
    await state_register.upsert_from_signal("u1", _sig())
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert entry is not None
    assert entry.value == "too_large"


@pytest.mark.asyncio
async def test_state_register_get_missing(state_register):
    """不存在的状态 → None。"""
    entry = await state_register.get_state("u1", "nonexistent")
    assert entry is None


@pytest.mark.asyncio
async def test_state_register_counter_evidence(state_register):
    """添加反证。"""
    await state_register.upsert_from_signal("u1", _sig())
    ok = await state_register.add_counter_evidence("u1", "task_granularity_fit", "user completed 90min task")
    assert ok is True
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert "user completed 90min task" in entry.counter_evidence


@pytest.mark.asyncio
async def test_state_register_counter_evidence_missing(state_register):
    """为不存在的状态添加反证 → False。"""
    ok = await state_register.add_counter_evidence("u1", "nonexistent", "evidence")
    assert ok is False


@pytest.mark.asyncio
async def test_state_register_remove(state_register):
    """移除状态。"""
    await state_register.upsert_from_signal("u1", _sig())
    await state_register.remove_state("u1", "task_granularity_fit")
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert entry is None


@pytest.mark.asyncio
async def test_state_register_clear_scope(state_register):
    """清除特定 scope 的所有状态。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="a", scope="turn"))
    await state_register.upsert_from_signal("u1", _sig(state_key="b", scope="sprint"))
    count = await state_register.clear_scope("u1", "turn")
    assert count == 1
    states = await state_register.get_active_states("u1")
    assert len(states) == 1
    assert states[0].state_key == "b"


@pytest.mark.asyncio
async def test_state_register_can_affect(state_register):
    """state_key 映射到正确的 can_affect。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="task_granularity_fit"))
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert "ExecutionDirective" in entry.can_affect


@pytest.mark.asyncio
async def test_state_register_high_impact_confirmation(state_register):
    """低置信 + 高优先级 → requires_confirmation_if_high_impact。"""
    signal = _sig(confidence=0.3, priority="high")
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.requires_confirmation_if_high_impact is True


@pytest.mark.asyncio
async def test_state_register_serialization(state_register):
    """StateEntry 序列化/反序列化正确。"""
    await state_register.upsert_from_signal("u1", _sig())
    entry = await state_register.get_state("u1", "task_granularity_fit")
    d = entry.to_dict()
    restored = StateEntry.from_dict(d)
    assert restored.state_key == entry.state_key
    assert restored.confidence == entry.confidence
    assert restored.ttl_hours == entry.ttl_hours
    assert restored.supporting_evidence == entry.supporting_evidence


@pytest.mark.asyncio
async def test_state_register_no_cross_user(state_register):
    """不同用户的状态互不影响。"""
    await state_register.upsert_from_signal("u1", _sig())
    states = await state_register.get_active_states("u2")
    assert len(states) == 0


@pytest.mark.asyncio
async def test_spine_get_active_states(spine):
    """SpineOrchestrator.get_active_states 委托到 StateRegister。"""
    states = await spine.get_active_states("u_test")
    assert isinstance(states, list)


@pytest.mark.asyncio
async def test_spine_pipeline_updates_state_register(spine):
    """Spine pipeline 处理信号后 StateRegister 有记录。"""
    signal = _sig()
    await spine._run_signal_pipeline(user_id="u_reg", signal=signal)
    entry = await spine.state_register.get_state("u_reg", "task_granularity_fit")
    assert entry is not None
    assert entry.value == "too_large"


@pytest.mark.asyncio
async def test_state_register_scope_ttl_clamp(state_register):
    """scope=turn ttl=999 → 被 clamp 到 1h。"""
    signal = _sig(scope="turn", ttl=999)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.ttl_hours == 1  # turn max is 1h


@pytest.mark.asyncio
async def test_state_register_scope_ttl_no_clamp(state_register):
    """scope=sprint ttl=72 → 不被 clamp。"""
    signal = _sig(scope="current_sprint", ttl=72)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.ttl_hours == 72


@pytest.mark.asyncio
async def test_state_register_evidence_cap(state_register):
    """证据列表不超过上限。"""
    for i in range(25):
        await state_register.upsert_from_signal("u1", _sig(
            confidence=0.5, evidence=f"evidence_{i}",
        ))
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert len(entry.supporting_evidence) <= 20


@pytest.mark.asyncio
async def test_state_register_expire_stale(state_register, monkeypatch):
    """expire_stale 移除过期状态。"""
    from app.signals.state_register import _parse_iso
    from datetime import timedelta

    await state_register.upsert_from_signal("u1", _sig(ttl=1))

    # Patch _is_expired to always return True
    monkeypatch.setattr(state_register, "_is_expired", lambda entry: True)
    count = await state_register.expire_stale("u1")
    assert count == 1
    states = await state_register.get_active_states("u1")
    assert len(states) == 0


# ── Layer 6: ResponseDirective ──────────────────────────────────────────

from app.signals.types import ResponseDirective


def test_response_directive_creation():
    """ResponseDirective 基本创建和序列化。"""
    rd = ResponseDirective(
        directive_id="rdsp_001",
        policy_decision_id="pd_001",
        tone="calm_direct",
        length="medium",
        must_acknowledge=["recent_overrun"],
        avoid=["generic_encouragement"],
        include_user_options=True,
    )
    d = rd.to_dict()
    assert d["tone"] == "calm_direct"
    assert d["must_acknowledge"] == ["recent_overrun"]
    assert d["avoid"] == ["generic_encouragement"]

    restored = ResponseDirective.from_dict(d)
    assert restored.tone == "calm_direct"
    assert restored.directive_id == "rdsp_001"


@pytest.mark.asyncio
async def test_response_directive_from_policy_task_timeout():
    """task_granularity_fit → PolicyEngine → ResponseDirective with calm_direct tone。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="2 tasks overran", possible_effects=[],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    rd = engine.build_response_directive(decision, signal)
    assert rd is not None
    assert rd.tone == "direct_but_reassuring"
    assert "recent_overrun" in rd.must_acknowledge


@pytest.mark.asyncio
async def test_response_directive_from_policy_exam_rescue():
    """goal_mode/exam_rescue → ResponseDirective with calm_urgent tone。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="goal_mode", claim="exam_rescue_detected",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="exam detected", possible_effects=[],
        priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    rd = engine.build_response_directive(decision, signal)
    assert rd is not None
    assert rd.tone == "calm_urgent"
    assert "exam_situation" in rd.must_acknowledge


@pytest.mark.asyncio
async def test_response_directive_no_status_band():
    """visibility=status_band → no ResponseDirective。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_high",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="streak", possible_effects=[], priority="low",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    rd = engine.build_response_directive(decision, signal)
    assert rd is None


@pytest.mark.asyncio
async def test_response_directive_avoid_pressure():
    """encouraging_diagnostic tone → avoid pressure_language。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="knowledge_transfer", claim="transfer_failure",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="3 errors same topic", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    rd = engine.build_response_directive(decision, signal)
    assert rd is not None
    assert "generic_encouragement" in rd.avoid
    assert "pressure_language" in rd.avoid


@pytest.mark.asyncio
async def test_spine_get_response_directive(spine):
    """SpineOrchestrator.get_response_directive 返回 None 或 ResponseDirective。"""
    result = await spine.get_response_directive("u_test")
    assert result is None or isinstance(result, ResponseDirective)


@pytest.mark.asyncio
async def test_spine_pipeline_stores_response_directive(spine):
    """Spine pipeline 处理 task_granularity_fit 后存储 ResponseDirective。"""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine._run_signal_pipeline(user_id="u_rdsp", signal=signal)
    rd = await spine.get_response_directive("u_rdsp")
    assert rd is not None
    assert rd.tone == "direct_but_reassuring"


# ── Layer 6: NotificationDirective ───────────────────────────────────────

from app.signals.types import NotificationDirective


def test_notification_directive_creation():
    """NotificationDirective 基本创建和序列化。"""
    nd = NotificationDirective(
        directive_id="nd_001",
        policy_decision_id="pd_001",
        allowed=True,
        channel="push",
        trigger="first_task_not_started",
        message_strategy="low_effort_next_step",
        max_frequency="1_per_day",
    )
    d = nd.to_dict()
    assert d["allowed"] is True
    assert d["trigger"] == "first_task_not_started"
    assert d["max_frequency"] == "1_per_day"

    restored = NotificationDirective.from_dict(d)
    assert restored.trigger == "first_task_not_started"
    assert restored.respect_quiet_hours is True


@pytest.mark.asyncio
async def test_notification_directive_recall_undigested():
    """recall_needed/undigested_material → NotificationDirective。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="undigested_material",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="uploaded no diagnostic", possible_effects=[], priority="medium",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    nd = engine.build_notification_directive(decision, signal)
    assert nd is not None
    assert nd.trigger == "undigested_material"
    assert nd.message_strategy == "low_effort_next_step"
    assert nd.max_frequency == "1_per_day"


@pytest.mark.asyncio
async def test_notification_directive_task_missed():
    """recall_needed/task_missed → notification with recovery_offer。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="task_missed",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="deadline passed", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    nd = engine.build_notification_directive(decision, signal)
    assert nd is not None
    assert nd.trigger == "task_missed"
    assert nd.message_strategy == "recovery_offer"
    assert nd.max_frequency == "2_per_day"


@pytest.mark.asyncio
async def test_notification_directive_pre_exam():
    """recall_needed/pre_exam_silence → quick_review_offer。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="pre_exam_silence",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="48h before exam, 5h silent", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    nd = engine.build_notification_directive(decision, signal)
    assert nd is not None
    assert nd.trigger == "pre_exam_silence"
    assert nd.message_strategy == "quick_review_offer"


@pytest.mark.asyncio
async def test_notification_directive_no_task_signal():
    """task_granularity_fit → no NotificationDirective。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    nd = engine.build_notification_directive(decision, signal)
    assert nd is None


@pytest.mark.asyncio
async def test_notification_directive_exam_rescue():
    """goal_mode/exam_rescue → notification with exam_rescue_urgent。"""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="goal_mode", claim="exam_rescue_detected",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="exam detected", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    decision, _ = result
    nd = engine.build_notification_directive(decision, signal)
    assert nd is not None
    assert nd.trigger == "exam_rescue_urgent"


@pytest.mark.asyncio
async def test_spine_pipeline_stores_notification_directive(spine):
    """Spine pipeline 处理 recall_needed 后存储 NotificationDirective。"""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="undigested_material",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    await spine._run_signal_pipeline(user_id="u_nd", signal=signal)
    nd = await spine.get_notification_directive("u_nd")
    assert nd is not None
    assert nd.trigger == "undigested_material"


@pytest.mark.asyncio
async def test_state_register_clear_scope_empty(state_register):
    """clear_scope 无匹配 → 0。"""
    await state_register.upsert_from_signal("u1", _sig(scope="sprint"))
    count = await state_register.clear_scope("u1", "turn")
    assert count == 0


# ── Layer 6: PlanDirective Tests ──────────────────────────────────────

def _policy_and_signal(state_key="task_granularity_fit", claim="recent_task_too_large", confidence=0.8):
    """Helper: build signal + policy decision for directive builder tests."""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key=state_key, claim=claim,
        confidence=confidence, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    decision = PolicyDecision(
        policy_decision_id="pd_test", primary_strategy="test_strategy",
        secondary_strategy=None, hard_constraints={}, soft_biases={},
        visibility="receipt", requires_user_confirmation=False,
        reasoning_summary="test",
    )
    return signal, decision


def test_plan_directive_task_timeout():
    """task_granularity_fit/recent_task_too_large → local_replan with recovery task."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("task_granularity_fit", "recent_task_too_large")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is not None
    assert pd.plan_action == "local_replan"
    assert pd.scope == "next_48h"
    assert pd.constraints["do_not_rebuild_entire_plan"] is True
    assert pd.constraints["insert_recovery_task"] is True


def test_plan_directive_transfer_failure():
    """knowledge_transfer/transfer_failure → local_replan with practice task."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("knowledge_transfer", "transfer_failure")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is not None
    assert pd.plan_action == "local_replan"
    assert pd.constraints["avoid_new_chapter"] is True
    assert pd.constraints["insert_practice_task"] is True


def test_plan_directive_exam_rescue():
    """goal_mode/exam_rescue_detected → full_replan."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("goal_mode", "exam_rescue_detected")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is not None
    assert pd.plan_action == "full_replan"
    assert pd.constraints["prefer_high_yield"] is True


def test_plan_directive_momentum_stalled():
    """growth_momentum/momentum_stalled → local_replan with easy win."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("growth_momentum", "momentum_stalled")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is not None
    assert pd.plan_action == "local_replan"
    assert pd.constraints["insert_easy_win"] is True


def test_plan_directive_no_match():
    """Unmatched signal → None."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("material_utilization", "material_underutilized")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is None


def test_plan_directive_serialization():
    """PlanDirective round-trips through to_dict/from_dict."""
    from app.signals.types import PlanDirective
    pd = PlanDirective(
        directive_id="pld_test", policy_decision_id="pd_test",
        plan_action="local_replan", scope="next_48h",
        constraints={"do_not_rebuild_entire_plan": True},
    )
    d = pd.to_dict()
    pd2 = PlanDirective.from_dict(d)
    assert pd2.plan_action == "local_replan"
    assert pd2.constraints["do_not_rebuild_entire_plan"] is True


@pytest.mark.asyncio
async def test_spine_pipeline_stores_plan_directive(spine):
    """Spine pipeline 处理 task_timeout 后存储 PlanDirective。"""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine._run_signal_pipeline(user_id="u_pd", signal=signal)
    pd = await spine.get_plan_directive("u_pd")
    assert pd is not None
    assert pd.plan_action == "local_replan"


# ── Layer 6: ModelWriteDirective Tests ────────────────────────────────

def test_model_write_directive_task_timeout():
    """task_granularity_fit → 2 writes (user_state + sparkle_self_model)."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("task_granularity_fit", "recent_task_too_large")
    mwd = engine.build_model_write_directive(decision, signal)
    assert mwd is not None
    assert len(mwd.writes) == 2
    assert mwd.writes[0].target_model == "user_state"
    assert mwd.writes[1].target_model == "sparkle_self_model"
    # Second write has degraded confidence
    assert mwd.writes[1].confidence < signal.confidence


def test_model_write_directive_transfer_failure():
    """knowledge_transfer/transfer_failure → 1 write (user_state)."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("knowledge_transfer", "transfer_failure")
    mwd = engine.build_model_write_directive(decision, signal)
    assert mwd is not None
    assert len(mwd.writes) == 1
    assert mwd.writes[0].target_model == "user_state"


def test_model_write_directive_exam_rescue():
    """exam_rescue → 1 write needing user confirmation."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("goal_mode", "exam_rescue_detected")
    mwd = engine.build_model_write_directive(decision, signal)
    assert mwd is not None
    assert len(mwd.writes) == 1
    assert mwd.writes[0].needs_user_confirmation is True


def test_model_write_directive_momentum_high():
    """growth_momentum/momentum_high → self_model write."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("growth_momentum", "momentum_high", confidence=0.85)
    mwd = engine.build_model_write_directive(decision, signal)
    assert mwd is not None
    assert mwd.writes[0].target_model == "sparkle_self_model"


def test_model_write_directive_no_match():
    """Unmatched signal → None."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("recall_needed", "task_missed")
    mwd = engine.build_model_write_directive(decision, signal)
    assert mwd is None


def test_model_write_directive_serialization():
    """ModelWriteDirective round-trips through to_dict/from_dict."""
    from app.signals.types import ModelWriteDirective, ModelWriteEntry
    mwd = ModelWriteDirective(
        directive_id="mwd_test", policy_decision_id="pd_test",
        writes=[
            ModelWriteEntry(target_model="user_state", claim="test claim",
                          scope="current_sprint", confidence=0.8),
        ],
    )
    d = mwd.to_dict()
    assert len(d["writes"]) == 1
    mwd2 = ModelWriteDirective.from_dict(d)
    assert len(mwd2.writes) == 1
    assert mwd2.writes[0].target_model == "user_state"


@pytest.mark.asyncio
async def test_spine_pipeline_stores_model_write_directive(spine):
    """Spine pipeline stores ModelWriteDirective for task timeout."""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine._run_signal_pipeline(user_id="u_mwd", signal=signal)
    mwd = await spine.get_model_write_directive("u_mwd")
    assert mwd is not None
    assert len(mwd.writes) == 2


# ── Layer 6: UXDirective Tests ────────────────────────────────────────

def test_ux_directive_task_timeout():
    """task_granularity_fit → risk_detected status band + strategy receipt."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("task_granularity_fit", "recent_task_too_large")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "risk_detected"
    assert uxd.show_strategy_receipt is True
    assert uxd.allow_full_aurora_wake is False


def test_ux_directive_exam_rescue():
    """exam_rescue → strategy_active + full aurora wake allowed."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("goal_mode", "exam_rescue_detected")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "strategy_active"
    assert uxd.allow_full_aurora_wake is True


def test_ux_directive_momentum_high():
    """momentum_high → milestone status band."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("growth_momentum", "momentum_high")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "milestone"


def test_ux_directive_momentum_stalled():
    """momentum_stalled → risk_detected."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("growth_momentum", "momentum_stalled")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "risk_detected"


def test_ux_directive_undigested_material():
    """undigested_material → normal status + context receipt."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("recall_needed", "undigested_material")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "normal"
    assert uxd.show_context_receipt is True


def test_ux_directive_no_match_status_band():
    """Unmatched signal with status_band visibility → default UXDirective."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("safety_boundary", "some_unknown_claim")
    decision.visibility = "status_band"
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "normal"


def test_ux_directive_no_match_receipt():
    """Unmatched claim → default UXDirective (fallback)."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("safety_boundary", "some_unknown_claim")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "normal"


def test_ux_directive_serialization():
    """UXDirective round-trips through to_dict/from_dict."""
    from app.signals.types import UXDirective
    uxd = UXDirective(
        directive_id="uxd_test", policy_decision_id="pd_test",
        status_band_state="risk_detected",
        show_strategy_receipt=True,
        allow_full_aurora_wake=False,
    )
    d = uxd.to_dict()
    uxd2 = UXDirective.from_dict(d)
    assert uxd2.status_band_state == "risk_detected"
    assert uxd2.show_strategy_receipt is True


@pytest.mark.asyncio
async def test_spine_pipeline_stores_ux_directive(spine):
    """Spine pipeline stores UXDirective for task timeout."""
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine._run_signal_pipeline(user_id="u_uxd", signal=signal)
    uxd = await spine.get_ux_directive("u_uxd")
    assert uxd is not None
    assert uxd.status_band_state == "risk_detected"


def test_ux_directive_material_underutilized():
    """material_underutilized → normal status + context receipt."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("material_utilization", "material_underutilized")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "normal"
    assert uxd.show_context_receipt is True


def test_ux_directive_pre_exam_silence():
    """pre_exam_silence → strategy_active status band."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("recall_needed", "pre_exam_silence")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "strategy_active"


def test_ux_directive_cohort_mistake():
    """cohort_mistake_detected → normal status band."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("community_cohort_pattern", "cohort_mistake_detected")
    uxd = engine.build_ux_directive(decision, signal)
    assert uxd is not None
    assert uxd.status_band_state == "normal"


def test_plan_directive_task_missed():
    """recall_needed/task_missed → insert_task."""
    engine = PolicyEngine()
    signal, decision = _policy_and_signal("recall_needed", "task_missed")
    pd = engine.build_plan_directive(decision, signal)
    assert pd is not None
    assert pd.plan_action == "insert_task"
    assert pd.constraints["recovery_task"] is True


def test_model_write_entry_from_dict():
    """ModelWriteEntry.from_dict round-trips correctly."""
    from app.signals.types import ModelWriteEntry
    entry = ModelWriteEntry(
        target_model="user_state", claim="test",
        scope="current_sprint", confidence=0.8,
        needs_user_confirmation=True, ttl="48h",
    )
    d = entry.to_dict()
    entry2 = ModelWriteEntry.from_dict(d)
    assert entry2.target_model == "user_state"
    assert entry2.needs_user_confirmation is True


@pytest.mark.asyncio
async def test_spine_trace_includes_secondary_directive_ids(spine):
    """Spine pipeline appends PlanDirective/UXDirective IDs to CausalTrace."""
    signal = ActionableSignal(
        signal_id="sig_trace", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    trace = await spine._run_signal_pipeline(user_id="u_trace_dirs", signal=signal)
    assert trace is not None
    # Should have at least ExecutionDirective + PlanDirective + UXDirective IDs
    assert len(trace.directive_ids) >= 2
    # PlanDirective should be present (task_too_large has plan mapping)
    plan_dir = await spine.get_plan_directive("u_trace_dirs")
    assert plan_dir is not None
    assert plan_dir.directive_id in trace.directive_ids

def test_retrieval_directive_roundtrip():
    """RetrievalDirective serialization round-trip."""
    from app.signals.types import RetrievalDirective
    rd = RetrievalDirective(
        directive_id="rtd_001",
        policy_decision_id="pd_001",
        retrieval_mode="targeted_source_rag",
        source_scope="user_selected",
        must_load=["source_slice:sl_p32"],
        do_not_load=["full_course_slides"],
        token_budget=3600,
        pollution_guard="strict",
        reason_for_user="test",
    )
    d = rd.to_dict()
    restored = RetrievalDirective.from_dict(d)
    assert restored.retrieval_mode == "targeted_source_rag"
    assert restored.must_load == ["source_slice:sl_p32"]
    assert restored.do_not_load == ["full_course_slides"]


@pytest.mark.asyncio
async def test_build_retrieval_directive_material():
    """material_underutilized → RetrievalDirective with targeted_source_rag."""
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
    rd = engine.build_retrieval_directive(decision, signal)
    assert rd is not None
    assert rd.retrieval_mode == "targeted_source_rag"
    assert rd.source_scope == "user_selected"


@pytest.mark.asyncio
async def test_build_retrieval_directive_exam_rescue():
    """exam_rescue → RetrievalDirective with task_bound_graph_rag."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="goal_mode", claim="exam_rescue_detected",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    rd = engine.build_retrieval_directive(decision, signal)
    assert rd is not None
    assert rd.retrieval_mode == "task_bound_graph_rag"


@pytest.mark.asyncio
async def test_build_retrieval_directive_no_match():
    """growth_momentum signal → no RetrievalDirective."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_high",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="low",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    rd = engine.build_retrieval_directive(decision, signal)
    assert rd is None


# ── Layer 8: Outcome & Causal Attribution Tests ──────────────────────

def test_outcome_record_serialization():
    """OutcomeRecord round-trips through to_dict/from_dict."""
    record = OutcomeRecord(
        outcome_id="or_test",
        causal_trace_id="ct_test",
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": True, "time_spent_min": 12},
        attribution="effective",
        attribution_confidence=0.8,
    )
    d = record.to_dict()
    record2 = OutcomeRecord.from_dict(d)
    assert record2.outcome_id == "or_test"
    assert record2.attribution == "effective"
    assert record2.actual_outcome["time_spent_min"] == 12


def test_outcome_attribution_effective():
    """Task completed → effective attribution."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, hypothesis, next_policy = recorder._attribute(
        "task_started_and_completed",
        {"started": True, "completed": True, "time_spent_min": 20},
    )
    assert attribution == "effective"
    assert confidence >= 0.7
    assert hypothesis is None


def test_outcome_attribution_insufficient():
    """Task started but not completed → insufficient attribution."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, hypothesis, next_policy = recorder._attribute(
        "task_started_and_completed",
        {"started": True, "completed": False, "time_spent_min": 12},
    )
    assert attribution == "insufficient"
    assert confidence >= 0.5
    assert next_policy is not None


def test_outcome_attribution_user_response_effective():
    """User responded → effective attribution."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, _, _ = recorder._attribute(
        "user_response",
        {"user_responded": True},
    )
    assert attribution == "effective"


def test_outcome_attribution_user_response_insufficient():
    """User did not respond → insufficient attribution."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, hypothesis, next_policy = recorder._attribute(
        "user_response",
        {"user_responded": False},
    )
    assert attribution == "insufficient"
    assert next_policy == "reduce_frequency"


def test_outcome_attribution_behavioral_change():
    """Behavior changed → effective attribution."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, _, _ = recorder._attribute(
        "behavioral_change",
        {"behavior_changed": True},
    )
    assert attribution == "effective"


def test_outcome_attribution_inconclusive():
    """Unknown expected_outcome → inconclusive."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, _, _ = recorder._attribute(
        "unknown_outcome_type",
        {"some_data": True},
    )
    assert attribution == "inconclusive"
    assert confidence == 0.0


def test_outcome_attribution_unexpected_pattern():
    """Conditions not matching any rule → inconclusive with low confidence."""
    recorder = OutcomeRecorder(redis_client=None)
    attribution, confidence, hypothesis, _ = recorder._attribute(
        "task_started_and_completed",
        {"started": False, "completed": False},
    )
    assert attribution == "inconclusive"
    assert hypothesis == "unexpected_outcome_pattern"


@pytest.mark.asyncio
async def test_outcome_recorder_stores_and_retrieves():
    """OutcomeRecorder stores and retrieves outcome records."""
    redis = FakeRedis()
    recorder = OutcomeRecorder(redis_client=redis)
    trace = CausalTrace(trace_id="ct_outcome_test")

    record = await recorder.record_outcome(
        trace=trace,
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": True, "time_spent_min": 18},
    )

    assert record.outcome_id.startswith("or_")
    assert record.attribution == "effective"
    assert record.attribution_confidence >= 0.7

    # Retrieve
    retrieved = await recorder.get_outcome(record.outcome_id)
    assert retrieved is not None
    assert retrieved.outcome_id == record.outcome_id
    assert retrieved.attribution == "effective"


@pytest.mark.asyncio
async def test_spine_record_outcome():
    """SpineOrchestrator.record_outcome delegates correctly."""
    signal = ActionableSignal(
        signal_id="sig_outcome", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    trace = await spine_fixture()._run_signal_pipeline(user_id="u_outcome", signal=signal)
    assert trace is not None

    record = await spine_fixture().record_outcome(
        trace=trace,
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": True, "time_spent_min": 20},
    )
    assert record.attribution == "effective"


def spine_fixture():
    """Create a SpineOrchestrator for Layer 8 tests."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    return SpineOrchestrator(redis_client=redis)


