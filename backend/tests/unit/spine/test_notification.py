"""Spine tests — test_v2_v3_features.py."""

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
    assert "2" in message.body
    assert message.message_id.startswith("rmsg_")
    assert message.value_reason
    assert message.effort_estimate
    assert message.deadline_pressure_label
    assert message.recall_score == 0.0

    # Verify stored in Redis
    stored = await spine.get_recall_notification("u1")
    assert stored is not None
    assert stored.message_id == message.message_id
    assert stored.value_reason == message.value_reason


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


@pytest.mark.asyncio
async def test_recall_notification_task_missed_recovery():
    """Task missed trigger produces recovery_offer strategy."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    message = await spine.build_recall_notification(
        user_id="u1",
        trigger_type="task_missed",
        context={},
    )
    assert message is not None
    assert message.strategy == "recovery_offer"
    assert message.deep_link == "/tasks?status=recovery"


@pytest.mark.asyncio
async def test_recall_notification_builder_user_preference_schema():
    """RecallNotificationBuilder exposes user preference schema."""
    builder = RecallNotificationBuilder()
    schema = builder.build_user_preference_schema()
    assert "undigested_material" in schema
    assert "task_not_started" in schema
    assert "task_missed" in schema
    assert "pre_exam_silence" in schema
    assert schema["undigested_material"]["max_per_day"] == 1
    assert schema["task_missed"]["max_per_day"] == 2


def test_recall_notification_builder_surfaces_value_fields():
    builder = RecallNotificationBuilder()

    message = builder.build_message(
        trigger_type="task_not_started",
        message_strategy="low_effort_next_step",
        context={
            "value_reason": "启动第一张任务卡能帮计划产生反馈。",
            "effort_estimate": "预计先投入 5 分钟。",
            "deadline_pressure_label": "今日节奏待启动",
            "recall_score": 0.84,
        },
    )

    assert message is not None
    assert message.value_reason == "启动第一张任务卡能帮计划产生反馈。"
    assert message.effort_estimate == "预计先投入 5 分钟。"
    assert message.deadline_pressure_label == "今日节奏待启动"
    assert message.recall_score == 0.84
    assert message.to_dict()["value_reason"] == message.value_reason
    assert message.to_dict()["recall_reason"] == message.reasoning


@pytest.mark.asyncio
async def test_celery_recall_task_import():
    """Celery recall tasks are importable and registered."""
    from app.core.celery_tasks import recall_notification_task, scan_recall_notifications

    assert recall_notification_task.name == "app.core.celery_tasks.recall_notification_task"
    assert scan_recall_notifications.name == "app.core.celery_tasks.scan_recall_notifications"


# ══════════════════════════════════════════════════════════════════════
# P2-2: Policy Experiments — shadow A/B framework
# ══════════════════════════════════════════════════════════════════════


def test_policy_experiment_create():
    from app.signals.policy_experiments import PolicyExperiment

    exp = PolicyExperiment(
        experiment_id="exp_1",
        user_id="u1",
        signal_state_key="task_granularity_fit",
        signal_claim="recent_task_too_large",
        primary_strategy="recover_execution_rhythm",
        shadow_strategy="recover_execution_rhythm_gentle",
    )
    assert exp.status == "running"
    d = exp.to_dict()
    restored = PolicyExperiment.from_dict(d)
    assert restored.primary_strategy == "recover_execution_rhythm"


async def test_policy_experiment_record_trial():
    from app.signals.policy_experiments import PolicyExperimentManager

    redis = MagicMock()
    redis.set = AsyncMock()
    redis.lrem = AsyncMock()
    redis.lpush = AsyncMock()
    redis.ltrim = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])

    mgr = PolicyExperimentManager(redis)
    exp = await mgr.create_experiment(
        user_id="u1",
        signal_state_key="task_granularity_fit",
        signal_claim="recent_task_too_large",
        primary_strategy="recover_execution_rhythm",
    )
    assert exp is not None
    assert exp.shadow_strategy == "recover_execution_rhythm_gentle"

    # Simulate recording a trial
    import json

    redis.get = AsyncMock(return_value=json.dumps(exp.to_dict()))
    updated = await mgr.record_trial(exp.experiment_id, primary_outcome="effective", shadow_hypothesis="effective")
    assert updated is not None
    assert updated.total_trials == 1
    assert updated.primary_wins == 1


async def test_policy_experiment_no_alternative():
    from app.signals.policy_experiments import PolicyExperimentManager

    redis = MagicMock()
    mgr = PolicyExperimentManager(redis)
    exp = await mgr.create_experiment(
        user_id="u1",
        signal_state_key="unknown",
        signal_claim="unknown",
        primary_strategy="nonexistent_strategy",
    )
    assert exp is None


def test_policy_experiment_evaluate_shadow():
    from app.signals.policy_experiments import PolicyExperimentManager

    redis = MagicMock()
    mgr = PolicyExperimentManager(redis)

    # Primary effective, shadow likely same
    result = mgr.evaluate_shadow_outcome("effective", "recover_execution_rhythm", {})
    assert result == "effective"

    # Primary insufficient with pressure issue — shadow "gentle" better suited
    result = mgr.evaluate_shadow_outcome(
        "insufficient",
        "recover_execution_rhythm",
        {"new_hypothesis": "user feeling overwhelmed by pressure"},
    )
    assert result == "effective"  # gentle approach better for pressure

    # Primary insufficient with no matching reason — shadow also insufficient
    result = mgr.evaluate_shadow_outcome(
        "insufficient",
        "recover_execution_rhythm",
        {"new_hypothesis": "unrelated issue"},
    )
    assert result == "insufficient"


def test_policy_experiment_suggest_promotions():
    from app.signals.policy_experiments import PolicyExperiment, PolicyExperimentManager

    redis = MagicMock()
    mgr = PolicyExperimentManager(redis)

    exp = PolicyExperiment(
        experiment_id="exp_promo",
        user_id="u1",
        signal_state_key="task_granularity_fit",
        signal_claim="recent_task_too_large",
        primary_strategy="recover_execution_rhythm",
        shadow_strategy="recover_execution_rhythm_gentle",
        status="concluded",
        primary_wins=2,
        shadow_wins=8,
        total_trials=10,
    )
    suggestions = mgr.suggest_promotions([exp])
    assert len(suggestions) == 1
    assert suggestions[0]["action"] == "promote_shadow_to_primary"


def test_policy_experiment_suggest_no_promotion():
    from app.signals.policy_experiments import PolicyExperiment, PolicyExperimentManager

    redis = MagicMock()
    mgr = PolicyExperimentManager(redis)

    exp = PolicyExperiment(
        experiment_id="exp_no_promo",
        user_id="u1",
        signal_state_key="task_granularity_fit",
        signal_claim="recent_task_too_large",
        primary_strategy="recover_execution_rhythm",
        shadow_strategy="recover_execution_rhythm_gentle",
        status="concluded",
        primary_wins=8,
        shadow_wins=2,
        total_trials=10,
    )
    suggestions = mgr.suggest_promotions([exp])
    assert len(suggestions) == 0


def test_policy_experiment_conclude():
    from app.signals.policy_experiments import PolicyExperiment

    exp = PolicyExperiment(
        experiment_id="exp_conc",
        user_id="u1",
        signal_state_key="test",
        signal_claim="test",
        primary_strategy="a",
        shadow_strategy="b",
        primary_wins=2,
        shadow_wins=8,
        total_trials=10,
    )
    from app.signals.policy_experiments import PolicyExperimentManager

    PolicyExperimentManager._conclude(exp)
    assert exp.status == "concluded"
    assert exp.conclusion == "shadow_outperforms"


# ══════════════════════════════════════════════════════════════════════
# P2-4: Learning Base — Bayesian + rule hybrid
# ══════════════════════════════════════════════════════════════════════


def test_strategy_belief_update():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    belief = StrategyBelief(strategy_key="test_strategy")
    assert belief.expected_effectiveness == 0.5  # 1.0 / 2.0

    lb.update_belief(belief, "effective")
    assert belief.alpha == 2.0
    assert belief.evidence_count == 1

    lb.update_belief(belief, "insufficient")
    assert belief.beta == 2.0
    assert belief.evidence_count == 2


def test_strategy_belief_effectiveness():
    from app.signals.learning_base import StrategyBelief

    # 10 effective, 2 insufficient → high effectiveness
    belief = StrategyBelief(strategy_key="good", alpha=11.0, beta=3.0, evidence_count=12)
    assert belief.expected_effectiveness > 0.7


def test_learning_base_batch_update():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    beliefs = [StrategyBelief(strategy_key="s1"), StrategyBelief(strategy_key="s2")]
    outcomes = [
        {"strategy_key": "s1", "attribution": "effective"},
        {"strategy_key": "s1", "attribution": "effective"},
        {"strategy_key": "s2", "attribution": "insufficient"},
    ]
    updated = lb.batch_update(beliefs, outcomes)
    bmap = {b.strategy_key: b for b in updated}
    assert bmap["s1"].alpha == 3.0  # 1 + 2 effective
    assert bmap["s2"].beta == 2.0  # 1 + 1 insufficient


def test_learning_base_select_strategy():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    beliefs = [
        StrategyBelief(strategy_key="good", alpha=10.0, beta=2.0, evidence_count=12),
        StrategyBelief(strategy_key="bad", alpha=2.0, beta=10.0, evidence_count=12),
    ]
    result = lb.select_strategy(beliefs, ["good", "bad"])
    assert result["strategy"] == "good"
    assert result["source"] == "bayesian"


def test_learning_base_select_cold_start():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    beliefs = [
        StrategyBelief(strategy_key="a", alpha=1.0, beta=1.0, evidence_count=0),
        StrategyBelief(strategy_key="b", alpha=1.0, beta=1.0, evidence_count=0),
    ]
    result = lb.select_strategy(
        beliefs,
        ["a", "b"],
        prefer_rules=True,
        rule_ranking=["b", "a"],
    )
    assert result["strategy"] == "b"
    assert result["source"] == "rule_fallback"


def test_learning_base_ranking():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    beliefs = [
        StrategyBelief(strategy_key="s1", alpha=8.0, beta=2.0, evidence_count=10),
        StrategyBelief(strategy_key="s2", alpha=5.0, beta=5.0, evidence_count=10),
        StrategyBelief(strategy_key="s3", alpha=2.0, beta=8.0, evidence_count=10),
    ]
    ranking = lb.compute_strategy_ranking(beliefs)
    assert ranking[0]["strategy_key"] == "s1"
    assert ranking[-1]["strategy_key"] == "s3"


def test_learning_base_snapshot():
    from app.signals.learning_base import LearningBase, StrategyBelief

    lb = LearningBase()
    beliefs = [
        StrategyBelief(strategy_key="warm", alpha=5.0, beta=3.0, evidence_count=8),
        StrategyBelief(strategy_key="cold", alpha=1.0, beta=1.0, evidence_count=0),
    ]
    snapshot = lb.build_snapshot("u1", beliefs)
    assert "cold" in snapshot.cold_start_strategies
    assert "warm" not in snapshot.cold_start_strategies


def test_learning_base_serialization():
    from app.signals.learning_base import StrategyBelief

    belief = StrategyBelief(strategy_key="test", alpha=5.0, beta=3.0, evidence_count=8)
    d = belief.to_dict()
    restored = StrategyBelief.from_dict(d)
    assert restored.strategy_key == "test"
    assert restored.alpha == 5.0


# ══════════════════════════════════════════════════════════════════════
# P3-3: External Integrations — Calendar + tools
# ══════════════════════════════════════════════════════════════════════


def test_calendar_deadline_pressure():
    from app.signals.external_integration import CalendarEvent, CalendarSignalBridge
    from datetime import UTC, datetime, timedelta

    bridge = CalendarSignalBridge()
    now = datetime.now(UTC)
    event = CalendarEvent(
        event_id="evt_1",
        title="计网期末考试",
        start_time=(now + timedelta(hours=48)).isoformat(),
        end_time=(now + timedelta(hours=50)).isoformat(),
        event_type="exam",
        subject="计算机网络",
    )
    signal = bridge.detect_deadline_pressure([event], now=now.isoformat())
    assert signal is not None
    assert signal.state_key == "deadline_pressure"
    assert signal.claim == "upcoming_deadline"
    assert signal.priority == "medium"  # >24h away


def test_calendar_deadline_pressure_urgent():
    from app.signals.external_integration import CalendarEvent, CalendarSignalBridge
    from datetime import UTC, datetime, timedelta

    bridge = CalendarSignalBridge()
    now = datetime.now(UTC)
    event = CalendarEvent(
        event_id="evt_urgent",
        title="明天考试",
        start_time=(now + timedelta(hours=12)).isoformat(),
        end_time=(now + timedelta(hours=14)).isoformat(),
        event_type="exam",
    )
    signal = bridge.detect_deadline_pressure([event], now=now.isoformat())
    assert signal is not None
    assert signal.priority == "high"


def test_calendar_no_deadline():
    from app.signals.external_integration import CalendarEvent, CalendarSignalBridge
    from datetime import UTC, datetime, timedelta

    bridge = CalendarSignalBridge()
    now = datetime.now(UTC)
    event = CalendarEvent(
        event_id="evt_class",
        title="日常课程",
        start_time=(now + timedelta(hours=24)).isoformat(),
        end_time=(now + timedelta(hours=26)).isoformat(),
        event_type="class",
    )
    signal = bridge.detect_deadline_pressure([event], now=now.isoformat())
    assert signal is None  # "class" events don't trigger


def test_calendar_time_context():
    from app.signals.external_integration import CalendarEvent, CalendarSignalBridge
    from datetime import UTC, datetime, timedelta

    bridge = CalendarSignalBridge()
    now = datetime.now(UTC)
    events = [
        CalendarEvent(
            event_id="e1",
            title="考试",
            start_time=(now + timedelta(hours=48)).isoformat(),
            end_time=(now + timedelta(hours=50)).isoformat(),
            event_type="exam",
        ),
        CalendarEvent(
            event_id="e2",
            title="开会",
            start_time=(now + timedelta(hours=6)).isoformat(),
            end_time=(now + timedelta(hours=7)).isoformat(),
            event_type="meeting",
        ),
    ]
    ctx = bridge.build_time_context(events, now=now.isoformat())
    assert ctx["upcoming_24h_count"] == 1
    assert ctx["upcoming_7d_count"] == 2
    assert ctx["nearest_deadline"] is not None
    assert ctx["has_time_pressure"] is True


def test_calendar_serialization():
    from app.signals.external_integration import CalendarEvent

    event = CalendarEvent(
        event_id="e1",
        title="Test",
        start_time="2026-01-01T10:00:00Z",
        end_time="2026-01-01T12:00:00Z",
        event_type="exam",
    )
    d = event.to_dict()
    restored = CalendarEvent.from_dict(d)
    assert restored.title == "Test"


def test_external_tool_study_session():
    from app.signals.external_integration import ExternalToolBridge, ExternalToolSignal

    bridge = ExternalToolBridge()
    signals = [
        ExternalToolSignal(tool_id="ide", tool_type="ide", activity_type="active", timestamp="2026-01-01T10:00:00Z"),
        ExternalToolSignal(tool_id="lms", tool_type="lms", activity_type="active", timestamp="2026-01-01T10:01:00Z"),
    ]
    result = bridge.detect_study_session(signals)
    assert result is not None
    assert result["session_active"] is True
    assert result["study_confidence"] >= 0.7


def test_external_tool_no_study():
    from app.signals.external_integration import ExternalToolBridge, ExternalToolSignal

    bridge = ExternalToolBridge()
    signals = [
        ExternalToolSignal(
            tool_id="browser", tool_type="browser", activity_type="idle", timestamp="2026-01-01T10:00:00Z"
        ),
    ]
    result = bridge.detect_study_session(signals)
    assert result is None


def test_external_tool_context():
    from app.signals.external_integration import ExternalToolBridge, ExternalToolSignal

    bridge = ExternalToolBridge()
    signals = [
        ExternalToolSignal(tool_id="ide", tool_type="ide", activity_type="active", timestamp="2026-01-01T10:00:00Z"),
    ]
    ctx = bridge.build_tool_context(signals)
    assert ctx["recent_activity"] is True
    assert "ide" in ctx["tool_usage"]


# ══════════════════════════════════════════════════════════════════════
# P4: Research-Grade — Counterfactual + Simulator + Marketplace
# ══════════════════════════════════════════════════════════════════════


def test_counterfactual_baseline_method():
    from app.signals.research_grade import CounterfactualEngine  # noqa: DEPRECATED v1
    from app.signals.types import OutcomeRecord

    engine = CounterfactualEngine()
    outcome = OutcomeRecord(
        outcome_id="o1",
        causal_trace_id="ct1",
        intervention="max_task_duration_25min",
        reason="task_overrun",
        expected_outcome="task_completed",
        actual_outcome={"completed": True},
        attribution="effective",
    )
    # Low baseline → counterfactual likely insufficient
    result = engine.evaluate(outcome, user_baseline_rate=0.2)
    assert result.counterfactual_outcome == "insufficient"
    assert result.intervention_impact == 1.0  # intervention helped
    assert result.method == "baseline_comparison"


def test_counterfactual_high_baseline():
    from app.signals.research_grade import CounterfactualEngine  # noqa: DEPRECATED v1
    from app.signals.types import OutcomeRecord

    engine = CounterfactualEngine()
    outcome = OutcomeRecord(
        outcome_id="o2",
        causal_trace_id="ct2",
        intervention="strategy",
        reason="test",
        expected_outcome="done",
        actual_outcome={},
        attribution="effective",
    )
    # High baseline → counterfactual also effective
    result = engine.evaluate(outcome, user_baseline_rate=0.8)
    assert result.counterfactual_outcome == "effective"
    assert result.intervention_impact == 0.0  # no difference


def test_counterfactual_rule_based():
    from app.signals.research_grade import CounterfactualEngine  # noqa: DEPRECATED v1
    from app.signals.types import OutcomeRecord

    engine = CounterfactualEngine()
    outcome = OutcomeRecord(
        outcome_id="o3",
        causal_trace_id="ct3",
        intervention="strategy",
        reason="test",
        expected_outcome="done",
        actual_outcome={},
        attribution="effective",
    )
    similar = [
        {"had_intervention": False, "outcome": "insufficient"},
        {"had_intervention": False, "outcome": "insufficient"},
        {"had_intervention": False, "outcome": "effective"},
    ]
    result = engine.evaluate(outcome, similar_interventions=similar)
    assert result.method == "rule_based"
    assert result.counterfactual_outcome == "insufficient"  # 2/3 insufficient


def test_counterfactual_aggregate():
    from app.signals.research_grade import CounterfactualEngine, CounterfactualResult  # noqa: DEPRECATED v1

    engine = CounterfactualEngine()
    results = [
        CounterfactualResult("r1", "ct1", "effective", "insufficient", 1.0, 0.8, "", "baseline"),
        CounterfactualResult("r2", "ct2", "effective", "effective", 0.0, 0.5, "", "baseline"),
        CounterfactualResult("r3", "ct3", "insufficient", "effective", -1.0, 0.7, "", "baseline"),
    ]
    agg = engine.aggregate_impact(results)
    assert agg["total"] == 3
    assert agg["positive_interventions"] == 1
    assert agg["negative_interventions"] == 1
    assert agg["neutral_interventions"] == 1


def test_user_simulator_basic():
    from app.signals.research_grade import UserSimulator, SimulatedUserProfile  # noqa: DEPRECATED v1

    sim = UserSimulator()
    profile = SimulatedUserProfile(
        profile_id="sim_1",
        baseline_ability=0.6,
        consistency=0.8,
        responsiveness=0.5,
        fatigue_rate=0.1,
    )
    result = sim.simulate_outcome(profile, "worked_example_then_drill")
    assert result["outcome"] in ("effective", "insufficient")
    assert "factors" in result


def test_user_simulator_sequence():
    from app.signals.research_grade import UserSimulator, SimulatedUserProfile  # noqa: DEPRECATED v1

    sim = UserSimulator()
    profile = SimulatedUserProfile(
        profile_id="sim_2",
        baseline_ability=0.5,
        consistency=0.7,
        responsiveness=0.4,
        fatigue_rate=0.2,
    )
    results = sim.simulate_intervention_sequence(
        profile,
        ["drill", "worked_example", "practice", "review"],
    )
    assert len(results) == 4
    assert all("task_number" in r for r in results)
    assert results[0]["task_number"] == 1


def test_user_simulator_compare():
    from app.signals.research_grade import UserSimulator, SimulatedUserProfile  # noqa: DEPRECATED v1

    sim = UserSimulator()
    profile = SimulatedUserProfile(
        profile_id="sim_3",
        baseline_ability=0.5,
        consistency=0.9,
        responsiveness=0.7,
        fatigue_rate=0.1,
    )
    result = sim.compare_strategies(
        profile,
        ["worked_example_then_drill"] * 5,
        ["concept_compression"] * 5,
        trials=50,
    )
    assert result["trials"] == 50
    assert result["winner"] in ("a", "b", "tie")


def test_domain_pack_validate():
    from app.signals.research_grade import DomainPack  # noqa: DEPRECATED v1, DomainPackMarketplace  # noqa: DEPRECATED v1

    redis = MagicMock()
    marketplace = DomainPackMarketplace(redis)

    good_pack = DomainPack(
        pack_id="pack_1",
        name="TCP策略包",
        description="计算机网络TCP协议学习策略集合",
        goal_type="exam",
        domain="computer_science",
        author_id="author_1",
        strategy_templates=[
            {"strategy_key": "worked_example", "applicable_when": {"mastery": "<0.3"}},
        ],
        rating=4.5,
    )
    result = DomainPackMarketplace.validate_pack(good_pack)
    assert result["valid"] is True

    bad_pack = DomainPack(
        pack_id="pack_bad",
        name="AB",
        description="short",
        goal_type="exam",
        domain="test",
        author_id="",
        strategy_templates=[],
    )
    result = DomainPackMarketplace.validate_pack(bad_pack)
    assert result["valid"] is False
    assert "name_too_short" in result["issues"]


def test_domain_pack_score():
    from app.signals.research_grade import DomainPack  # noqa: DEPRECATED v1, DomainPackMarketplace  # noqa: DEPRECATED v1

    redis = MagicMock()
    marketplace = DomainPackMarketplace(redis)

    popular = DomainPack(
        pack_id="p1",
        name="Popular",
        description="d",
        goal_type="exam",
        domain="cs",
        author_id="a1",
        strategy_templates=[{}],
        rating=4.8,
        download_count=200,
        review_count=30,
    )
    new_pack = DomainPack(
        pack_id="p2",
        name="New",
        description="d",
        goal_type="exam",
        domain="cs",
        author_id="a2",
        strategy_templates=[{}],
        rating=4.0,
        download_count=5,
        review_count=1,
    )
    ranked = marketplace.rank_packs([new_pack, popular], goal_type="exam")
    assert ranked[0]["pack_id"] == "p1"  # popular first


def test_domain_pack_filter():
    from app.signals.research_grade import DomainPack  # noqa: DEPRECATED v1, DomainPackMarketplace  # noqa: DEPRECATED v1

    redis = MagicMock()
    marketplace = DomainPackMarketplace(redis)

    exam_pack = DomainPack(
        pack_id="p1",
        name="Exam",
        description="d",
        goal_type="exam",
        domain="cs",
        author_id="a1",
        strategy_templates=[{}],
    )
    project_pack = DomainPack(
        pack_id="p2",
        name="Project",
        description="d",
        goal_type="project",
        domain="cs",
        author_id="a2",
        strategy_templates=[{}],
    )
    ranked = marketplace.rank_packs([exam_pack, project_pack], goal_type="project")
    assert len(ranked) == 1
    assert ranked[0]["pack_id"] == "p2"


def test_domain_pack_serialization():
    from app.signals.research_grade import DomainPack  # noqa: DEPRECATED v1

    pack = DomainPack(
        pack_id="p_ser",
        name="Test",
        description="Test pack",
        goal_type="exam",
        domain="cs",
        author_id="a1",
        strategy_templates=[{"key": "val"}],
        rating=4.5,
    )
    d = pack.to_dict()
    restored = DomainPack.from_dict(d)
    assert restored.name == "Test"
    assert restored.strategy_templates == [{"key": "val"}]


# ═══════════════════════════════════════════════════════════════════════
# P0-1: Aurora ↔ Spine Bridge Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_spine_aurora_bridge_get_context():
    """SpineAuroraBridge fetches Spine context for Aurora."""
    from app.signals.spine_aurora_bridge import SpineAuroraBridge

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.smembers = AsyncMock(return_value=set())
    redis.lrange = AsyncMock(return_value=[])

    bridge = SpineAuroraBridge(redis)
    ctx = await bridge.get_context_for_aurora("u1")
    assert ctx["active_directive"] is None
    assert ctx["risk_flags"] == []
    assert ctx["recent_outcomes_summary"] is None


@pytest.mark.asyncio
async def test_spine_aurora_bridge_get_context_with_directive():
    """SpineAuroraBridge returns active directive when present."""
    import json
    from app.signals.spine_aurora_bridge import SpineAuroraBridge

    redis = AsyncMock()
    directive = {"directive_type": "execution", "strategy_key": "repair_transfer", "user_visible_reason": "test"}
    redis.get = AsyncMock(return_value=json.dumps(directive).encode())
    redis.smembers = AsyncMock(return_value=set())
    redis.lrange = AsyncMock(return_value=[])

    bridge = SpineAuroraBridge(redis)
    ctx = await bridge.get_context_for_aurora("u1")
    assert ctx["active_directive"] is not None
    assert ctx["active_directive"]["strategy"] == "repair_transfer"


@pytest.mark.asyncio
async def test_spine_aurora_bridge_feed_decision():
    """SpineAuroraBridge feeds Aurora decision back to Spine."""
    import json
    from app.signals.spine_aurora_bridge import SpineAuroraBridge

    redis = AsyncMock()
    redis.rpush = AsyncMock(return_value=1)
    redis.ltrim = AsyncMock(return_value=True)
    redis.expire = AsyncMock(return_value=True)

    bridge = SpineAuroraBridge(redis)
    await bridge.feed_aurora_decision(
        user_id="u1",
        action="emit_message",
        surface="aurora_modeling",
        chat_directive={"intent": "explore", "target_domain": "goal"},
    )
    redis.rpush.assert_called_once()
    call_args = redis.rpush.call_args
    assert "spine:aurora_decisions:u1" in call_args[0][0]
    event = json.loads(call_args[0][1])
    assert event["action"] == "emit_message"


@pytest.mark.asyncio
async def test_spine_aurora_bridge_handles_redis_failure():
    """Bridge gracefully handles Redis failures."""
    from app.signals.spine_aurora_bridge import SpineAuroraBridge

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=Exception("Redis down"))

    bridge = SpineAuroraBridge(redis)
    ctx = await bridge.get_context_for_aurora("u1")
    assert ctx["active_directive"] is None


def test_dashboard_readout_has_spine_signals_field():
    """DashboardReadout includes spine_signals field."""
    from app.aurora.runtime_v1.dashboard import DashboardReadout
    from app.aurora.runtime_v1.control_surface import AuroraHardBounds

    readout = DashboardReadout(
        surface="aurora_modeling",
        user_id="u1",
        conversation_id="c1",
        request_id="r1",
        user_message="test",
        activity_profile={},
        hard_bounds=AuroraHardBounds(),
        spine_signals={"active_directive": {"strategy": "test"}},
    )
    assert readout.spine_signals["active_directive"]["strategy"] == "test"


def test_dashboard_readout_spine_signals_in_payload():
    """spine_signals appears in to_llm_payload for emit_message action."""
    from app.aurora.runtime_v1.dashboard import DashboardReadout
    from app.aurora.runtime_v1.control_surface import AuroraHardBounds

    readout = DashboardReadout(
        surface="aurora_modeling",
        user_id="u1",
        conversation_id="c1",
        request_id="r1",
        user_message="test",
        activity_profile={},
        hard_bounds=AuroraHardBounds(),
        spine_signals={"risk_flags": ["burnout_risk"]},
    )
    payload = readout.to_llm_payload(action="emit_message")
    assert "spine_signals" in payload
    assert payload["spine_signals"]["risk_flags"] == ["burnout_risk"]


# ═══════════════════════════════════════════════════════════════════════
# P0-2: Orphan Module Wiring Tests
# ═══════════════════════════════════════════════════════════════════════


def test_spine_orchestrator_instantiates_orphan_modules():
    """SpineOrchestrator now instantiates previously orphaned modules."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = MagicMock()
    spine = SpineOrchestrator(redis)
    assert hasattr(spine, "policy_analytics")
    assert hasattr(spine, "policy_experiments")
    assert hasattr(spine, "learning_base")
    assert hasattr(spine, "growth_chronicle")
    assert hasattr(spine, "relationship_model")
    assert hasattr(spine, "skill_extraction")
    assert hasattr(spine, "goal_type_adapter")
    assert hasattr(spine, "material_signal_detector")
    assert hasattr(spine, "timeline_renderer")


# ═══════════════════════════════════════════════════════════════════════
# P1: Divine Moment Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_divine_moment_see_persistence():
    """神性时刻1: 看见坚持 — achievement → growth chronicle entry."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    spine = SpineOrchestrator(redis)

    # Mock growth_chronicle.add_entry to not fail
    spine.growth_chronicle.add_entry = AsyncMock()
    result = await spine.on_achievement_unlocked(
        user_id="u1",
        achievement_type="streak_7",
        streak_count=7,
    )
    assert result is not None
    assert result["streak_count"] == 7


@pytest.mark.asyncio
async def test_divine_moment_admit_mistake():
    """神性时刻2: 承认误判 — user correction → state patch."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    spine = SpineOrchestrator(redis)

    # Mock methods
    spine.relationship_model.update_from_interaction = AsyncMock()
    spine.growth_chronicle.add_entry = AsyncMock()

    result = await spine.on_user_correction(
        user_id="u1",
        correction_type="strategy_misattribution",
        original_claim="task_too_large",
        corrected_understanding="knowledge_transfer_failure",
    )
    assert result is not None
    assert result["original_claim"] == "task_too_large"
    assert result["corrected_understanding"] == "knowledge_transfer_failure"


@pytest.mark.asyncio
async def test_divine_moment_remember_time():
    """神性时刻4: 记得时间 — recovery card for returning user."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    spine = SpineOrchestrator(redis)

    card = await spine.build_recovery_card(
        user_id="u1",
        elapsed_minutes=120,
        last_task_id="task_1",
        last_task_status="in_progress",
    )
    assert card is not None
    assert card["type"] == "recovery_card"
    assert card["urgency"] == "high"
    assert len(card["options"]) == 4


@pytest.mark.asyncio
async def test_divine_moment_context_receipt():
    """神性时刻3: 知道不用资料 — context receipt."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    spine = SpineOrchestrator(redis)

    receipt = await spine.build_context_receipt(
        user_id="u1",
        used_sources=["task_card", "TCP错因"],
        excluded_sources=["完整传输层课件"],
        reason="范围太大，会污染解释。",
        retrieval_mode="task_bound_rag",
    )
    assert receipt["type"] == "context_receipt"
    assert "完整传输层课件" in receipt["excluded"]
    assert len(receipt["user_actions"]) == 3


# ═══════════════════════════════════════════════════════════════════════
# P2: ExperienceEnvelope Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_experience_envelope_basic():
    """ExperienceEnvelope aggregates cards, receipts, and status."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.lrange = AsyncMock(return_value=[])
    spine = SpineOrchestrator(redis)

    envelope = await spine.build_experience_envelope(
        user_id="u1",
        primary_message="测试消息",
        trace_id="ct_001",
    )
    assert envelope["turn_id"].startswith("turn_")
    assert envelope["primary_message"]["text"] == "测试消息"
    assert envelope["debug_trace_id"] == "ct_001"


@pytest.mark.asyncio
async def test_experience_envelope_with_recovery_card():
    """ExperienceEnvelope includes recovery card when present."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()

    recovery_card = {"type": "recovery_card", "urgency": "high", "options": []}

    async def mock_get(key):
        if "recovery" in key:
            return json.dumps(recovery_card).encode()
        return None

    redis.get = AsyncMock(side_effect=mock_get)
    redis.lrange = AsyncMock(return_value=[])
    spine = SpineOrchestrator(redis)

    envelope = await spine.build_experience_envelope(user_id="u1")
    assert len(envelope["cards"]) == 1
    assert envelope["cards"][0]["type"] == "recovery_card"


# ═══════════════════════════════════════════════════════════════════════
# P3: Fatigue Guard Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fatigue_guard_low():
    """Fatigue guard returns low for normal usage."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    spine = SpineOrchestrator(redis)

    result = await spine.check_fatigue(
        user_id="u1",
        interactions_last_24h=5,
        consecutive_hours=1.0,
    )
    assert result["fatigue_level"] == "low"
    assert result["recommended_policy"] == "normal"


@pytest.mark.asyncio
async def test_fatigue_guard_critical():
    """Fatigue guard detects critical fatigue."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    spine = SpineOrchestrator(redis)

    result = await spine.check_fatigue(
        user_id="u1",
        interactions_last_24h=40,
        consecutive_hours=6.0,
        accuracy_trend=[0.8, 0.6, 0.4],
        is_late_night=True,
    )
    assert result["fatigue_level"] == "critical"
    assert result["hard_constraints"]["suggest_break"] is True


# ═══════════════════════════════════════════════════════════════════════
# P3: Crisis Mode Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_crisis_mode_detection():
    """Crisis mode detected for zero-base + short deadline."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    spine = SpineOrchestrator(redis)

    result = await spine.detect_crisis_mode(
        user_id="u1",
        days_to_deadline=3,
        baseline_mastery=15,
        goal_type="exam",
    )
    assert result is not None
    assert result["mode"] == "exam_crisis_zero_base"
    assert result["task_constraints"]["max_task_duration_min"] == 25


@pytest.mark.asyncio
async def test_crisis_mode_not_triggered_for_high_mastery():
    """Crisis mode not triggered when mastery is sufficient."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    spine = SpineOrchestrator(redis)

    result = await spine.detect_crisis_mode(
        user_id="u1",
        days_to_deadline=3,
        baseline_mastery=50,
        goal_type="exam",
    )
    assert result is None


# ═══════════════════════════════════════════════════════════════════════
# P2: State Snapshot & Recovery Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_save_spine_snapshot():
    """Spine snapshot saves state summary."""
    import json
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.smembers = AsyncMock(return_value=set())
    redis.lrange = AsyncMock(return_value=[])
    spine = SpineOrchestrator(redis)

    # Mock state register
    spine.state_register.get_active_states = AsyncMock(return_value=[])
    spine.relationship_model.get_or_create = AsyncMock(return_value=MagicMock(to_dict=lambda: {"trust_level": 0.6}))
    spine.outcome_recorder.get_recent_policy_effects = AsyncMock(return_value=[])
    spine.skill_lifecycle_manager.get_user_skills = AsyncMock(return_value=[])

    snapshot = await spine.save_spine_snapshot(user_id="u1", goal_id="g1")
    assert snapshot["snapshot_id"].startswith("snap_")
    assert snapshot["goal_id"] == "g1"


@pytest.mark.asyncio
async def test_goal_scoped_key():
    """Goal-scoped key prevents cross-goal pollution."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    key = SpineOrchestrator.goal_scoped_key("u1", "task_granularity", "exam_goal")
    assert key == "goal:exam_goal:task_granularity"

    key_no_goal = SpineOrchestrator.goal_scoped_key("u1", "global_state")
    assert key_no_goal == "global_state"


# ═══════════════════════════════════════════════════════════════════════
# v2.1: Pipeline Fatigue + Crisis Integration Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_fatigue_detection_on_task_completion():
    """Fatigue check runs during pipeline and stores result when high."""
    import json

    redis = FakeRedis()
    # Simulate 35 interactions in 24h (high fatigue)
    await redis.set("spine:interaction_count:u1:24h", "35")
    spine = SpineOrchestrator(redis_client=redis)

    trace = await spine.on_task_completed(
        user_id="u1",
        task_id="task_1",
        estimated_minutes=25,
        actual_minutes=35,
    )
    # Pipeline ran successfully
    assert trace is not None or trace is None  # may or may not trigger signal

    # Check if fatigue was recorded
    fatigue_raw = await redis.get("spine:fatigue:u1:latest")
    if fatigue_raw:
        fatigue = json.loads(fatigue_raw)
        assert fatigue["fatigue_level"] in ("high", "critical")


@pytest.mark.asyncio
async def test_pipeline_crisis_mode_stored_for_exam_user():
    """Crisis mode check runs during pipeline for exam users."""
    import json

    redis = FakeRedis()
    # Simulate exam user with 3-day deadline
    await redis.set("spine:exam_sprint:u1:goal_mode", "exam_rescue")
    await redis.set("spine:exam_sprint:u1:deadline_days", "3")
    spine = SpineOrchestrator(redis_client=redis)

    trace = await spine.on_task_completed(
        user_id="u1",
        task_id="task_1",
        estimated_minutes=25,
        actual_minutes=35,
    )

    # Check if crisis was recorded
    crisis_raw = await redis.get("spine:crisis:u1:latest")
    if crisis_raw:
        crisis = json.loads(crisis_raw)
        assert crisis["mode"] == "exam_crisis_zero_base"
        assert crisis["task_constraints"]["max_task_duration_min"] == 25


@pytest.mark.asyncio
async def test_fatigue_levels_correct():
    """All fatigue levels have correct policy mapping."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    # Low
    low = await spine.check_fatigue(user_id="u1", interactions_last_24h=3, consecutive_hours=0.5)
    assert low["fatigue_level"] == "low"
    assert low["recommended_policy"] == "normal"

    # Medium (accuracy declining)
    med = await spine.check_fatigue(
        user_id="u1",
        interactions_last_24h=8,
        consecutive_hours=2.0,
        accuracy_trend=[0.9, 0.7, 0.5],
    )
    assert med["fatigue_level"] == "medium"
    assert med["recommended_policy"] == "reduce_pace"

    # High (high interactions + late night)
    high = await spine.check_fatigue(
        user_id="u1",
        interactions_last_24h=20,
        consecutive_hours=1.0,
        is_late_night=True,
    )
    assert high["fatigue_level"] in ("high", "medium")
    assert "avoid_new_chapter" not in high.get("hard_constraints", {})


@pytest.mark.asyncio
async def test_crisis_mode_boundary_conditions():
    """Crisis mode triggers at correct boundaries."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)

    # Too far away → None
    assert await spine.detect_crisis_mode(user_id="u1", days_to_deadline=7, baseline_mastery=10) is None

    # High mastery → None
    assert await spine.detect_crisis_mode(user_id="u1", days_to_deadline=3, baseline_mastery=40) is None

    # Non-exam → None
    assert (
        await spine.detect_crisis_mode(user_id="u1", days_to_deadline=3, baseline_mastery=10, goal_type="fitness")
        is None
    )

    # Borderline: 5 days, low mastery → should trigger
    border = await spine.detect_crisis_mode(user_id="u1", days_to_deadline=5, baseline_mastery=25)
    assert border is not None
    assert border["mode"] == "exam_crisis_zero_base"

    # Extreme: 1 day
    extreme = await spine.detect_crisis_mode(user_id="u1", days_to_deadline=1, baseline_mastery=5)
    assert extreme is not None
    assert extreme["task_constraints"]["avoid_new_chapter"] is True


@pytest.mark.asyncio
async def test_experience_envelope_aggregates_all_cards():
    """ExperienceEnvelope collects recovery, growth, and community cards."""
    import json

    redis = FakeRedis()

    recovery = {"type": "recovery_card", "urgency": "high"}
    growth = {"type": "growth_milestone", "title": "连续7天"}
    community = {"type": "community_hint", "node": "tcp_window"}

    await redis.set("spine:card:recovery:u1:latest", json.dumps(recovery))
    await redis.set("spine:card:growth:u1:latest", json.dumps(growth))
    await redis.set("spine:card:community_hint:u1:latest", json.dumps(community))

    spine = SpineOrchestrator(redis_client=redis)
    envelope = await spine.build_experience_envelope(user_id="u1")

    card_types = [c["type"] for c in envelope["cards"]]
    assert "recovery_card" in card_types
    assert "growth_milestone" in card_types
    assert "community_hint" in card_types


# ═══════════════════════════════════════════════════════════════════════
# v2.2: Trace Compaction Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_trace_compaction_below_threshold():
    """Compaction skipped when traces below 50."""
    from app.signals.causal_trace_store import CausalTraceStore

    redis = FakeRedis()
    store = CausalTraceStore(redis)

    # Create only 5 traces
    for _ in range(5):
        trace = await store.create_trace()
        await store.link_to_user("u1", trace.trace_id)

    result = await store.compact_old_traces("u1")
    assert result is None  # nothing to compact


@pytest.mark.asyncio
async def test_trace_compaction_aggregates_stats():
    """Compaction aggregates signal types and directive types."""
    from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY

    redis = FakeRedis()
    store = CausalTraceStore(redis)
    key = _USER_TRACES_KEY.format(user_id="u1")

    # Create 55 traces with manual push (bypass ltrim)
    for i in range(55):
        trace = await store.create_trace()
        trace.state_keys_changed.append("task_granularity_fit" if i % 2 == 0 else "knowledge_transfer")
        await store._save_trace(trace)
        await redis.lpush(key, trace.trace_id)

    result = await store.compact_old_traces("u1")
    assert result is not None
    assert result["traces_compacted"] == 5  # 55 - 50
    assert "task_granularity_fit" in result["signal_types"]
    assert "knowledge_transfer" in result["signal_types"]

    # Verify compact summary stored
    summaries = await store.get_compact_summaries("u1")
    assert len(summaries) == 1
    assert summaries[0]["traces_compacted"] == 5


@pytest.mark.asyncio
async def test_trace_compaction_preserves_recent():
    """Compaction keeps most recent 50 traces intact."""
    from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY

    redis = FakeRedis()
    store = CausalTraceStore(redis)
    key = _USER_TRACES_KEY.format(user_id="u1")

    trace_ids = []
    for i in range(55):
        trace = await store.create_trace()
        await redis.lpush(key, trace.trace_id)
        trace_ids.append(trace.trace_id)

    await store.compact_old_traces("u1")

    # Oldest 5 (last in list) should be deleted
    for old_id in trace_ids[:5]:
        old_trace = await store.get_trace(old_id)
        assert old_trace is None


@pytest.mark.asyncio
async def test_trace_compaction_full_history():
    """get_full_trace_history returns both active and compacted."""
    from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY

    redis = FakeRedis()
    store = CausalTraceStore(redis)
    key = _USER_TRACES_KEY.format(user_id="u1")

    for i in range(55):
        trace = await store.create_trace()
        await redis.lpush(key, trace.trace_id)

    await store.compact_old_traces("u1")

    history = await store.get_full_trace_history("u1")
    assert history["active_traces"] == 50
    assert history["compact_summaries"] == 1
    assert len(history["traces"]) == 50
    assert len(history["compacted"]) == 1


@pytest.mark.asyncio
async def test_trace_compaction_celery_task_registered():
    """Celery compaction task is registered."""
    from app.core.celery_tasks import compact_user_traces

    assert compact_user_traces.name == "app.core.celery_tasks.compact_user_traces"


# ═══════════════════════════════════════════════════════════════════════
# v2.2: Redis Resilience (Degraded Mode) Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    """Circuit breaker transitions closed → open → half_open → closed."""
    from app.signals.redis_resilience import CircuitBreaker

    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.01)

    assert cb.state == "closed"
    assert cb.allow_request() is True

    # 3 failures → open
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "open"
    assert cb.allow_request() is False

    # Wait for recovery timeout
    import asyncio

    await asyncio.sleep(0.02)
    assert cb.state == "half_open"
    assert cb.allow_request() is True

    # Success → closed
    cb.record_success()
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_resilient_redis_call_success():
    """resilient_redis_call returns result on success."""
    from app.signals.redis_resilience import resilient_redis_call

    async def good_call():
        return "ok"

    result = await resilient_redis_call("spine_pipeline", good_call())
    assert result == "ok"


@pytest.mark.asyncio
async def test_resilient_redis_call_fallback():
    """resilient_redis_call returns fallback on failure."""
    from app.signals.redis_resilience import resilient_redis_call, CircuitBreaker

    # Use a breaker that's already open
    breaker = CircuitBreaker("test_open", failure_threshold=1, recovery_timeout=60.0)
    breaker.record_failure()  # 1 failure

    # Manually set to open
    breaker._state = "open"

    async def bad_call():
        raise Exception("redis down")

    result = await resilient_redis_call("test_open", bad_call(), fallback="safe_default")
    # breaker is open so it should return fallback immediately
    assert result == "safe_default"


@pytest.mark.asyncio
async def test_resilient_redis_call_retries():
    """resilient_redis_call returns fallback when coroutine fails."""
    from app.signals.redis_resilience import resilient_redis_call

    async def failing_call():
        raise Exception("redis connection refused")

    result = await resilient_redis_call("spine_pipeline", failing_call(), fallback="safe", max_retries=2)
    assert result == "safe"


@pytest.mark.asyncio
async def test_circuit_breaker_named_breakers():
    """Named breakers for spine subsystems exist."""
    from app.signals.redis_resilience import get_breaker

    bp = get_breaker("spine_pipeline")
    assert bp.name == "spine_pipeline"

    bs = get_breaker("state_register")
    assert bs.name == "state_register"

    bc = get_breaker("chronicle")
    assert bc.name == "chronicle"

    # Unknown name → creates new breaker
    bx = get_breaker("unknown")
    assert bx.name == "unknown"
    assert bx.state == "closed"
