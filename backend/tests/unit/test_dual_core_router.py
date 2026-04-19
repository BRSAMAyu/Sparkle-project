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


def test_dual_core_router_shifts_from_execution_to_cognitive_when_procrastination_pattern_is_present() -> None:
    baseline = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
        )
    )
    shifted = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            procrastination_pattern=True,
            behavior_pattern_details=[
                {
                    "pattern_name": "拖延回避",
                    "canonical_key": "procrastination_avoidance",
                    "description": "总在真正开始前往后拖。",
                    "confidence": 0.82,
                }
            ],
        )
    )

    assert baseline.mode == "execution_first"
    assert shifted.mode == "cognitive_first"
    assert shifted.routing_debug["explicit_procrastination_signal"] is True


def test_dual_core_router_uses_cognitive_mode_signal_for_concept_confusion() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="knowledge",
            intent_confidence=0.66,
            information_sufficient=True,
            primary_challenge_area="cognitive",
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=True,
            plan_health_status="warning",
            recent_task_feedback_distribution={"unclear": 1},
            cognitive_mode_suggested=True,
            behavior_pattern_details=[
                {
                    "pattern_name": "认知盲点",
                    "canonical_key": "cognitive_blindspot",
                    "description": "在相似概念上反复误解。",
                    "confidence": 0.71,
                }
            ],
        )
    )

    assert decision.mode == "cognitive_first"
    assert decision.routing_debug["explicit_cognitive_signal"] is True


def test_dual_core_router_emits_bounded_strategy_adjustments_for_high_friction_turns() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.88,
            information_sufficient=False,
            primary_challenge_area="emotional",
            recent_sentiment_distribution={"overwhelmed": 2, "neutral": 1},
            has_active_plan=True,
            plan_health_status="critical",
            recent_task_feedback_distribution={"too_long": 2, "too_difficult": 1},
            procrastination_pattern=True,
            cognitive_mode_suggested=True,
            suggested_verbosity="supportive",
        )
    )

    assert decision.mode == "cognitive_first"
    adjustments = {item["field"]: item["recommended_value"] for item in decision.strategy_adjustments}
    assert adjustments["session_mode"] == "recovery"
    assert adjustments["intervention_intensity"] == "low"
    assert adjustments["difficulty_level"] == 2
    assert adjustments["explanation_style"] == "step_by_step"
    assert adjustments["push_vs_support"] == 0.25
