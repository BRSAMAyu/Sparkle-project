
import pytest
from app.core.profile_context import ProfileContext, KnowledgeSummary, CognitiveSummary, ActivePattern, WeakSpot
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
    assert state.contradiction_map[0]["id"] == "conflict:difficulty_vs_paralysis"
    assert state.contradiction_map[0]["severity"] == "high"

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
