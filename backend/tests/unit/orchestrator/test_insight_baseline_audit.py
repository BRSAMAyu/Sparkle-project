
import pytest
from app.orchestration.situation_brief import SituationBriefBuilder
from app.core.profile_context import ProfileContext, KnowledgeSummary, CognitiveSummary

@pytest.mark.asyncio
async def test_baseline_audit_cold_start_blindness():
    """
    Audit Case A: Cold Start Blindness (Improved)
    Scenario: User asks for a 14-day exam plan with NO mastery data.
    Expected behavior: Sparkle detects LOW readiness and asks for baseline mastery.
    """
    # Empty profile context
    empty_context = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.0,
            weak_spots=[],
            recent_mastery_changes=[],
            active_learning_subjects=[]
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[],
            dominant_pattern_type=None,
            risk_signals=[]
        )
    )
    
    builder = SituationBriefBuilder()
    brief = await builder.build(
        user_context_payload={"profile_context": empty_context.model_dump(), "context_focus": {"route_intent": "plan"}},
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={"prompt_instruction": "User wants a 14-day Physics exam plan"},
        session_feedback_signal=None
    )

    # ASSERT IMPROVEMENT: Readiness is now explicitly modeled.
    assert brief.insight_state["readiness_level"] == "low"
    assert "baseline_mastery" in brief.insight_state["blocking_unknowns"]
    assert len(brief.insight_state["recommended_clarification"]) > 0
    # Verify decision context has injected the readiness for prompt use
    assert brief.decision_context["planning_readiness"] == "low"
    assert brief.decision_context["planning_readiness_action"] == "ask"
    assert brief.decision_context["experience_mode"] == "clarify"
    assert brief.decision_context["phase_a_guardrail"] == "ask_before_plan"

@pytest.mark.asyncio
async def test_baseline_audit_contradictory_signal_merging():
    """
    Audit Case B: Contradictory Signal Merging (Improved)
    Scenario: User wants 'hard' difficulty but has 'perfectionism_paralysis' pattern.
    Expected behavior: System detects and flags the contradiction.
    """
    contradictory_context = ProfileContext(
        preferences={"difficulty": "hard"},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.5,
            weak_spots=[],
            recent_mastery_changes=[],
            active_learning_subjects=["Physics"]
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[{
                "pattern_name": "Perfectionism Paralysis",
                "pattern_type": "execution",
                "confidence": 0.9,
                "policy_signals": ["task.difficulty.start_easy"]
            }],
            dominant_pattern_type="execution",
            risk_signals=["risk.execution_delay"]
        )
    )

    builder = SituationBriefBuilder()
    brief = await builder.build(
        user_context_payload={"profile_context": contradictory_context.model_dump()},
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal=None
    )

    # ASSERT IMPROVEMENT: Conflict is now detected.
    assert len(brief.insight_state["contradiction_map"]) > 0
    assert "difficulty" in brief.insight_state["contradiction_map"][0]["description"].lower()
    # Verify decision context injection
    assert len(brief.decision_context["insight_contradictions"]) > 0
    assert brief.insight_state["readiness_score"] < 1.0

@pytest.mark.asyncio
async def test_baseline_audit_strategic_gap_blindness():
    """
    Audit Case C: Strategic Gap Blindness (Improved)
    Scenario: User changes timing, but system doesn't ask 'Why?'.
    """
    builder = SituationBriefBuilder()
    brief = await builder.build(
        user_context_payload={"context_focus": {"route_intent": "preference_update"}},
        plan_context={},
        focused_memory={},
        context_briefing_note="User wants to study in the morning now.",
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal=None
    )

    # ASSERT IMPROVEMENT: Readiness level is available even for preference updates.
    assert "readiness_level" in brief.insight_state


@pytest.mark.asyncio
async def test_baseline_audit_multilingual_goal_specificity_and_material_detection():
    context = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.3,
            weak_spots=[],
            recent_mastery_changes=[],
            active_learning_subjects=["热力学"],
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[],
            dominant_pattern_type=None,
            risk_signals=[],
        ),
    )

    builder = SituationBriefBuilder()
    brief = await builder.build(
        user_context_payload={
            "current_query": "帮我做一个热力学期中冲刺计划",
            "profile_context": context.model_dump(),
            "context_focus": {"route_intent": "plan"},
            "active_goals": [{"title": "热力学期中冲刺"}],
        },
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal=None,
    )

    assert "goal_specificity" not in brief.insight_state["blocking_unknowns"]
    assert "material_source" in brief.insight_state["blocking_unknowns"]


@pytest.mark.asyncio
async def test_baseline_audit_misleading_self_report_keeps_real_gaps_visible():
    context = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.2,
            weak_spots=[],
            recent_mastery_changes=[],
            active_learning_subjects=["Physics"],
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[],
            dominant_pattern_type=None,
            risk_signals=[],
        ),
    )

    brief = await SituationBriefBuilder().build(
        user_context_payload={
            "current_query": "I already know the basics. Just give me a 14-day physics exam sprint plan.",
            "profile_context": context.model_dump(),
            "context_focus": {"route_intent": "plan"},
        },
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal=None,
    )

    contradiction_ids = {item["id"] for item in brief.insight_state["contradiction_map"]}
    assert "conflict:self_report_mastery_vs_profile_mastery" in contradiction_ids
    assert "material_source" in brief.insight_state["blocking_unknowns"]
