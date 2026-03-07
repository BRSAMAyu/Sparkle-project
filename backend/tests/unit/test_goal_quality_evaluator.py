from app.orchestration.goal_quality_evaluator import GoalQualityEvaluator


def test_goal_quality_evaluator_flags_vague_goal():
    evaluator = GoalQualityEvaluator()

    result = evaluator._heuristic_fallback("我想学好数学")

    assert result.passed is False
    assert result.scores.specificity < 0.5
    assert result.scores.measurability < 0.5
    assert any("具体" in question or "哪门课" in question for question in result.clarification_questions)


def test_goal_quality_evaluator_passes_specific_goal():
    evaluator = GoalQualityEvaluator()

    result = evaluator._heuristic_fallback("这学期期末前把高数成绩提高到85分")

    assert result.passed is True
    assert result.scores.specificity >= 0.5
    assert result.scores.measurability >= 0.5
    assert result.scores.time_bound >= 0.5
