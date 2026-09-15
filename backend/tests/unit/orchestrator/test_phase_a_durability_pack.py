import pytest

from app.core.profile_context import ActivePattern, CognitiveSummary, KnowledgeSummary, ProfileContext, WeakSpot
from app.orchestration.planning_intent import detect_planning_like_turn, is_planning_like_turn
from app.orchestration.schemas import CompiledInsightState
from app.orchestration.situation_brief import SituationBriefBuilder
from app.services.insight_gap_detector import InsightGapDetector
from app.services.planning_readiness_gate import PlanningReadinessGate


pytestmark = pytest.mark.phase_a_durability


def _profile(
    *,
    overall_mastery: float = 0.0,
    active_subjects: list[str] | None = None,
    preferences: dict | None = None,
    weak_spots: list[WeakSpot] | None = None,
    active_patterns: list[ActivePattern] | None = None,
) -> ProfileContext:
    return ProfileContext(
        preferences=preferences or {},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=overall_mastery,
            weak_spots=weak_spots or [],
            recent_mastery_changes=[],
            active_learning_subjects=active_subjects or [],
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=active_patterns or [],
            dominant_pattern_type=None,
            risk_signals=[],
        ),
    )


async def _build_brief(
    *,
    current_query: str,
    profile_context: ProfileContext,
    route_intent: str = "plan",
    user_strategy_state: dict | None = None,
    file_ids: list[str] | None = None,
) -> object:
    return await SituationBriefBuilder().build(
        user_context_payload={
            "current_query": current_query,
            "context_focus": {"route_intent": route_intent},
            "profile_context": profile_context.model_dump(),
            "user_strategy_state": user_strategy_state or {},
            "file_ids": file_ids or [],
        },
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal=None,
    )


@pytest.mark.asyncio
async def test_phase_a_durability_cold_start_exam_sprint_requires_one_top_clarification() -> None:
    brief = await _build_brief(
        current_query="帮我做一个 14 天物理考试冲刺计划",
        profile_context=_profile(),
        route_intent="create_plan",
    )

    assert brief.insight_state["readiness_level"] == "low"
    assert brief.decision_context["planning_readiness_action"] == "ask"
    assert brief.decision_context["phase_a_guardrail"] == "ask_before_plan"
    assert brief.decision_context["strategic_clarification_questions"][0].startswith("你目前对这个主题的掌握")


@pytest.mark.asyncio
async def test_phase_a_durability_detector_treats_create_plan_and_time_planning_as_planning_like() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h", "deadline": "next week"},
        current_state={"overall_mastery": 0.45, "active_subjects": ["Physics"]},
    )

    for intent in ("create_plan", "time_planning"):
        gaps = await detector.detect_gaps(
            insight_state=state,
            user_message="Help me make an exam plan",
            intent=intent,
            planning_context={
                "route_intent": intent,
                "goal_text": "exam plan",
                "vision": {"primary_goal": "exam plan"},
                "current_state": {},
            },
        )
        assert "material_source" in gaps


@pytest.mark.asyncio
async def test_phase_a_durability_vague_goal_triggers_goal_specificity_gap() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h", "deadline": "tomorrow"},
        current_state={"overall_mastery": 0.5, "active_subjects": ["Physics"]},
    )

    gaps = await detector.detect_gaps(
        insight_state=state,
        user_message="plan",
        intent="create_plan",
        planning_context={
            "route_intent": "create_plan",
            "goal_text": "plan",
            "vision": {"primary_goal": ""},
            "current_state": {},
        },
    )

    assert "goal_specificity" in gaps


@pytest.mark.asyncio
async def test_phase_a_durability_uploaded_materials_clear_material_gap() -> None:
    brief = await _build_brief(
        current_query="帮我做一个 thermodynamics sprint plan for chapter 2",
        profile_context=_profile(
            overall_mastery=0.5,
            active_subjects=["Thermodynamics"],
            preferences={"daily_cap": "2h", "deadline": "next week"},
        ),
        route_intent="time_planning",
        file_ids=["file-thermo-1"],
    )

    assert "material_source" not in brief.insight_state["blocking_unknowns"]


@pytest.mark.asyncio
async def test_phase_a_durability_material_hints_without_attachments_keep_current_frozen_behavior() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h", "deadline": "next week"},
        current_state={"overall_mastery": 0.4, "active_subjects": ["Physics"]},
    )

    gaps = await detector.detect_gaps(
        insight_state=state,
        user_message="Use my notes to help me make an exam sprint plan",
        intent="knowledge_query",
        planning_context={
            "route_intent": "",
            "goal_text": "Physics exam sprint plan",
            "vision": {"primary_goal": "Physics exam sprint plan"},
            "current_state": {},
        },
    )

    assert "material_source" not in gaps


def test_phase_a_durability_shared_planning_predicate_handles_mixed_language_and_message_fallback() -> None:
    planning_like, source = detect_planning_like_turn(
        normalized_intent="knowledge_query",
        route_intent="",
        user_message="帮我做一个 thermodynamics sprint plan",
        decision_context=None,
    )

    assert planning_like is True
    assert source == "message_fallback"
    assert is_planning_like_turn("knowledge_query", "", "帮我做一个 thermodynamics sprint plan", None) is True


@pytest.mark.asyncio
async def test_phase_a_durability_recovery_mode_harder_push_surfaces_contradiction() -> None:
    brief = await _build_brief(
        current_query="Please push me harder and give me a strict sprint plan.",
        profile_context=_profile(overall_mastery=0.5, active_subjects=["Physics"]),
        route_intent="create_plan",
        user_strategy_state={"session_mode": "recovery"},
    )

    contradiction_ids = {item["id"] for item in brief.insight_state["contradiction_map"]}
    assert "conflict:push_vs_recovery_state" in contradiction_ids


@pytest.mark.asyncio
async def test_phase_a_durability_i_already_know_this_keeps_mastery_conflict_visible() -> None:
    brief = await _build_brief(
        current_query="I already know this. Just give me a 14-day physics exam sprint plan.",
        profile_context=_profile(
            overall_mastery=0.2,
            active_subjects=["Physics"],
            weak_spots=[WeakSpot(node_id="physics-1", node_name="Kinematics", mastery=0.25)],
        ),
        route_intent="create_plan",
    )

    contradiction_ids = {item["id"] for item in brief.insight_state["contradiction_map"]}
    assert "conflict:self_report_mastery_vs_profile_mastery" in contradiction_ids
    assert brief.insight_state["ask_before_plan"] is (
        brief.decision_context["planning_readiness_action"] == "ask"
    )


def test_phase_a_durability_contract_freezes_allowed_values_and_version() -> None:
    gate = PlanningReadinessGate()

    assert CompiledInsightState().version == "1.0"

    low = gate.evaluate(
        insight_state=CompiledInsightState(
            contradiction_map=[{"severity": "high", "description": "conflict"}],
        ),
        gaps=["baseline_mastery", "capacity_hours"],
    )
    medium = gate.evaluate(
        insight_state=CompiledInsightState(),
        gaps=["goal_specificity"],
    )
    high = gate.evaluate(
        insight_state=CompiledInsightState(),
        gaps=[],
    )

    assert {low["recommended_action"], medium["recommended_action"], high["recommended_action"]} == {
        "ask",
        "provisional",
        "proceed",
    }
    assert low["ask_before_plan"] is True
    assert medium["ask_before_plan"] is False
    assert high["ask_before_plan"] is False
