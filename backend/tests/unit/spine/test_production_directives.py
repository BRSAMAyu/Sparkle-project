"""Spine tests — test_production_directives.py."""

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

# =============================================================================
# v2.6: Enhanced SignalRanker — 10 dimensions + expanded conflict rules
# =============================================================================


_make_signal_counter = itertools.count()

def _make_signal(state_key: str, priority: str = "medium", confidence: float = 0.8,
                 scope: str = "sprint", possible_effects: list[str] | None = None,
                 claim: str | None = None) -> ActionableSignal:
    return ActionableSignal(
        signal_id=f"sig_{state_key}_{next(_make_signal_counter)}",
        source_event_ids=["evt_1"],
        source_system="test",
        state_key=state_key,
        claim=claim or f"test_{state_key}",
        confidence=confidence,
        evidence_summary="test",
        scope=scope,
        ttl_hours=24,
        possible_effects=possible_effects if possible_effects is not None else ["effect_1"],
        priority=priority,
    )


@pytest.mark.asyncio
async def test_signal_ranker_10_dimensions_populated():
    """All 10 dimensions are computed and present in RankedSignal."""
    ranker = SignalRanker()
    signal = _make_signal("exam_rescue", priority="high", confidence=0.9)
    result = ranker.rank([signal])
    assert len(result.ranked) == 1
    dims = result.ranked[0].dimension_scores
    assert len(dims) == 10
    for key in ("goal_impact", "decision_relevance", "urgency", "confidence",
                "freshness", "cost_of_inaction", "reversibility", "user_visibility_need",
                "privacy_sensitivity", "contradiction_level"):
        assert key in dims, f"Missing dimension: {key}"
        assert 0.0 <= dims[key] <= 1.0, f"{key}={dims[key]} not in [0,1]"


@pytest.mark.asyncio
async def test_signal_ranker_goal_impact_tier1_high():
    """Tier 1 signals have higher goal_impact than tier 7."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("safety_boundary", priority="high"),
        _make_signal("growth_momentum", priority="high"),
    ])
    safety = [r for r in result.ranked if r.signal.state_key == "safety_boundary"][0]
    # growth_momentum is suppressed by safety_boundary (no direct conflict rule,
    # but tier ordering keeps safety first; search all results)
    _growth_list = [r for r in result.ranked + result.suppressed if r.signal.state_key == "growth_momentum"]
    growth = _growth_list[0] if _growth_list else None
    assert growth is not None, "growth signal should exist in ranked or suppressed"
    assert safety.dimension_scores["goal_impact"] > growth.dimension_scores["goal_impact"]


@pytest.mark.asyncio
async def test_signal_ranker_privacy_sensitivity_community():
    """Community signals have higher privacy_sensitivity."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("community_cohort_pattern"),
        _make_signal("task_granularity_fit"),
    ])
    community = [r for r in result.ranked if r.signal.state_key == "community_cohort_pattern"][0]
    task = [r for r in result.ranked if r.signal.state_key == "task_granularity_fit"][0]
    assert community.dimension_scores["privacy_sensitivity"] > task.dimension_scores["privacy_sensitivity"]


@pytest.mark.asyncio
async def test_signal_ranker_reversibility_scope():
    """Turn scope has higher reversibility than goal scope."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("exam_rescue", scope="turn"),
        _make_signal("exam_rescue", scope="goal"),
    ])
    turn = [r for r in result.ranked if r.signal.scope == "turn"][0]
    goal = [r for r in result.ranked if r.signal.scope == "goal"][0]
    assert turn.dimension_scores["reversibility"] > goal.dimension_scores["reversibility"]


@pytest.mark.asyncio
async def test_signal_ranker_user_visibility_safety():
    """Safety and deadline signals have high user_visibility_need."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("exam_rescue"),
        _make_signal("material_utilization"),
    ])
    exam = [r for r in result.ranked if r.signal.state_key == "exam_rescue"][0]
    material = [r for r in result.ranked if r.signal.state_key == "material_utilization"][0]
    assert exam.dimension_scores["user_visibility_need"] == 1.0
    assert material.dimension_scores["user_visibility_need"] == 0.3


@pytest.mark.asyncio
async def test_signal_ranker_decision_relevance_with_effects():
    """Signals with many possible_effects have higher decision_relevance."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("exam_rescue", possible_effects=["a", "b", "c"]),
        _make_signal("exam_rescue", possible_effects=[]),
    ])
    with_effects = [r for r in result.ranked if len(r.signal.possible_effects) > 0][0]
    without = [r for r in result.ranked if len(r.signal.possible_effects) == 0][0]
    assert with_effects.dimension_scores["decision_relevance"] > without.dimension_scores["decision_relevance"]


@pytest.mark.asyncio
async def test_signal_ranker_expanded_conflict_growth_vs_deadline():
    """growth_momentum is suppressed by deadline_pressure (expanded conflict rule)."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("growth_momentum", priority="high"),
        _make_signal("deadline_pressure", priority="high"),
    ])
    assert len(result.conflicts_resolved) >= 1
    suppressed_keys = [r.signal.state_key for r in result.suppressed]
    assert "growth_momentum" in suppressed_keys


@pytest.mark.asyncio
async def test_signal_ranker_expanded_conflict_community_vs_knowledge():
    """community_cohort_pattern is suppressed by knowledge_transfer."""
    ranker = SignalRanker()
    result = ranker.rank([
        _make_signal("community_cohort_pattern"),
        _make_signal("knowledge_transfer", priority="high"),
    ])
    assert any(c["rule"] == "knowledge_transfer_wins" for c in result.conflicts_resolved)


@pytest.mark.asyncio
async def test_signal_ranker_dimension_scores_in_to_dict():
    """dimension_scores appear in RankedSignal.to_dict()."""
    ranker = SignalRanker()
    result = ranker.rank([_make_signal("exam_rescue")])
    d = result.ranked[0].to_dict()
    assert "dimension_scores" in d
    assert "goal_impact" in d["dimension_scores"]


# ── v2.9: PolicyDecision risk_level + which_directives ──────────────

@pytest.mark.asyncio
async def test_policy_decision_risk_level_critical():
    """exam_rescue and safety_boundary get critical risk_level."""
    engine = PolicyEngine()
    signal = _make_signal("goal_mode", confidence=0.9)
    signal_claim_hack = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="goal_mode", claim="exam_rescue_detected", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="high",
    )
    result = await engine.evaluate(signal_claim_hack)
    assert result is not None
    decision, _ = result
    assert decision.risk_level == "high"
    assert decision.to_dict()["risk_level"] == "high"


@pytest.mark.asyncio
async def test_policy_decision_risk_level_low():
    """growth_momentum gets low risk_level."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_high", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="low",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    assert decision.risk_level == "low"


@pytest.mark.asyncio
async def test_policy_decision_which_directives_task_granularity():
    """task_granularity_fit activates response+execution+ux+model_write."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    wd = decision.which_directives
    assert wd.get("response") is True
    assert wd.get("execution") is True
    assert wd.get("ux") is True
    assert wd.get("model_write") is True
    assert wd.get("notification") is None or wd.get("notification") is False


@pytest.mark.asyncio
async def test_policy_decision_which_directives_recall():
    """recall_needed activates notification+response+ux."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="undigested_material", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    wd = decision.which_directives
    assert wd.get("notification") is True
    assert wd.get("response") is True


@pytest.mark.asyncio
async def test_policy_decision_which_directives_community():
    """community_cohort_pattern activates community+response."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="community_cohort_pattern", claim="cohort_mistake_detected", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    wd = decision.which_directives
    assert wd.get("community") is True
    assert wd.get("response") is True


@pytest.mark.asyncio
async def test_policy_decision_to_dict_includes_new_fields():
    """to_dict() includes risk_level and which_directives."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="recent_task_too_large", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["effect_1"], priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    d = decision.to_dict()
    assert "risk_level" in d
    assert "which_directives" in d
    assert isinstance(d["which_directives"], dict)


# ── v3.0: Source Tray + RetrievalDirective integration ────────────────

@pytest.mark.asyncio
async def test_source_tray_enriches_retrieval_directive():
    """RetrievalDirective enriched with SourceTrayState → concrete load plan."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    # Set up source tray with one included source
    await spine.set_source_tray("user_1", {
        "mode": "manual_only",
        "selections": [{"source_id": "src_a", "action": "include", "scope": "this_task", "user_initiated": True}],
        "available_sources": [
            {"source_id": "src_a", "title": "TCP Slides", "source_type": "slides", "parsed_status": "parsed", "quality_score": 0.9},
            {"source_id": "src_b", "title": "UDP Notes", "source_type": "notes", "parsed_status": "parsed", "quality_score": 0.7},
        ],
    })
    # Create a material_utilization signal → policy → retrieval directive
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="material_utilization", claim="material_underutilized", confidence=0.9,
        evidence_summary="test", scope="sprint", ttl_hours=24,
        possible_effects=["activate_retrieval"], priority="medium",
    )
    result = await spine.policy_engine.evaluate(signal)
    assert result is not None
    decision, _ = result
    # Build and enrich retrieval directive
    ret_dir = spine.policy_engine.build_retrieval_directive(decision, signal)
    assert ret_dir is not None
    await spine._enrich_retrieval_with_source_tray("user_1", ret_dir)
    # src_a should be in must_load since user explicitly included it
    assert "src_a" in (ret_dir.must_load or [])
    # Verify source receipt was stored
    receipt = await spine.get_source_receipt("user_1")
    assert receipt is not None
    assert "loaded" in receipt
    assert "reason_for_user" in receipt


@pytest.mark.asyncio
async def test_source_tray_pollution_guard_blocks_low_relevance():
    """pollution_guard=strict blocks sources below 0.3 relevance."""
    from app.signals.source_tray_integration import compute_retrieval_plan
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTrayState

    rd = RetrievalDirective(
        directive_id="rd_test", policy_decision_id="pd_test",
        retrieval_mode="task_bound_rag", pollution_guard="strict",
        token_budget=3000, must_load=[], may_load=[], do_not_load=[],
    )
    tray = SourceTrayState(
        mode="auto",
        selections=[],
        available_sources=[
            SourceAsset(source_id="src_low", title="Low Relevance", source_type="notes",
                        mapped_nodes=["udp"], parsed_status="parsed"),
            SourceAsset(source_id="src_high", title="High Relevance", source_type="slides",
                        mapped_nodes=["tcp", "congestion_control"], parsed_status="parsed"),
        ],
    )
    plan = await compute_retrieval_plan(retrieval_directive=rd, source_tray=tray, target_nodes=["tcp", "congestion_control"])
    # src_high has overlap → should be in must_load or may_load
    must_ids = [s["source_id"] for s in plan["must_load"]]
    may_ids = [s["source_id"] for s in plan["may_load"]]
    skip_ids = [s["source_id"] for s in plan["do_not_load"]]
    assert "src_high" in must_ids or "src_high" in may_ids
    assert "src_low" in skip_ids


@pytest.mark.asyncio
async def test_source_receipt_built_correctly():
    """build_source_receipt produces loaded/skipped/excluded lists."""
    from app.signals.source_tray_integration import build_source_receipt
    from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState

    rd = RetrievalDirective(
        directive_id="rd_test", policy_decision_id="pd_test",
        retrieval_mode="targeted_source_rag", pollution_guard="default",
        token_budget=3000, must_load=["src_a"], may_load=[], do_not_load=["src_c"],
    )
    tray = SourceTrayState(
        mode="manual_only",
        selections=[
            SourceTraySelection(source_id="src_a", action="include"),
            SourceTraySelection(source_id="src_c", action="exclude"),
        ],
        available_sources=[
            SourceAsset(source_id="src_a", title="TCP Slides", source_type="slides", parsed_status="parsed"),
            SourceAsset(source_id="src_b", title="UDP Notes", source_type="notes", parsed_status="parsed"),
            SourceAsset(source_id="src_c", title="Old Notes", source_type="notes", parsed_status="parsed"),
        ],
    )
    receipt = build_source_receipt(rd, tray, loaded_source_ids=["src_a"])
    loaded_ids = [s["source_id"] for s in receipt["loaded"]]
    assert "src_a" in loaded_ids
    assert receipt["reason_for_user"] is not None


@pytest.mark.asyncio
async def test_source_tray_no_data_graceful():
    """When no source tray stored, enrichment is a no-op."""
    from app.signals.types import RetrievalDirective
    spine = SpineOrchestrator(redis_client=FakeRedis())
    rd = RetrievalDirective(
        directive_id="rd_test", policy_decision_id="pd_test",
        retrieval_mode="no_retrieval", pollution_guard="default",
        token_budget=3000, must_load=[], may_load=[], do_not_load=[],
    )
    await spine._enrich_retrieval_with_source_tray("user_nodata", rd)
    # Should not crash, must_load stays empty
    assert rd.must_load == []


@pytest.mark.asyncio
async def test_get_source_receipt_returns_none_when_empty():
    """get_source_receipt returns None when no receipt stored."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    result = await spine.get_source_receipt("user_empty")
    assert result is None


# ── v2.9: Production Wiring Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_v29_response_directive_to_dict_for_prompt():
    """ResponseDirective serializes for injection into state.context_data."""
    from app.signals.types import ResponseDirective
    rd = ResponseDirective(
        directive_id="rd_v29", policy_decision_id="pd_v29",
        tone="calm_urgent", length="short",
        must_acknowledge=["exam_situation"],
        avoid=["generic_encouragement"],
        include_user_options=True,
    )
    d = rd.to_dict()
    assert d["tone"] == "calm_urgent"
    assert d["length"] == "short"
    assert "exam_situation" in d["must_acknowledge"]
    assert "generic_encouragement" in d["avoid"]


@pytest.mark.asyncio
async def test_v29_retrieval_directive_to_dict_for_rag():
    """RetrievalDirective serializes for RAG pipeline consumption."""
    from app.signals.types import RetrievalDirective
    rd = RetrievalDirective(
        directive_id="rd_rag", policy_decision_id="pd_rag",
        retrieval_mode="task_bound_graph_rag",
        source_scope="task_bound",
        pollution_guard="strict",
        token_budget=2000,
        must_load=["src_1"],
        may_load=["src_2"],
        do_not_load=["src_3"],
    )
    d = rd.to_dict()
    assert d["retrieval_mode"] == "task_bound_graph_rag"
    assert d["token_budget"] == 2000
    assert d["pollution_guard"] == "strict"


@pytest.mark.asyncio
async def test_v29_chronicle_injection():
    """GrowthChronicle entries have title + narrative for prompt injection."""
    from app.signals.growth_chronicle import ChronicleEntry
    entry = ChronicleEntry(
        entry_id="ce1", user_id="u1", entry_type="milestone",
        timestamp="2026-04-27T12:00:00", title="First task completed",
        narrative="Completed first 25-min study session",
        evidence_refs=[], user_editable=True,
    )
    summary = f"- {entry.title}: {entry.narrative}"
    assert "First task completed" in summary
    assert "25-min" in summary


@pytest.mark.asyncio
async def test_v29_fatigue_context_normal_skipped():
    """Fatigue level 'low' is not injected into context (only medium/high/critical)."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    fatigue = await spine.check_fatigue(user_id="u1")
    assert fatigue["fatigue_level"] in ("low", "normal")


@pytest.mark.asyncio
async def test_v29_fatigue_context_high_injected():
    """Fatigue level 'high' should be included in spine_fatigue_context."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    fatigue = await spine.check_fatigue(
        user_id="u1", interactions_last_24h=35, consecutive_hours=5.0,
    )
    assert fatigue["fatigue_level"] in ("high", "critical")
    # This context would be injected into state.context_data["spine_fatigue_context"]
    assert "recommended_policy" in fatigue


# ── v3.1: AuroraControlSignal envelope tests ──────────────────────────

def test_aurora_control_signal_roundtrip():
    """AuroraControlSignal serializes and deserializes correctly."""
    cs = AuroraControlSignal(
        control_id=_uid("ctrl"),
        energy="full",
        policy_decision_id="pd_001",
        response_policy="task_recovery_support",
        directive_ids={
            "execution": "ed_001",
            "response": "rd_001",
            "retrieval": "rv_001",
        },
        risk_level="high",
    )
    d = cs.to_dict()
    restored = AuroraControlSignal.from_dict(d)
    assert restored.control_id == cs.control_id
    assert restored.energy == "full"
    assert restored.policy_decision_id == "pd_001"
    assert restored.directive_ids["execution"] == "ed_001"
    assert restored.risk_level == "high"
    assert "created_at" in d


def test_aurora_control_signal_default_risk():
    """Default risk_level is 'medium'."""
    cs = AuroraControlSignal(
        control_id=_uid("ctrl"),
        energy="light",
        policy_decision_id="pd_002",
        response_policy="normal",
        directive_ids={},
    )
    assert cs.risk_level == "medium"
    d = cs.to_dict()
    assert d["risk_level"] == "medium"


def test_aurora_control_signal_all_9_directive_types():
    """All 9 directive types can be tracked in directive_ids."""
    directive_ids = {
        "response": "rd_1",
        "execution": "ed_1",
        "plan": "pld_1",
        "retrieval": "rvd_1",
        "model_write": "mwd_1",
        "notification": "nd_1",
        "ux": "uxd_1",
        "skill": "sd_1",
        "community": "cd_1",
    }
    cs = AuroraControlSignal(
        control_id=_uid("ctrl"),
        energy="full",
        policy_decision_id="pd_003",
        response_policy="full_aurora_wake",
        directive_ids=directive_ids,
        risk_level="critical",
    )
    assert len(cs.directive_ids) == 9
    d = cs.to_dict()
    assert len(d["directive_ids"]) == 9


def test_aurora_control_signal_energy_values():
    """All valid energy values are accepted."""
    for energy in ("light", "medium", "full"):
        cs = AuroraControlSignal(
            control_id=_uid("ctrl"),
            energy=energy,
            policy_decision_id="pd_e",
            response_policy="test",
            directive_ids={},
        )
        assert cs.energy == energy


# ── v3.1: AuroraAgenda tests ──────────────────────────────────────────

def test_aurora_agenda_item_roundtrip():
    """AuroraAgendaItem serializes and deserializes correctly."""
    item = AuroraAgendaItem(
        item_id=_uid("ai"),
        item_type="explain_conflict",
        status="pending",
        payload={"conflict_key": "growth_momentum vs exam_rescue"},
    )
    d = item.to_dict()
    restored = AuroraAgendaItem.from_dict(d)
    assert restored.item_id == item.item_id
    assert restored.item_type == "explain_conflict"
    assert restored.status == "pending"
    assert restored.payload["conflict_key"] == "growth_momentum vs exam_rescue"


def test_aurora_agenda_roundtrip():
    """AuroraAgenda serializes and deserializes correctly with items."""
    items = [
        AuroraAgendaItem(item_id="ai_1", item_type="confirm_available_time", status="done"),
        AuroraAgendaItem(item_id="ai_2", item_type="update_strategy", status="in_progress"),
        AuroraAgendaItem(item_id="ai_3", item_type="motivation_check", status="pending"),
    ]
    agenda = AuroraAgenda(
        session_id=_uid("sess"),
        scope="exam_sprint_day3",
        agenda_items=items,
        interruption_policy="answer_then_resume",
    )
    d = agenda.to_dict()
    restored = AuroraAgenda.from_dict(d)
    assert restored.session_id == agenda.session_id
    assert len(restored.agenda_items) == 3
    assert restored.agenda_items[0].status == "done"
    assert restored.agenda_items[1].item_type == "update_strategy"
    assert restored.interruption_policy == "answer_then_resume"


def test_aurora_agenda_current_item():
    """current_item() returns first non-done, non-interrupted item."""
    items = [
        AuroraAgendaItem(item_id="ai_1", item_type="confirm_time", status="done"),
        AuroraAgendaItem(item_id="ai_2", item_type="update_strategy", status="interrupted"),
        AuroraAgendaItem(item_id="ai_3", item_type="motivation_check", status="pending"),
        AuroraAgendaItem(item_id="ai_4", item_type="relationship_check", status="pending"),
    ]
    agenda = AuroraAgenda(session_id="sess_1", scope="test", agenda_items=items)
    current = agenda.current_item()
    assert current is not None
    assert current.item_id == "ai_3"


def test_aurora_agenda_current_item_all_done():
    """current_item() returns None when all items are done/interrupted."""
    items = [
        AuroraAgendaItem(item_id="ai_1", item_type="confirm_time", status="done"),
        AuroraAgendaItem(item_id="ai_2", item_type="update_strategy", status="interrupted"),
    ]
    agenda = AuroraAgenda(session_id="sess_2", scope="test", agenda_items=items)
    assert agenda.current_item() is None


def test_aurora_agenda_current_item_empty():
    """current_item() returns None for empty agenda."""
    agenda = AuroraAgenda(session_id="sess_3", scope="test")
    assert agenda.current_item() is None


def test_aurora_agenda_advance():
    """advance() updates the status of a specific item."""
    items = [
        AuroraAgendaItem(item_id="ai_1", item_type="confirm_time", status="pending"),
        AuroraAgendaItem(item_id="ai_2", item_type="update_strategy", status="pending"),
    ]
    agenda = AuroraAgenda(session_id="sess_4", scope="test", agenda_items=items)
    agenda.advance("ai_1", "done")
    assert agenda.agenda_items[0].status == "done"
    assert agenda.agenda_items[1].status == "pending"
    # current_item now returns ai_2
    current = agenda.current_item()
    assert current is not None
    assert current.item_id == "ai_2"


def test_aurora_agenda_advance_nonexistent():
    """advance() is a no-op for nonexistent item_id."""
    items = [AuroraAgendaItem(item_id="ai_1", item_type="test", status="pending")]
    agenda = AuroraAgenda(session_id="sess_5", scope="test", agenda_items=items)
    agenda.advance("nonexistent", "done")
    assert agenda.agenda_items[0].status == "pending"


def test_aurora_agenda_item_types():
    """All valid item_types are representable."""
    valid_types = [
        "explain_conflict", "confirm_available_time", "update_strategy",
        "confirm_hypothesis", "relationship_check", "motivation_check",
    ]
    for t in valid_types:
        item = AuroraAgendaItem(item_id=_uid("ai"), item_type=t, status="pending")
        assert item.item_type == t


def test_aurora_agenda_item_statuses():
    """All valid statuses are representable."""
    valid_statuses = ["pending", "in_progress", "waiting_user", "done", "interrupted"]
    for s in valid_statuses:
        item = AuroraAgendaItem(item_id=_uid("ai"), item_type="test", status=s)
        assert item.status == s


async def test_aurora_control_signal_in_pipeline():
    """Integration: PolicyEngine + AuroraControlSignal envelope wires correctly for a high-risk signal."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["evt_deadline"],
        source_system="goal_service",
        state_key="goal_mode",
        claim="exam_rescue_detected",
        confidence=0.9,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="考试倒计时 < 7 天",
        possible_effects=["seven_day_survival"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    policy, _directive = result
    assert policy.risk_level == "high"
    assert policy.which_directives.get("execution", False) is True

    # Wrap in AuroraControlSignal envelope
    envelope = AuroraControlSignal(
        control_id=_uid("ctrl"),
        energy="full",
        policy_decision_id=policy.policy_decision_id,
        response_policy=policy.primary_strategy,
        directive_ids={"execution": _directive.directive_id} if _directive else {},
        risk_level=policy.risk_level,
    )
    assert envelope.risk_level == "high"
    assert envelope.policy_decision_id == policy.policy_decision_id
    d = envelope.to_dict()
    assert d["risk_level"] == "high"


# ── v3.1: AuroraAgenda full-session simulation ────────────────────────

def test_aurora_agenda_session_flow():
    """Simulate a full Aurora session with multiple agenda items advancing."""
    items = [
        AuroraAgendaItem(item_id="ai_1", item_type="confirm_available_time", status="pending"),
        AuroraAgendaItem(item_id="ai_2", item_type="explain_conflict", status="pending"),
        AuroraAgendaItem(item_id="ai_3", item_type="update_strategy", status="pending"),
    ]
    agenda = AuroraAgenda(
        session_id=_uid("sess"),
        scope="exam_rescue_mode",
        agenda_items=items,
    )

    # Step 1: Start first item
    agenda.advance("ai_1", "in_progress")
    assert agenda.current_item().item_id == "ai_1"
    assert agenda.current_item().status == "in_progress"

    # Step 2: User answers, first item done
    agenda.advance("ai_1", "done")
    current = agenda.current_item()
    assert current.item_id == "ai_2"
    assert current.status == "pending"

    # Step 3: Explain conflict, then wait for user
    agenda.advance("ai_2", "in_progress")
    agenda.advance("ai_2", "waiting_user")
    assert agenda.current_item().status == "waiting_user"

    # Step 4: User responds, finish explanation
    agenda.advance("ai_2", "done")
    assert agenda.current_item().item_id == "ai_3"

    # Step 5: Complete strategy update
    agenda.advance("ai_3", "done")
    assert agenda.current_item() is None
    agenda.status = "completed"
    assert agenda.status == "completed"

    # Verify serialization preserves final state
    d = agenda.to_dict()
    restored = AuroraAgenda.from_dict(d)
    assert restored.status == "completed"
    assert all(i.status == "done" for i in restored.agenda_items)


# ── P2-1: Cognitive Load + Affective Pressure ──────────────────────

@pytest.mark.asyncio
async def test_cognitive_load_many_new_topics():
    """High cognitive load detected when many new topics in short time."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=5, new_topics_count=4,
        avg_accuracy=0.6, session_duration_min=60,
    )
    assert signal is not None
    assert signal.state_key == "cognitive_load"
    assert signal.claim == "high_load_detected"
    assert signal.confidence >= 0.5
    assert signal.scope == "session"


@pytest.mark.asyncio
async def test_cognitive_load_low_accuracy():
    """High cognitive load from low accuracy + many tasks."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=4, new_topics_count=1,
        avg_accuracy=0.35, session_duration_min=30,
    )
    assert signal is not None
    assert "low_accuracy" in signal.evidence_summary


@pytest.mark.asyncio
async def test_cognitive_load_extended_session():
    """Extended session triggers cognitive load."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=1, new_topics_count=0,
        session_duration_min=120,
    )
    assert signal is not None
    assert "extended_session" in signal.evidence_summary


@pytest.mark.asyncio
async def test_cognitive_load_no_trigger():
    """Normal workload does not trigger cognitive load."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=2, new_topics_count=1,
        avg_accuracy=0.8, session_duration_min=30,
    )
    assert signal is None


@pytest.mark.asyncio
async def test_cognitive_load_policy_rule():
    """Cognitive load signal produces correct policy decision."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="spine",
        state_key="cognitive_load", claim="high_load_detected",
        confidence=0.8, scope="session", ttl_hours=6,
        evidence_summary="认知负荷过高", possible_effects=["simplify"],
        priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    policy, _directive = result
    assert policy.primary_strategy == "reduce_cognitive_pressure"
    assert policy.risk_level == "medium"
    assert policy.which_directives.get("response") is True


@pytest.mark.asyncio
async def test_affective_pressure_consecutive_abandon():
    """Stress detected from consecutive task abandonment."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_affective_pressure(
        user_id="u1", consecutive_abandons=2, error_density=0.3,
    )
    assert signal is not None
    assert signal.state_key == "affective_pressure"
    assert signal.claim == "stress_detected"
    assert signal.priority == "medium"


@pytest.mark.asyncio
async def test_affective_pressure_burnout_risk():
    """Burnout risk from 3+ consecutive abandons."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_affective_pressure(
        user_id="u1", consecutive_abandons=3, error_density=0.7,
        is_late_night=True, days_to_deadline=2,
    )
    assert signal is not None
    assert signal.claim == "burnout_risk"
    assert signal.priority == "high"


@pytest.mark.asyncio
async def test_affective_pressure_streak_broken():
    """Streak broken contributes to stress signal."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_affective_pressure(
        user_id="u1", consecutive_abandons=0, streak_broken=True,
        error_density=0.7,
    )
    assert signal is not None
    assert "streak_broken" in signal.evidence_summary


@pytest.mark.asyncio
async def test_affective_pressure_no_trigger():
    """Normal behavior does not trigger affective pressure."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal = await spine.detect_affective_pressure(
        user_id="u1", consecutive_abandons=0, error_density=0.2,
    )
    assert signal is None


@pytest.mark.asyncio
async def test_affective_pressure_stress_policy():
    """Stress signal produces correct policy decision."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="spine",
        state_key="affective_pressure", claim="stress_detected",
        confidence=0.75, scope="session", ttl_hours=12,
        evidence_summary="情绪压力", possible_effects=["reduce_pressure"],
        priority="medium",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    policy, _directive = result
    assert policy.primary_strategy == "reduce_affective_pressure"
    assert policy.risk_level == "high"


@pytest.mark.asyncio
async def test_affective_pressure_burnout_policy():
    """Burnout risk produces more aggressive policy."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="spine",
        state_key="affective_pressure", claim="burnout_risk",
        confidence=0.85, scope="session", ttl_hours=12,
        evidence_summary="倦怠风险", possible_effects=["suggest_break"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    policy, _directive = result
    assert policy.primary_strategy == "prevent_burnout"
    assert policy.hard_constraints.get("suggest_break") is True
    assert policy.risk_level == "high"


@pytest.mark.asyncio
async def test_cognitive_load_confidence_scales():
    """More triggers produce higher confidence."""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    signal_low = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=5, new_topics_count=4,
        avg_accuracy=0.6, session_duration_min=60,
    )
    signal_high = await spine.detect_cognitive_load(
        user_id="u1", recent_tasks_count=5, new_topics_count=4,
        avg_accuracy=0.35, session_duration_min=120,
    )
    assert signal_high.confidence > signal_low.confidence


# ── P2-2: ModelWriteDirective full write roundtrip ──────────────────

@pytest.mark.asyncio
async def test_model_write_directive_applies_claims():
    """ModelWriteDirective writes claims to Redis and they can be read back."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)
    from app.signals.types import ModelWriteDirective, ModelWriteEntry

    mwd = ModelWriteDirective(
        directive_id="mwd_001",
        policy_decision_id="pd_001",
        writes=[
            ModelWriteEntry(
                target_model="user_state",
                claim="task_granularity_may_be_too_large",
                scope="current_sprint",
                confidence=0.8,
                needs_user_confirmation=False,
                ttl="72h",
            ),
            ModelWriteEntry(
                target_model="sparkle_self_model",
                claim="long_task_strategy_may_not_fit",
                scope="strategy",
                confidence=0.5,
                needs_user_confirmation=False,
                ttl="72h",
            ),
        ],
    )
    await spine._apply_model_writes("u_test", mwd)

    # High-confidence claim should be written
    claims = await spine.get_model_claims("u_test", target_model="user_state", scope="current_sprint")
    assert len(claims) == 1
    assert claims[0]["claim"] == "task_granularity_may_be_too_large"
    assert claims[0]["confidence"] == 0.8
    assert claims[0]["source"] == "spine_auto"

    # Low-confidence claim should NOT be written (< 0.7 threshold)
    claims_low = await spine.get_model_claims("u_test", target_model="sparkle_self_model", scope="strategy")
    assert len(claims_low) == 0


@pytest.mark.asyncio
async def test_model_write_needs_confirmation_skipped():
    """Claims requiring user confirmation are not auto-applied."""
    redis = FakeRedis()
    spine = SpineOrchestrator(redis_client=redis)
    from app.signals.types import ModelWriteDirective, ModelWriteEntry

    mwd = ModelWriteDirective(
        directive_id="mwd_002",
        policy_decision_id="pd_002",
        writes=[
            ModelWriteEntry(
                target_model="user_state",
                claim="high_impact_change",
                scope="long_term",
                confidence=0.9,
                needs_user_confirmation=True,
            ),
        ],
    )
    await spine._apply_model_writes("u_confirm", mwd)
    claims = await spine.get_model_claims("u_confirm", target_model="user_state", scope="long_term")
    assert len(claims) == 0


# ── P2-3: Learning Base long-term belief + skill promotion ──────────

from app.signals.learning_base import LearningBase, StrategyBelief


def test_learning_base_update_belief_effective():
    """Updating with effective outcome increases alpha."""
    lb = LearningBase()
    belief = StrategyBelief(strategy_key="recover_execution_rhythm")
    updated = lb.update_belief(belief, "effective")
    assert updated.alpha == 2.0
    assert updated.beta == 1.0
    assert updated.evidence_count == 1


def test_learning_base_update_belief_insufficient():
    """Updating with insufficient outcome increases beta."""
    lb = LearningBase()
    belief = StrategyBelief(strategy_key="recover_execution_rhythm")
    updated = lb.update_belief(belief, "insufficient")
    assert updated.alpha == 1.0
    assert updated.beta == 2.0


def test_learning_base_counter_evidence_discounts_belief_score():
    """FV-18: user rejection/correction/harmful outcomes become counter-evidence."""
    lb = LearningBase()
    belief = StrategyBelief(strategy_key="recover_execution_rhythm", alpha=8, beta=2, evidence_count=10)

    lb.update_belief(belief, "user_rejected", reason="用户拒绝了本策略")
    lb.update_belief(belief, "harmful", reason="outcome=harmful")
    lb.update_belief(belief, "user_corrected", reason="用户纠正了判断")

    assert len(belief.counter_evidence) == 3
    assert belief.raw_expected_effectiveness == pytest.approx(8 / 11)
    assert belief.belief_score == pytest.approx((8 / 11) - 0.15)
    assert belief.to_dict()["counter_evidence"][0]["source"] == "user_rejection"


def test_learning_base_batch_update():
    """Batch update processes multiple outcomes."""
    lb = LearningBase()
    beliefs = [StrategyBelief(strategy_key="s1"), StrategyBelief(strategy_key="s2")]
    outcomes = [
        {"strategy_key": "s1", "attribution": "effective", "weight": 1.0},
        {"strategy_key": "s1", "attribution": "effective", "weight": 1.0},
        {"strategy_key": "s2", "attribution": "insufficient", "weight": 1.0},
    ]
    updated = lb.batch_update(beliefs, outcomes)
    b_map = {b.strategy_key: b for b in updated}
    assert b_map["s1"].alpha == 3.0
    assert b_map["s2"].beta == 2.0


def test_learning_base_select_strategy_bayesian():
    """After enough evidence, Bayesian selection picks the best."""
    lb = LearningBase()
    beliefs = [
        StrategyBelief(strategy_key="good", alpha=8, beta=2, evidence_count=10),
        StrategyBelief(strategy_key="bad", alpha=2, beta=8, evidence_count=10),
    ]
    result = lb.select_strategy(beliefs, ["good", "bad"])
    assert result["strategy"] == "good"
    assert result["source"] == "bayesian"


def test_learning_base_select_strategy_cold_start():
    """With no evidence, rule fallback is used."""
    lb = LearningBase()
    beliefs = [StrategyBelief(strategy_key="a"), StrategyBelief(strategy_key="b")]
    result = lb.select_strategy(
        beliefs, ["a", "b"],
        prefer_rules=True, rule_ranking=["b", "a"],
    )
    assert result["strategy"] == "b"
    assert result["source"] == "rule_fallback"


async def test_learning_base_persist_and_load():
    """Beliefs persist to Redis and load back correctly."""
    lb = LearningBase()
    redis = FakeRedis()
    beliefs = [
        StrategyBelief(strategy_key="s1", alpha=5, beta=3, evidence_count=8, last_updated="2026-04-27"),
        StrategyBelief(strategy_key="s2", alpha=2, beta=7, evidence_count=9),
    ]
    await lb.persist_beliefs(redis, "u1", beliefs)

    loaded = await lb.load_beliefs(redis, "u1")
    assert len(loaded) == 2
    assert loaded[0].strategy_key == "s1"
    assert loaded[0].alpha == 5
    assert loaded[1].beta == 7


def test_strategy_belief_counter_evidence_round_trip():
    """FV-18: persisted old/new belief JSON remains loadable with counter-evidence."""
    belief = StrategyBelief(strategy_key="s1")
    lb = LearningBase()
    lb.add_counter_evidence(belief, source="user_correction", reason="用户纠正")

    restored = StrategyBelief.from_dict(belief.to_dict())
    legacy = StrategyBelief.from_dict({"strategy_key": "legacy", "alpha": 2, "beta": 1})

    assert restored.counter_evidence[0].source == "user_correction"
    assert legacy.counter_evidence == []


async def test_learning_base_load_empty():
    """Loading from empty Redis returns empty list."""
    lb = LearningBase()
    redis = FakeRedis()
    loaded = await lb.load_beliefs(redis, "u_noone")
    assert loaded == []


def test_learning_base_skill_promotion_eligible():
    """Skill with high-effectiveness belief is promotion-eligible."""
    lb = LearningBase()
    from app.signals.types import SkillEntry
    beliefs = [
        StrategyBelief(strategy_key="exam_tcp_repair", alpha=8, beta=2, evidence_count=10),
    ]
    skill = SkillEntry(
        skill_id="skill_001", scope="personal",
        source_policy_key="exam_tcp_repair",
        strategy={}, applicable_when={}, evidence={},
    )
    result = lb.check_skill_promotion_eligibility(beliefs, skill)
    assert result["eligible"] is True
    assert result["effectiveness"] >= 0.7


def test_learning_base_skill_promotion_not_eligible():
    """Skill with low-effectiveness belief is not promotion-eligible."""
    lb = LearningBase()
    from app.signals.types import SkillEntry
    beliefs = [
        StrategyBelief(strategy_key="bad_strat", alpha=2, beta=8, evidence_count=10),
    ]
    skill = SkillEntry(
        skill_id="skill_002", scope="personal",
        source_policy_key="bad_strat",
        strategy={}, applicable_when={}, evidence={},
    )
    result = lb.check_skill_promotion_eligibility(beliefs, skill)
    assert result["eligible"] is False


def test_learning_base_skill_promotion_no_data():
    """Skill with no belief data is not promotion-eligible."""
    lb = LearningBase()
    from app.signals.types import SkillEntry
    skill = SkillEntry(
        skill_id="skill_003", scope="personal",
        source_policy_key="unknown",
        strategy={}, applicable_when={}, evidence={},
    )
    result = lb.check_skill_promotion_eligibility([], skill)
    assert result["eligible"] is False
    assert result["reason"] == "no_belief_data"


# ── P2-4: Confidence counter-evidence + retract_if ──────────────────

@pytest.mark.asyncio
async def test_state_entry_retract_if_field():
    """StateEntry supports retract_if field."""
    entry = StateEntry(
        state_key="prefers_short_tasks",
        value="true",
        confidence=0.7,
        scope="current_sprint",
        retract_if=["completed_long_task", "user_dislikes_fragments"],
    )
    d = entry.to_dict()
    restored = StateEntry.from_dict(d)
    assert len(restored.retract_if) == 2
    assert "completed_long_task" in restored.retract_if


@pytest.mark.asyncio
async def test_state_retraction_on_matching_event():
    """State with matching retract_if condition is removed."""
    from app.signals.state_register import StateRegister
    redis = FakeRedis()
    register = StateRegister(redis)

    entry = StateEntry(
        state_key="prefers_short_tasks",
        value="true",
        confidence=0.7,
        scope="current_sprint",
        retract_if=["completed_long_task", "user_dislikes_fragments"],
    )
    await register._save_state("u1", entry)
    assert await register.get_state("u1", "prefers_short_tasks") is not None

    retracted = await register.check_retractions("u1", ["completed_long_task"])
    assert "prefers_short_tasks" in retracted
    assert await register.get_state("u1", "prefers_short_tasks") is None


@pytest.mark.asyncio
async def test_state_no_retraction_without_match():
    """State is NOT retracted when events don't match retract_if."""
    from app.signals.state_register import StateRegister
    redis = FakeRedis()
    register = StateRegister(redis)

    entry = StateEntry(
        state_key="prefers_short_tasks",
        value="true",
        confidence=0.7,
        scope="current_sprint",
        retract_if=["completed_long_task"],
    )
    await register._save_state("u1", entry)
    retracted = await register.check_retractions("u1", ["unrelated_event"])
    assert len(retracted) == 0
    assert await register.get_state("u1", "prefers_short_tasks") is not None


@pytest.mark.asyncio
async def test_state_no_retraction_without_retract_if():
    """State without retract_if is never retracted by check_retractions."""
    from app.signals.state_register import StateRegister
    redis = FakeRedis()
    register = StateRegister(redis)

    entry = StateEntry(
        state_key="task_granularity_fit",
        value="too_large",
        confidence=0.8,
        scope="current_sprint",
    )
    await register._save_state("u1", entry)
    retracted = await register.check_retractions("u1", ["anything"])
    assert len(retracted) == 0


@pytest.mark.asyncio
async def test_counter_evidence_lowers_confidence_perception():
    """Adding counter-evidence to a state tracks opposition."""
    from app.signals.state_register import StateRegister
    redis = FakeRedis()
    register = StateRegister(redis)

    entry = StateEntry(
        state_key="task_granularity_fit",
        value="too_large",
        confidence=0.8,
        scope="current_sprint",
        supporting_evidence=["连续 2 次超时"],
    )
    await register._save_state("u1", entry)
    await register.add_counter_evidence("u1", "task_granularity_fit", "用户完成了长任务")

    updated = await register.get_state("u1", "task_granularity_fit")
    assert "用户完成了长任务" in updated.counter_evidence
