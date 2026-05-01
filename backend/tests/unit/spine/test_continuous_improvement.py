"""Spine tests — test_research_and_bridge.py."""

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

# ─────────────────────────────────────────────────────────────────────────────
# P10 Tests: Aurora Status Band Summary API
# Demo Experience Point #10: Aurora 状态带显示"策略风险 / 资料感知"
# ─────────────────────────────────────────────────────────────────────────────


async def test_p10_get_status_band_empty(fake_redis):
    """No active signals → all risk flags False, band_severity = none."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    result = await spine.get_status_band_summary(user_id="u_band0")
    assert result["strategy_risk"] is False
    assert result["material_aware"] is False
    assert result["execution_risk"] is False
    assert result["stale_guard"] is False
    assert result["has_active_directive"] is False
    assert result["band_severity"] == "none"
    assert isinstance(result["active_claims"], list)
    assert isinstance(result["active_state_keys"], list)


async def test_p10_get_status_band_transfer_failure(fake_redis):
    """knowledge_transfer:transfer_failure signal → strategy_risk=True, severity=warning."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ActionableSignal, _uid
    spine = SpineOrchestrator(fake_redis)
    # Seed a transfer_failure signal into StateRegister
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["err_001"],
        source_system="mistake_signal",
        state_key="knowledge_transfer",
        claim="transfer_failure",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="3 consecutive errors on TCP windowing",
        possible_effects=["avoid_new_chapter"],
        priority="high",
    )
    await spine.state_register.upsert_from_signal("u_band1", signal)

    result = await spine.get_status_band_summary(user_id="u_band1")
    assert result["strategy_risk"] is True
    assert result["material_aware"] is False
    assert result["band_severity"] == "warning"
    assert "transfer_failure" in result["active_claims"]
    assert "knowledge_transfer" in result["active_state_keys"]


async def test_p10_get_status_band_material_aware(fake_redis):
    """source_material:material_received signal → material_aware=True, severity=info."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ActionableSignal, _uid
    spine = SpineOrchestrator(fake_redis)
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["file_002"],
        source_system="file_integration",
        state_key="source_material",
        claim="material_received",
        confidence=0.75,
        scope="current_sprint",
        ttl_hours=168,
        evidence_summary="File organic_chemistry.pdf uploaded",
        possible_effects=["prefer_targeted_source_rag"],
        priority="medium",
    )
    await spine.state_register.upsert_from_signal("u_band2", signal)

    result = await spine.get_status_band_summary(user_id="u_band2")
    assert result["material_aware"] is True
    assert result["strategy_risk"] is False
    assert result["band_severity"] == "info"
    assert "material_received" in result["active_claims"]


async def test_p10_get_status_band_execution_risk(fake_redis):
    """task_granularity_fit:too_large signal → execution_risk=True, severity=warning."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ActionableSignal, _uid
    spine = SpineOrchestrator(fake_redis)
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["task_timeout"],
        source_system="task_timeout_detector",
        state_key="task_granularity_fit",
        claim="too_large",
        confidence=0.80,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="2 consecutive task timeouts",
        possible_effects=["reduce_task_duration"],
        priority="high",
    )
    await spine.state_register.upsert_from_signal("u_band3", signal)

    result = await spine.get_status_band_summary(user_id="u_band3")
    assert result["execution_risk"] is True
    assert result["strategy_risk"] is False
    assert result["band_severity"] == "warning"


async def test_p10_get_status_band_combined_critical(fake_redis):
    """strategy_risk + execution_risk simultaneously → band_severity = critical."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ActionableSignal, _uid
    spine = SpineOrchestrator(fake_redis)
    # Seed both signals
    for state_key, claim in [
        ("knowledge_transfer", "transfer_failure"),
        ("task_granularity_fit", "too_large"),
    ]:
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=["combined_test"],
            source_system="test",
            state_key=state_key,
            claim=claim,
            confidence=0.80,
            scope="current_sprint",
            ttl_hours=24,
            evidence_summary=f"Combined {state_key}",
            possible_effects=[],
            priority="high",
        )
        await spine.state_register.upsert_from_signal("u_band4", signal)

    result = await spine.get_status_band_summary(user_id="u_band4")
    assert result["strategy_risk"] is True
    assert result["execution_risk"] is True
    assert result["band_severity"] == "critical"


async def test_p10_get_status_band_structure_complete(fake_redis):
    """Response contains all required fields for Flutter status band rendering."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    result = await spine.get_status_band_summary(user_id="u_band5")
    required_keys = {
        "strategy_risk", "material_aware", "execution_risk", "stale_guard",
        "has_active_directive", "active_claims", "active_state_keys",
        "directive_summary", "band_severity",
    }
    for key in required_keys:
        assert key in result, f"Missing required field: {key}"
    assert result["band_severity"] in ("none", "info", "warning", "critical")


async def test_p10_get_status_band_wired_to_orchestrator(fake_redis):
    """SpineOrchestrator exposes get_status_band_summary as a public method."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    assert hasattr(spine, "get_status_band_summary"), "get_status_band_summary must exist"
    assert callable(spine.get_status_band_summary)


# ─────────────────────────────────────────────────────────────────────────────
# P12 Tests: SourceTraySelection User Override
# Demo Experience Point #5: 用户能手动选择资料参与本轮
# ─────────────────────────────────────────────────────────────────────────────


async def test_p12_source_tray_methods_wired(fake_redis):
    """SpineOrchestrator has set_source_tray_selection and get_source_tray_state."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    assert hasattr(spine, "set_source_tray_selection")
    assert hasattr(spine, "get_source_tray_state")
    assert callable(spine.set_source_tray_selection)
    assert callable(spine.get_source_tray_state)


async def test_p12_get_source_tray_empty_default(fake_redis):
    """No selections → get_source_tray_state returns auto mode with empty selections."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    result = await spine.get_source_tray_state(user_id="u_tray0")
    assert result["mode"] == "auto"
    assert isinstance(result["selections"], list)
    assert len(result["selections"]) == 0


async def test_p12_set_source_tray_persists(fake_redis):
    """set_source_tray_selection stores selections in Redis."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    await spine.set_source_tray_selection(
        user_id="u_tray1",
        selections=[
            {"source_id": "file_001", "action": "include", "scope": "this_task"},
        ],
        mode="manual_only",
    )
    raw = await fake_redis.get("spine:source_tray:u_tray1")
    assert raw is not None, "Selection must be persisted to Redis"


async def test_p12_get_source_tray_returns_stored(fake_redis):
    """get_source_tray_state returns exactly what was stored by set."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    await spine.set_source_tray_selection(
        user_id="u_tray2",
        selections=[
            {"source_id": "file_abc", "action": "include", "scope": "this_turn", "user_initiated": True},
            {"source_id": "file_xyz", "action": "exclude", "scope": "today", "user_initiated": True},
        ],
        mode="manual_only",
    )
    state = await spine.get_source_tray_state(user_id="u_tray2")
    assert state["mode"] == "manual_only"
    assert len(state["selections"]) == 2
    source_ids = {s["source_id"] for s in state["selections"]}
    assert "file_abc" in source_ids
    assert "file_xyz" in source_ids


async def test_p12_source_tray_session_isolated(fake_redis):
    """Different users have independent source tray states."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    await spine.set_source_tray_selection(
        user_id="u_tray3",
        selections=[{"source_id": "u3_file", "action": "include", "scope": "this_task"}],
        mode="manual_only",
    )
    # Different user should have no selections
    state_other = await spine.get_source_tray_state(user_id="u_tray4")
    assert state_other["mode"] == "auto"
    assert len(state_other["selections"]) == 0


async def test_p12_source_tray_override_existing(fake_redis):
    """Calling set_source_tray_selection twice replaces previous selections."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    await spine.set_source_tray_selection(
        user_id="u_tray5",
        selections=[{"source_id": "old_file", "action": "include", "scope": "this_task"}],
        mode="manual_only",
    )
    # Override with new selection
    await spine.set_source_tray_selection(
        user_id="u_tray5",
        selections=[{"source_id": "new_file", "action": "include", "scope": "today"}],
        mode="manual_only",
    )
    state = await spine.get_source_tray_state(user_id="u_tray5")
    assert len(state["selections"]) == 1
    assert state["selections"][0]["source_id"] == "new_file"


async def test_p12_source_tray_no_materials_mode(fake_redis):
    """mode=no_materials stores correctly and is readable."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    result = await spine.set_source_tray_selection(
        user_id="u_tray6",
        selections=[],
        mode="no_materials",
    )
    assert result["mode"] == "no_materials"
    state = await spine.get_source_tray_state(user_id="u_tray6")
    assert state["mode"] == "no_materials"


# ─────────────────────────────────────────────────────────────────────────────
# P11 Tests: CausalTrace Timeline Rendering in Experience Envelope
# Demo Experience Point #11: 混合时间轴记录完整 causal trace
# ─────────────────────────────────────────────────────────────────────────────


async def test_p11_get_rendered_timeline_wired(fake_redis):
    """SpineOrchestrator has get_rendered_timeline method."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    assert hasattr(spine, "get_rendered_timeline")
    assert callable(spine.get_rendered_timeline)


async def test_p11_get_rendered_timeline_empty(fake_redis):
    """No traces → get_rendered_timeline returns empty list."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    result = await spine.get_rendered_timeline(user_id="u_tl1")
    assert isinstance(result, list)
    assert len(result) == 0


async def test_p11_timeline_card_renderer_in_orchestrator(fake_redis):
    """SpineOrchestrator has timeline_renderer attribute (TimelineCardRenderer)."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.timeline_card_renderer import TimelineCardRenderer
    spine = SpineOrchestrator(fake_redis)
    assert hasattr(spine, "timeline_renderer")
    assert isinstance(spine.timeline_renderer, TimelineCardRenderer)


async def test_p11_get_rendered_timeline_returns_list_structure(fake_redis):
    """get_rendered_timeline result items have required trace fields."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.causal_trace_store import CausalTraceStore
    from app.signals.types import CausalTrace, _uid
    spine = SpineOrchestrator(fake_redis)
    store = CausalTraceStore(fake_redis)

    # Manually create a trace and register it to user traces
    trace = await store.create_trace()
    await store.link_to_user("u_tl2", trace.trace_id)

    result = await spine.get_rendered_timeline(user_id="u_tl2")
    assert isinstance(result, list)
    assert len(result) >= 1
    item = result[0]
    assert "trace_id" in item
    assert "created_at" in item
    assert "event_summary" in item
    assert "signal" in item
    assert "policy_decision" in item
    assert "directives" in item
    assert "card" in item


async def test_p11_build_experience_envelope_has_timeline(fake_redis):
    """build_experience_envelope returns timeline_updates list."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    envelope = await spine.build_experience_envelope(user_id="u_tl3")
    assert "timeline_updates" in envelope
    assert isinstance(envelope["timeline_updates"], list)


async def test_p11_build_experience_envelope_complete_structure(fake_redis):
    """build_experience_envelope returns all required top-level keys."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(fake_redis)
    envelope = await spine.build_experience_envelope(user_id="u_tl4", primary_message="test")
    required = {
        "turn_id", "primary_message", "status_band", "receipts",
        "context_receipt", "cards", "predicted_reply_options",
        "timeline_updates", "task_card_updates",
    }
    for key in required:
        assert key in envelope, f"Missing envelope key: {key}"
    assert isinstance(envelope["timeline_updates"], list)


async def test_p11_get_rendered_timeline_graceful_on_missing_data(fake_redis):
    """Trace with no signals/policy still returns item without raising."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.causal_trace_store import CausalTraceStore
    spine = SpineOrchestrator(fake_redis)
    store = CausalTraceStore(fake_redis)

    # Trace with no signals or policy
    trace = await store.create_trace()
    await store.link_to_user("u_tl5", trace.trace_id)

    result = await spine.get_rendered_timeline(user_id="u_tl5")
    assert isinstance(result, list)
    # Should succeed without exception; empty card is acceptable
    if result:
        assert "trace_id" in result[0]
        assert result[0]["card"] is None  # No signal → card=None


