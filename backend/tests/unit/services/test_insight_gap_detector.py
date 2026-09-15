import pytest

from app.orchestration.schemas import CompiledInsightState
from app.services.insight_gap_detector import InsightGapDetector


@pytest.mark.asyncio
async def test_insight_gap_detector_handles_specific_chinese_goal_without_vagueness_false_positive() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h"},
        current_state={"overall_mastery": 0.35, "active_subjects": ["热力学"]},
    )

    gaps = await detector.detect_gaps(
        insight_state=state,
        user_message="帮我做一个热力学第二章期中冲刺计划",
        intent="plan",
        planning_context={
            "goal_text": "热力学第二章期中冲刺计划",
            "vision": {"primary_goal": "热力学第二章期中冲刺"},
            "current_state": {},
        },
    )

    assert "goal_specificity" not in gaps


@pytest.mark.asyncio
async def test_insight_gap_detector_distinguishes_material_hints_from_actual_material_sources() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h"},
        current_state={"overall_mastery": 0.4, "active_subjects": ["Physics"]},
    )

    hinted_only = await detector.detect_gaps(
        insight_state=state,
        user_message="Use my notes to help me make an exam plan",
        intent="plan",
        planning_context={
            "goal_text": "Physics exam plan",
            "vision": {"primary_goal": "Physics exam plan"},
            "current_state": {},
        },
    )
    grounded = await detector.detect_gaps(
        insight_state=state,
        user_message="Help me make an exam plan",
        intent="plan",
        planning_context={
            "goal_text": "Physics exam plan",
            "vision": {"primary_goal": "Physics exam plan"},
            "current_state": {},
            "file_ids": ["file-1"],
        },
    )

    assert "material_source" not in hinted_only
    assert "material_source" not in grounded


@pytest.mark.asyncio
async def test_insight_gap_detector_flags_material_source_when_exam_plan_has_no_real_material_context() -> None:
    detector = InsightGapDetector()
    state = CompiledInsightState(
        stable_traits={"daily_cap": "2h"},
        current_state={"overall_mastery": 0.4, "active_subjects": ["Physics"]},
    )

    gaps = await detector.detect_gaps(
        insight_state=state,
        user_message="Help me make a physics exam sprint plan",
        intent="plan",
        planning_context={
            "goal_text": "Physics exam sprint plan",
            "vision": {"primary_goal": "Physics exam sprint plan"},
            "current_state": {},
        },
    )

    assert "material_source" in gaps
