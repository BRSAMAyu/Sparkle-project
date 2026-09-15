from datetime import datetime

from app.config import settings
from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.unified_evidence import EvidenceTarget
from app.services.social_signal_types import SocialSignalsV1
from app.services.srl_phase_types import SRLPhaseHint
from app.state_aggregator.schema import MetacognitionHintV1


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


def test_dual_core_router_adds_social_constraints_when_social_signals_are_present() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.84,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            social_signals=SocialSignalsV1(
                mention_count=2,
                relationship_count=1,
                pending_commitments_count=1,
                social_learning_preference=0.81,
                summary_lines=(
                    "最近 7 天提到过 2 位学习相关人物。",
                    "目前有 1 条到期承诺待跟进。",
                ),
            ),
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert "boundaries" in rendered
    assert "external commitments" in rendered
    assert "peers or groups" in rendered
    assert decision.routing_debug["explicit_social_signal"] is True
    assert decision.routing_debug["social_pending_commitments_count"] == 1


def test_dual_core_router_uses_srl_reflection_hint_to_prefer_cognitive_first() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            srl_phase_hint=SRLPhaseHint(
                current_phase="reflection",
                confidence=0.78,
                source="aggregator",
                freshness_seconds=12,
            ),
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "cognitive_first"
    assert "reflection phase" in rendered
    assert decision.routing_debug["explicit_srl_signal"] is True
    assert decision.routing_debug["srl_phase"] == "reflection"


def test_dual_core_router_prefers_cognitive_first_when_metacognition_accuracy_is_low() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.88,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            metacognition_hint=MetacognitionHintV1(
                accuracy=0.34,
                awareness="moderate",
                last_updated=datetime(2026, 4, 22, 9, 0, 0),
            ),
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "cognitive_first"
    assert "recalibrate judgment" in rendered
    assert decision.routing_debug["metacognition_accuracy"] == 0.34


def test_dual_core_router_prefers_execution_first_when_metacognition_awareness_is_strong() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.72,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            metacognition_hint=MetacognitionHintV1(
                accuracy=0.92,
                awareness="strong",
                last_updated=datetime(2026, 4, 22, 9, 0, 0),
            ),
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "execution_first"
    assert "reduce redundant confirmations" in rendered
    assert decision.routing_debug["metacognition_awareness"] == "strong"


def test_dual_core_router_biases_toward_cognitive_support_when_cognitive_load_is_high() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            cognitive_load=0.84,
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "cognitive_first"
    assert "Cognitive load is currently high" in rendered
    assert decision.routing_debug["cognitive_load"] == 0.84


def test_dual_core_router_can_use_belief_state_as_signal_source(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED", True)
    monkeypatch.setattr(settings, "SPARKLE_DUAL_CORE_BELIEF_UNCERTAINTY_MAX", 0.1)
    belief_state = BeliefState(user_id="u1")
    emotional_block = belief_state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    emotional_block.mean = 0.86
    emotional_block.variance = 0.02

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
            belief_state=belief_state,
        )
    )

    assert decision.mode == "cognitive_first"
    assert decision.routing_debug["belief_signals_active"] is True
    assert decision.routing_debug["belief_signal_targets"]["emotional_block"]["confident"] is True
    assert decision.signal_scores["emotional_block"] == 0.86


def test_dual_core_router_ignores_high_uncertainty_belief_signal(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED", True)
    monkeypatch.setattr(settings, "SPARKLE_DUAL_CORE_BELIEF_UNCERTAINTY_MAX", 0.1)
    belief_state = BeliefState(user_id="u1")
    emotional_block = belief_state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    emotional_block.mean = 0.86
    emotional_block.variance = 0.22

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
            belief_state=belief_state,
        )
    )

    assert decision.mode == "execution_first"
    assert decision.routing_debug["belief_signals_active"] is True
    assert decision.routing_debug["belief_signal_targets"]["emotional_block"]["confident"] is False


def test_dual_core_router_logs_and_uses_capsule_method_preferences() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            capsule_preferences={
                "favorite_count": 1,
                "method_preferences": [
                    {"key": "pomodoro", "label": "番茄钟方法", "count": 1, "confidence": 0.8}
                ],
                "method_preference_summary": ["用户偏好番茄钟方法"],
            },
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert "User prefers 番茄钟方法" in rendered
    assert decision.routing_debug["explicit_capsule_signal"] is True
    assert decision.routing_debug["capsule_preferences"]["method_preference_summary"] == ["用户偏好番茄钟方法"]
    assert decision.routing_debug["capsule_method_preferences"][0]["key"] == "pomodoro"


def test_dual_core_router_uses_spine_state_register_for_cognitive_routing() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.92,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            spine_active_states=[
                {
                    "state_key": "knowledge_bottleneck",
                    "value": "transfer_failure",
                    "confidence": 0.82,
                    "scope": "session",
                }
            ],
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "cognitive_first"
    assert "Spine detected a knowledge bottleneck" in rendered
    assert decision.routing_debug["explicit_spine_state_signal"] is True
    assert decision.routing_debug["spine_knowledge_bottleneck"] is True


def test_dual_core_router_uses_spine_state_register_for_execution_granularity() -> None:
    decision = dual_core_router.route(
        DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.92,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 1},
            spine_active_states=[
                {
                    "state_key": "task_granularity_fit",
                    "value": "too_large",
                    "confidence": 0.72,
                    "scope": "task",
                }
            ],
        )
    )

    rendered = "\n".join(decision.cognitive_adjustments + decision.execution_constraints)
    assert decision.mode == "execution_first"
    assert "Spine detected execution consistency or task granularity drift" in rendered
    assert decision.routing_debug["spine_execution_low"] is True
    assert any(
        item["field"] == "planning_granularity"
        and item["recommended_value"] == "startup_ready"
        for item in decision.strategy_adjustments
    )


def test_dual_core_router_stabilizes_single_round_execution_to_cognitive_flip() -> None:
    decision = dual_core_router.route(
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
                    "description": "开始前往后拖。",
                    "confidence": 0.82,
                }
            ],
            previous_mode_state={
                "mode": "execution_first",
                "commitment_remaining": 1,
                "high_support_streak": 0,
                "low_risk_streak": 0,
            },
        )
    )

    assert decision.mode == "balanced"
    assert decision.routing_debug["mode_stability"]["reason"] == "execution_to_cognitive_requires_sustained_support_signal"
