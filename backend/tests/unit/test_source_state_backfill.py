from __future__ import annotations

from app.services.source_state_encoder import build_backfill_source_state, encode_source_state_key


def test_backfill_source_state_uses_follow_up_question_to_mark_low_sufficiency() -> None:
    state = build_backfill_source_state(
        decision_type="balanced",
        decision_payload={"follow_up_question": "你现在最卡在哪一步？", "route_reason": "plan review"},
        skills_injected=[],
    )

    assert state["tool_category"] == "plan"
    assert state["sufficiency_level"] == "low"
    assert encode_source_state_key(state).startswith("tool_category=plan|")


def test_backfill_source_state_marks_skill_domain_when_skills_present() -> None:
    state = build_backfill_source_state(
        decision_type="execution_first",
        decision_payload={"route_reason": "task drill"},
        skills_injected=["skill-1"],
    )

    assert state["tool_category"] == "task"
    assert state["skill_domain"] == "mixed"
