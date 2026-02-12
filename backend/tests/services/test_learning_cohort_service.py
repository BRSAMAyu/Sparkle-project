from app.services.learning_cohort_service import LearningCohortService


def test_resolve_cohort_id_and_user_scope():
    cohort = LearningCohortService.resolve_cohort_id(
        user_id="9f1f26f8-96e8-4a5d-9de8-8ea9f4d47e2a",
        message="帮我做一个学习计划，分阶段准备考试",
        chat_mode="study_plan",
        task_type="study_plan",
        complexity_tier="medium",
        user_context={
            "analytics_summary": {"engagement_score": 0.8},
            "decomposition_signals": {"historical_execution_rhythm": 0.38},
        },
    )
    assert cohort.startswith("cohort::study::medium::high_engagement::")

    scope = LearningCohortService.user_scope_key("9f1f26f8-96e8-4a5d-9de8-8ea9f4d47e2a")
    assert scope.startswith("usr::")
    assert len(scope) > 8
