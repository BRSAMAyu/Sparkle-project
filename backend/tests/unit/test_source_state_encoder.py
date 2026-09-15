from __future__ import annotations

from types import SimpleNamespace

from app.services.source_state_encoder import (
    SOURCE_STATE_MAX_COMBINATIONS,
    SourceStateEncoder,
    canonicalize_source_state,
    encode_source_state_key,
    prune_dimension_space_for_budget,
)
from app.state_aggregator.schema import ActiveSkillSummaryItemValue, ActiveSkillsSummaryValue, SufficiencySummaryValue


def test_source_state_encoder_builds_expected_dimensions() -> None:
    encoder = SourceStateEncoder()

    state = encoder.build(
        routing_input=SimpleNamespace(intent="plan"),
        task_summary=SufficiencySummaryValue(score=0.55, top_missing_dimensions=("goal",)),
        context_summary=SufficiencySummaryValue(score=0.92, top_missing_dimensions=()),
        user_context_payload={
            "achievement_summary": {"recent_unlocks": [{"name": "七日连胜"}], "total_achievement_score": 4.5},
            "calendar_context": {"workload_density": "medium", "upcoming_deadlines": [{"title": "Exam"}]},
        },
        plan_context={"user_profile": {"goal_type": "exam", "knowledge_level": "beginner"}},
        active_skills_summary=ActiveSkillsSummaryValue(
            items=(ActiveSkillSummaryItemValue(skill_id="1", name="Plan Sprint", activation_match_score=0.9),)
        ),
        selected_skill_names=["Plan Sprint"],
        state_context_data={"unresolved_conflicts": []},
    )

    assert state["tool_category"] == "plan"
    assert state["sufficiency_level"] == "low"
    assert state["skill_domain"] == "plan"
    assert state["achievement_tier"] == "active"
    assert state["calendar_pressure"] == "medium"
    assert state["cohort_segment"] == "exam_beginner"


def test_source_state_encoder_key_is_stable() -> None:
    left = encode_source_state_key({"tool_category": "plan", "sufficiency_level": "high"})
    right = encode_source_state_key({"sufficiency_level": "high", "tool_category": "plan"})

    assert left == right
    assert "tool_category=plan" in left


def test_source_state_encoder_canonicalizes_unknown_values() -> None:
    state = canonicalize_source_state({"tool_category": "???", "calendar_pressure": "panic"})

    assert state["tool_category"] == "general"
    assert state["calendar_pressure"] == "none"


def test_prune_dimension_space_for_budget_keeps_combination_count_bounded() -> None:
    pruned = prune_dimension_space_for_budget(
        {
            "tool_category": {"chat", "plan", "task", "reflection", "general"},
            "sufficiency_level": {"low", "medium", "high"},
            "conflict_outcome": {"clear", "pending", "resolved"},
            "skill_domain": {"none", "plan", "focus", "reflection", "mixed"},
            "achievement_tier": {"none", "emerging", "active", "advanced"},
            "calendar_pressure": {"none", "low", "medium", "high"},
            "cohort_segment": {"general", "exam_beginner", "exam_intermediate", "exam_advanced"},
        }
    )

    total = 1
    for values in pruned.values():
        total *= len(values)
    assert total <= SOURCE_STATE_MAX_COMBINATIONS
