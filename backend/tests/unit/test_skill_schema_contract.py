from datetime import datetime

import pytest

from app.services.skill_schema import (
    SkillSelectionContext,
    normalize_activation_conditions,
    normalize_examples,
    normalize_name,
    normalize_pattern_template,
    time_of_day_token,
    weekday_token,
)


def test_skill_schema_v1_normalizers_accept_valid_payload() -> None:
    assert normalize_name("Exam Triage") == "Exam Triage"
    assert normalize_pattern_template("Scope first and compress the next step.") == "Scope first and compress the next step."
    conditions = normalize_activation_conditions(
        [{"kind": "intent_keywords", "value": ["exam", "prep"]}]
    )
    assert conditions[0].kind == "intent_keywords"
    assert normalize_examples(["先缩小范围"]) == ("先缩小范围",)


def test_skill_schema_v1_rejects_invalid_condition_kind() -> None:
    with pytest.raises(ValueError, match="Unsupported activation condition kind"):
        normalize_activation_conditions([{"kind": "llm_intent", "value": ["exam"]}])


def test_skill_selection_context_time_tokens_are_deterministic() -> None:
    context = SkillSelectionContext(
        intent="exam planning",
        tool_category="direct",
        current_time=datetime(2026, 4, 21, 9, 0, 0),
    )
    assert time_of_day_token(context.current_time) == "morning"
    assert weekday_token(context.current_time) == "tue"
