"""Spine tests — test_audit_and_vision.py."""

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

# ── P0 Audit Fix Tests ─────────────────────────────────────────────


class TestGOV016HighImpactConfirmation:
    """GOV-016: Low-confidence high-priority signals force receipt visibility."""

    @pytest.mark.asyncio
    async def test_high_impact_signal_forces_receipt_visibility(self, spine):
        signal = ActionableSignal(
            signal_id="sig_high_impact",
            source_event_ids=["test"],
            source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large",
            confidence=0.3,
            scope="current_sprint",
            ttl_hours=24,
            evidence_summary="Critical state detected",
            possible_effects=["immediate_action"],
            priority="high",
        )
        trace = await spine._run_signal_pipeline(user_id="u_gov16", signal=signal)
        assert trace is not None
        assert trace.policy_decision_id is not None


class TestSTAB006InteractionCounter:
    """STAB-006: Pipeline auto-increments 24h interaction counter."""

    @pytest.mark.asyncio
    async def test_interaction_counter_auto_incremented(self, spine):
        signal = ActionableSignal(
            signal_id="sig_counter",
            source_event_ids=["test"],
            source_system="test",
            state_key="task_granularity_fit",
            claim="recent_task_too_large",
            confidence=0.7,
            scope="next_24h",
            ttl_hours=24,
            evidence_summary="Test",
            possible_effects=["adjust_task_size"],
            priority="medium",
        )
        await spine._run_signal_pipeline(user_id="u_counter", signal=signal)
        count = await spine.redis.get(f"spine:interaction_count:u_counter:24h")
        assert count is not None
        assert int(count) == 1


class TestSTAB004ReturnCaseFile:
    """STAB-004: ReturnCaseFile wired into on_user_return."""

    @pytest.mark.asyncio
    async def test_return_case_file_stored_on_return(self, spine):
        from app.signals.growth_chronicle import ChronicleEntry

        # Seed a confirmed chronicle entry
        entry = ChronicleEntry(
            entry_id="chron_return",
            user_id="u_return",
            entry_type="milestone",
            timestamp="2026-01-01T00:00:00",
            title="Test milestone",
            narrative="Test narrative",
            evidence_refs=[],
            user_editable=True,
            user_status="confirmed",
            claim="test_claim",
            scope="current_sprint",
            confidence=0.85,
        )
        await spine.growth_chronicle._save_entries("u_return", [entry])

        trace = await spine.on_user_return(
            user_id="u_return",
            time_context={
                "now": "2026-01-01T10:00:00",
                "elapsed_since_last_interaction_min": 120,
            },
        )
        assert trace is not None

        rcf_raw = await spine.redis.get(f"spine:return_case_file:u_return:latest")
        assert rcf_raw is not None
        import json
        rcf = json.loads(rcf_raw)
        assert rcf["chronicle_summary"]["confirmed_count"] == 1

