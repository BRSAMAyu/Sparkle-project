"""Spine tests — test_policy_engine.py."""

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

# ── PolicyEngine gap coverage: growth_momentum + recall_needed rules ──

from app.signals.policy_engine import PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.mark.asyncio
async def test_policy_growth_momentum_high(policy_engine):
    """growth_momentum/momentum_high → sustain_momentum strategy。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_high",
        confidence=0.80, scope="current_sprint", ttl_hours=48,
        evidence_summary="test", possible_effects=[], priority="low",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "sustain_momentum"
    assert "tone" in decision.soft_biases
    assert decision.visibility == "status_band"


@pytest.mark.asyncio
async def test_policy_growth_momentum_stalled(policy_engine):
    """growth_momentum/momentum_stalled → rekindle_engagement。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_stalled",
        confidence=0.70, scope="current_sprint", ttl_hours=24,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].primary_strategy == "rekindle_engagement"


@pytest.mark.asyncio
async def test_policy_recall_pre_exam(policy_engine):
    """recall_needed/pre_exam_silence → urgent_exam_prep + hard constraints。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="pre_exam_silence",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "urgent_exam_prep"
    assert directive.hard_constraints.get("prefer_high_yield_review") is True


@pytest.mark.asyncio
async def test_policy_recall_task_missed(policy_engine):
    """recall_needed/task_missed → requires_user_confirmation。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="task_missed",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].requires_user_confirmation is True


@pytest.mark.asyncio
async def test_policy_recall_undigested_material(policy_engine):
    """recall_needed/undigested_material → prompt_diagnostic。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="undigested_material",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].primary_strategy == "prompt_diagnostic"


@pytest.mark.asyncio
async def test_policy_growth_momentum_no_rule_for_other_claims(policy_engine):
    """growth_momentum/unknown_claim → no match。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="some_other_claim",
        confidence=0.80, scope="current_sprint", ttl_hours=48,
        evidence_summary="test", possible_effects=[], priority="low",
    )
    result = await policy_engine.evaluate(signal)
    assert result is None


