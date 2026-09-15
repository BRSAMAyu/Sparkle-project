from app.services.sufficiency_judge_schema import CurrentTurnParseResult, SufficiencyJudgment, SufficiencyScore


def test_sufficiency_judgment_defaults() -> None:
    judgment = SufficiencyJudgment(
        task_sufficiency=SufficiencyScore(score=0.75, missing_dimensions=("constraint_explicit",)),
        context_sufficiency=SufficiencyScore(score=0.5, missing_dimensions=("social_context_loaded",)),
    )

    assert judgment.judge_version == "v1"
    assert judgment.task_sufficiency.missing_dimensions == ("constraint_explicit",)
    assert judgment.context_sufficiency.missing_dimensions == ("social_context_loaded",)
    assert judgment.computed_at is not None


def test_current_turn_parse_result_is_frozen_contract() -> None:
    payload = CurrentTurnParseResult(
        intent="plan",
        intent_confidence=0.81,
        information_sufficient=True,
        target_object_resolved=True,
        constraint_explicit=False,
    )

    assert payload.intent == "plan"
    assert payload.intent_confidence == 0.81
    assert payload.information_sufficient is True
