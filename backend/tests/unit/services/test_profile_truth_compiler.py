
import pytest
from app.core.profile_context import ProfileContext, KnowledgeSummary, CognitiveSummary, ActivePattern, WeakSpot
from app.core.user_insight_state import UserInsightState
from app.services.profile_truth_compiler import ProfileTruthCompiler

@pytest.mark.asyncio
async def test_profile_truth_compiler_basic_compilation():
    pc = ProfileContext(
        preferences={"difficulty": "hard", "focus_time": "morning"},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.45,
            weak_spots=[WeakSpot(node_id="math_1", node_name="Algebra", mastery=0.3)],
            recent_mastery_changes=[],
            active_learning_subjects=["Math"]
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[
                ActivePattern(
                    pattern_name="Perfectionism Paralysis",
                    pattern_type="execution",
                    confidence=0.85,
                    policy_signals=["task.difficulty.start_easy"]
                )
            ],
            dominant_pattern_type="execution",
            risk_signals=["risk.execution_delay"]
        )
    )

    compiler = ProfileTruthCompiler()
    state = await compiler.compile(profile_context=pc)

    # Verify traits
    assert state.stable_traits["difficulty"] == "hard"
    
    # Verify bottlenecks
    assert any(b["label"] == "Algebra" for b in state.active_bottlenecks)
    assert any(b["label"] == "risk.execution_delay" for b in state.active_bottlenecks)

    # Verify contradictions (Case B)
    assert len(state.contradiction_map) == 1
    assert state.contradiction_map[0]["id"] == "conflict:difficulty_vs_start_friction"
    assert state.contradiction_map[0]["severity"] == "high"
    assert state.contradiction_map[0]["evidence"]

    # Verify confidence
    assert state.confidence_map["cognitive:Perfectionism Paralysis"] == 0.85


@pytest.mark.asyncio
async def test_profile_truth_compiler_uses_session_strategy_fields() -> None:
    pc = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.4,
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

    compiler = ProfileTruthCompiler()
    state = await compiler.compile(
        profile_context=pc,
        user_strategy_state={
            "session_mode": "recovery",
            "push_vs_support": 0.2,
            "retrieval_emphasis": "user_materials",
        },
    )

    assert state.current_state["strategy_mode"] == "recovery"
    assert state.current_state["push_vs_support"] == 0.2
    assert state.current_state["retrieval_emphasis"] == "user_materials"


@pytest.mark.asyncio
async def test_profile_truth_compiler_detects_push_vs_recovery_state() -> None:
    pc = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.55,
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

    compiler = ProfileTruthCompiler()
    state = await compiler.compile(
        profile_context=pc,
        user_strategy_state={"session_mode": "recovery"},
        turn_signals={"wants_push": True, "requested_difficulty": "hard"},
    )

    contradiction_ids = {item["id"] for item in state.contradiction_map}
    assert "conflict:push_vs_recovery_state" in contradiction_ids


@pytest.mark.asyncio
async def test_profile_truth_compiler_detects_misleading_mastery_self_report() -> None:
    pc = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.25,
            weak_spots=[WeakSpot(node_id="thermo_1", node_name="Entropy", mastery=0.2)],
            recent_mastery_changes=[],
            active_learning_subjects=["Thermodynamics"],
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[],
            dominant_pattern_type=None,
            risk_signals=[],
        ),
    )

    compiler = ProfileTruthCompiler()
    state = await compiler.compile(
        profile_context=pc,
        turn_signals={"self_report_high_mastery": True},
    )

    contradiction = next(
        item for item in state.contradiction_map if item["id"] == "conflict:self_report_mastery_vs_profile_mastery"
    )
    assert contradiction["severity"] == "high"
    assert any("overall_mastery" in evidence["detail"] for evidence in contradiction["evidence"])


@pytest.mark.asyncio
async def test_profile_truth_compiler_detects_maximal_pace_vs_low_capacity() -> None:
    pc = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.4,
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

    compiler = ProfileTruthCompiler()
    state = await compiler.compile(
        profile_context=pc,
        user_strategy_state={"session_mode": "recovery"},
        turn_signals={"aggressive_pace": True, "low_capacity_language": True},
    )

    contradiction = next(
        item for item in state.contradiction_map if item["id"] == "conflict:maximal_pace_vs_available_capacity"
    )
    assert contradiction["severity"] in {"medium", "high"}
    assert contradiction["evidence"]


@pytest.mark.asyncio
async def test_profile_truth_compiler_projects_multi_span_analysis_and_predictions_from_canonical_state() -> None:
    canonical = UserInsightState(
        multi_span_analysis={
            "short_span": {"overload_pressure": "high", "current_traction": "low"},
            "medium_span": {"task_start_completion_drift": {"label": "high_drift"}},
        },
        prediction_summaries={
            "overload_risk": {"level": "high", "score": 0.82},
            "schedule_fit": {"level": "low", "score": 0.24},
        },
    )
    pc = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(),
        cognitive_summary=CognitiveSummary(),
        user_insight_state=canonical,
    )

    state = await ProfileTruthCompiler().compile(profile_context=pc)

    assert state.multi_span_analysis["short_span"]["overload_pressure"] == "high"
    assert state.prediction_summary["overload_risk"]["level"] == "high"
