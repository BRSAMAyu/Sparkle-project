from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router


def test_dual_core_router_selects_cognitive_first_for_repeated_difficulty_feedback() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.91,
            information_sufficient=True,
            primary_challenge_area="emotional",
            recent_sentiment_distribution={"anxious": 3, "neutral": 1},
            has_active_plan=True,
            plan_health_status="warning",
            recent_task_feedback_distribution={"too_difficult": 3, "too_long": 1},
            session_length_preference=25,
            difficulty_preference=0.4,
        )
    )

    assert decision.mode == "cognitive_first"
    assert "情绪阻力" in decision.reason or "阻力" in decision.reason
    assert decision.cognitive_adjustments


def test_dual_core_router_selects_execution_first_for_clear_goal() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.95,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 4},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 2},
            session_length_preference=25,
            difficulty_preference=0.5,
        )
    )

    assert decision.mode == "execution_first"
    assert decision.execution_constraints


def test_dual_core_router_falls_back_to_balanced_for_mixed_signals() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.68,
            information_sufficient=True,
            primary_challenge_area="cognitive",
            recent_sentiment_distribution={"neutral": 2, "frustrated": 1},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={"too_long": 1},
        )
    )

    assert decision.mode in {"balanced", "cognitive_first"}
