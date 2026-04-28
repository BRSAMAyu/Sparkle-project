"""Spine tests — test_p1_features.py."""

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

# ── P1-3: PredictedReplyOption Engine Tests ────────────────────────

from app.signals.predicted_reply_options import SpineReplyOptionEngine


def test_reply_options_for_task_granularity():
    """任务颗粒度信号应生成假设确认选项。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="task_service",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.72, scope="current_sprint", ttl_hours=72,
        evidence_summary="连续 2 次超时", possible_effects=["cap_duration"],
        priority="high",
    )
    question = engine.generate_options(signal)

    assert question is not None
    assert question.question_type == "hypothesis_confirm"
    assert question.state_key == "task_granularity_fit"
    assert len(question.options) >= 4  # 3 specific + 1 freeform


def test_reply_options_always_has_freeform():
    """每组选项必须包含自由输入选项。"""
    engine = SpineReplyOptionEngine()
    for state_key in ["task_granularity_fit", "knowledge_transfer", "material_utilization", "goal_mode"]:
        signal = ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=[], source_system="test",
            state_key=state_key, claim="test",
            confidence=0.7, scope="test", ttl_hours=1,
            evidence_summary="test", possible_effects=[], priority="high",
        )
        question = engine.generate_options(signal)
        if question is None:
            continue
        freeform = [o for o in question.options if o.is_freeform]
        assert len(freeform) == 1, f"state_key={state_key} missing freeform option"
        assert "都不对" in freeform[0].label


def test_reply_options_disconfirming_exists():
    """每组至少有一个反驳选项。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    disconfirming = [o for o in question.options if o.is_disconfirming and not o.is_freeform]
    assert len(disconfirming) >= 1


def test_reply_options_no_template_returns_none():
    """没有模板的 state_key 应返回 None。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="unknown_state_key", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    assert engine.generate_options(signal) is None


def test_reply_options_process_selection():
    """用户选择后应返回正确的状态补丁。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)

    # Select the "确实排大了" option
    confirm_opt = [o for o in question.options if o.semantic_value == "task_too_large"][0]
    patch = engine.process_user_selection(question, confirm_opt.option_id)

    assert patch["task_granularity_fit"] == "too_large"


def test_reply_options_process_freeform():
    """自由输入选项应包含用户文本。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)

    freeform = [o for o in question.options if o.is_freeform][0]
    patch = engine.process_user_selection(
        question, freeform.option_id,
        freeform_text="其实是我最近心情不好，学不进去",
    )

    assert patch["open_free_input"] is True
    assert patch["freeform_text"] == "其实是我最近心情不好，学不进去"


def test_reply_options_process_invalid_selection():
    """无效选项 ID 应返回空补丁。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    patch = engine.process_user_selection(question, "nonexistent_id")
    assert patch == {}


def test_reply_options_serialization():
    """PredictedReplyQuestion to_dict 包含完整信息。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="knowledge_transfer", claim="transfer_failure",
        confidence=0.8, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    d = question.to_dict()

    assert d["question_type"] == "hypothesis_confirm"
    assert d["state_key"] == "knowledge_transfer"
    assert len(d["options"]) >= 4
    assert all("label" in o for o in d["options"])


# ── P1-5: SparkleSelfModel Tests ──────────────────────────────────

from app.signals.self_model import SparkleSelfModelService, SelfModelClaim, StrategyOutcome
import pytest


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def self_model_svc(fake_redis):
    return SparkleSelfModelService(redis_client=fake_redis)


@pytest.mark.asyncio
async def test_self_model_record_claim(self_model_svc):
    """记录一个自我模型判断。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="任务拆小策略在 deadline<7 天时有效",
        confidence=0.65,
        scope="strategy",
        evidence=["task_timeout → reduce_duration → completion_rate_up"],
        policy_effects=["recover_execution_rhythm"],
    )
    assert claim.claim_id.startswith("smc_")
    assert claim.confidence == 0.65
    assert claim.scope == "strategy"
    assert claim.outcome is None


@pytest.mark.asyncio
async def test_self_model_record_outcome(self_model_svc):
    """记录策略执行结果并更新 claim。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="exam_rescue 策略有效",
        confidence=0.70,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_001",
        claim_id=claim.claim_id,
        expected_outcome="用户完成抢救任务",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    assert outcome.outcome_id.startswith("smo_")
    assert outcome.attribution["effect"] == "effective"
    assert outcome.next_policy_suggestion == "maintain_current_strategy"


@pytest.mark.asyncio
async def test_self_model_outcome_negative_feedback(self_model_svc):
    """用户完成了但反馈负面 → completed_but_resented。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="pushy 策略",
        confidence=0.60,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_002",
        claim_id=claim.claim_id,
        expected_outcome="用户完成任务",
        actual_outcome={"completed": True, "user_feedback": "negative"},
    )
    assert outcome.attribution["effect"] == "completed_but_resented"
    assert outcome.next_policy_suggestion == "adjust_tone"


@pytest.mark.asyncio
async def test_self_model_outcome_insufficient(self_model_svc):
    """用户不会做 → insufficient。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="任务难度合理",
        confidence=0.50,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_003",
        claim_id=claim.claim_id,
        expected_outcome="用户完成练习",
        actual_outcome={"completed": False, "user_feedback": "不会做"},
    )
    assert outcome.attribution["effect"] == "insufficient"
    assert "switch_strategy:" in (outcome.next_policy_suggestion or "")


@pytest.mark.asyncio
async def test_self_model_confidence_adjustment(self_model_svc):
    """策略有效时置信度上升，无效时下降。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="初始策略",
        confidence=0.50,
        scope="current_sprint",
    )
    # 有效结果 → 置信度上升
    await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_010",
        claim_id=claim.claim_id,
        expected_outcome="ok",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    claims = await self_model_svc.get_active_claims("u1")
    updated = [c for c in claims if c.claim_id == claim.claim_id][0]
    assert updated.confidence > 0.50
    assert updated.outcome == "effective"


@pytest.mark.asyncio
async def test_self_model_get_active_claims(self_model_svc):
    """获取用户活跃 claims。"""
    await self_model_svc.record_claim(
        user_id="u2", claim="c1", confidence=0.5, scope="strategy",
    )
    await self_model_svc.record_claim(
        user_id="u2", claim="c2", confidence=0.6, scope="current_sprint",
    )
    claims = await self_model_svc.get_active_claims("u2")
    assert len(claims) == 2


@pytest.mark.asyncio
async def test_self_model_user_correction(self_model_svc):
    """用户纠正记录为高置信度 claim。"""
    claim = await self_model_svc.record_user_correction(
        user_id="u1",
        signal_id="sig_001",
        reason="不是任务太大，是我不知道前置知识",
    )
    assert claim.confidence == 0.90
    assert "retract_related_directive" in claim.policy_effects


@pytest.mark.asyncio
async def test_self_model_max_claims_cap(self_model_svc):
    """claims 列表不超过 _MAX_CLAIMS。"""
    for i in range(55):
        await self_model_svc.record_claim(
            user_id="u3", claim=f"claim_{i}", confidence=0.5, scope="strategy",
        )
    claims = await self_model_svc.get_active_claims("u3", limit=100)
    assert len(claims) <= 50


@pytest.mark.asyncio
async def test_self_model_serialization():
    """SelfModelClaim 和 StrategyOutcome to_dict 完整。"""
    claim = SelfModelClaim(
        claim_id="smc_test", claim="test", confidence=0.8, scope="strategy",
        evidence=["e1"], counter_evidence=["ce1"], policy_effects=["p1"],
    )
    d = claim.to_dict()
    assert d["claim_id"] == "smc_test"
    assert d["confidence"] == 0.8

    outcome = StrategyOutcome(
        outcome_id="smo_test", directive_id="dir", claim_id="smc_test",
        expected_outcome="ok", actual_outcome={"completed": True},
        attribution={"effect": "effective"},
    )
    d2 = outcome.to_dict()
    assert d2["outcome_id"] == "smo_test"
    assert d2["attribution"]["effect"] == "effective"


# ── P1-1: AchievementReinforcementConsumer Tests ──────────────────

from app.signals.achievement_reinforcement import AchievementReinforcementConsumer


@pytest.fixture
def achievement_consumer():
    return AchievementReinforcementConsumer()


def test_achievement_high_momentum(achievement_consumer):
    """7天解锁3个成就+2连击 → momentum >= 0.7 → high signal。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.unlocked",
        recent_unlocks=3,
        active_streaks=2,
        in_progress_count=4,
    )
    assert signal is not None
    assert signal.claim == "momentum_high"
    assert signal.state_key == "growth_momentum"
    assert signal.priority == "low"


def test_achievement_stalled_momentum(achievement_consumer):
    """0解锁但有进行中 → stalled signal。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=0,
        active_streaks=0,
        in_progress_count=3,
    )
    assert signal is not None
    assert signal.claim == "momentum_stalled"
    assert signal.priority == "medium"


def test_achievement_moderate_no_signal(achievement_consumer):
    """中等动量 → 不产生信号。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=1,
        active_streaks=1,
        in_progress_count=2,
    )
    assert signal is None


def test_achievement_zero_no_signal(achievement_consumer):
    """零活跃零进度 → 不产生 stalled（in_progress=0）。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=0,
        active_streaks=0,
        in_progress_count=0,
    )
    assert signal is None


def test_achievement_momentum_score_calculation(achievement_consumer):
    """动量分数计算验证。"""
    m = achievement_consumer.compute_momentum(
        user_id="u1", recent_unlocks=4, active_streaks=3, in_progress_count=5,
    )
    assert m.momentum_score == 1.0  # 全部满分
    assert m.recent_unlocks == 4
    assert m.active_streaks == 3


def test_achievement_momentum_serialization(achievement_consumer):
    """AchievementMomentum to_dict。"""
    m = achievement_consumer.compute_momentum(
        user_id="u1", recent_unlocks=1, active_streaks=0, in_progress_count=1,
    )
    d = m.to_dict()
    assert d["user_id"] == "u1"
    assert "momentum_score" in d


# ── P1-4: RecallOpportunity Tests ─────────────────────────────────

from app.signals.recall_opportunity import RecallOpportunityDetector


@pytest.fixture
def recall_detector():
    return RecallOpportunityDetector()


def test_recall_undigested_material(recall_detector):
    """上传了资料但没诊断 → 触发召回。"""
    trigger = recall_detector.check_undigested_material(
        user_id="u1", uploaded_files_count=3, diagnosed_files_count=1,
        hours_since_upload=2.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "undigested_material"
    assert trigger.context["undigested"] == 2


def test_recall_no_trigger_all_diagnosed(recall_detector):
    """所有资料都诊断了 → 不触发。"""
    trigger = recall_detector.check_undigested_material(
        user_id="u1", uploaded_files_count=2, diagnosed_files_count=2,
        hours_since_upload=5.0,
    )
    assert trigger is None


def test_recall_task_not_started(recall_detector):
    """任务超过 1 小时未启动 → 触发召回。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=2.0,
        has_started=False,
    )
    assert trigger is not None
    assert trigger.trigger_type == "task_not_started"


def test_recall_task_started_no_trigger(recall_detector):
    """任务已启动 → 不触发。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=5.0,
        has_started=True,
    )
    assert trigger is None


def test_recall_task_too_recent(recall_detector):
    """任务分配不到 1 小时 → 不触发。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=0.5,
        has_started=False,
    )
    assert trigger is None


def test_recall_task_missed(recall_detector):
    """任务错过 deadline → 高优先级召回。"""
    trigger = recall_detector.check_task_missed(
        user_id="u1", task_id="t1", deadline_hours=-3.0,
        is_completed=False,
    )
    assert trigger is not None
    assert trigger.urgency == "high"


def test_recall_pre_exam_silence(recall_detector):
    """考前 48h 沉默 → 触发召回。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=1.5,
        hours_since_last_activity=5.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "pre_exam_silence"


def test_recall_pre_exam_still_active(recall_detector):
    """考前但用户还活跃 → 不触发。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=1.0,
        hours_since_last_activity=0.5,
    )
    assert trigger is None


def test_recall_to_actionable_signal(recall_detector):
    """RecallTrigger → ActionableSignal 转换。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=0.5,
        hours_since_last_activity=10.0,
    )
    signal = recall_detector.to_actionable_signal(trigger)
    assert signal.state_key == "recall_needed"
    assert signal.claim == "pre_exam_silence"
    assert signal.confidence == 0.80


def test_recall_cooldown(recall_detector):
    """冷却期返回正确值。"""
    assert recall_detector.get_cooldown_seconds("pre_exam_silence") == 1800
    assert recall_detector.get_cooldown_seconds("task_not_started") == 7200


# ── P1-2: AuroraWakeEligibility Tests ─────────────────────────────

from app.signals.aurora_wake import AuroraWakeJudge


@pytest.fixture
def wake_judge():
    return AuroraWakeJudge()


def test_wake_strategy_failure(wake_judge):
    """连续 2 次负向 → strategy_recalibration。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
        consecutive_negative_outcomes=2,
    )
    assert result.can_wake is True
    assert result.recommended_session_type == "strategy_recalibration"
    assert "consecutive_strategy_failure" in result.wake_reasons


def test_wake_user_requested(wake_judge):
    """用户主动请求 → deep_review。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=1,
        cooldown_status="available",
        user_requested_deep_review=True,
    )
    assert result.can_wake is True
    assert result.recommended_session_type == "deep_review"


def test_wake_momentum_stalled(wake_judge):
    """动量停滞 → motivation_check。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=3,
        cooldown_status="available",
        momentum_stalled=True,
    )
    assert result.can_wake is True
    assert "momentum_stalled" in result.wake_reasons


def test_wake_no_reason(wake_judge):
    """无唤醒理由 → 不可唤醒。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=3,
        cooldown_status="available",
    )
    assert result.can_wake is False
    assert result.wake_reasons == []


def test_wake_quota_exhausted(wake_judge):
    """配额耗尽 → 不可唤醒（即使有理由）。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=0,
        cooldown_status="available",
        consecutive_negative_outcomes=3,
    )
    assert result.can_wake is False
    assert result.cooldown_status == "exhausted"


def test_wake_cooldown_active(wake_judge):
    """冷却中 → 不可唤醒。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="cooling",
        cooldown_minutes_left=30,
        consecutive_negative_outcomes=2,
    )
    assert result.can_wake is False
    assert result.cooldown_minutes_left == 30


def test_wake_serialization(wake_judge):
    """AuroraWakeEligibility to_dict。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=1,
        cooldown_status="available",
        user_requested_deep_review=True,
    )
    d = result.to_dict()
    assert d["can_wake"] is True
    assert d["quota_remaining"] == 1


# ── P1-6: CommunitySignal v1 Tests ────────────────────────────────

from app.signals.community_signal import CommunitySignalDetector


@pytest.fixture
def community_detector():
    return CommunitySignalDetector()


def test_community_cohort_mistake(community_detector):
    """群体 >= 5 + 出错率 >= 40% → 检测到共性错因。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp_congestion",
        subject="computer_networks",
        mistake_type="concept_confusion",
        cohort_size=10,
        error_count=6,
        common_misconception="混淆拥塞控制和流量控制",
    )
    assert pattern is not None
    assert pattern.frequency_ratio == 0.6


def test_community_cohort_too_small(community_detector):
    """群体 < 5 → 不检测（隐私保护）。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp",
        subject="cn", mistake_type="test",
        cohort_size=3, error_count=3,
        common_misconception="test",
    )
    assert pattern is None


def test_community_cohort_low_ratio(community_detector):
    """出错率 < 40% → 不检测。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp", subject="cn", mistake_type="test",
        cohort_size=10, error_count=3,
        common_misconception="test",
    )
    assert pattern is None


def test_community_shared_resource(community_detector):
    """使用人数 >= 3 + 相关度 >= 0.5 → 推荐资料。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r1",
        resource_title="计网速通笔记",
        subject="computer_networks",
        recommendation_reason="highly_rated_by_cohort",
        peer_count=8,
        relevance_score=0.75,
    )
    assert rec is not None
    assert rec.peer_count == 8


def test_community_shared_resource_low_relevance(community_detector):
    """相关度 < 0.5 → 不推荐。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r2", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=5, relevance_score=0.3,
    )
    assert rec is None


def test_community_shared_resource_too_few_peers(community_detector):
    """使用人数 < 3 → 不推荐。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r3", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=1, relevance_score=0.9,
    )
    assert rec is None


def test_community_mistake_to_signal(community_detector):
    """CohortMistakePattern → ActionableSignal，priority <= medium。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp",
        subject="cn", mistake_type="confusion",
        cohort_size=10, error_count=7,
        common_misconception="test",
    )
    signal = community_detector.to_actionable_signal(pattern)
    assert signal.state_key == "community_cohort_pattern"
    assert signal.priority == "medium"
    assert signal.confidence <= 0.85


def test_community_resource_to_signal(community_detector):
    """SharedResourceRecommendation → ActionableSignal，priority=low。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r1", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=5, relevance_score=0.8,
    )
    signal = community_detector.to_actionable_signal(rec)
    assert signal.state_key == "community_resource_recommendation"
    assert signal.priority == "low"


def test_community_no_high_priority(community_detector):
    """社群信号优先级永远不超过 medium（铁律验证）。"""
    # 构造极端情况
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="x", subject="s", mistake_type="m",
        cohort_size=100, error_count=99,
        common_misconception="extreme",
    )
    signal = community_detector.to_actionable_signal(pattern)
    assert signal.priority in ("low", "medium")


