"""Spine tests — test_advanced_features.py."""

from __future__ import annotations
from tests.unit.spine._helpers import FakeRedis, _make_signal


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

# ── v2.10: Full Directive Coverage Production Wiring ───────────────────


@pytest.mark.asyncio
async def test_v210_ux_directive_stored_and_retrievable():
    """UXDirective is stored in Redis and retrievable for stream metadata."""
    from app.signals.types import UXDirective
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = _make_signal("task_granularity_fit", claim="recent_task_too_large", confidence=0.9)
    await spine._run_signal_pipeline(user_id="u_ux_test", signal=signal)
    ux = await spine.get_ux_directive("u_ux_test")
    assert ux is not None
    assert ux.status_band_state == "risk_detected"
    assert ux.show_context_receipt is True


@pytest.mark.asyncio
async def test_v210_community_directive_stored_and_retrievable():
    """CommunityDirective is stored and retrievable."""
    from app.signals.types import CommunityDirective
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = _make_signal("community_cohort_pattern", claim="cohort_mistake_detected", confidence=0.8)
    await spine._run_signal_pipeline(user_id="u_comm_test", signal=signal)
    comm = await spine.get_community_directive("u_comm_test")
    assert comm is not None
    assert comm.peer_context_mode == "anonymous"


@pytest.mark.asyncio
async def test_v210_skill_directive_stored_and_retrievable():
    """SkillDirective is stored and retrievable."""
    from app.signals.types import SkillDirective
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = _make_signal("knowledge_transfer", claim="transfer_failure", confidence=0.9)
    await spine._run_signal_pipeline(user_id="u_skill_test", signal=signal)
    skill = await spine.get_skill_directive("u_skill_test")
    assert skill is not None
    assert skill.skill_action in ("none", "inject", "recommend")


@pytest.mark.asyncio
async def test_v210_ux_directive_to_dict_for_metadata():
    """UXDirective serializes correctly for stream metadata."""
    from app.signals.types import UXDirective
    ux = UXDirective(
        directive_id="ux1", policy_decision_id="pd1",
        status_band_state="strategy_active",
        show_context_receipt=True,
        show_strategy_receipt=True,
        predicted_reply_options=["option_a", "option_b"],
        allow_full_aurora_wake=True,
    )
    d = ux.to_dict()
    assert d["status_band_state"] == "strategy_active"
    assert d["allow_full_aurora_wake"] is True
    assert len(d["predicted_reply_options"]) == 2


@pytest.mark.asyncio
async def test_v210_all_directive_types_fetched():
    """All 9 directive types can be fetched without error (null-safe)."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    # No pipeline run — all should return None gracefully
    assert await spine.get_response_directive("u_none") is None
    assert await spine.get_retrieval_directive("u_none") is None
    assert await spine.get_plan_directive("u_none") is None
    assert await spine.get_ux_directive("u_none") is None
    assert await spine.get_community_directive("u_none") is None
    assert await spine.get_skill_directive("u_none") is None
    assert await spine.get_model_write_directive("u_none") is None
    assert await spine.get_notification_directive("u_none") is None
    assert await spine.get_active_directive("u_none") is None


# ============================================================
# P2-5: Relationship model dynamic evolution (behavioral signals)
# ============================================================


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_task_completed():
    """task_completed behavioral signal increases trust."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    state = await svc.update_from_behavioral_signal("u1", "task_completed")
    assert state.trust_level > 0.5
    assert state.total_tasks_completed == 1


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_task_abandoned():
    """task_abandoned decreases trust slightly."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    state = await svc.update_from_behavioral_signal("u1", "task_abandoned")
    assert state.trust_level < 0.5
    assert state.total_tasks_abandoned == 1


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_streak_maintained():
    """streak_maintained scales trust bonus with streak length."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    state = await svc.update_from_behavioral_signal("u1", "streak_maintained", {"streak_length": 5})
    assert state.trust_level > 0.5
    assert state.current_streak == 5
    assert state.longest_streak == 5


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_streak_broken():
    """streak_broken resets current streak and lowers trust."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    # Build up a streak first
    await svc.update_from_behavioral_signal("u1", "streak_maintained", {"streak_length": 7})
    state = await svc.update_from_behavioral_signal("u1", "streak_broken")
    assert state.current_streak == 0
    assert state.longest_streak == 7
    # trust went up from streak bonus then down from break — net still above default
    assert state.trust_level < 0.5 + 0.035


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_session_signals():
    """session_engaged increases, session_idle decreases trust."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    s1 = await svc.update_from_behavioral_signal("u1", "session_engaged")
    assert s1.trust_level > 0.5

    s2 = await svc.update_from_behavioral_signal("u2", "session_idle")
    assert s2.trust_level < 0.5


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_invalid_signal():
    """Invalid behavioral signal raises ValueError."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    with pytest.raises(ValueError, match="Unsupported behavioral signal"):
        await svc.update_from_behavioral_signal("u1", "invalid_signal")


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_counts_tracked():
    """Behavioral counts are tracked in preferences."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    await svc.update_from_behavioral_signal("u1", "task_completed")
    await svc.update_from_behavioral_signal("u1", "task_completed")
    await svc.update_from_behavioral_signal("u1", "streak_maintained", {"streak_length": 3})

    state = await svc.get_or_create("u1")
    counts = state.preferences.get("behavioral_counts", {})
    assert counts.get("task_completed") == 2
    assert counts.get("streak_maintained") == 1


@pytest.mark.asyncio
async def test_v210_relationship_behavioral_persistence():
    """Behavioral state persists across get_or_create calls."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    await svc.update_from_behavioral_signal("u1", "task_completed")
    await svc.update_from_behavioral_signal("u1", "streak_maintained", {"streak_length": 4})

    reloaded = await svc.get_or_create("u1")
    assert reloaded.total_tasks_completed == 1
    assert reloaded.current_streak == 4


@pytest.mark.asyncio
async def test_v210_spine_on_task_completed_updates_relationship():
    """on_task_completed triggers relationship behavioral update even without signal."""
    spine = SpineOrchestrator(redis_client=FakeRedis())

    # Normal task completion (no timeout signal generated)
    trace = await spine.on_task_completed(
        user_id="u_rel",
        task_id="t1",
        estimated_minutes=30,
        actual_minutes=25,
    )
    assert trace is not None

    # Relationship should have been updated
    rel = await spine.relationship_model.get_or_create("u_rel")
    assert rel.total_tasks_completed == 1


@pytest.mark.asyncio
async def test_v210_spine_on_streak_update():
    """on_streak_update correctly delegates to relationship model."""
    spine = SpineOrchestrator(redis_client=FakeRedis())

    await spine.on_streak_update(user_id="u_streak", streak_length=5)
    rel = await spine.relationship_model.get_or_create("u_streak")
    assert rel.current_streak == 5
    assert rel.longest_streak == 5

    await spine.on_streak_update(user_id="u_streak", streak_length=5, broken=True)
    rel = await spine.relationship_model.get_or_create("u_streak")
    assert rel.current_streak == 0
    assert rel.longest_streak == 5


# ============================================================
# P2-6: Multi-strategy experiment system upgrade
# ============================================================


@pytest.mark.asyncio
async def test_v210_experiment_cognitive_shadow():
    """Cognitive load strategies have shadow alternatives."""
    from app.signals.policy_experiments import PolicyExperimentManager, _SHADOW_ALTERNATIVES
    assert "reduce_cognitive_pressure" in _SHADOW_ALTERNATIVES
    assert "reduce_affective_pressure" in _SHADOW_ALTERNATIVES
    assert "prevent_burnout" in _SHADOW_ALTERNATIVES

    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)
    exp = await mgr.create_experiment(
        user_id="u1",
        signal_state_key="cognitive_load",
        signal_claim="high_load_detected",
        primary_strategy="reduce_cognitive_pressure",
    )
    assert exp is not None
    assert exp.shadow_strategy == "reduce_cognitive_pressure_micro"


@pytest.mark.asyncio
async def test_v210_experiment_affective_shadow():
    """Affective pressure shadow experiment."""
    from app.signals.policy_experiments import PolicyExperimentManager
    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)
    exp = await mgr.create_experiment(
        user_id="u1",
        signal_state_key="affective_pressure",
        signal_claim="stress_detected",
        primary_strategy="reduce_affective_pressure",
    )
    assert exp is not None
    assert exp.shadow_strategy == "reduce_affective_pressure_social"


@pytest.mark.asyncio
async def test_v210_experiment_conclude_all_for_user():
    """conclude_all_for_user closes all running experiments."""
    from app.signals.policy_experiments import PolicyExperimentManager
    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)

    e1 = await mgr.create_experiment(
        user_id="u1", signal_state_key="k1", signal_claim="c1",
        primary_strategy="recover_execution_rhythm",
    )
    # Add trials
    for _ in range(5):
        await mgr.record_trial(e1.experiment_id, primary_outcome="effective", shadow_hypothesis="insufficient")

    concluded = await mgr.conclude_all_for_user("u1")
    assert len(concluded) == 1
    assert concluded[0].status == "concluded"


@pytest.mark.asyncio
async def test_v210_experiment_get_best_strategy():
    """get_best_strategy_for_signal returns best performing strategy."""
    from app.signals.policy_experiments import PolicyExperimentManager
    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)

    exp = await mgr.create_experiment(
        user_id="u1", signal_state_key="cognitive_load", signal_claim="high_load",
        primary_strategy="reduce_cognitive_pressure",
    )
    # Shadow wins more
    for _ in range(8):
        await mgr.record_trial(exp.experiment_id, primary_outcome="insufficient", shadow_hypothesis="effective")
    for _ in range(2):
        await mgr.record_trial(exp.experiment_id, primary_outcome="effective", shadow_hypothesis="insufficient")

    best = await mgr.get_best_strategy_for_signal("u1", "cognitive_load")
    assert best is not None
    assert best["strategy"] == "reduce_cognitive_pressure_micro"
    assert best["win_rate"] == 0.8


@pytest.mark.asyncio
async def test_v210_experiment_shadow_cognitive_context():
    """Shadow evaluation handles cognitive context keywords."""
    from app.signals.policy_experiments import PolicyExperimentManager
    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)

    result = mgr.evaluate_shadow_outcome(
        primary_outcome="insufficient",
        primary_strategy="reduce_cognitive_pressure",
        context={"new_hypothesis": "cognitive overload from complex material"},
    )
    assert result == "effective"


@pytest.mark.asyncio
async def test_v210_experiment_shadow_affective_context():
    """Shadow evaluation handles affective context keywords."""
    from app.signals.policy_experiments import PolicyExperimentManager
    redis = FakeRedis()
    mgr = PolicyExperimentManager(redis)

    result = mgr.evaluate_shadow_outcome(
        primary_outcome="insufficient",
        primary_strategy="reduce_affective_pressure",
        context={"new_hypothesis": "user experiencing stress and anxiety"},
    )
    assert result == "effective"


# ============================================================
# P2-7: Partner accountability loop completion
# ============================================================


@pytest.mark.asyncio
async def test_v210_partner_checkin_records():
    """record_partner_checkin stores check-in and returns count."""
    from app.signals.community_loops import CommunityLoopManager
    redis = FakeRedis()
    mgr = CommunityLoopManager()

    result = await mgr.record_partner_checkin(
        redis, user_id="u1", partner_id="p1", checkin_type="encouragement",
    )
    assert result["recorded"] is True
    assert result["total_checkins"] == 1
    assert result["signal"] is None  # Below threshold


@pytest.mark.asyncio
async def test_v210_partner_checkin_signal_after_threshold():
    """Partner accountability signal generated after 3 check-ins."""
    from app.signals.community_loops import CommunityLoopManager
    redis = FakeRedis()
    mgr = CommunityLoopManager()

    for i in range(3):
        result = await mgr.record_partner_checkin(
            redis, user_id="u1", partner_id="p1", checkin_type="nudge",
        )
    assert result["total_checkins"] == 3
    assert result["signal"] is not None
    assert result["signal"]["state_key"] == "partner_accountability_active"


@pytest.mark.asyncio
async def test_v210_partner_checkin_confidence_scales():
    """Signal confidence increases with more check-ins."""
    from app.signals.community_loops import CommunityLoopManager
    redis = FakeRedis()
    mgr = CommunityLoopManager()

    for i in range(5):
        await mgr.record_partner_checkin(
            redis, user_id="u1", partner_id="p1", checkin_type="check_in",
        )
    state = await mgr.get_accountability_state(redis, "u1")
    assert state["active"] is True
    assert state["total_checkins"] == 5


@pytest.mark.asyncio
async def test_v210_partner_get_accountability_state_empty():
    """get_accountability_state returns default when no check-ins."""
    from app.signals.community_loops import CommunityLoopManager
    redis = FakeRedis()
    mgr = CommunityLoopManager()

    state = await mgr.get_accountability_state(redis, "u1")
    assert state["active"] is False
    assert state["total_checkins"] == 0


@pytest.mark.asyncio
async def test_v210_spine_on_partner_checkin():
    """SpineOrchestrator.on_partner_checkin creates state after 3 check-ins."""
    spine = SpineOrchestrator(redis_client=FakeRedis())

    for i in range(3):
        result = await spine.on_partner_checkin(
            user_id="u1", partner_id="p1", checkin_type="celebration",
        )
    assert result is not None
    assert result["total_checkins"] == 3

    # State should exist in StateRegister
    state = await spine.state_register.get_state("u1", "partner_accountability_active")
    assert state is not None
    assert "3" in state.value


# ============================================================
# P2-8: Quota/cooldown system upgrade
# ============================================================


@pytest.mark.asyncio
async def test_v210_quota_check_allowed_initial():
    """First directive of any type is always allowed."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    result = await svc.check_allowed("u1", "notification")
    assert result["allowed"] is True
    assert result["quota_remaining"] > 0


@pytest.mark.asyncio
async def test_v210_quota_hourly_limit():
    """Directive is blocked after hourly quota exceeded."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    # notification quota = 4
    for i in range(4):
        await svc.record_emission("u1", "notification")

    result = await svc.check_allowed("u1", "notification")
    assert result["allowed"] is False
    assert result["reason"] == "hourly_quota_exceeded"


@pytest.mark.asyncio
async def test_v210_quota_cooldown_blocks():
    """Cooldown prevents rapid re-emission."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    await svc.record_emission("u1", "notification")
    result = await svc.check_allowed("u1", "notification")
    assert result["allowed"] is False
    assert result["reason"] == "cooldown_active"


@pytest.mark.asyncio
async def test_v210_quota_response_no_cooldown():
    """Response type has no cooldown (cooldown = 0)."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    await svc.record_emission("u1", "response")
    result = await svc.check_allowed("u1", "response")
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_v210_quota_get_status():
    """get_status returns status for all directive types."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    await svc.record_emission("u1", "notification")
    await svc.record_emission("u1", "execution")

    status = await svc.get_status("u1")
    assert "notification" in status
    assert status["notification"]["used"] == 1
    assert status["execution"]["used"] == 1
    assert "response" in status


@pytest.mark.asyncio
async def test_v210_quota_independent_per_type():
    """Each directive type has independent quota."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    # Fill notification quota
    for i in range(4):
        await svc.record_emission("u1", "notification")

    # Execution should still be allowed
    result = await svc.check_allowed("u1", "execution")
    assert result["allowed"] is True


# ============================================================
# P3-1: Core Session closure + phase transition hooks
# ============================================================


@pytest.mark.asyncio
async def test_v210_session_get_or_create():
    """get_or_create_active returns existing or creates new."""
    from app.signals.core_session import CoreSessionManager
    redis = FakeRedis()
    mgr = CoreSessionManager(redis)

    s1 = await mgr.get_or_create_active("u1", goal_id="g1")
    assert s1.phase == "modeling"

    s2 = await mgr.get_or_create_active("u1")
    assert s2.session_id == s1.session_id


@pytest.mark.asyncio
async def test_v210_session_phase_transition_validation():
    """Invalid phase transitions raise ValueError."""
    from app.signals.core_session import CoreSessionManager
    redis = FakeRedis()
    mgr = CoreSessionManager(redis)

    session = await mgr.create_session("u1")
    with pytest.raises(ValueError, match="invalid transition"):
        await mgr.advance_phase(session.session_id, "executing")  # modeling → executing not allowed


@pytest.mark.asyncio
async def test_v210_session_valid_transitions():
    """Valid phase transitions work: modeling → planning → executing → reflecting → completed."""
    from app.signals.core_session import CoreSessionManager
    redis = FakeRedis()
    mgr = CoreSessionManager(redis)

    session = await mgr.create_session("u1")
    s = await mgr.advance_phase(session.session_id, "planning")
    assert s.phase == "planning"
    s = await mgr.advance_phase(session.session_id, "executing")
    assert s.phase == "executing"
    s = await mgr.advance_phase(session.session_id, "reflecting")
    assert s.phase == "reflecting"
    s = await mgr.advance_phase(session.session_id, "completed")
    assert s.phase == "completed"


@pytest.mark.asyncio
async def test_v210_session_complete_with_summary():
    """complete_with_summary returns lifecycle metrics."""
    from app.signals.core_session import CoreSessionManager
    redis = FakeRedis()
    mgr = CoreSessionManager(redis)

    session = await mgr.create_session("u1", goal_id="g1")
    await mgr.advance_phase(session.session_id, "planning")
    await mgr.advance_phase(session.session_id, "executing")
    for _ in range(3):
        await mgr.record_task(session.session_id, completed=True)
    await mgr.record_task(session.session_id, completed=False)

    summary = await mgr.complete_with_summary(session.session_id)
    assert summary["completed_tasks"] == 3
    assert summary["total_tasks"] == 4
    assert summary["completion_rate"] == 0.75


@pytest.mark.asyncio
async def test_v210_session_summary_persistence():
    """Session summary can be retrieved after completion."""
    from app.signals.core_session import CoreSessionManager
    redis = FakeRedis()
    mgr = CoreSessionManager(redis)

    session = await mgr.create_session("u1")
    await mgr.complete_with_summary(session.session_id)

    retrieved = await mgr.get_session_summary(session.session_id)
    assert retrieved is not None
    assert retrieved["session_id"] == session.session_id


# ============================================================
# P3-2: Multi-message queue
# ============================================================


@pytest.mark.asyncio
async def test_v210_agenda_save_and_get():
    """Agenda persists and can be retrieved."""
    from app.signals.agenda_queue import AgendaQueueService
    from app.signals.types import AuroraAgenda, AuroraAgendaItem, _uid
    redis = FakeRedis()
    svc = AgendaQueueService(redis)

    agenda = AuroraAgenda(
        session_id="sess_1",
        scope="test agenda",
        agenda_items=[
            AuroraAgendaItem(item_id=_uid("ai"), item_type="confirm_available_time", status="pending"),
        ],
    )
    await svc.save_agenda("u1", agenda)

    loaded = await svc.get_agenda("sess_1")
    assert loaded is not None
    assert len(loaded.agenda_items) == 1


@pytest.mark.asyncio
async def test_v210_agenda_pending_items():
    """get_pending_items returns items needing user interaction."""
    from app.signals.agenda_queue import AgendaQueueService
    from app.signals.types import AuroraAgenda, AuroraAgendaItem, _uid
    redis = FakeRedis()
    svc = AgendaQueueService(redis)

    agenda = AuroraAgenda(
        session_id="sess_2",
        scope="pending test",
        agenda_items=[
            AuroraAgendaItem(item_id=_uid("ai"), item_type="confirm_available_time", status="pending"),
            AuroraAgendaItem(item_id=_uid("ai"), item_type="motivation_check", status="done"),
        ],
    )
    await svc.save_agenda("u1", agenda)

    pending = await svc.get_pending_items("u1")
    assert len(pending) == 1
    assert pending[0]["item"]["item_type"] == "confirm_available_time"


@pytest.mark.asyncio
async def test_v210_agenda_add_item():
    """add_item_to_agenda adds a new pending item."""
    from app.signals.agenda_queue import AgendaQueueService
    from app.signals.types import AuroraAgenda
    redis = FakeRedis()
    svc = AgendaQueueService(redis)

    agenda = AuroraAgenda(session_id="sess_3", scope="add test")
    await svc.save_agenda("u1", agenda)

    item = await svc.add_item_to_agenda("u1", "sess_3", "relationship_check", {"reason": "test"})
    assert item is not None
    assert item.item_type == "relationship_check"
    assert item.status == "pending"


# ============================================================
# P3-3: L4 Async Deep Learning
# ============================================================


@pytest.mark.asyncio
async def test_v210_deep_learner_accumulate():
    """Signal accumulation works without triggering below threshold."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    result = await learner.accumulate_signal("u1", {"state_key": "test"})
    assert result["triggered"] is False
    assert result["accumulated_count"] == 1


@pytest.mark.asyncio
async def test_v210_deep_learner_trigger_on_diversity():
    """Deep learning triggers when diverse signals accumulate."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    # Add 10 signals with 5+ unique keys
    for i in range(10):
        key = f"key_{i % 6}"
        result = await learner.accumulate_signal("u1", {"state_key": key})

    assert result["triggered"] is True


@pytest.mark.asyncio
async def test_v210_deep_learner_pop_and_analyze():
    """Pop task and run analysis on accumulated signals."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    # Trigger a task with fresh user
    for i in range(12):
        result = await learner.accumulate_signal("u_pop_test", {"state_key": f"k{i % 6}"})

    assert result["triggered"] is True
    task = await learner.pop_task()
    assert task is not None
    assert task["user_id"] == "u_pop_test"

    # Analyze patterns — use data that creates persistent issues
    signals = [{"state_key": f"k{i % 2}"} for i in range(12)]
    analysis = learner.analyze_signal_patterns(signals)
    assert analysis["total_signals"] == 12
    assert len(analysis["patterns"]) > 0  # persistent_issue detected


@pytest.mark.asyncio
async def test_v210_deep_learner_store_result():
    """Deep learning results can be stored and retrieved."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    result = {"patterns": [{"type": "persistent_issue"}], "recommendations": []}
    await learner.store_result("u1", result)

    retrieved = await learner.get_result("u1")
    assert retrieved is not None
    assert retrieved["patterns"][0]["type"] == "persistent_issue"


# ============================================================
# P3-4: Strategy Marketplace
# ============================================================


@pytest.mark.asyncio
async def test_v210_marketplace_publish_and_get():
    """Strategy can be published and retrieved."""
    from app.signals.strategy_marketplace import StrategyMarketplace
    redis = FakeRedis()
    mp = StrategyMarketplace(redis)

    entry = await mp.publish_strategy(
        "recover_execution_rhythm",
        source_user_id="u1",
        effectiveness=0.85,
        evidence_count=12,
        goal_type="exam_prep",
        subject="数学",
    )
    assert entry["effectiveness"] == 0.85
    assert entry["source_user_id"] != "u1"  # anonymized

    retrieved = await mp.get_strategy("recover_execution_rhythm")
    assert retrieved is not None
    assert retrieved["evidence_count"] == 12


@pytest.mark.asyncio
async def test_v210_marketplace_find_recommendations():
    """Recommendations filtered by effectiveness and goal type."""
    from app.signals.strategy_marketplace import StrategyMarketplace
    redis = FakeRedis()
    mp = StrategyMarketplace(redis)

    await mp.publish_strategy("s1", source_user_id="u1", effectiveness=0.9, evidence_count=10, goal_type="exam_prep")
    await mp.publish_strategy("s2", source_user_id="u2", effectiveness=0.6, evidence_count=5, goal_type="exam_prep")
    await mp.publish_strategy("s3", source_user_id="u3", effectiveness=0.85, evidence_count=8, goal_type="fitness")

    recs = await mp.find_recommendations(goal_type="exam_prep", min_effectiveness=0.7)
    assert len(recs) == 1
    assert recs[0]["strategy_key"] == "s1"


@pytest.mark.asyncio
async def test_v210_marketplace_cache_recommendations():
    """Recommendations can be cached and retrieved for a user."""
    from app.signals.strategy_marketplace import StrategyMarketplace
    redis = FakeRedis()
    mp = StrategyMarketplace(redis)

    recs = [{"strategy_key": "s1", "effectiveness": 0.9}]
    await mp.store_recommendations("u1", recs)

    cached = await mp.get_cached_recommendations("u1")
    assert len(cached) == 1
    assert cached[0]["strategy_key"] == "s1"


# ============================================================
# P2-5: Full Aurora Core Session v1
# ============================================================


@pytest.mark.asyncio
async def test_v210_aurora_case_file_build():
    """AuroraCaseFile is built with correct structure from context."""
    from app.signals.aurora_core_session import AuroraCoreSessionService
    svc = AuroraCoreSessionService(FakeRedis())

    case = svc.build_case_file(
        "u1",
        goal_summary="7天计网先过",
        current_plan_summary="第3天 TCP 拥塞控制",
        wake_reason="consecutive_strategy_failure",
        active_states=[
            {"state_key": "task_granularity_fit", "value": "too_large"},
            {"state_key": "knowledge_bottleneck", "value": "tcp_window_transfer"},
        ],
        recent_outcomes=[
            {"attribution": "insufficient", "strategy": "shrink_duration"},
        ],
    )
    assert case.user_id == "u1"
    assert len(case.active_hypotheses) == 2
    assert len(case.conflicts_to_resolve) == 1
    assert "可能不是太大" in case.conflicts_to_resolve[0]


@pytest.mark.asyncio
async def test_v210_aurora_agenda_from_case_file():
    """Agenda is generated with 5 standard items."""
    from app.signals.aurora_core_session import AuroraCoreSessionService
    svc = AuroraCoreSessionService(FakeRedis())

    case = svc.build_case_file("u1", goal_summary="test", current_plan_summary="", wake_reason="test")
    agenda = svc.build_agenda_from_case_file(case)

    # Without conflicts: enter + ask + apply + close = 4
    assert len(agenda.agenda_items) >= 4
    types = [item.item_type for item in agenda.agenda_items]
    assert "enter_session" in types
    assert "ask_confirmation" in types
    assert "close_session" in types


@pytest.mark.asyncio
async def test_v210_aurora_reply_options_have_free_text():
    """Predicted reply options always include a free-text entry."""
    from app.signals.aurora_core_session import AuroraCoreSessionService
    svc = AuroraCoreSessionService(FakeRedis())

    options = svc.build_reply_options("确实是这样")
    assert len(options) >= 2
    assert any(o.is_free_text for o in options)


@pytest.mark.asyncio
async def test_v210_aurora_session_create_and_get():
    """Session is created and can be retrieved."""
    from app.signals.aurora_core_session import AuroraCoreSessionService
    redis = FakeRedis()
    svc = AuroraCoreSessionService(redis)

    case = svc.build_case_file("u1", goal_summary="test", current_plan_summary="", wake_reason="test")
    agenda = svc.build_agenda_from_case_file(case)

    session = await svc.create_session("u1", case, agenda)
    assert session["status"] == "active"

    loaded = await svc.get_session(agenda.session_id)
    assert loaded is not None
    assert loaded["user_id"] == "u1"


@pytest.mark.asyncio
async def test_v210_aurora_session_record_reply():
    """Recording a reply advances the agenda."""
    from app.signals.aurora_core_session import AuroraCoreSessionService
    redis = FakeRedis()
    svc = AuroraCoreSessionService(redis)

    case = svc.build_case_file("u1", goal_summary="test", current_plan_summary="", wake_reason="test")
    agenda = svc.build_agenda_from_case_file(case)
    await svc.create_session("u1", case, agenda)

    result = await svc.record_reply(agenda.session_id, 0, "好的")
    assert result is not None
    items = result["agenda"]["agenda_items"]
    assert items[0]["status"] == "done"
    assert items[1]["status"] == "waiting_user"


@pytest.mark.asyncio
async def test_v210_aurora_session_close():
    """Closing a session stores closure and clears active pointer."""
    from app.signals.aurora_core_session import AuroraCoreSessionService, SessionClosure, StatePatch
    redis = FakeRedis()
    svc = AuroraCoreSessionService(redis)

    case = svc.build_case_file("u1", goal_summary="test", current_plan_summary="", wake_reason="test")
    agenda = svc.build_agenda_from_case_file(case)
    await svc.create_session("u1", case, agenda)

    closure = SessionClosure(
        session_id=agenda.session_id,
        state_patches=[StatePatch("task_granularity_fit", "too_large", "knowledge_bottleneck", "用户反馈", 0.8)],
        user_visible_summary="我把判断从任务太大改成题型迁移失败。",
    )
    result = await svc.close_session(agenda.session_id, closure)
    assert result["status"] == "completed"
    assert len(result["closure"]["state_patches"]) == 1

    # Active session should be cleared
    active = await svc.get_active_session("u1")
    assert active is None


@pytest.mark.asyncio
async def test_v210_spine_start_aurora_core_session():
    """SpineOrchestrator can start an Aurora Core Session."""
    spine = SpineOrchestrator(redis_client=FakeRedis())

    result = await spine.start_aurora_core_session(
        user_id="u1",
        goal_summary="7天计网先过",
        current_plan_summary="第3天 TCP",
        wake_reason="consecutive_strategy_failure",
    )
    assert result is not None
    assert result["status"] == "active"
    assert "case_file" in result
    assert "agenda" in result


@pytest.mark.asyncio
async def test_v210_spine_close_aurora_session():
    """SpineOrchestrator closes Aurora session and applies state patches."""
    spine = SpineOrchestrator(redis_client=FakeRedis())

    session = await spine.start_aurora_core_session(
        user_id="u1",
        goal_summary="test",
        current_plan_summary="",
        wake_reason="test",
    )
    session_id = session["agenda"]["session_id"]

    result = await spine.close_aurora_session(
        session_id,
        state_patches=[{"state_key": "test_key", "old_value": "old", "new_value": "new", "reason": "calibration", "confidence": 0.8}],
        user_summary="已更新判断",
    )
    assert result is not None
    assert result["status"] == "completed"

    # State should be in StateRegister
    state = await spine.state_register.get_state("u1", "test_key")
    assert state is not None
    assert state.value == "new"


# ============================================================
# D4: RelationshipModel hybrid FSM + continuous dimensions
# ============================================================


@pytest.mark.asyncio
async def test_v210_relationship_stance_starts_new():
    """New user starts with stance=new."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    state = await svc.get_or_create("u_new")
    assert state.stance == "new"
    assert state.directness_tolerance == 0.5


@pytest.mark.asyncio
async def test_v210_relationship_stance_transitions_to_calibrating():
    """After 3+ interactions with decent trust, stance becomes calibrating."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    for _ in range(4):
        await svc.update_from_interaction("u1", "confirmed")

    state = await svc.get_or_create("u1")
    assert state.stance == "calibrating"
    assert state.trust_in_strategy > 0.5


@pytest.mark.asyncio
async def test_v210_relationship_stance_becomes_trusted():
    """High trust + low corrections → trusted stance."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    for _ in range(15):
        await svc.update_from_interaction("u1", "confirmed")

    state = await svc.get_or_create("u1")
    assert state.stance == "trusted"
    assert state.trust_level >= 0.7


@pytest.mark.asyncio
async def test_v210_relationship_stance_becomes_strained():
    """High correction frequency → strained stance."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    # 5 corrections gives correction_frequency >= 3 but won't hit cooldown
    for _ in range(5):
        await svc.update_from_interaction("u1", "corrected")

    state = await svc.get_or_create("u1")
    assert state.stance in ("strained", "cooldown")  # FSM may transition further


@pytest.mark.asyncio
async def test_v210_relationship_dimensions_update():
    """Continuous dimensions update correctly from interactions."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    # Corrections increase explanation_need and pressure_sensitivity
    await svc.update_from_interaction("u_dim", "corrected")
    state = await svc.get_or_create("u_dim")
    assert state.explanation_need > 0.5
    assert state.pressure_sensitivity > 0.5

    # Confirmations increase trust_in_strategy and directness_tolerance
    await svc.update_from_interaction("u_dim2", "confirmed")
    state = await svc.get_or_create("u_dim2")
    assert state.trust_in_strategy > 0.5
    assert state.directness_tolerance > 0.5


@pytest.mark.asyncio
async def test_v210_relationship_strategy_adjustment_by_stance():
    """Strategy adjustment uses FSM stance for richer output."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    # New user → gentle_exploratory
    adj = await svc.get_strategy_adjustment("u1")
    assert adj["stance"] == "new"
    assert adj["tone_adjustment"] == "gentle_exploratory"
    assert adj["requires_confirmation"] is True
    assert "directness_tolerance" in adj
    assert "pressure_sensitivity" in adj


@pytest.mark.asyncio
async def test_v210_relationship_dimension_persistence():
    """Continuous dimensions persist across get_or_create calls."""
    from app.signals.relationship_model import RelationshipModelService
    redis = FakeRedis()
    svc = RelationshipModelService(redis)

    await svc.update_from_interaction("u1", "corrected")
    state = await svc.get_or_create("u1")
    saved_need = state.explanation_need

    reloaded = await svc.get_or_create("u1")
    assert abs(reloaded.explanation_need - saved_need) < 0.001


# ── D10: Per-Scenario Quota Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_v211_aurora_quota_normal_user_initiated():
    """D10: Normal scenario allows 1 user-initiated Aurora session per day."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    result = await svc.check_aurora_session_allowed("u1", "normal", "user_initiated")
    assert result["allowed"] is True
    assert result["daily_quota"] == 1

    # Consume the quota
    await svc.record_aurora_session("u1", "normal", "user_initiated")

    # Now blocked
    result2 = await svc.check_aurora_session_allowed("u1", "normal", "user_initiated")
    assert result2["allowed"] is False
    assert result2["reason"] == "daily_quota_exceeded"


@pytest.mark.asyncio
async def test_v211_aurora_quota_sprint_allows_2():
    """D10: Sprint scenario allows 2 user-initiated sessions per day."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    result1 = await svc.check_aurora_session_allowed("u1", "sprint", "user_initiated")
    assert result1["allowed"] is True

    await svc.record_aurora_session("u1", "sprint", "user_initiated")

    result2 = await svc.check_aurora_session_allowed("u1", "sprint", "user_initiated")
    assert result2["allowed"] is True

    await svc.record_aurora_session("u1", "sprint", "user_initiated")

    result3 = await svc.check_aurora_session_allowed("u1", "sprint", "user_initiated")
    assert result3["allowed"] is False


@pytest.mark.asyncio
async def test_v211_aurora_quota_crisis_allows_3():
    """D10: Crisis scenario allows 3 user-initiated sessions per day."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    for i in range(3):
        result = await svc.check_aurora_session_allowed("u1", "crisis", "user_initiated")
        assert result["allowed"] is True, f"iteration {i} should be allowed"
        await svc.record_aurora_session("u1", "crisis", "user_initiated")

    result4 = await svc.check_aurora_session_allowed("u1", "crisis", "user_initiated")
    assert result4["allowed"] is False


@pytest.mark.asyncio
async def test_v211_aurora_quota_quick_calibration_unlimited():
    """D10: Quick calibration is always unlimited (lightweight)."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    for _ in range(10):
        result = await svc.check_aurora_session_allowed("u1", "normal", "quick_calibration")
        assert result["allowed"] is True
        assert result["reason"] == "quick_calibration_unlimited"


@pytest.mark.asyncio
async def test_v211_aurora_quota_technical_failure_no_consume():
    """D10: Technical failures don't consume quota."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    await svc.record_aurora_session("u1", "normal", "user_initiated", was_technical_failure=True)

    result = await svc.check_aurora_session_allowed("u1", "normal", "user_initiated")
    assert result["allowed"] is True
    assert result["daily_used"] == 0


@pytest.mark.asyncio
async def test_v211_aurora_quota_crisis_system_override():
    """D10: Crisis mode system-initiated gets override flag but still has limits."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    result = await svc.check_aurora_session_allowed("u1", "crisis", "system_initiated")
    assert result["allowed"] is True
    assert result["requires_wake_reason"] is True


@pytest.mark.asyncio
async def test_v211_aurora_quota_status():
    """D10: get_aurora_quota_status returns all scenarios."""
    from app.signals.directive_quota import DirectiveQuotaService
    redis = FakeRedis()
    svc = DirectiveQuotaService(redis)

    await svc.record_aurora_session("u1", "sprint", "user_initiated")
    status = await svc.get_aurora_quota_status("u1")

    assert "normal" in status
    assert "sprint" in status
    assert "crisis" in status
    assert status["sprint"]["user_initiated"]["daily_used"] == 1
    assert status["normal"]["user_initiated"]["daily_used"] == 0


# ── L4: 6 Async Deep Learning Jobs Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_v212_daily_goal_reflection():
    """L4 Job 1: DailyGoalReflection produces bottleneck + focus."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    signals = [
        {"state_key": "knowledge_bottleneck", "claim": "stuck_on_tcp"},
        {"state_key": "knowledge_bottleneck", "claim": "stuck_on_tcp"},
        {"state_key": "knowledge_bottleneck", "claim": "stuck_on_tcp"},
        {"state_key": "task_granularity_fit", "claim": "too_large"},
    ]
    outcomes = [
        {"attribution": "insufficient"},
        {"attribution": "insufficient"},
        {"attribution": "sufficient"},
    ]

    candidate = await learner.run_daily_goal_reflection("u1", signals, outcomes)

    assert candidate["job_type"] == "daily_goal_reflection"
    assert candidate["user_visible"] is True
    assert candidate["output"]["yesterday_bottleneck"] == "knowledge_bottleneck"
    assert candidate["output"]["strategy_correction_needed"] is True
    assert candidate["confidence"] > 0
    assert "evidence" in candidate


@pytest.mark.asyncio
async def test_v212_policy_effect_compaction():
    """L4 Job 2: PolicyEffectCompaction compresses ledger → beliefs."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    ledger = [
        {"strategy": "worked_example", "outcome": "positive"},
        {"strategy": "worked_example", "outcome": "positive"},
        {"strategy": "worked_example", "outcome": "positive"},
        {"strategy": "full_review", "outcome": "negative"},
        {"strategy": "full_review", "outcome": "negative"},
    ]

    candidate = await learner.run_policy_effect_compaction("u1", ledger)

    assert candidate["job_type"] == "policy_effect_compaction"
    beliefs = candidate["output"]["strategy_beliefs"]
    assert len(beliefs) == 2
    we_belief = next(b for b in beliefs if b["strategy"] == "worked_example")
    assert we_belief["belief_strength"] > 0
    assert candidate["user_visible"] is False


@pytest.mark.asyncio
async def test_v212_skill_candidate():
    """L4 Job 3: SkillCandidate extracts repeated effective strategies."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    history = [
        {"strategy": "worked_example_practice", "outcome": "positive"},
        {"strategy": "worked_example_practice", "outcome": "positive"},
        {"strategy": "worked_example_practice", "outcome": "positive"},
        {"strategy": "failed_strategy", "outcome": "negative"},
    ]

    candidate = await learner.run_skill_candidate("u1", history)

    assert candidate["job_type"] == "skill_candidate"
    skills = candidate["output"]["skill_candidates"]
    assert len(skills) == 1
    assert skills[0]["strategy"] == "worked_example_practice"
    assert skills[0]["success_rate"] >= 0.6
    assert skills[0]["skill_type"] == "practice_oriented"


@pytest.mark.asyncio
async def test_v212_source_effectiveness():
    """L4 Job 4: SourceEffectiveness tags materials by context."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    interactions = [
        {"source_id": "ch3_slides", "outcome": "positive", "context": "concept_compression"},
        {"source_id": "ch3_slides", "outcome": "positive", "context": "concept_compression"},
        {"source_id": "past_exam", "outcome": "positive", "context": "worked_example"},
        {"source_id": "past_exam", "outcome": "positive", "context": "worked_example"},
        {"source_id": "full_textbook", "outcome": "negative", "context": "exam_eve"},
        {"source_id": "full_textbook", "outcome": "negative", "context": "exam_eve"},
    ]

    candidate = await learner.run_source_effectiveness("u1", interactions)

    assert candidate["job_type"] == "source_effectiveness"
    effs = candidate["output"]["source_effectiveness"]
    assert len(effs) == 3
    ch3 = next(e for e in effs if e["source_id"] == "ch3_slides")
    assert ch3["effectiveness_tag"] == "effective"
    assert ch3["best_context"] == "concept_compression"


@pytest.mark.asyncio
async def test_v212_community_aggregation():
    """L4 Job 5: CommunityAggregation produces anonymous common errors."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    signals = [
        {"error_pattern": "tcp_window_confusion", "resource_id": "ch3", "rating": 3.0},
        {"error_pattern": "tcp_window_confusion", "resource_id": "ch3", "rating": 4.0},
        {"error_pattern": "tcp_window_confusion", "resource_id": "past_exam", "rating": 4.5},
        {"error_pattern": "subnet_mask_mistake", "resource_id": "ch4", "rating": 2.0},
        {"error_pattern": "subnet_mask_mistake", "resource_id": "ch4", "rating": 3.0},
    ]

    candidate = await learner.run_community_aggregation("u1", signals)

    assert candidate["job_type"] == "community_aggregation"
    errors = candidate["output"]["common_errors"]
    assert len(errors) == 2
    tcp = next(e for e in errors if e["pattern"] == "tcp_window_confusion")
    assert tcp["frequency"] >= 2
    res_qual = candidate["output"]["resource_quality"]
    assert len(res_qual) >= 1


@pytest.mark.asyncio
async def test_v212_state_decay_and_retraction():
    """L4 Job 6: StateDecayAndRetraction decays old states + finds counter-evidence."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    from datetime import UTC, datetime, timedelta
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    old_time = (datetime.now(UTC) - timedelta(hours=72)).isoformat()
    active_states = [
        {"state_key": "knowledge_bottleneck", "value": "tcp", "confidence": 0.8, "created_at": old_time},
        {"state_key": "task_granularity", "value": "too_large", "confidence": 0.6, "created_at": old_time},
    ]
    new_signals = [
        {"state_key": "knowledge_bottleneck", "claim": "not_tcp_actually_subnet"},
    ]

    candidate = await learner.run_state_decay_and_retraction("u1", active_states, new_signals)

    assert candidate["job_type"] == "state_decay_and_retraction"
    decayed = candidate["output"]["decayed_states"]
    assert len(decayed) == 2
    for d in decayed:
        assert d["new_confidence"] < d["old_confidence"]

    retractions = candidate["output"]["retractions"]
    assert len(retractions) == 1
    assert retractions[0]["state_key"] == "knowledge_bottleneck"


@pytest.mark.asyncio
async def test_v212_l4_candidate_stored_and_retrieved():
    """L4 candidates are stored in Redis and retrievable."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    await learner.run_daily_goal_reflection("u_stored", [{"state_key": "x", "claim": "y"}] * 5)

    candidate = await learner.get_candidate("u_stored", "daily_goal_reflection")
    assert candidate is not None
    assert candidate["job_type"] == "daily_goal_reflection"


@pytest.mark.asyncio
async def test_v212_l4_empty_input_returns_zero_confidence():
    """L4 jobs with empty input return zero-confidence empty candidates."""
    from app.signals.async_deep_learner import AsyncDeepLearner
    redis = FakeRedis()
    learner = AsyncDeepLearner(redis)

    candidate = await learner.run_policy_effect_compaction("u_empty", [])
    assert candidate["confidence"] == 0.0
    assert candidate["evidence"]["note"] == "insufficient_data"


# ── D3: Three-Layer ModelWrite Tests ──────────────────────────────────

def test_v213_model_write_entry_write_layer_hot():
    """D3: Scope turn/session/task/day maps to 'hot' (Redis)."""
    from app.signals.types import ModelWriteEntry
    for scope in ("turn", "session", "task", "day"):
        entry = ModelWriteEntry(
            target="state_register",
            scope=scope,
            claim="test",
            confidence=0.8,
        )
        assert entry.write_layer == "hot"


def test_v213_model_write_entry_write_layer_warm():
    """D3: Scope sprint/goal/domain/relationship maps to 'warm' (Postgres)."""
    from app.signals.types import ModelWriteEntry
    for scope in ("sprint", "goal", "domain", "relationship"):
        entry = ModelWriteEntry(
            target="goal_state",
            scope=scope,
            claim="test",
            confidence=0.7,
        )
        assert entry.write_layer == "warm"


def test_v213_model_write_entry_write_layer_cold():
    """D3: Scope long_term maps to 'cold' (GrowthChronicle)."""
    from app.signals.types import ModelWriteEntry
    entry = ModelWriteEntry(
        target="growth_chronicle_candidate",
        scope="long_term",
        claim="user shows consistent pattern",
        confidence=0.6,
        evidence=["30-day streak", "consistent correction pattern"],
        counter_evidence=["one week of inactivity"],
        requires_user_confirmation=True,
        retract_if=["no_activity_14_days"],
    )
    assert entry.write_layer == "cold"
    assert entry.requires_user_confirmation is True


def test_v213_model_write_entry_serialization():
    """D3: ModelWriteEntry serializes with write_layer and D3 fields."""
    from app.signals.types import ModelWriteEntry
    entry = ModelWriteEntry(
        target="sparkle_self_model",
        scope="relationship",
        claim="trust improved after 5 consecutive completions",
        confidence=0.75,
        evidence=["5 task completions", "2 streak maintained"],
        counter_evidence=["1 correction last week"],
        requires_user_confirmation=False,
        retract_if=["correction_frequency_above_3"],
        ttl="30d",
    )
    d = entry.to_dict()
    assert d["write_layer"] == "warm"
    assert d["target"] == "sparkle_self_model"
    assert len(d["evidence"]) == 2
    assert len(d["counter_evidence"]) == 1
    assert d["retract_if"] == ["correction_frequency_above_3"]


def test_v213_model_write_entry_backwards_compat():
    """D3: Old target_model field still works via backwards compat."""
    from app.signals.types import ModelWriteEntry
    entry = ModelWriteEntry(
        target_model="user_state",
        claim="test claim",
        scope="turn",
        confidence=0.5,
        needs_user_confirmation=True,
    )
    assert entry.target == "user_state"
    assert entry.requires_user_confirmation is True
    d = entry.to_dict()
    assert d["target_model"] == "user_state"
    assert d["write_layer"] == "hot"


def test_v213_model_write_entry_roundtrip():
    """D3: ModelWriteEntry round-trips through dict serialization."""
    from app.signals.types import ModelWriteEntry
    original = ModelWriteEntry(
        target="learning_base",
        scope="domain",
        claim="calculus mastery improving",
        confidence=0.65,
        evidence=["3 consecutive good scores"],
        counter_evidence=[],
        requires_user_confirmation=False,
        retract_if=["score_below_50"],
        ttl="14d",
    )
    d = original.to_dict()
    restored = ModelWriteEntry.from_dict(d)
    assert restored.target == original.target
    assert restored.scope == original.scope
    assert restored.claim == original.claim
    assert restored.confidence == original.confidence
    assert restored.write_layer == "warm"


# ── P2-C: Aurora Core Policy/Directive Regeneration Tests ─────────────

@pytest.mark.asyncio
async def test_v214_aurora_close_regenerates_directives():
    """P2-C: Closing Aurora session regenerates directives for patched states."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    redis = FakeRedis()
    orch = SpineOrchestrator(redis)

    # Create an Aurora session first
    await orch.aurora_core.create_session(
        user_id="u1",
        case_file=orch.aurora_core.build_case_file(
            "u1", goal_summary="test", current_plan_summary="plan", wake_reason="test",
        ),
        agenda=orch.aurora_core.build_agenda_from_case_file(
            orch.aurora_core.build_case_file(
                "u1", goal_summary="test", current_plan_summary="plan", wake_reason="test",
            ),
        ),
    )
    session_id = orch.aurora_core.build_agenda_from_case_file(
        orch.aurora_core.build_case_file(
            "u1", goal_summary="test", current_plan_summary="plan", wake_reason="test",
        ),
    ).session_id

    # Set up state that the patch will modify
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["e1"],
        source_system="test",
        state_key="task_granularity_fit",
        claim="too_large",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="test",
        possible_effects=["strategy_change"],
        priority="high",
    )
    await orch.state_register.upsert_from_signal("u1", signal)

    # Create session properly
    case_file = orch.aurora_core.build_case_file(
        "u1", goal_summary="test", current_plan_summary="plan", wake_reason="calibration",
    )
    agenda = orch.aurora_core.build_agenda_from_case_file(case_file)
    await orch.aurora_core.create_session("u1", case_file, agenda)

    # Close with state patches
    result = await orch.close_aurora_session(
        agenda.session_id,
        state_patches=[{
            "state_key": "task_granularity_fit",
            "old_value": "too_large",
            "new_value": "appropriate",
            "reason": "user confirmed tasks are right size",
            "confidence": 0.9,
        }],
        policy_changes=[{
            "signal_state_key": "task_granularity_fit",
            "old_strategy": "recover_execution_rhythm",
            "new_strategy": "maintain_pace",
            "reason": "calibration corrected",
        }],
        user_summary="我更新了对任务大小的判断。",
    )

    assert result is not None
    assert "error" not in result
    # Check that directive regeneration was attempted
    assert "regenerated_directives" in result


@pytest.mark.asyncio
async def test_v214_aurora_close_applies_state_patches():
    """P2-C: State patches from Aurora closure update the state register."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    redis = FakeRedis()
    orch = SpineOrchestrator(redis)

    case_file = orch.aurora_core.build_case_file(
        "u2", goal_summary="calculus exam", current_plan_summary="7 day sprint", wake_reason="conflict",
    )
    agenda = orch.aurora_core.build_agenda_from_case_file(case_file)
    await orch.aurora_core.create_session("u2", case_file, agenda)

    result = await orch.close_aurora_session(
        agenda.session_id,
        state_patches=[
            {
                "state_key": "knowledge_bottleneck",
                "old_value": "tcp_window",
                "new_value": "subnet_masking",
                "reason": "user clarified actual weak point",
                "confidence": 0.85,
            },
        ],
        user_summary="校准完成。",
    )

    # Verify state was updated in register
    active_states = await orch.state_register.get_active_states("u2")
    state_map = {s.state_key: s for s in active_states}
    assert "knowledge_bottleneck" in state_map
    assert state_map["knowledge_bottleneck"].value == "subnet_masking"


# ── P3-1: GoalWorldGraph Node Type Generalization Tests ──────────────

@pytest.mark.asyncio
async def test_v215_graph_node_knowledge_type():
    """P3-1: KnowledgeNode tracks mastery (default, backward compat)."""
    from app.signals.goal_world_graph import GoalWorldGraphService, GraphNode
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u1",
        goal_id="exam",
        goal_type="exam_sprint",
        node_specs=[
            {"node_id": "tcp", "label": "TCP", "node_type": "knowledge"},
            {"node_id": "ip", "label": "IP", "node_type": "knowledge"},
        ],
    )
    assert len(graph.nodes) == 2
    assert graph.nodes[0].node_type == "knowledge"
    assert graph.nodes[0].tracks_mastery is True


@pytest.mark.asyncio
async def test_v215_graph_node_artifact_binary():
    """P3-1: ArtifactNode is binary (done/not-done)."""
    from app.signals.goal_world_graph import GoalWorldGraphService
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u2",
        goal_id="job",
        goal_type="job_search",
        node_specs=[
            {"node_id": "resume", "label": "简历", "node_type": "artifact"},
            {"node_id": "portfolio", "label": "作品集", "node_type": "artifact"},
        ],
    )

    # Update to 0.4 → not done yet
    graph = await svc.update_node_mastery("u2", "job", "resume", 0.4)
    assert graph is not None
    resume = next(n for n in graph.nodes if n.node_id == "resume")
    assert resume.status == "pending"
    assert resume.mastery == 0.0

    # Update to 0.7 → done
    graph = await svc.update_node_mastery("u2", "job", "resume", 0.7)
    resume = next(n for n in graph.nodes if n.node_id == "resume")
    assert resume.status == "done"
    assert resume.mastery == 1.0


@pytest.mark.asyncio
async def test_v215_graph_node_capability_tracks_mastery():
    """P3-1: CapabilityNode tracks mastery like knowledge."""
    from app.signals.goal_world_graph import GoalWorldGraphService
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u3",
        goal_id="project",
        goal_type="project_delivery",
        node_specs=[
            {"node_id": "sysdesign", "label": "系统设计能力", "node_type": "capability"},
        ],
    )

    graph = await svc.update_node_mastery("u3", "project", "sysdesign", 0.85)
    cap = graph.nodes[0]
    assert cap.status == "mastered"
    assert cap.mastery == 0.85
    assert cap.tracks_mastery is True


@pytest.mark.asyncio
async def test_v215_graph_node_risk_informational():
    """P3-1: RiskNode is informational (no mastery tracking)."""
    from app.signals.goal_world_graph import GraphNode
    node = GraphNode(node_id="r1", label="范围膨胀", node_type="risk")
    assert node.is_informational is True
    assert node.tracks_mastery is False
    assert node.is_binary is False


@pytest.mark.asyncio
async def test_v215_graph_mixed_node_types():
    """P3-1: GoalWorldGraph with mixed node types (job search example)."""
    from app.signals.goal_world_graph import GoalWorldGraphService
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u4",
        goal_id="job_interview",
        goal_type="job_search_interview",
        node_specs=[
            {"node_id": "sysdesign_cap", "label": "系统设计表达", "node_type": "capability"},
            {"node_id": "resume_art", "label": "简历", "node_type": "artifact"},
            {"node_id": "mock_ms", "label": "模拟面试", "node_type": "milestone"},
            {"node_id": "scatter_risk", "label": "回答太散", "node_type": "risk"},
            {"node_id": "interviewer_fb", "label": "面试官反馈", "node_type": "feedback"},
        ],
    )

    assert len(graph.nodes) == 5
    types = {n.node_type for n in graph.nodes}
    assert types == {"capability", "artifact", "milestone", "risk", "feedback"}


@pytest.mark.asyncio
async def test_v215_graph_suggest_includes_node_type():
    """P3-1: Focus suggestions include node_type field."""
    from app.signals.goal_world_graph import GoalWorldGraphService
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u5",
        goal_id="proj",
        goal_type="project_delivery",
        node_specs=[
            {"node_id": "mvp", "label": "MVP 原型", "node_type": "artifact"},
            {"node_id": "test_ms", "label": "用户测试", "node_type": "milestone", "dependency_ids": ["mvp"]},
            {"node_id": "scope_risk", "label": "范围膨胀", "node_type": "risk"},
        ],
    )

    suggestions = svc.suggest_focus_nodes(graph)
    assert len(suggestions) >= 1
    assert "node_type" in suggestions[0]


@pytest.mark.asyncio
async def test_v215_graph_backward_compat_no_type():
    """P3-1: GraphNode without node_type defaults to knowledge (backward compat)."""
    from app.signals.goal_world_graph import GraphNode
    node = GraphNode(node_id="old_1", label="Old style node")
    assert node.node_type == "knowledge"
    assert node.tracks_mastery is True


@pytest.mark.asyncio
async def test_v215_graph_project_delivery_example():
    """P3-1: Project delivery example from ruling."""
    from app.signals.goal_world_graph import GoalWorldGraphService
    redis = FakeRedis()
    svc = GoalWorldGraphService(redis)

    graph = await svc.create_graph(
        user_id="u6",
        goal_id="proj_deliver",
        goal_type="project_delivery",
        node_specs=[
            {"node_id": "mvp", "label": "MVP 原型", "node_type": "artifact"},
            {"node_id": "user_test", "label": "用户测试", "node_type": "milestone", "dependency_ids": ["mvp"]},
            {"node_id": "scope_bloat", "label": "范围膨胀", "node_type": "risk"},
            {"node_id": "two_weeks", "label": "两周 deadline", "node_type": "constraint"},
        ],
    )

    # Complete MVP → user_test becomes unblocked
    graph = await svc.update_node_mastery("u6", "proj_deliver", "mvp", 1.0)
    user_test = next(n for n in graph.nodes if n.node_id == "user_test")
    assert user_test.status != "blocked"

    suggestions = svc.suggest_focus_nodes(graph)
    # Should suggest user_test since MVP is done
    suggested_ids = [s["node_id"] for s in suggestions]
    assert "user_test" in suggested_ids


# ── P3-2: DomainPack System Tests ────────────────────────────────────

def test_v216_exam_sprint_pack_node_schema():
    """P3-2: Exam sprint pack requires knowledge nodes."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("exam_sprint")
    assert pack.domain == "exam_sprint"
    required_types = [e.node_type for e in pack.node_schema if e.required]
    assert "knowledge" in required_types
    assert len(pack.feedback_taxonomy) >= 3
    assert len(pack.risk_patterns) >= 3
    assert len(pack.checkpoint_rules) >= 2
    assert len(pack.aurora_trigger_rules) >= 2


def test_v216_job_search_pack_schema():
    """P3-2: Job search pack has capability + artifact nodes."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("job_search_interview")
    assert pack.domain == "job_search_interview"
    required = [e.node_type for e in pack.node_schema if e.required]
    assert "capability" in required
    assert "artifact" in required
    assert "feedback" in required
    assert pack.supported_goal_modes == ["interview_sprint", "resume_refinement", "portfolio_building"]


def test_v216_project_delivery_pack():
    """P3-2: Project delivery pack has artifact + milestone + risk."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("project_delivery")
    required = [e.node_type for e in pack.node_schema if e.required]
    assert "artifact" in required
    assert "milestone" in required
    assert "risk" in required


def test_v216_domain_pack_serialization():
    """P3-2: DomainPack serializes to dict with all fields."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("exam_sprint")
    d = pack.to_dict()
    assert "domain_pack_id" in d
    assert "node_schema" in d
    assert "feedback_taxonomy" in d
    assert "risk_patterns" in d
    assert "checkpoint_rules" in d
    assert "aurora_trigger_rules" in d
    assert "skill_library" in d
    assert "source_types" in d
    assert "outcome_metrics" in d
    assert len(d["node_schema"]) > 0


def test_v216_domain_pack_fallback():
    """P3-2: Unknown goal type falls back to exam_sprint."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("unknown_goal")
    assert pack.domain == "exam_sprint"


def test_v216_list_domain_packs():
    """P3-2: list_domain_packs returns 3 unique packs."""
    from app.signals.domain_pack import list_domain_packs
    packs = list_domain_packs()
    assert len(packs) == 3
    domains = {p.domain for p in packs}
    assert domains == {"exam_sprint", "job_search_interview", "project_delivery"}


def test_v216_get_node_schema_for_goal():
    """P3-2: get_node_schema_for_goal returns required types."""
    from app.signals.domain_pack import get_node_schema_for_goal
    exam_types = get_node_schema_for_goal("exam_sprint")
    assert "knowledge" in exam_types

    job_types = get_node_schema_for_goal("job_search_interview")
    assert "capability" in job_types
    assert "artifact" in job_types


def test_v216_goal_mode_aliases():
    """P3-2: Goal mode aliases map to correct pack."""
    from app.signals.domain_pack import get_domain_pack
    assert get_domain_pack("exam_rescue").domain == "exam_sprint"
    assert get_domain_pack("interview_sprint").domain == "job_search_interview"
    assert get_domain_pack("mvp_sprint").domain == "project_delivery"
    assert get_domain_pack("resume_refinement").domain == "job_search_interview"


def test_v216_aurora_trigger_rules():
    """P3-2: Aurora trigger rules have proper structure."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("exam_sprint")
    for rule in pack.aurora_trigger_rules:
        assert rule.condition
        assert rule.trigger_id
        d = rule.to_dict()
        assert "condition" in d
        assert "quota_override" in d


def test_v216_risk_patterns():
    """P3-2: Risk patterns have detection signals and mitigations."""
    from app.signals.domain_pack import get_domain_pack
    pack = get_domain_pack("project_delivery")
    for risk in pack.risk_patterns:
        assert risk.detection_signal
        assert risk.mitigation_strategy
        assert risk.severity in ("low", "medium", "high")


# ── P3-3: MultiGoal Arbitration + CausalTrace Tests ───────────────────

@pytest.mark.asyncio
async def test_v217_arbitrate_goals_writes_causal_trace():
    """P3-3: Goal arbitration with conflicts writes to CausalTrace."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    redis = FakeRedis()
    orch = SpineOrchestrator(redis)

    # Register two competing goals
    await orch.register_goal("u1", "exam", "exam_sprint", "计网考试", deadline_days=2, mastery=0.3)
    await orch.register_goal("u1", "resume", "job_search", "简历投递", deadline_days=5, mastery=0.5)

    result = await orch.arbitrate_goals("u1")
    assert result is not None
    assert result.primary_goal_id == "exam"
    assert result.reason == "deadline_urgent"

    # Check CausalTrace was written
    traces = await orch.trace_store.get_user_traces("u1", limit=5)
    assert len(traces) >= 1
    last_trace = traces[-1]
    assert "multi_goal_arbitration" in last_trace.signal_ids


@pytest.mark.asyncio
async def test_v217_arbitrate_single_goal_no_trace():
    """P3-3: Single goal arbitration doesn't create trace (no conflict)."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    redis = FakeRedis()
    orch = SpineOrchestrator(redis)

    await orch.register_goal("u2", "exam", "exam_sprint", "计网考试", deadline_days=5)

    result = await orch.arbitrate_goals("u2")
    assert result is not None
    assert result.primary_goal_id == "exam"
    assert result.conflicts == []

    # No trace with arbitration for single goal
    traces = await orch.trace_store.get_user_traces("u2", limit=5)
    arbitration_traces = [t for t in traces if "multi_goal_arbitration" in t.signal_ids]
    assert len(arbitration_traces) == 0


# ── P3-4: Long-term Growth Chronicle Tests ────────────────────────────

@pytest.mark.asyncio
async def test_v218_chronicle_entry_has_p34_fields():
    """P3-4: ChronicleEntry has claim, scope, confidence, user_status."""
    from app.signals.growth_chronicle import ChronicleEntry
    entry = ChronicleEntry(
        entry_id="ce_1",
        user_id="u1",
        entry_type="pattern_discovered",
        timestamp="2026-04-27T00:00:00Z",
        title="短任务更适合高压",
        narrative="在deadline高压下，25-40分钟任务更容易启动",
        evidence_refs=["tcp_sprint_short_high_rate", "long_task_timeout_2x"],
        user_editable=True,
        claim="在 deadline 高压下，25-40 分钟任务比 90 分钟任务更容易启动",
        scope="exam_sprint_context",
        confidence=0.72,
        user_status="pending",
        recommended_future_use=["deadline_sprint_planning", "task_granularity"],
        retract_if=["short_task_completion_rate_drops_below_50percent"],
    )
    assert entry.claim != ""
    assert entry.scope == "exam_sprint_context"
    assert entry.user_status == "pending"
    assert not entry.is_confirmed


@pytest.mark.asyncio
async def test_v218_chronicle_confirm_entry():
    """P3-4: User can confirm a chronicle entry."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
    redis = FakeRedis()
    svc = GrowthChronicleService(redis)

    entry = ChronicleEntry(
        entry_id="ce_confirm",
        user_id="u2",
        entry_type="pattern_discovered",
        timestamp="2026-04-27T00:00:00Z",
        title="测试确认",
        narrative="test",
        evidence_refs=[],
        user_editable=True,
        claim="test claim",
        scope="general",
        confidence=0.6,
        user_status="pending",
    )
    await svc.add_entry("u2", entry)

    result = await svc.confirm_entry("u2", "ce_confirm")
    assert result is True

    entries = await svc.get_chronicle("u2")
    assert entries[0].user_status == "confirmed"
    assert entries[0].is_confirmed is True


@pytest.mark.asyncio
async def test_v218_chronicle_reject_entry():
    """P3-4: User can reject a chronicle entry (hidden)."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
    redis = FakeRedis()
    svc = GrowthChronicleService(redis)

    entry = ChronicleEntry(
        entry_id="ce_reject",
        user_id="u3",
        entry_type="pattern_discovered",
        timestamp="2026-04-27T00:00:00Z",
        title="测试拒绝",
        narrative="test",
        evidence_refs=[],
        user_editable=True,
        user_status="pending",
    )
    await svc.add_entry("u3", entry)

    result = await svc.reject_entry("u3", "ce_reject")
    assert result is True

    # Rejected entries are hidden, so won't appear in get_chronicle
    entries = await svc.get_chronicle("u3")
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_v218_chronicle_get_confirmed_only():
    """P3-4: get_confirmed_entries returns only confirmed entries."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
    redis = FakeRedis()
    svc = GrowthChronicleService(redis)

    confirmed = ChronicleEntry(
        entry_id="ce_c1", user_id="u4", entry_type="milestone",
        timestamp="2026-04-27T00:00:00Z", title="C1", narrative="c1",
        evidence_refs=[], user_editable=True, user_status="confirmed",
    )
    pending = ChronicleEntry(
        entry_id="ce_p1", user_id="u4", entry_type="pattern_discovered",
        timestamp="2026-04-27T00:00:00Z", title="P1", narrative="p1",
        evidence_refs=[], user_editable=True, user_status="pending",
    )
    await svc.add_entry("u4", confirmed)
    await svc.add_entry("u4", pending)

    confirmed_entries = await svc.get_confirmed_entries("u4")
    assert len(confirmed_entries) == 1
    assert confirmed_entries[0].entry_id == "ce_c1"


@pytest.mark.asyncio
async def test_v218_chronicle_build_return_case_file():
    """P3-4: build_return_case_file generates summary for returning users."""
    from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
    redis = FakeRedis()
    svc = GrowthChronicleService(redis)

    entry = ChronicleEntry(
        entry_id="ce_rcf", user_id="u5", entry_type="pattern_discovered",
        timestamp="2026-04-27T00:00:00Z", title="短任务更适合", narrative="test",
        evidence_refs=["e1"], user_editable=True,
        claim="短任务更适合高压", scope="exam_sprint", confidence=0.7,
        user_status="confirmed", recommended_future_use=["task_granularity"],
    )
    await svc.add_entry("u5", entry)

    case_file = await svc.build_return_case_file("u5")
    assert case_file["user_id"] == "u5"
    assert case_file["chronicle_summary"]["confirmed_count"] == 1
    assert len(case_file["confirmed_insights"]) == 1
    assert case_file["confirmed_insights"][0]["claim"] == "短任务更适合高压"


# ══════════════════════════════════════════════════════════════════════════════
# P3-5: Generalized Task Protocol
# ══════════════════════════════════════════════════════════════════════════════

def test_p3_5_task_card_protocol_study():
    """TaskCardProtocol for study type binds to knowledge/capability nodes."""
    from app.signals.task_card_protocol import TaskCardBuilder
    from app.signals.types import WhyThisTask

    why = WhyThisTask(
        signal_ids=["sig_1"], policy_decision_id="pd_1",
        bottleneck_node_id="cn.tcp", reasoning_summary="learning gap",
    )
    card = TaskCardBuilder.for_study(
        goal_id="g1", bound_nodes=["cn.tcp", "cn.tcp.congestion"],
        why=why, steps=["Read material", "Take notes"],
    )
    assert card.task_type == "study"
    assert card.goal_id == "g1"
    assert "cn.tcp" in card.bound_nodes
    assert card.is_knowledge_task()
    assert not card.is_artifact_task()
    d = card.to_dict()
    rt = type(card).from_dict(d)
    assert rt.task_type == "study"
    assert rt.why_this_task.bottleneck_node_id == "cn.tcp"


def test_p3_5_task_card_protocol_practice():
    """TaskCardProtocol for practice type."""
    from app.signals.task_card_protocol import TaskCardBuilder

    card = TaskCardBuilder.for_practice(goal_id="g1", bound_nodes=["cn.tcp.cwnd"])
    assert card.task_type == "practice"
    assert card.stuck_protocol.aurora_wake_on_stuck
    assert "capability_mastery" in card.updates_after_completion


def test_p3_5_task_card_protocol_artifact_build():
    """TaskCardProtocol for artifact_build requires minimum_output."""
    from app.signals.task_card_protocol import TaskCardBuilder

    card = TaskCardBuilder.for_artifact_build(
        goal_id="g2", bound_nodes=["proj.mvp"],
        minimum_output="Working login page",
    )
    assert card.task_type == "artifact_build"
    assert card.minimum_output == "Working login page"
    assert not card.is_knowledge_task()
    assert card.is_artifact_task()
    assert "artifact_status" in card.updates_after_completion


def test_p3_5_task_card_protocol_habit():
    """TaskCardProtocol for habit_action doesn't load materials."""
    from app.signals.task_card_protocol import TaskCardBuilder

    card = TaskCardBuilder.for_habit_action(goal_id="g3", bound_nodes=["habit.morning"])
    assert card.task_type == "habit_action"
    assert card.materials_protocol.retrieval_mode == "none"
    assert card.is_habit_task()
    assert "habit_streak" in card.updates_after_completion


def test_p3_5_task_card_protocol_all_types():
    """All 6 task types construct correctly."""
    from app.signals.task_card_protocol import TaskCardBuilder
    from app.signals.types import TASK_TYPES

    builders = {
        "study": TaskCardBuilder.for_study,
        "practice": TaskCardBuilder.for_practice,
        "artifact_build": TaskCardBuilder.for_artifact_build,
        "habit_action": TaskCardBuilder.for_habit_action,
        "review": TaskCardBuilder.for_review,
        "feedback_collection": TaskCardBuilder.for_feedback_collection,
    }
    for ttype, builder in builders.items():
        card = builder(goal_id="g", bound_nodes=["n1"])
        assert card.task_type == ttype, f"{ttype} mismatch"
        assert ttype in TASK_TYPES


def test_p3_5_task_card_validator():
    """Validator catches missing fields."""
    from app.signals.task_card_protocol import TaskCardBuilder, TaskCardValidator
    from app.signals.types import TaskCardProtocol

    # Valid card
    card = TaskCardBuilder.for_study(goal_id="g1", bound_nodes=["n1"])
    issues = TaskCardValidator.validate(card)
    assert len(issues) == 0

    # Invalid: no goal_id
    bad = TaskCardProtocol(task_id="t1", task_type="study")
    issues = TaskCardValidator.validate(bad)
    assert any("goal_id" in i for i in issues)

    # Invalid task_type is caught by __post_init__, not validator
    with pytest.raises(ValueError, match="task_type"):
        TaskCardProtocol(task_id="t2", goal_id="g1", task_type="invalid_type")


def test_p3_5_task_card_from_goal_type():
    """from_goal_type selects correct builder per domain."""
    from app.signals.task_card_protocol import TaskCardBuilder

    exam_card = TaskCardBuilder.from_goal_type("exam_sprint", goal_id="g1", bound_nodes=["n1"])
    assert exam_card.task_type == "study"

    job_card = TaskCardBuilder.from_goal_type("job_search_interview", goal_id="g2", bound_nodes=["n2"])
    assert job_card.task_type == "practice"

    project_card = TaskCardBuilder.from_goal_type("project_delivery", goal_id="g3", bound_nodes=["n3"])
    assert project_card.task_type == "artifact_build"


def test_p3_5_outcome_fields_for_type():
    """outcome_fields_for_type returns correct state keys per task type."""
    from app.signals.task_card_protocol import TaskCardValidator

    assert "knowledge_mastery" in TaskCardValidator.outcome_fields_for_type("study")
    assert "capability_mastery" in TaskCardValidator.outcome_fields_for_type("practice")
    assert "artifact_status" in TaskCardValidator.outcome_fields_for_type("artifact_build")
    assert "habit_streak" in TaskCardValidator.outcome_fields_for_type("habit_action")
    assert "knowledge_retention" in TaskCardValidator.outcome_fields_for_type("review")
    assert "feedback_data" in TaskCardValidator.outcome_fields_for_type("feedback_collection")


def test_p3_5_binds_to_node_type():
    """TaskCardProtocol.binds_to_node_type validates node-type compatibility."""
    from app.signals.task_card_protocol import TaskCardBuilder

    study_card = TaskCardBuilder.for_study(goal_id="g1", bound_nodes=["n1"])
    assert study_card.binds_to_node_type("knowledge")
    assert study_card.binds_to_node_type("capability")
    assert not study_card.binds_to_node_type("habit")

    artifact_card = TaskCardBuilder.for_artifact_build(goal_id="g2", bound_nodes=["n2"])
    assert artifact_card.binds_to_node_type("artifact")
    assert not artifact_card.binds_to_node_type("knowledge")


# ══════════════════════════════════════════════════════════════════════════════
# P3-6: External Integration v1
# ══════════════════════════════════════════════════════════════════════════════

def test_p3_6_external_raw_event_required():
    """All external events must become ExternalRawEvent before Spine."""
    from app.signals.external_integration import ExternalRawEvent

    evt = ExternalRawEvent(
        event_id="evt_cal_1", source="calendar", source_detail="google_calendar",
        goal_id="g1", raw_payload={"action": "deadline_detected", "hours_until": 48},
    )
    assert evt.source == "calendar"
    assert evt.user_visible
    assert evt.revocable
    d = evt.to_dict()
    rt = ExternalRawEvent.from_dict(d)
    assert rt.event_id == "evt_cal_1"
    assert rt.raw_payload["hours_until"] == 48


def test_p3_6_file_integration():
    """File uploads are converted to ExternalRawEvents."""
    from app.signals.external_integration import FileIntegration, FileReference

    fref = FileReference(
        file_id="f1", file_name="ch4_transport.pdf", source="upload",
        mime_type="application/pdf", goal_id="g1", parsed_summary="传输层课件",
    )
    handler = FileIntegration()
    evt = handler.on_file_received(fref)
    assert evt.source == "file"
    assert evt.raw_payload["file_name"] == "ch4_transport.pdf"

    # Undiagnosed detection
    undiag = handler.detect_undiagnosed_materials(
        [fref], diagnosed_file_ids={"other_file"},
    )
    assert len(undiag) == 1
    assert undiag[0].file_id == "f1"

    # File context
    ctx = handler.build_file_context([fref], goal_id="g1")
    assert ctx["total_files"] == 1
    assert ctx["undiagnosed_count"] == 0  # parsed_summary is set


def test_p3_6_email_deadline_extractor():
    """Email subjects with deadline keywords produce ExternalRawEvents."""
    from app.signals.external_integration import EmailDeadlineExtractor

    extractor = EmailDeadlineExtractor()
    hint = extractor.extract_from_subject(
        email_id="em1", subject="明天计网期中考试", goal_id="g1",
    )
    assert hint is not None
    assert "考试" in hint.extracted_keywords or any("exam" in kw.lower() for kw in hint.extracted_keywords)
    assert hint.confidence >= 0.3

    evt = extractor.to_external_event(hint)
    assert evt.source == "email"
    assert evt.user_visible

    # No deadline keywords → None
    no_hint = extractor.extract_from_subject(
        email_id="em2", subject="今天天气不错", goal_id="g1",
    )
    assert no_hint is None

    # Batch extraction
    hints = extractor.batch_extract([
        {"email_id": "em3", "subject": "Final exam schedule", "goal_id": "g2"},
        {"email_id": "em4", "subject": "Lunch meeting"},
    ])
    assert len(hints) == 1


def test_p3_6_github_repo_bridge():
    """GitHub activity summaries become ExternalRawEvents."""
    from app.signals.external_integration import GitHubRepoBridge, GitHubRepoSummary

    repo = GitHubRepoSummary(
        repo_id="r1", repo_name="sparkle-app", owner="team",
        recent_commits=12, open_prs=3, open_issues=7,
        last_activity="2026-04-27T10:00:00Z", goal_id="g3",
    )
    bridge = GitHubRepoBridge()
    evt = bridge.summarize_repo(repo)
    assert evt.source == "github"
    assert evt.raw_payload["recent_commits"] == 12

    # Project velocity
    velocity = bridge.detect_project_velocity([repo])
    assert velocity["total_commits"] == 12
    assert not velocity["has_stalled"]

    stale_repo = GitHubRepoSummary(
        repo_id="r2", repo_name="stale-project", owner="team",
        recent_commits=0, open_prs=0, open_issues=0, goal_id="g3",
    )
    velocity2 = bridge.detect_project_velocity([stale_repo])
    assert velocity2["has_stalled"]


def test_p3_6_external_integration_gateway():
    """Gateway enforces all events route through Spine."""
    from app.signals.external_integration import (
        ExternalIntegrationGateway, ExternalRawEvent,
    )

    gw = ExternalIntegrationGateway()

    # Register integration
    iid = gw.register_integration("u1", "calendar", "google_calendar", goal_id="g1")
    assert iid
    assert gw.is_connected(iid)

    # Route event
    evt = ExternalRawEvent(
        event_id="evt_99", source="calendar", source_detail="google_calendar",
        goal_id="g1", raw_payload={"action": "test"},
    )
    receipt = gw.route_to_spine(evt)
    assert receipt["event_type"] == "external_raw_event"
    assert receipt["source"] == "calendar"

    # Disconnect
    assert gw.disconnect_integration(iid)
    assert not gw.is_connected(iid)

    # List active
    gw.register_integration("u1", "email", "gmail", goal_id="g1")
    active = gw.list_active_integrations("u1")
    assert len(active) == 1  # only the second one is active

    # Unknown source still routes (with warning)
    unknown = ExternalRawEvent(
        event_id="evt_100", source="slack", source_detail="slack_workspace",
        goal_id="g1",
    )
    receipt2 = gw.route_to_spine(unknown)
    assert receipt2["event_type"] == "external_raw_event"


# ─── P4-4: Research-grade Experiment Platform ───────────────────────────────

def test_p4_4_experiment_creation():
    from app.signals.research_experiment_platform import MultivariateExperimentEngine
    exp = MultivariateExperimentEngine.create_experiment(
        name="worked_example_first",
        hypothesis="Starting with worked examples reduces task abandonment",
        variants=[
            {"name": "control", "description": "current default", "policy_params": {}},
            {"name": "worked_first", "description": "worked example first", "policy_params": {"task_type": "worked_example"}},
        ],
        min_samples=10,
    )
    assert exp.experiment_name == "worked_example_first"
    assert len(exp.variants) == 2
    assert exp.min_samples_per_variant == 10
    assert exp.status == "draft"


def test_p4_4_record_and_analyze():
    from app.signals.research_experiment_platform import MultivariateExperimentEngine
    exp = MultivariateExperimentEngine.create_experiment(
        name="short_task_test",
        hypothesis="Shorter tasks improve completion",
        variants=[
            {"name": "control", "policy_params": {"max_duration": 45}},
            {"name": "short", "policy_params": {"max_duration": 25}},
        ],
        min_samples=5,
    )
    v_control = exp.variants[0].variant_id
    v_short = exp.variants[1].variant_id

    # Record outcomes: short wins
    for _ in range(6):
        MultivariateExperimentEngine.record_outcome(exp, v_control, success=False)
        MultivariateExperimentEngine.record_outcome(exp, v_short, success=True)

    conclusion = MultivariateExperimentEngine.analyze(exp)
    assert conclusion.winning_variant_id == v_short
    assert conclusion.is_conclusive is True
    assert "outperforms" in conclusion.recommendation


def test_p4_4_segment_matching():
    from app.signals.research_experiment_platform import UserSegment
    seg = UserSegment(
        segment_id="seg_1",
        segment_name="exam_sprint_high_activity",
        criteria={"goal_type": "exam_sprint", "activity_level": "high"},
    )
    assert seg.matches({"goal_type": "exam_sprint", "activity_level": "high"})
    assert not seg.matches({"goal_type": "exam_sprint", "activity_level": "low"})
    assert not seg.matches({"goal_type": "project_delivery"})


def test_p4_4_insufficient_samples_not_conclusive():
    from app.signals.research_experiment_platform import MultivariateExperimentEngine
    exp = MultivariateExperimentEngine.create_experiment(
        name="small_test",
        hypothesis="X outperforms Y",
        variants=[
            {"name": "A", "policy_params": {}},
            {"name": "B", "policy_params": {}},
        ],
        min_samples=30,
    )
    # Only 2 outcomes — not enough
    MultivariateExperimentEngine.record_outcome(exp, exp.variants[0].variant_id, success=True)
    MultivariateExperimentEngine.record_outcome(exp, exp.variants[1].variant_id, success=False)

    conclusion = MultivariateExperimentEngine.analyze(exp)
    assert conclusion.is_conclusive is False
    assert conclusion.winning_variant_id is None


# ─── P4-5: Privacy-Preserving Community Intelligence ────────────────────────

def test_p4_5_privacy_budget_spend_and_exhaust():
    from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine
    engine = PrivacyPreservingCommunityEngine()
    budget = engine.get_or_create_budget("user_1", epsilon=1.0, max_epsilon=0.3)
    # With max_epsilon=0.3 and default query cost=0.1, can answer 3 times
    assert engine.check_privacy_budget("user_1", "cohort_lookup")  # cost=0.05
    budget.spend(0.15)
    budget.spend(0.15)
    # Now spent 0.3 → exhausted
    assert not budget.can_answer(0.1)


def test_p4_5_cohort_privacy_tiers():
    from app.signals.privacy_community_intelligence import (
        PrivacyPreservingCommunityEngine,
        PrivacyPreservingCohort,
    )
    engine = PrivacyPreservingCommunityEngine()

    # < 5 → suppressed
    cohort_tiny = engine.create_cohort({"goal_type": "exam_sprint"}, member_count=3)
    assert cohort_tiny.privacy_tier == "suppressed"
    d = cohort_tiny.to_dict()
    assert d["stats"] == []  # suppressed: nothing shared

    # 5-14 → trend_only
    cohort_small = engine.create_cohort({"goal_type": "exam_sprint"}, member_count=10)
    assert cohort_small.privacy_tier == "trend_only"

    # 16+ → anonymous_aggregate
    cohort_large = engine.create_cohort({"goal_type": "exam_sprint"}, member_count=20)
    assert cohort_large.privacy_tier == "anonymous_aggregate"


def test_p4_5_anonymized_stat_suppresses_small_cohort():
    from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine
    engine = PrivacyPreservingCommunityEngine()
    # Cohort of 3 → stat suppressed
    stat = engine.compute_anonymized_stat("task_completion_rate", [0.8, 0.9, 0.7])
    assert stat.is_reliable is False
    assert stat.value == 0.0  # suppressed


def test_p4_5_anonymized_stat_large_cohort():
    from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine
    engine = PrivacyPreservingCommunityEngine()
    raw = [0.7, 0.8, 0.75, 0.9, 0.65, 0.85, 0.7, 0.8, 0.9, 0.72]
    stat = engine.compute_anonymized_stat("task_completion_rate", raw, epsilon=1.0)
    assert stat.is_reliable is True
    assert stat.cohort_size == 10
    # Value is noised with Laplace(scale=1) — wide plausible range
    assert -1.0 <= stat.value <= 3.0
    d = stat.to_dict()
    assert "noise_std" in d
    assert d["noise_std"] > 0


# ─── P4-6: Spine Quality Guard ──────────────────────────────────────────────

def test_p4_6_quality_guard_healthy_state():
    from app.signals.spine_quality_guard import SpineQualityGuard
    signal_history = [
        {"had_policy_decision": True, "had_directive": True},
        {"had_policy_decision": True, "had_directive": True},
        {"had_policy_decision": True, "had_directive": True},
    ]
    check = SpineQualityGuard.check_signal_actionability(signal_history, min_actionable_ratio=0.5)
    assert check.passed is True
    assert check.score == 1.0


def test_p4_6_quality_guard_orphan_signals():
    from app.signals.spine_quality_guard import SpineQualityGuard
    check = SpineQualityGuard.check_orphan_signal_buildup(orphan_count=5, total_signal_count=10, max_orphan_ratio=0.3)
    assert check.passed is False
    assert check.score == 0.5  # 1 - 0.5


def test_p4_6_quality_guard_chain_break():
    from app.signals.spine_quality_guard import SpineQualityGuard
    metrics = {
        "signals_generated": 100,
        "policies_evaluated": 40,   # <70% → chain break
        "directives_applied": 35,
    }
    check = SpineQualityGuard.check_chain_breaks(metrics)
    assert check.passed is False
    assert "Signal→Policy chain broken" in check.recommendations[0]


def test_p4_6_quality_guard_empty_data_graceful():
    from app.signals.spine_quality_guard import SpineQualityGuard
    check1 = SpineQualityGuard.check_signal_actionability([])
    assert check1.passed is True
    check2 = SpineQualityGuard.check_orphan_signal_buildup(0, 0)
    assert check2.passed is True
    check3 = SpineQualityGuard.check_causal_trace_completeness([])
    assert check3.passed is True


def test_p4_6_quality_report_full_healthy():
    from app.signals.spine_quality_guard import SpineQualityGuard
    report = SpineQualityGuard.generate_quality_report(
        signal_history=[
            {"had_policy_decision": True, "had_directive": True},
            {"had_policy_decision": True, "had_directive": True},
        ],
        traces=[{
            "signal_ids": ["s1"],
            "policy_decision_id": "pd1",
            "directive_ids": ["d1"],
            "audit_ids": ["a1"],
            "receipt_ids": ["r1"],
        }],
        audits=[{"applied": True}],
        metrics={"signals_generated": 10, "policies_evaluated": 9, "directives_applied": 8, "orphan_signal_count": 1},
        outcome_count=6,
        directive_count=8,
        outcomes=[{"attribution": "effective", "attribution_confidence": 0.8}],
    )
    assert report.health_status in ("healthy", "degraded")
    assert 0.0 <= report.overall_score <= 1.0
    assert len(report.checks) == 7  # 7 checks in generate_quality_report


def test_p4_6_degradation_detection():
    from app.signals.spine_quality_guard import SpineQualityGuard, QualityReport
    # Create declining reports
    reports = []
    for score in [0.9, 0.8, 0.7]:
        r = QualityReport(
            report_id=f"r_{score}",
            window_start="2026-04-27T00:00:00",
            window_end="2026-04-27T23:59:59",
            overall_score=score,
        )
        reports.append(r)

    result = SpineQualityGuard.detect_degradation(reports, window_count=3, degradation_threshold=0.05)
    assert result["degrading"] is True
    assert "Consistent decline" in result["reason"]


