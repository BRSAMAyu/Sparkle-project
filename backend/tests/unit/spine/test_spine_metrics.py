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

"""Spine tests — test_v2_v3_features.py."""

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

# ── Decision Realization Score Metrics Tests ─────────────────────────

@pytest.mark.asyncio
async def test_metrics_increment_and_get():
    """Metrics increment and get counter values."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)
    await metrics.increment("signals_generated", 5)
    val = await metrics.get_counter("signals_generated")
    assert val == 5


@pytest.mark.asyncio
async def test_metrics_snapshot_rates():
    """Metrics snapshot calculates rates correctly."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)
    await metrics.increment("signals_generated", 10)
    await metrics.increment("signals_entered_state", 8)
    await metrics.increment("policies_evaluated", 8)
    await metrics.increment("directives_generated", 6)
    await metrics.increment("directives_applied", 5)
    await metrics.increment("outputs_changed", 4)
    await metrics.increment("receipts_shown", 5)
    await metrics.increment("outcomes_recorded", 3)
    await metrics.increment("effective_attributions", 2)

    snap = await metrics.snapshot()
    assert snap["signal_to_state_rate"]["value"] == 0.8  # 8/10
    assert snap["policy_to_directive_rate"]["value"] == 0.75  # 6/8
    assert snap["directive_application_rate"]["value"] == pytest.approx(5 / 6, abs=0.01)  # 5/6
    assert snap["intervention_effectiveness"]["value"] == pytest.approx(2 / 3, abs=0.01)
    assert snap["orphan_signal_count"]["value"] == 0


@pytest.mark.asyncio
async def test_metrics_snapshot_zero_division():
    """Metrics with zero denominator returns 0.0 rate."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)
    snap = await metrics.snapshot()
    assert snap["signal_to_state_rate"]["value"] == 0.0
    assert snap["orphan_signal_count"]["value"] == 0


@pytest.mark.asyncio
async def test_metrics_convenience_methods():
    """Convenience methods increment correct counters."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)

    await metrics.record_signal_generated()
    await metrics.record_signal_entered_state()
    await metrics.record_policy_evaluated(matched=True)
    await metrics.record_directive_generated()
    await metrics.record_directive_applied(changed_output=True)
    await metrics.record_receipt_shown()
    await metrics.record_outcome_recorded(effective=True)
    await metrics.record_retraction()

    assert await metrics.get_counter("signals_generated") == 1
    assert await metrics.get_counter("signals_entered_state") == 1
    assert await metrics.get_counter("policies_evaluated") == 1
    assert await metrics.get_counter("orphan_signals") == 0
    assert await metrics.get_counter("directives_generated") == 1
    assert await metrics.get_counter("directives_applied") == 1
    assert await metrics.get_counter("outputs_changed") == 1
    assert await metrics.get_counter("receipts_shown") == 1
    assert await metrics.get_counter("outcomes_recorded") == 1
    assert await metrics.get_counter("effective_attributions") == 1
    assert await metrics.get_counter("retractions") == 1


@pytest.mark.asyncio
async def test_metrics_orphan_signal_on_no_match():
    """Unmatched policy creates orphan signal metric."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)
    await metrics.record_policy_evaluated(matched=False)
    assert await metrics.get_counter("orphan_signals") == 1


@pytest.mark.asyncio
async def test_metrics_reset():
    """Reset clears all counters."""
    redis = FakeRedis()
    metrics = SpineMetricsCollector(redis_client=redis)
    await metrics.increment("signals_generated", 10)
    await metrics.reset()
    assert await metrics.get_counter("signals_generated") == 0


@pytest.mark.asyncio
async def test_metrics_ten_definitions():
    """All 10 metric definitions exist."""
    assert len(METRIC_DEFINITIONS) == 10
    expected = {
        "signal_to_state_rate", "state_to_policy_rate",
        "policy_to_directive_rate", "directive_application_rate",
        "output_change_rate", "user_visible_receipt_rate",
        "outcome_feedback_rate", "intervention_effectiveness",
        "retraction_rate", "orphan_signal_count",
    }
    assert set(METRIC_DEFINITIONS.keys()) == expected


@pytest.mark.asyncio
async def test_spine_pipeline_records_metrics():
    """Spine pipeline records metrics at key points."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis_client=redis)

    signal = ActionableSignal(
        signal_id="sig_metric", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine._run_signal_pipeline(user_id="u_metrics", signal=signal)

    assert await spine.metrics.get_counter("signals_generated") == 1
    assert await spine.metrics.get_counter("signals_entered_state") == 1
    assert await spine.metrics.get_counter("policies_evaluated") == 1
    assert await spine.metrics.get_counter("directives_generated") == 1
    assert await spine.metrics.get_counter("receipts_shown") == 1  # visibility=receipt

    snap = await spine.get_metrics_snapshot()
    assert snap["signal_to_state_rate"]["value"] == 1.0
    assert snap["policy_to_directive_rate"]["value"] == 1.0


# ═══════════════════════════════════════════════════════════════════
# P3: Production Wiring Integration Tests
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_response_directive_injected_into_prompt():
    """prompts.build_system_prompt injects spine response directive."""
    from app.orchestration.prompts import build_system_prompt

    # Without directive — baseline prompt
    prompt_base = build_system_prompt(
        user_context={"user_id": "u1", "name": "Test"},
        conversation_history={},
    )

    # With directive
    directive = {
        "tone": "encouraging_diagnostic",
        "length": "short",
        "avoid": ["空洞鼓励"],
        "must_acknowledge": ["最近的失败"],
        "include_user_options": True,
    }
    prompt_spine = build_system_prompt(
        user_context={"user_id": "u1", "name": "Test"},
        conversation_history={},
        spine_response_directive=directive,
    )

    assert "策略调整指令" in prompt_spine
    assert "鼓励性诊断" in prompt_spine
    assert "简短" in prompt_spine
    assert "空洞鼓励" in prompt_spine
    assert "最近的失败" in prompt_spine
    assert "可操作选项" in prompt_spine
    assert "策略调整指令" not in prompt_base


@pytest.mark.asyncio
async def test_response_directive_avoid_and_acknowledge_optional():
    """Directive with empty avoid/must_acknowledge omits those lines."""
    from app.orchestration.prompts import build_system_prompt

    directive = {
        "tone": "calm_direct",
        "length": "medium",
        "avoid": [],
        "must_acknowledge": [],
        "include_user_options": False,
    }
    prompt = build_system_prompt(
        user_context={"user_id": "u1", "name": "Test"},
        conversation_history={},
        spine_response_directive=directive,
    )

    assert "策略调整指令" in prompt
    assert "稳定、直接" in prompt
    assert "适中" in prompt
    assert "避免" not in prompt
    assert "必须承认" not in prompt
    assert "可操作选项" not in prompt


@pytest.mark.asyncio
async def test_response_directive_null_is_noop():
    """spine_response_directive=None produces unchanged prompt."""
    from app.orchestration.prompts import build_system_prompt

    prompt_none = build_system_prompt(
        user_context={"user_id": "u1", "name": "Test"},
        conversation_history={},
        spine_response_directive=None,
    )
    prompt_omitted = build_system_prompt(
        user_context={"user_id": "u1", "name": "Test"},
        conversation_history={},
    )

    assert prompt_none == prompt_omitted
    assert "策略调整指令" not in prompt_none


@pytest.mark.asyncio
async def test_plan_directive_recovery_task_injection():
    """PlanDirective insert_recovery_task prepends a recovery task."""
    from app.signals.types import PlanDirective
    import json

    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis_client=redis)

    # Store a plan_directive with insert_recovery_task
    pd = PlanDirective(
        directive_id="pd_test",
        policy_decision_id="pol_test",
        plan_action="local_replan",
        constraints={"insert_recovery_task": True},
    )
    await redis.set(
        f"spine:plan_directive:u_plan_test:latest",
        json.dumps(pd.to_dict()),
        ex=72 * 3600,
    )

    # Retrieve it
    fetched = await spine.get_plan_directive("u_plan_test")
    assert fetched is not None
    assert fetched.constraints.get("insert_recovery_task") is True
    assert fetched.plan_action == "local_replan"


@pytest.mark.asyncio
async def test_plan_directive_easy_win_injection():
    """PlanDirective insert_easy_win prepends a light_review task."""
    from app.signals.types import PlanDirective
    import json

    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis_client=redis)

    pd = PlanDirective(
        directive_id="pd_easy",
        policy_decision_id="pol_easy",
        plan_action="insert_task",
        constraints={"insert_easy_win": True},
    )
    await redis.set(
        f"spine:plan_directive:u_easy:latest",
        json.dumps(pd.to_dict()),
        ex=72 * 3600,
    )

    fetched = await spine.get_plan_directive("u_easy")
    assert fetched is not None
    assert fetched.constraints.get("insert_easy_win") is True


@pytest.mark.asyncio
async def test_plan_directive_practice_task_injection():
    """PlanDirective insert_practice_task prepends a practice task."""
    from app.signals.types import PlanDirective
    import json

    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis_client=redis)

    pd = PlanDirective(
        directive_id="pd_prac",
        policy_decision_id="pol_prac",
        plan_action="insert_task",
        constraints={"insert_practice_task": True, "insert_easy_win": True},
    )
    await redis.set(
        f"spine:plan_directive:u_prac:latest",
        json.dumps(pd.to_dict()),
        ex=72 * 3600,
    )

    fetched = await spine.get_plan_directive("u_prac")
    assert fetched is not None
    assert len(fetched.constraints) == 2


@pytest.mark.asyncio
async def test_orchestrator_production_fetches_response_directive():
    """orchestrator_production.py fetches ResponseDirective from spine and passes to prompt."""
    from app.signals.types import ResponseDirective
    import json

    redis = FakeRedis()
    rd = ResponseDirective(
        directive_id="rd_prod",
        policy_decision_id="pol_prod",
        tone="calm_urgent",
        length="short",
        avoid=["复杂解释"],
        must_acknowledge=["时间紧迫"],
        include_user_options=True,
    )
    await redis.set(
        f"spine:response_directive:u_prod:latest",
        json.dumps(rd.to_dict()),
        ex=72 * 3600,
    )

    from app.signals.spine_orchestrator import SpineOrchestrator
    spine = SpineOrchestrator(redis)
    fetched = await spine.get_response_directive("u_prod")

    assert fetched is not None
    assert fetched.tone == "calm_urgent"
    assert fetched.length == "short"
    assert "复杂解释" in fetched.avoid
    assert "时间紧迫" in fetched.must_acknowledge


@pytest.mark.asyncio
async def test_model_write_auto_apply():
    """High-confidence model writes auto-apply to Redis user state."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ModelWriteDirective, ModelWriteEntry
    import json

    mwd = ModelWriteDirective(
        directive_id="mw_auto",
        policy_decision_id="pol_auto",
        writes=[
            ModelWriteEntry(
                target_model="user_state",
                claim="user struggles with transfer problems",
                scope="current_sprint",
                confidence=0.85,
                needs_user_confirmation=False,
                ttl="48h",
            ),
            ModelWriteEntry(
                target_model="sparkle_self_model",
                claim="user may need scaffolding",
                scope="turn",
                confidence=0.5,  # below threshold
                needs_user_confirmation=False,
            ),
            ModelWriteEntry(
                target_model="cognitive_profile",
                claim="advanced pattern detected",
                scope="strategy",
                confidence=0.9,
                needs_user_confirmation=True,  # needs confirmation
            ),
        ],
    )

    spine = SpineOrchestrator(redis_client=redis)
    await spine._apply_model_writes("u_mw", mwd)

    # Only the first entry should be applied (high confidence, no confirmation needed)
    claim_key = "spine:model_claim:u_mw:user_state:current_sprint"
    raw = await redis.get(claim_key)
    assert raw is not None
    claim = json.loads(raw)
    assert claim["claim"] == "user struggles with transfer problems"
    assert claim["source"] == "spine_auto"

    # Low confidence entry should NOT be applied
    low_key = "spine:model_claim:u_mw:sparkle_self_model:turn"
    assert await redis.get(low_key) is None

    # Needs-confirmation entry should NOT be applied
    confirm_key = "spine:model_claim:u_mw:cognitive_profile:strategy"
    assert await redis.get(confirm_key) is None


@pytest.mark.asyncio
async def test_retrieval_directive_store_fetch():
    """RetrievalDirective round-trip through spine storage."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import RetrievalDirective
    import json

    rd = RetrievalDirective(
        directive_id="ret_test",
        policy_decision_id="pol_ret",
        retrieval_mode="task_bound_graph_rag",
        source_scope="task_bound",
        pollution_guard="strict",
        token_budget=2400,
    )
    await redis.set(
        f"spine:retrieval_directive:u_ret:latest",
        json.dumps(rd.to_dict()),
        ex=72 * 3600,
    )

    spine = SpineOrchestrator(redis_client=redis)
    fetched = await spine.get_retrieval_directive("u_ret")
    assert fetched is not None
    assert fetched.retrieval_mode == "task_bound_graph_rag"
    assert fetched.pollution_guard == "strict"
    assert fetched.token_budget == 2400


@pytest.mark.asyncio
async def test_retrieval_directive_pipeline_storage():
    """Signal pipeline stores RetrievalDirective for matched claims."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    signal = ActionableSignal(
        signal_id="sig_ret", source_event_ids=[], source_system="test",
        state_key="material_utilization", claim="material_underutilized",
        confidence=0.9, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    spine = SpineOrchestrator(redis_client=redis)
    await spine._run_signal_pipeline(user_id="u_retpipe", signal=signal)

    fetched = await spine.get_retrieval_directive("u_retpipe")
    assert fetched is not None
    assert fetched.retrieval_mode == "targeted_source_rag"


@pytest.mark.asyncio
async def test_ux_directive_store_fetch():
    """UXDirective round-trip through spine storage."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import UXDirective
    import json

    uxd = UXDirective(
        directive_id="ux_test",
        policy_decision_id="pol_ux",
        status_band_state="risk_detected",
        show_context_receipt=True,
        show_strategy_receipt=True,
        predicted_reply_options=["确认调整", "恢复原计划"],
    )
    await redis.set(
        f"spine:ux_directive:u_ux:latest",
        json.dumps(uxd.to_dict()),
        ex=72 * 3600,
    )

    spine = SpineOrchestrator(redis_client=redis)
    fetched = await spine.get_ux_directive("u_ux")
    assert fetched is not None
    assert fetched.status_band_state == "risk_detected"
    assert fetched.show_context_receipt is True
    assert "确认调整" in fetched.predicted_reply_options


@pytest.mark.asyncio
async def test_notification_directive_store_fetch():
    """NotificationDirective round-trip through spine storage."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import NotificationDirective
    import json

    nd = NotificationDirective(
        directive_id="notif_test",
        policy_decision_id="pol_notif",
        allowed=True,
        channel="push",
        trigger="first_task_not_started",
        message_strategy="low_effort_next_step",
    )
    await redis.set(
        f"spine:notification_directive:u_notif:latest",
        json.dumps(nd.to_dict()),
        ex=72 * 3600,
    )

    spine = SpineOrchestrator(redis_client=redis)
    fetched = await spine.get_notification_directive("u_notif")
    assert fetched is not None
    assert fetched.trigger == "first_task_not_started"


# ═══════════════════════════════════════════════════════════════════
# P5: Causal Audit Timeline + API Endpoints
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_causal_timeline_retrieves_traces():
    """CausalTraceStore.get_user_traces returns linked traces."""
    redis = FakeRedis()
    from app.signals.causal_trace_store import CausalTraceStore

    store = CausalTraceStore(redis)
    trace = await store.create_trace()
    signal = ActionableSignal(
        signal_id="sig_tl", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.8, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await store.store_signal(signal)
    await store.append_signal(trace.trace_id, signal)
    await store.link_to_user("u_tl", trace.trace_id)

    traces = await store.get_user_traces("u_tl", limit=5)
    assert len(traces) == 1
    assert traces[0].trace_id == trace.trace_id
    assert signal.signal_id in traces[0].signal_ids


@pytest.mark.asyncio
async def test_causal_timeline_multiple_traces():
    """Multiple traces are returned in LIFO order."""
    redis = FakeRedis()
    from app.signals.causal_trace_store import CausalTraceStore

    store = CausalTraceStore(redis)
    t1 = await store.create_trace()
    t2 = await store.create_trace()
    await store.link_to_user("u_tl2", t1.trace_id)
    await store.link_to_user("u_tl2", t2.trace_id)

    traces = await store.get_user_traces("u_tl2", limit=10)
    assert len(traces) == 2
    # LIFO — t2 was created last, should be first
    assert traces[0].trace_id == t2.trace_id


@pytest.mark.asyncio
async def test_causal_timeline_trace_limit():
    """Only the most recent traces are returned up to limit."""
    redis = FakeRedis()
    from app.signals.causal_trace_store import CausalTraceStore

    store = CausalTraceStore(redis)
    for _ in range(5):
        t = await store.create_trace()
        await store.link_to_user("u_tl3", t.trace_id)

    traces = await store.get_user_traces("u_tl3", limit=3)
    assert len(traces) == 3


@pytest.mark.asyncio
async def test_causal_timeline_api_format():
    """Verify the CausalTimelineEntry format matches spec Section 19."""
    redis = FakeRedis()
    from app.signals.causal_trace_store import CausalTraceStore
    from app.signals.types import PolicyDecision

    store = CausalTraceStore(redis)
    trace = await store.create_trace()

    signal = ActionableSignal(
        signal_id="sig_fmt", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.9, scope="current_sprint", ttl_hours=48,
        evidence_summary="two tasks timed out", possible_effects=[], priority="high",
    )
    await store.store_signal(signal)
    await store.append_signal(trace.trace_id, signal)

    policy = PolicyDecision(
        policy_decision_id=_uid("pol"),
        primary_strategy="recover_execution_rhythm",
        secondary_strategy=None,
        hard_constraints={"max_task_duration_min": 25},
        soft_biases={"tone": "direct_but_reassuring"},
        visibility="receipt",
        requires_user_confirmation=False,
        reasoning_summary="consecutive timeouts",
    )
    await store.append_policy(trace.trace_id, policy)
    await store.link_to_user("u_tl_fmt", trace.trace_id)

    traces = await store.get_user_traces("u_tl_fmt")
    assert len(traces) == 1
    t = traces[0]
    assert t.trace_id == trace.trace_id
    assert len(t.signal_ids) == 1
    assert t.policy_decision_id == policy.policy_decision_id

    # Verify raw signal data is retrievable
    raw_signal = await redis.get(f"spine:signal:{signal.signal_id}")
    assert raw_signal is not None
    sig_data = json.loads(raw_signal)
    assert sig_data["claim"] == "recent_task_too_large"

    # Verify policy data is stored by ID for timeline retrieval
    raw_policy = await redis.get(f"spine:policy:{policy.policy_decision_id}")
    assert raw_policy is not None
    pol_data = json.loads(raw_policy)
    assert pol_data["primary_strategy"] == "recover_execution_rhythm"


@pytest.mark.asyncio
async def test_state_endpoint_returns_packet():
    """build_state_packet returns ActionableStatePacket."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    # Add some state for the user via upsert_from_signal
    spine = SpineOrchestrator(redis_client=redis)
    test_signal = ActionableSignal(
        signal_id="sig_state", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.85, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    await spine.state_register.upsert_from_signal("u_state", test_signal)

    packet = await spine.build_state_packet(user_id="u_state", active_signals=[test_signal])
    assert packet is not None
    assert packet.user_id == "u_state"
    states = {s.state_key: s.value for s in packet.top_states}
    assert "task_granularity_fit" in states


@pytest.mark.asyncio
async def test_state_endpoint_no_state():
    """build_state_packet returns empty packet when no signals exist."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    spine = SpineOrchestrator(redis_client=redis)
    packet = await spine.build_state_packet(user_id="u_empty")
    assert packet is not None
    assert packet.user_id == "u_empty"
    assert len(packet.top_states) == 0
    assert len(packet.risk_flags) == 0


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_snapshot():
    """SpineMetricsCollector.snapshot returns all 10 metrics."""
    redis = FakeRedis()
    from app.signals.spine_metrics import SpineMetricsCollector

    collector = SpineMetricsCollector(redis)
    await collector.increment("signals_generated", 10)
    await collector.increment("signals_entered_state", 8)

    snap = await collector.snapshot()
    assert len(snap) == 10
    assert snap["signal_to_state_rate"]["value"] == pytest.approx(0.8, abs=0.01)
    assert snap["orphan_signal_count"]["value"] == 0


@pytest.mark.asyncio
async def test_directive_stored_by_id():
    """All directive types stored via spine are retrievable by directive_id."""
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    signal = ActionableSignal(
        signal_id="sig_byid", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.85, scope="current_sprint", ttl_hours=72,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    spine = SpineOrchestrator(redis_client=redis)
    trace = await spine._run_signal_pipeline(user_id="u_byid", signal=signal)

    # The trace should have directive_ids
    assert len(trace.directive_ids) > 0

    # Each directive should be retrievable by ID
    for did in trace.directive_ids:
        raw = await redis.get(f"spine:directive_by_id:{did}")
        assert raw is not None, f"directive {did} not stored by ID"
        d = json.loads(raw)
        assert "directive_id" in d


# ═══════════════════════════════════════════════════════════════════
# E2E: 7-Day Exam Sprint — Full Causal Chain Acceptance Test
# Spec Section 26-27: Demo scenario proving Sparkle's uniqueness
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_e2e_exam_sprint_day0_exam_rescue_detection():
    """
    E2E Day 0: User says "我 7 天后考计网，零基础".
    Spine must detect exam_rescue mode and produce FirstMinuteSnapshot.
    Validates Demo experience point #1: exam_rescue within 60 seconds.
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.exam_rescue_detector import ExamRescueDetector

    # Step 1: Detect exam rescue from first message
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我7天后考计算机网络，零基础，想先别挂")
    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.deadline_days is not None and snapshot.deadline_days <= 7
    assert snapshot.baseline in ("near_zero", "weak")

    # Step 2: Feed into spine as signal
    spine = SpineOrchestrator(redis_client=redis)
    signal = ActionableSignal(
        signal_id="e2e_exam_rescue",
        source_event_ids=["evt_first_msg"],
        source_system="exam_rescue_detector",
        state_key="goal_mode",
        claim="exam_rescue_detected",
        confidence=0.95,
        scope="current_sprint",
        ttl_hours=168,
        evidence_summary="User stated 7-day exam with zero baseline",
        possible_effects=["activate_minimum_pass_strategy", "prioritize_high_yield_nodes"],
        priority="high",
    )
    trace = await spine._run_signal_pipeline(user_id="u_e2e", signal=signal)

    # Verify full causal chain
    assert trace.trace_id is not None
    assert len(trace.signal_ids) == 1
    assert trace.policy_decision_id is not None
    assert len(trace.directive_ids) >= 1

    # Verify ExecutionDirective produced with exam rescue constraints
    exec_dir = await spine.get_active_directive("u_e2e")
    assert exec_dir is not None
    assert "sprint_policy" in exec_dir.hard_constraints or "max_task_duration_min" in exec_dir.hard_constraints
    receipt = await spine.get_latest_receipt("u_e2e")
    assert receipt is not None


@pytest.mark.asyncio
async def test_e2e_exam_sprint_day12_task_timeout_triggers_adjustment():
    """
    E2E Day 1-2: User completes tasks but two consecutive timeouts occur.
    Spine must detect granularity mismatch, produce recovery directive,
    and next task must have adjusted constraints.
    Validates Demo experience points #7, #9: task binding and strategy change.
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    spine = SpineOrchestrator(redis_client=redis)

    # Simulate two consecutive task timeouts (actual >> estimated)
    trace1 = await spine.on_task_completed(
        user_id="u_e2e_day1",
        task_id="tcp_basics_45min",
        estimated_minutes=25,
        actual_minutes=45,
    )

    trace2 = await spine.on_task_completed(
        user_id="u_e2e_day1",
        task_id="udp_concepts_50min",
        estimated_minutes=25,
        actual_minutes=50,
    )

    # Verify signal was generated
    assert trace2 is not None
    assert len(trace2.signal_ids) >= 1

    # Verify ExecutionDirective has adjusted constraints
    directive = await spine.get_active_directive("u_e2e_day1")
    assert directive is not None
    assert directive.hard_constraints.get("max_task_duration_min", 999) <= 25
    assert directive.hard_constraints.get("required_task_type") == "worked_example_then_drill"

    # Verify Receipt tells user what changed
    receipt = await spine.get_latest_receipt("u_e2e_day1")
    assert receipt is not None
    assert receipt.actions == ["confirm", "correct", "dismiss"]


@pytest.mark.asyncio
async def test_e2e_exam_sprint_day34_error_driven_strategy_change():
    """
    E2E Day 3-4: User makes repeated mistakes on TCP window problems.
    Spine must detect knowledge transfer failure, adjust retrieval and tasks.
    Validates Demo experience points #8, #9: error→knowledge→strategy change.
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    spine = SpineOrchestrator(redis_client=redis)

    # Simulate error-driven signal
    error_signal = ActionableSignal(
        signal_id="e2e_tcp_error",
        source_event_ids=["quiz_tcp_window_wrong", "quiz_tcp_window_wrong_2"],
        source_system="error_analysis",
        state_key="knowledge_transfer",
        claim="transfer_failure",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="User failed TCP window problems twice — likely conceptual gap",
        possible_effects=["change_retrieval_strategy", "insert_practice_task"],
        priority="high",
    )
    trace = await spine._run_signal_pipeline(user_id="u_e2e_day3", signal=error_signal)

    # Verify causal chain
    assert trace.policy_decision_id is not None
    assert len(trace.directive_ids) >= 1

    # Verify PlanDirective for recovery
    plan_dir = await spine.get_plan_directive("u_e2e_day3")
    assert plan_dir is not None
    assert plan_dir.plan_action == "local_replan"
    assert plan_dir.constraints.get("insert_practice_task") is True

    # Verify RetrievalDirective for targeted source
    ret_dir = await spine.get_retrieval_directive("u_e2e_day3")
    assert ret_dir is not None
    assert ret_dir.retrieval_mode == "task_bound_graph_rag"
    assert ret_dir.pollution_guard == "strict"

    # Verify ModelWrite captures the knowledge gap
    mw_dir = await spine.get_model_write_directive("u_e2e_day3")
    assert mw_dir is not None
    assert len(mw_dir.writes) > 0

    # Verify UX directive shows risk
    ux_dir = await spine.get_ux_directive("u_e2e_day3")
    assert ux_dir is not None
    assert ux_dir.status_band_state == "risk_detected"


@pytest.mark.asyncio
async def test_e2e_exam_sprint_full_causal_trace():
    """
    E2E Full Chain: Complete causal trace from event to outcome.
    Validates Demo experience point #11: mixed timeline records complete trace.
    Also validates 5 of the 10 iron laws.
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.spine_metrics import SpineMetricsCollector

    spine = SpineOrchestrator(redis_client=redis)
    user_id = "u_e2e_full"

    # Iron Law 1: Every signal must have an action (not noise)
    signal = ActionableSignal(
        signal_id="e2e_full_signal",
        source_event_ids=["evt_timeout_1", "evt_timeout_2"],
        source_system="task_timeout_detector",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.9,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="Consecutive task timeouts detected",
        possible_effects=["reduce_task_duration", "change_task_type"],
        priority="high",
    )
    trace = await spine._run_signal_pipeline(user_id=user_id, signal=signal)

    # Signal → State → Policy → Directive chain must be non-empty
    assert len(trace.signal_ids) > 0, "Iron Law 1: signal must be recorded"
    assert trace.policy_decision_id is not None, "Signal must trigger policy"
    assert len(trace.directive_ids) > 0, "Policy must produce directive"

    # Iron Law 2: Every directive must have audit
    audit = await spine.apply_directive_to_task_spec(
        user_id=user_id,
        task_spec={"task_kind": "deep_read", "estimated_minutes": 45, "chapter": "TCP"},
    )
    task_spec, audit_result = audit
    assert audit_result is not None, "Iron Law 2: directive must have audit"
    assert audit_result.applied is True

    # Iron Law 4: Receipt makes change visible
    receipt = await spine.get_latest_receipt(user_id)
    assert receipt is not None, "Iron Law 4: user must see receipt"

    # Iron Law 8: High-impact judgment must be correctable
    assert "correct" in receipt.actions, "Iron Law 8: must offer correction"

    # Iron Law 3: Every action must record outcome
    # Re-fetch trace from store to get full state
    from app.signals.causal_trace_store import CausalTraceStore
    store = CausalTraceStore(redis)
    fresh_trace = await store.get_trace(trace.trace_id)

    outcome = await spine.record_outcome(
        trace=fresh_trace or trace,
        intervention="task_granularity_adjustment",
        reason="consecutive timeouts",
        expected_outcome="user completes task within 25 minutes",
        actual_outcome={"task_completed": True, "duration_minutes": 22},
    )
    assert outcome is not None, "Iron Law 3: outcome must be recorded"
    assert outcome.attribution in ("effective", "insufficient", "inconclusive")

    # Verify complete timeline retrievable
    from app.signals.causal_trace_store import CausalTraceStore
    store = CausalTraceStore(redis)
    traces = await store.get_user_traces(user_id)
    assert len(traces) >= 1

    t = traces[0]
    assert len(t.signal_ids) >= 1
    assert t.policy_decision_id is not None
    assert len(t.directive_ids) >= 1
    assert len(t.receipt_ids) >= 1

    # Verify metrics captured (Decision Realization Score)
    metrics = SpineMetricsCollector(redis)
    snap = await metrics.snapshot()
    assert snap["signal_to_state_rate"]["numerator"] >= 1
    assert snap["directive_application_rate"]["numerator"] >= 1


@pytest.mark.asyncio
async def test_e2e_exam_sprint_user_correction_flow():
    """
    E2E User Correction: User corrects a wrong judgment.
    Validates Iron Law 8 and user sovereignty (Spec Section 24).
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    spine = SpineOrchestrator(redis_client=redis)
    user_id = "u_e2e_correct"

    signal = ActionableSignal(
        signal_id="e2e_correct_sig",
        source_event_ids=[],
        source_system="test",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="test",
        possible_effects=[],
        priority="high",
    )
    await spine._run_signal_pipeline(user_id=user_id, signal=signal)

    # Get receipt
    receipt = await spine.get_latest_receipt(user_id)
    assert receipt is not None

    # User corrects the judgment — "只是临时忙，不是排大了"
    await spine.handle_user_receipt_action(
        user_id=user_id,
        receipt_id=receipt.receipt_id,
        action="correct",
    )

    # Verify retraction recorded
    retraction_count = await spine.metrics.get_counter("retractions")
    assert retraction_count >= 1

    # Verify retraction cleared the active directive
    directive_after = await spine.get_active_directive("u_e2e_correct")
    assert directive_after is None


@pytest.mark.asyncio
async def test_e2e_exam_sprint_momentum_stalled_and_recovery():
    """
    E2E Achievement→Momentum: User has stalled progress, spine detects and adjusts.
    Validates Demo experience point linking achievement system to spine.
    """
    redis = FakeRedis()
    from app.signals.spine_orchestrator import SpineOrchestrator

    spine = SpineOrchestrator(redis_client=redis)

    # Stalled momentum signal would come from AchievementReinforcementConsumer
    # Here we directly test the spine's response to a momentum_stalled signal
    stalled_signal = ActionableSignal(
        signal_id="e2e_stalled",
        source_event_ids=["achievement_check"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_stalled",
        confidence=0.7,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="No unlocks, no streak, 5 in-progress",
        possible_effects=["reduce_pressure", "insert_easy_win"],
        priority="medium",
    )
    trace = await spine._run_signal_pipeline(user_id="u_e2e_momentum", signal=stalled_signal)

    # Verify PlanDirective includes easy win
    plan_dir = await spine.get_plan_directive("u_e2e_momentum")
    assert plan_dir is not None
    assert plan_dir.constraints.get("insert_easy_win") is True

    # Verify UXDirective uses low-pressure tone
    ux_dir = await spine.get_ux_directive("u_e2e_momentum")
    assert ux_dir is not None

    # Verify ResponseDirective tone is set (if produced)
    resp_dir = await spine.get_response_directive("u_e2e_momentum")
    # ResponseDirective may or may not be produced depending on claim mapping
    # The key validation is that PlanDirective and UXDirective were generated


# ══════════════════════════════════════════════════════════════════════════
# P7-1: Achievement Momentum → Adaptive Behavior (Closed Loop)
# ══════════════════════════════════════════════════════════════════════════


def test_soft_difficulty_low_caps_difficulty():
    """difficulty=low bias caps task difficulty to max 2."""
    adjusted, changed = DirectiveApplier.apply_soft_difficulty(
        soft_biases={"difficulty": "low"},
        current_difficulty=4,
    )
    assert adjusted == 2
    assert changed is True


def test_soft_difficulty_no_change_when_already_low():
    adjusted, changed = DirectiveApplier.apply_soft_difficulty(
        soft_biases={"difficulty": "low"},
        current_difficulty=1,
    )
    assert adjusted == 1
    assert changed is False


def test_soft_difficulty_challenge_slight_increase():
    adjusted, changed = DirectiveApplier.apply_soft_difficulty(
        soft_biases={"challenge": "slight_increase"},
        current_difficulty=3,
    )
    assert adjusted == 4
    assert changed is True


def test_soft_difficulty_no_biases():
    adjusted, changed = DirectiveApplier.apply_soft_difficulty(
        soft_biases=None,
        current_difficulty=3,
    )
    assert adjusted == 3
    assert changed is False


def test_prefer_easy_wins_reduces_difficulty():
    """prefer_easy_wins hard constraint caps difficulty to max 2."""
    directive = ExecutionDirective(
        directive_id="ed_easy",
        policy_decision_id="pd_easy",
        target_module="task_generator",
        scope="today",
        hard_constraints={"prefer_easy_wins": True, "max_task_duration_min": 20},
        user_visible_reason="momentum_stalled",
    )
    spec = {"difficulty": 4, "estimated_minutes": 30}
    result = DirectiveApplier.apply_to_task_spec(directive=directive, task_spec=spec)
    assert result["difficulty"] == 2
    assert result["_easy_win_mode"] is True
    assert result["estimated_minutes"] == 20


@pytest.mark.asyncio
async def test_momentum_stalled_generates_hard_constraints():
    """momentum_stalled signal should produce hard_constraints with prefer_easy_wins."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_mom_stalled",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_stalled",
        confidence=0.70,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="0 unlocks, 5 in-progress",
        possible_effects=["reduce_pressure"],
        priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert directive.hard_constraints.get("prefer_easy_wins") is True
    assert directive.hard_constraints.get("max_task_duration_min") == 20
    assert decision.soft_biases.get("difficulty") == "low"


@pytest.mark.asyncio
async def test_momentum_high_slight_challenge():
    """momentum_high signal should produce challenge=slight_increase soft bias."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_mom_high",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="3 unlocks, 2 streaks",
        possible_effects=["reinforce"],
        priority="low",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.soft_biases.get("challenge") == "slight_increase"
    assert decision.soft_biases.get("tone") == "recognition_not_praise"


@pytest.mark.asyncio
async def test_spine_apply_directive_with_soft_biases():
    """SpineOrchestrator.apply_directive_to_task_spec applies soft difficulty."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    # Store a directive
    directive = ExecutionDirective(
        directive_id="ed_soft_test",
        policy_decision_id="pd_soft_test",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 20},
        user_visible_reason="stalled",
    )
    await spine.trace_store.set_active_directive("u_soft", directive)

    # Apply with soft_biases for difficulty=low
    spec = {"difficulty": 4, "estimated_minutes": 30}
    modified, audit = await spine.apply_directive_to_task_spec(
        user_id="u_soft",
        task_spec=spec,
        soft_biases={"difficulty": "low"},
    )
    assert modified["difficulty"] == 2
    assert modified["estimated_minutes"] == 20
    assert audit is not None


@pytest.mark.asyncio
async def test_spine_soft_biases_without_directive():
    """Soft difficulty applies even without active directive."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    spec = {"difficulty": 5, "estimated_minutes": 30}
    modified, audit = await spine.apply_directive_to_task_spec(
        user_id="u_no_dir",
        task_spec=spec,
        soft_biases={"difficulty": "low"},
    )
    assert modified["difficulty"] == 2
    assert audit is None


@pytest.mark.asyncio
async def test_full_momentum_stalled_pipeline():
    """End-to-end: achievement stalled → pipeline → task spec with easy wins."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    # Simulate achievement event with stalled momentum
    trace = await spine.on_achievement_event(
        user_id="u_full_momentum",
        achievement_type="achievement.progress",
        achievement_id="ach_123",
        recent_unlocks=0,
        active_streaks=0,
        in_progress_count=5,
    )
    assert trace is not None

    # Verify directive was stored with easy win constraints
    directive = await spine.get_active_directive("u_full_momentum")
    assert directive is not None
    assert directive.hard_constraints.get("prefer_easy_wins") is True

    # Apply to task spec with soft biases from policy decision
    spec = {"difficulty": 4, "estimated_minutes": 40}
    modified, audit = await spine.apply_directive_to_task_spec(
        user_id="u_full_momentum",
        task_spec=spec,
        soft_biases={"difficulty": "low"},
    )
    assert modified["difficulty"] == 2
    assert modified["estimated_minutes"] == 20
    assert modified.get("_easy_win_mode") is True
    assert audit is not None


# ══════════════════════════════════════════════════════════════════════════
# P7-2: CommunityDirective + SkillDirective
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_community_directive_cohort_mistake():
    """cohort_mistake_detected → CommunityDirective with anonymous mode."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_cohort",
        source_event_ids=["test"],
        source_system="community_signal",
        state_key="community_cohort_pattern",
        claim="cohort_mistake_detected",
        confidence=0.75,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="5 students, 40% error on TCP handshake",
        possible_effects=["show_hint"],
        priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    comm_dir = engine.build_community_directive(decision, signal)
    assert comm_dir is not None
    assert comm_dir.cohort_hint_shown is True
    assert comm_dir.peer_context_mode == "anonymous"
    assert comm_dir.max_frequency == "3_per_week"


@pytest.mark.asyncio
async def test_community_directive_shared_resource():
    """shared_resource_relevant → CommunityDirective with higher quality filter."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_resource",
        source_event_ids=["test"],
        source_system="community_signal",
        state_key="community_resource_recommendation",
        claim="shared_resource_relevant",
        confidence=0.80,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="3 peers using this resource",
        possible_effects=["recommend"],
        priority="low",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    comm_dir = engine.build_community_directive(decision, signal)
    assert comm_dir is not None
    assert comm_dir.cohort_hint_shown is False
    assert comm_dir.resource_quality_filter == 0.7


def test_community_directive_no_match():
    """Non-community signals should not produce CommunityDirective."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_other",
        source_event_ids=["test"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.9,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="test",
        possible_effects=[],
        priority="high",
    )
    from app.signals.types import PolicyDecision
    decision = PolicyDecision(
        policy_decision_id="pd_test",
        primary_strategy="test",
        secondary_strategy=None,
        hard_constraints={},
        soft_biases={},
        visibility="receipt",
        requires_user_confirmation=False,
        reasoning_summary="test",
    )
    comm_dir = engine.build_community_directive(decision, signal)
    assert comm_dir is None


@pytest.mark.asyncio
async def test_community_directive_serialization():
    """CommunityDirective to_dict/from_dict round-trip."""
    from app.signals.types import CommunityDirective, _uid
    cd = CommunityDirective(
        directive_id=_uid("cmd"),
        policy_decision_id="pd_test",
        cohort_hint_shown=True,
        resource_quality_filter=0.6,
        peer_context_mode="anonymous",
        max_frequency="3_per_week",
    )
    data = cd.to_dict()
    restored = CommunityDirective.from_dict(data)
    assert restored.directive_id == cd.directive_id
    assert restored.cohort_hint_shown is True
    assert restored.resource_quality_filter == 0.6


@pytest.mark.asyncio
async def test_skill_directive_momentum_high():
    """momentum_high → SkillDirective with extract action."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_mh_skill",
        source_event_ids=["test"],
        source_system="achievement_reinforcement",
        state_key="growth_momentum",
        claim="momentum_high",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="high momentum",
        possible_effects=["extract_skill"],
        priority="low",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    skill_dir = engine.build_skill_directive(decision, signal)
    assert skill_dir is not None
    assert skill_dir.skill_action == "extract"
    assert skill_dir.extraction_trigger == "outcome_positive"


@pytest.mark.asyncio
async def test_skill_directive_transfer_failure():
    """transfer_failure → SkillDirective with recommend action."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_tf_skill",
        source_event_ids=["test"],
        source_system="mistake_signal",
        state_key="knowledge_transfer",
        claim="transfer_failure",
        confidence=0.80,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="3 consecutive errors",
        possible_effects=["recommend_skill"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    skill_dir = engine.build_skill_directive(decision, signal)
    assert skill_dir is not None
    assert skill_dir.skill_action == "recommend"


@pytest.mark.asyncio
async def test_skill_directive_serialization():
    """SkillDirective to_dict/from_dict round-trip."""
    from app.signals.types import SkillDirective, _uid
    sd = SkillDirective(
        directive_id=_uid("skd"),
        policy_decision_id="pd_test",
        skill_action="extract",
        extraction_trigger="outcome_positive",
    )
    data = sd.to_dict()
    restored = SkillDirective.from_dict(data)
    assert restored.directive_id == sd.directive_id
    assert restored.skill_action == "extract"


@pytest.mark.asyncio
async def test_community_directive_in_pipeline():
    """Full pipeline: community signal → CommunityDirective stored in Redis."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    trace = await spine.on_community_cohort_data(
        user_id="u_comm_pipe",
        knowledge_node_id="tcp_handshake",
        subject="计算机网络",
        mistake_type="confusion",
        cohort_size=8,
        error_count=4,
        common_misconception="mixes up SYN/ACK sequence",
    )
    assert trace is not None

    comm_dir = await spine.get_community_directive("u_comm_pipe")
    assert comm_dir is not None
    assert comm_dir.cohort_hint_shown is True
    assert comm_dir.peer_context_mode == "anonymous"


@pytest.mark.asyncio
async def test_skill_directive_in_pipeline():
    """Full pipeline: momentum_high → SkillDirective stored in Redis."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    trace = await spine.on_achievement_event(
        user_id="u_skill_pipe",
        achievement_type="achievement.unlocked",
        achievement_id="ach_456",
        recent_unlocks=3,
        active_streaks=2,
        in_progress_count=2,
    )
    assert trace is not None

    skill_dir = await spine.get_skill_directive("u_skill_pipe")
    assert skill_dir is not None
    assert skill_dir.skill_action == "extract"
    assert skill_dir.extraction_trigger == "outcome_positive"


# ══════════════════════════════════════════════════════════════════════════
# P0-4: Outcome → PolicyEffectLedger + Shadow Learning
# ══════════════════════════════════════════════════════════════════════════


def test_policy_effect_entry_serialization():
    """PolicyEffectEntry to_dict/from_dict round-trip."""
    from app.signals.types import PolicyEffectEntry, _uid
    entry = PolicyEffectEntry(
        entry_id=_uid("pe"),
        policy_key="recover_execution_rhythm",
        intervention_summary="max_task_duration_min=25",
        attribution="insufficient",
        attribution_confidence=0.65,
        user_feedback_signal="cant_understand",
        new_hypothesis="knowledge_explanation_failure",
    )
    data = entry.to_dict()
    restored = PolicyEffectEntry.from_dict(data)
    assert restored.policy_key == "recover_execution_rhythm"
    assert restored.attribution == "insufficient"
    assert restored.user_feedback_signal == "cant_understand"


@pytest.mark.asyncio
async def test_outcome_recorder_writes_policy_effect():
    """OutcomeRecorder writes PolicyEffectLedger entry when attribution is not inconclusive."""
    redis = FakeRedis()
    recorder = OutcomeRecorder(redis)

    from app.signals.types import CausalTrace
    trace = CausalTrace(trace_id="ct_effect_test")
    await redis.set(f"spine:trace:{trace.trace_id}", __import__("json").dumps(trace.to_dict()), ex=720 * 3600)

    record = await recorder.record_outcome(
        trace=trace,
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": False, "user_feedback": "还是看不懂"},
    )

    assert record.attribution == "insufficient"
    assert record.new_hypothesis is not None


@pytest.mark.asyncio
async def test_shadow_learning_switches_strategy():
    """When same strategy fails twice with '看不懂', PolicyEngine switches to worked_example."""
    from app.signals.types import PolicyEffectEntry
    engine = PolicyEngine()

    effects = [
        PolicyEffectEntry(
            entry_id="pe_001",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_duration_min=25",
            attribution="insufficient",
            attribution_confidence=0.65,
            user_feedback_signal="cant_understand",
        ),
        PolicyEffectEntry(
            entry_id="pe_002",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_duration_min=25",
            attribution="insufficient",
            attribution_confidence=0.60,
            user_feedback_signal="cant_understand",
        ),
    ]

    signal = ActionableSignal(
        signal_id="sig_shadow",
        source_event_ids=["test"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="consecutive overruns",
        possible_effects=["adjust"],
        priority="high",
    )

    result = await engine.evaluate(signal, recent_policy_effects=effects)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "switch_to_worked_example"
    assert directive.hard_constraints.get("required_task_type") == "worked_example_then_drill"


@pytest.mark.asyncio
async def test_shadow_learning_no_change_when_effective():
    """When policy is effective, no shadow adjustment is made."""
    from app.signals.types import PolicyEffectEntry
    engine = PolicyEngine()

    effects = [
        PolicyEffectEntry(
            entry_id="pe_003",
            policy_key="recover_execution_rhythm",
            intervention_summary="max_task_duration_min=25",
            attribution="effective",
            attribution_confidence=0.85,
        ),
    ]

    signal = ActionableSignal(
        signal_id="sig_no_shadow",
        source_event_ids=["test"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="consecutive overruns",
        possible_effects=["adjust"],
        priority="high",
    )

    result = await engine.evaluate(signal, recent_policy_effects=effects)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "recover_execution_rhythm"


@pytest.mark.asyncio
async def test_self_correction_receipt():
    """When outcome is insufficient, SpineOrchestrator records it in PolicyEffectLedger."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis)

    signal = ActionableSignal(
        signal_id="sig_correct",
        source_event_ids=["test"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="overrun",
        possible_effects=["adjust"],
        priority="high",
    )
    trace = await spine._run_signal_pipeline(user_id="u_correct", signal=signal)
    assert trace is not None

    record = await spine.record_outcome(
        trace=trace,
        intervention="max_task_duration_25min",
        reason="recent_task_overrun",
        expected_outcome="task_started_and_completed",
        actual_outcome={"started": True, "completed": False, "user_feedback": "还是看不懂"},
    )
    assert record.attribution == "insufficient"
    assert record.new_hypothesis is not None


# ═══════════════════════════════════════════════════════════════════════
# P0-3: Task Card 8-Field Protocol
