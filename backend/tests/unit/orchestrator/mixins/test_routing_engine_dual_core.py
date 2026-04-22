from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRoutingInput
from app.orchestration.routing_engine import RoutingEngineMixin
from app.orchestration.schemas import RouteDecision
from app.services.social_signal_types import SocialSignalsV1
from app.services.srl_phase_types import SRLPhaseHint
from app.state_aggregator.schema import (
    MetacognitionDimensionSummaryValue,
    MetacognitionProfileSummaryValue,
    StateFieldEnvelope,
    UserStateV1,
)


class MinimalRoutingOrchestrator(RoutingEngineMixin):
    def __init__(self):
        self.redis = MagicMock()
        self.dual_core_router = MagicMock()
        self._get_recent_sentiment_distribution = AsyncMock(
            return_value={"anxious": 2, "calm": 1}
        )
        self._get_recent_task_feedback_distribution = AsyncMock(
            return_value={"too_long": 2, "too_difficult": 1}
        )


@pytest.fixture
def orchestrator() -> MinimalRoutingOrchestrator:
    return MinimalRoutingOrchestrator()


@pytest.mark.asyncio
async def test_build_dual_core_input_uses_active_plan_from_user_context(orchestrator):
    active_plan_id = uuid.uuid4()
    fake_report = SimpleNamespace(severity="warning")

    with patch("app.orchestration.routing_engine.PlanProgressService") as progress_service_cls:
        progress_service = progress_service_cls.return_value
        progress_service.evaluate_progress = AsyncMock(return_value=fake_report)

        routing_input = await orchestrator._build_dual_core_input(
            active_db=object(),
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload={
                "active_plans": [{"id": str(active_plan_id)}],
                "preferences": {"focus_duration_preference": 20, "difficulty_preference": 0.3},
            },
            plan_context={
                "user_profile": {"derived_insights": {"primary_challenge_area": "emotional"}},
            },
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.88,
            ),
            information_sufficient=False,
        )

    assert routing_input.intent == "plan"
    assert routing_input.intent_confidence == pytest.approx(0.88)
    assert routing_input.has_active_plan is True
    assert routing_input.plan_health_status == "warning"
    assert routing_input.primary_challenge_area == "emotional"
    assert routing_input.session_length_preference == 20
    assert routing_input.difficulty_preference == pytest.approx(0.3)
    assert routing_input.recent_sentiment_distribution == {"anxious": 2, "calm": 1}
    assert routing_input.recent_task_feedback_distribution == {"too_long": 2, "too_difficult": 1}
    progress_service.evaluate_progress.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_dual_core_input_tolerates_plan_progress_failures(orchestrator):
    with patch("app.orchestration.routing_engine.PlanProgressService") as progress_service_cls:
        progress_service = progress_service_cls.return_value
        progress_service.evaluate_progress = AsyncMock(side_effect=RuntimeError("redis down"))

        routing_input = await orchestrator._build_dual_core_input(
            active_db=object(),
            user_id=str(uuid.uuid4()),
            plan_id=uuid.uuid4(),
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=None,
            information_sufficient=True,
        )

    assert routing_input.intent == "chat"
    assert routing_input.intent_confidence == pytest.approx(0.5)
    assert routing_input.has_active_plan is True
    assert routing_input.plan_health_status is None


@pytest.mark.asyncio
async def test_build_dual_core_input_includes_cognitive_patterns_and_routing_profile(orchestrator):
    user_id = str(uuid.uuid4())
    fake_patterns = [
        SimpleNamespace(
            pattern_name="完美主义回避循环",
            pattern_type="execution",
            confidence_score=0.78,
            description="总想准备到完美才开始。",
        ),
        SimpleNamespace(
            pattern_name="认知盲点",
            pattern_type="cognitive",
            confidence_score=0.68,
            description="在相似概念上会重复误解。",
        ),
    ]

    with (
        patch("app.orchestration.routing_engine.PlanProgressService") as progress_service_cls,
        patch("app.orchestration.routing_engine.RoutingProfileService") as profile_service_cls,
        patch("app.orchestration.routing_engine.CognitiveService") as cognitive_service_cls,
    ):
        progress_service_cls.return_value.evaluate_progress = AsyncMock(
            return_value=SimpleNamespace(severity="warning")
        )
        profile_service_cls.return_value.get_profile = AsyncMock(
            return_value={
                "procrastination_threshold": 0.42,
                "emotional_sensitivity": 0.51,
                "directness_preference": 0.47,
            }
        )
        cognitive_service_cls.return_value.get_user_patterns = AsyncMock(return_value=fake_patterns)

        routing_input = await orchestrator._build_dual_core_input(
            active_db=object(),
            user_id=user_id,
            plan_id=uuid.uuid4(),
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.81,
            ),
            information_sufficient=True,
        )

    assert routing_input.routing_profile["procrastination_threshold"] == pytest.approx(0.42)
    assert routing_input.procrastination_pattern is True
    assert routing_input.cognitive_mode_suggested is True
    assert routing_input.suggested_verbosity == "supportive"
    assert routing_input.current_guidance
    assert routing_input.behavior_pattern_details[0]["pattern_name"] == "完美主义回避循环"


@pytest.mark.asyncio
async def test_build_dual_core_input_extracts_cognitive_load_from_plan_context(orchestrator):
    routing_input = await orchestrator._build_dual_core_input(
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload=None,
        plan_context={
            "user_profile": {
                "cognitive_state": {
                    "cognitive_load": 0.67,
                }
            }
        },
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="plan"),
            confidence=0.8,
        ),
        information_sufficient=True,
    )

    assert routing_input.cognitive_load == pytest.approx(0.67)


@pytest.mark.asyncio
async def test_build_dual_core_input_extracts_stage33_social_signals_from_cognitive_context(orchestrator):
    routing_input = await orchestrator._build_dual_core_input(
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload={
            "cognitive_context": {
                "social_context_v1": {
                    "mention_count": 2,
                    "relationship_count": 1,
                    "pending_commitments_count": 1,
                    "summary_lines": [
                        "最近 7 天提到过 2 位学习相关人物。",
                        "目前有 1 条到期承诺待跟进。",
                    ],
                }
            }
        },
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="plan"),
            confidence=0.77,
        ),
        information_sufficient=True,
    )

    assert routing_input.social_signals is not None
    assert routing_input.social_signals.mention_count == 2
    assert routing_input.social_signals.relationship_count == 1
    assert routing_input.social_signals.pending_commitments_count == 1


@pytest.mark.asyncio
async def test_build_dual_core_input_extracts_stage33_srl_hint_from_profile_context(orchestrator):
    routing_input = await orchestrator._build_dual_core_input(
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload={
            "profile_context": {
                "user_insight_state": {
                    "srl_phase": {
                        "current_phase": "SELF_REFLECTION",
                        "confidence": 0.81,
                        "source": "aggregator",
                        "freshness_seconds": 9,
                    }
                }
            }
        },
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="plan"),
            confidence=0.77,
        ),
        information_sufficient=True,
    )

    assert routing_input.srl_phase_hint is not None
    assert routing_input.srl_phase_hint.current_phase == "reflection"
    assert routing_input.srl_phase_hint.confidence == pytest.approx(0.81)


@pytest.mark.asyncio
async def test_build_metacognition_hint_derives_accuracy_from_user_scoped_aggregator(orchestrator):
    user_id = str(uuid.uuid4())

    with patch(
        "app.orchestration.routing_engine.StateAggregatorService.get_user_state",
        AsyncMock(
            return_value=UserStateV1(
                user_id=uuid.UUID(user_id),
                metacognition_profile=StateFieldEnvelope(
                    value=MetacognitionProfileSummaryValue(
                        items=(
                            MetacognitionDimensionSummaryValue(
                                dim="time_estimation_bias",
                                sample_size=32,
                                bias_mean=0.18,
                                trend="improving",
                            ),
                            MetacognitionDimensionSummaryValue(
                                dim="completion_bias",
                                sample_size=30,
                                bias_mean=0.12,
                                trend="stable",
                            ),
                        )
                    ),
                    computed_at=datetime(2026, 4, 22, 9, 6, 0),
                    source_snapshot_ids=("metacognition:time_estimation_bias",),
                    freshness_seconds=0,
                ),
            )
        ),
    ):
        hint = await orchestrator._build_metacognition_hint(
            active_db=object(),
            user_id=user_id,
            user_context_payload=None,
        )

    assert hint is not None
    assert hint.accuracy == pytest.approx(0.85, abs=0.01)
    assert hint.awareness == "strong"
    assert hint.last_updated == datetime(2026, 4, 22, 9, 6, 0)


@pytest.mark.asyncio
async def test_build_metacognition_hint_returns_none_when_profile_is_empty(orchestrator):
    with patch(
        "app.orchestration.routing_engine.StateAggregatorService.get_user_state",
        AsyncMock(return_value=UserStateV1(user_id=uuid.uuid4())),
    ):
        hint = await orchestrator._build_metacognition_hint(
            active_db=object(),
            user_id=str(uuid.uuid4()),
            user_context_payload=None,
        )

    assert hint is None


@pytest.mark.asyncio
async def test_apply_dual_core_routing_for_cognitive_first_rewrites_langgraph_route(orchestrator):
    decision = DualCoreDecision(
        mode="cognitive_first",
        reason="need emotional grounding first",
        cognitive_adjustments=["先减轻焦虑"],
        execution_constraints=["先不要给太重的任务"],
    )
    orchestrator.dual_core_router.route.return_value = decision
    state = SimpleNamespace(context_data={"plan_metadata": {"existing": "value"}})
    stream_callback = AsyncMock()

    route_decision = RouteDecision(
        execution_mode="langgraph",
        reason="complex plan flow",
        risk_level="medium",
        confidence=0.8,
    )

    updated = await orchestrator._apply_dual_core_routing(
        route_decision=route_decision,
        state=state,
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload=None,
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="plan"),
            confidence=0.91,
        ),
        information_sufficient=False,
        stream_callback=stream_callback,
    )

    assert updated is route_decision
    assert updated.execution_mode == "direct"
    assert updated.reason.endswith("dual_core:cognitive_first")
    assert state.context_data["dual_core_decision"]["mode"] == "cognitive_first"
    assert "双核心认知调制" in state.context_data["dual_core_prompt_instruction"]
    assert state.context_data["dual_core_signal_snapshot"]["intent"] == "plan"
    assert state.context_data["plan_metadata"]["dual_core_mode"] == "cognitive_first"
    assert state.context_data["plan_metadata"]["dual_core_reason"] == "need emotional grounding first"
    stream_callback.assert_awaited_once()
    emitted = stream_callback.await_args.args[0]
    assert emitted.metadata
    assert "ux_progress" in emitted.metadata


@pytest.mark.asyncio
async def test_apply_dual_core_routing_persists_current_guidance_in_snapshot(orchestrator):
    decision = DualCoreDecision(
        mode="balanced",
        reason="need a lighter cognitive bridge",
        cognitive_adjustments=["先降摩擦"],
        execution_constraints=[],
        routing_debug={"explicit_procrastination_signal": True},
    )
    orchestrator.dual_core_router.route.return_value = decision
    state = SimpleNamespace(context_data={"plan_metadata": {}})

    with patch.object(
        orchestrator,
        "_build_dual_core_input",
        AsyncMock(
            return_value=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.76,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 2},
                has_active_plan=False,
                plan_health_status="warning",
                recent_task_feedback_distribution={"too_long": 1},
                behavior_pattern_names=["完美主义回避循环"],
                behavior_pattern_details=[{"pattern_name": "完美主义回避循环"}],
                behavior_pattern_types={"execution": 1},
                session_length_preference=None,
                difficulty_preference=None,
                emotional_block_detected=False,
                procrastination_pattern=False,
                cognitive_mode_suggested=False,
                suggested_verbosity=None,
                routing_profile={"procrastination_threshold": 0.6},
                adaptive_adjustments={},
                current_guidance="优先先搭桥，再给任务。",
            )
        ),
    ):
        await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="needs mixed handling",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.76,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert state.context_data["dual_core_signal_snapshot"]["current_guidance"] == "优先先搭桥，再给任务。"


@pytest.mark.asyncio
async def test_apply_dual_core_routing_short_circuits_general_chat_to_execution_first(orchestrator):
    state = SimpleNamespace(context_data={})
    stream_callback = AsyncMock()
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="simple answer path",
        risk_level="low",
        confidence=0.7,
    )

    updated = await orchestrator._apply_dual_core_routing(
        route_decision=route_decision,
        state=state,
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload=None,
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="chat"),
            confidence=0.8,
        ),
        information_sufficient=True,
        stream_callback=stream_callback,
    )

    assert updated.execution_mode == "direct"
    assert updated.reason.endswith("dual_core:execution_first")
    assert state.context_data["dual_core_decision"]["mode"] == "execution_first"
    orchestrator.dual_core_router.route.assert_not_called()


@pytest.mark.asyncio
async def test_apply_dual_core_routing_records_shadow_comparison_without_taking_over(orchestrator):
    legacy_decision = DualCoreDecision(
        mode="execution_first",
        reason="legacy decision",
        cognitive_adjustments=[],
        execution_constraints=[],
    )
    aurora_decision = DualCoreDecision(
        mode="cognitive_first",
        reason="aurora projected",
        cognitive_adjustments=["先支持"],
        execution_constraints=[],
    )
    orchestrator.dual_core_router.route.return_value = legacy_decision
    state = SimpleNamespace(context_data={"plan_metadata": {}})

    with (
        patch("app.orchestration.routing_engine.resolve_cutover_state", return_value=SimpleNamespace(mode="shadow", reason="shadow_cohort_selected")),
        patch(
            "app.orchestration.routing_engine.route_dual_core_via_aurora",
            return_value=SimpleNamespace(
                projected_decision=aurora_decision,
                transition_decision=SimpleNamespace(
                    decision_type="stay",
                    decision_basis=SimpleNamespace(value="behavioral_signal"),
                    impact_class=SimpleNamespace(value="medium"),
                ),
            ),
        ),
        patch("app.orchestration.routing_engine.record_shadow_divergence_if_needed", return_value=True) as divergence_mock,
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="legacy route",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.81,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert updated.reason.endswith("dual_core:execution_first")
    assert state.context_data["dual_core_decision"]["mode"] == "execution_first"
    assert state.context_data["aurora_cutover_state"]["mode"] == "shadow"
    assert state.context_data["aurora_shadow_comparison"]["aurora_mode"] == "cognitive_first"
    assert state.context_data["aurora_shadow_comparison"]["legacy_mode"] == "execution_first"
    assert state.context_data["aurora_shadow_comparison"]["diverged"] is True
    divergence_mock.assert_called_once()


@pytest.mark.asyncio
async def test_apply_dual_core_routing_records_stage33_social_shadow_delta(orchestrator):
    orchestrator.dual_core_router.route.side_effect = [
        DualCoreDecision(
            mode="execution_first",
            reason="legacy route",
            cognitive_adjustments=[],
            execution_constraints=[],
        ),
        DualCoreDecision(
            mode="execution_first",
            reason="social-aware route",
            cognitive_adjustments=["涉及他人或协作情境时，保持边界感，不要替用户许诺或推断他人立场。"],
            execution_constraints=["若要安排下一步，请先兼容用户已有的对外承诺，避免叠加新的长期负债。"],
        ),
    ]
    state = SimpleNamespace(context_data={"plan_metadata": {}})
    user_context_payload = {}

    with (
        patch(
            "app.orchestration.routing_engine.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "shadow",
                    "social": "shadow",
                    "srl": "shadow",
                    "wm_prompt": "shadow",
                    "events": "shadow",
                }
            ),
        ),
        patch(
            "app.orchestration.routing_engine.resolve_cutover_state",
            return_value=SimpleNamespace(mode="control", reason="test_control"),
        ),
        patch.object(
            orchestrator,
            "_build_dual_core_input",
            AsyncMock(
                return_value=DualCoreRoutingInput(
                    intent="plan",
                    intent_confidence=0.82,
                    information_sufficient=True,
                    primary_challenge_area="execution",
                    recent_sentiment_distribution={"neutral": 2},
                    has_active_plan=True,
                    plan_health_status="healthy",
                    recent_task_feedback_distribution={"just_right": 1},
                    behavior_pattern_names=[],
                    behavior_pattern_types={},
                    behavior_pattern_details=[],
                    session_length_preference=25,
                    difficulty_preference=0.5,
                    emotional_block_detected=False,
                    procrastination_pattern=False,
                    cognitive_mode_suggested=False,
                    suggested_verbosity=None,
                    current_guidance=None,
                    routing_profile={},
                    adaptive_adjustments={},
                    social_signals=SocialSignalsV1(
                        mention_count=2,
                        relationship_count=1,
                        pending_commitments_count=1,
                        summary_lines=(
                            "最近 7 天提到过 2 位学习相关人物。",
                            "目前有 1 条到期承诺待跟进。",
                        ),
                    ),
                )
            ),
        ),
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="legacy route",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=user_context_payload,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.82,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert updated.reason.endswith("dual_core:execution_first")
    assert user_context_payload["aurora_stage33_modes"]["social"] == "shadow"
    assert state.context_data["stage33_shadow_delta"]["social"]["mode_changed"] is False
    assert state.context_data["stage33_shadow_delta"]["social"]["added_execution_constraints"]
    assert state.context_data["stage33_shadow_delta"]["social"]["signal_payload"]["mention_count"] == 2


@pytest.mark.asyncio
async def test_apply_dual_core_routing_records_stage33_srl_shadow_delta(orchestrator):
    orchestrator.dual_core_router.route.side_effect = [
        DualCoreDecision(
            mode="execution_first",
            reason="legacy route",
            cognitive_adjustments=[],
            execution_constraints=[],
        ),
        DualCoreDecision(
            mode="cognitive_first",
            reason="reflection-aware route",
            cognitive_adjustments=["用户当前处在复盘反思阶段，先帮助总结哪里有效、哪里失灵，再决定下一轮怎么改。"],
            execution_constraints=[],
        ),
    ]
    state = SimpleNamespace(context_data={"plan_metadata": {}})
    user_context_payload = {}

    with (
        patch(
            "app.orchestration.routing_engine.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "shadow",
                    "social": "off",
                    "srl": "shadow",
                    "wm_prompt": "shadow",
                    "events": "shadow",
                }
            ),
        ),
        patch(
            "app.orchestration.routing_engine.resolve_cutover_state",
            return_value=SimpleNamespace(mode="control", reason="test_control"),
        ),
        patch.object(
            orchestrator,
            "_build_dual_core_input",
            AsyncMock(
                return_value=DualCoreRoutingInput(
                    intent="plan",
                    intent_confidence=0.82,
                    information_sufficient=True,
                    primary_challenge_area="execution",
                    recent_sentiment_distribution={"neutral": 2},
                    has_active_plan=True,
                    plan_health_status="healthy",
                    recent_task_feedback_distribution={"just_right": 1},
                    behavior_pattern_names=[],
                    behavior_pattern_types={},
                    behavior_pattern_details=[],
                    session_length_preference=25,
                    difficulty_preference=0.5,
                    emotional_block_detected=False,
                    procrastination_pattern=False,
                    cognitive_mode_suggested=False,
                    suggested_verbosity=None,
                    current_guidance=None,
                    routing_profile={},
                    adaptive_adjustments={},
                    srl_phase_hint=SRLPhaseHint(
                        current_phase="reflection",
                        confidence=0.79,
                        source="aggregator",
                        freshness_seconds=8,
                    ),
                )
            ),
        ),
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="legacy route",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=user_context_payload,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.82,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert updated.reason.endswith("dual_core:execution_first")
    assert user_context_payload["aurora_stage33_modes"]["srl"] == "shadow"
    assert state.context_data["stage33_shadow_delta"]["srl"]["mode_changed"] is True
    assert state.context_data["stage33_shadow_delta"]["srl"]["signal_payload"]["current_phase"] == "reflection"


@pytest.mark.asyncio
async def test_apply_dual_core_routing_records_stage35_metacognition_shadow_delta(orchestrator):
    orchestrator.dual_core_router.route.side_effect = [
        DualCoreDecision(
            mode="execution_first",
            reason="legacy route",
            cognitive_adjustments=[],
            execution_constraints=[],
        ),
        DualCoreDecision(
            mode="cognitive_first",
            reason="metacog-aware route",
            cognitive_adjustments=["用户最近对自己状态或耗时的判断偏差较大，先校准判断，再进入执行推进。"],
            execution_constraints=[],
        ),
    ]
    state = SimpleNamespace(context_data={"plan_metadata": {}})
    user_context_payload = {}

    with (
        patch(
            "app.orchestration.routing_engine.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "shadow",
                    "social": "off",
                    "srl": "off",
                    "wm_prompt": "shadow",
                    "events": "shadow",
                }
            ),
        ),
        patch(
            "app.orchestration.routing_engine.AuroraStage35KillSwitchService.summary",
            AsyncMock(return_value={"mode": "shadow", "metacog_router_mode": "shadow"}),
        ),
        patch(
            "app.orchestration.routing_engine.resolve_cutover_state",
            return_value=SimpleNamespace(mode="control", reason="test_control"),
        ),
        patch.object(
            orchestrator,
            "_build_dual_core_input",
            AsyncMock(
                return_value=DualCoreRoutingInput(
                    intent="plan",
                    intent_confidence=0.82,
                    information_sufficient=True,
                    primary_challenge_area="execution",
                    recent_sentiment_distribution={"neutral": 2},
                    has_active_plan=True,
                    plan_health_status="healthy",
                    recent_task_feedback_distribution={"just_right": 1},
                    behavior_pattern_names=[],
                    behavior_pattern_types={},
                    behavior_pattern_details=[],
                    session_length_preference=25,
                    difficulty_preference=0.5,
                    emotional_block_detected=False,
                    procrastination_pattern=False,
                    cognitive_mode_suggested=False,
                    suggested_verbosity=None,
                    current_guidance=None,
                    routing_profile={},
                    adaptive_adjustments={},
                    metacognition_hint=RoutingEngineMixin._derive_metacognition_hint_from_payload(
                        {
                            "computed_at": "2026-04-22T09:06:00",
                            "value": {
                                "items": [
                                    {"dim": "time_estimation_bias", "sample_size": 24, "bias_mean": 0.66},
                                ]
                            },
                        }
                    ),
                )
            ),
        ),
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="legacy route",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=user_context_payload,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.82,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert updated.reason.endswith("dual_core:execution_first")
    assert user_context_payload["aurora_stage35_modes"]["metacog_router_mode"] == "shadow"
    assert state.context_data["stage35_metacognition_shadow_delta"]["mode_changed"] is True
    assert state.context_data["stage35_metacognition_shadow_delta"]["hint_payload"]["awareness"] == "moderate"


@pytest.mark.asyncio
async def test_apply_dual_core_routing_records_stage39_cognitive_load_shadow_delta(orchestrator):
    orchestrator.dual_core_router.route.side_effect = [
        DualCoreDecision(
            mode="execution_first",
            reason="legacy route",
            cognitive_adjustments=[],
            execution_constraints=[],
        ),
        DualCoreDecision(
            mode="cognitive_first",
            reason="high cognitive load route",
            cognitive_adjustments=["当前认知负荷偏高，先降低方案复杂度，再给更容易启动的下一步。"],
            execution_constraints=[],
        ),
    ]
    state = SimpleNamespace(context_data={"plan_metadata": {}})
    user_context_payload = {}

    with (
        patch(
            "app.orchestration.routing_engine.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "shadow",
                    "social": "off",
                    "srl": "off",
                    "wm_prompt": "shadow",
                    "events": "shadow",
                }
            ),
        ),
        patch(
            "app.orchestration.routing_engine.AuroraStage35KillSwitchService.summary",
            AsyncMock(return_value={"mode": "shadow", "metacog_router_mode": "off"}),
        ),
        patch(
            "app.orchestration.routing_engine.AuroraStage39KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "live",
                    "scaffolding_prompt_mode": "live",
                    "cogload_route_mode": "shadow",
                    "galaxy_inject_mode": "shadow",
                }
            ),
        ),
        patch(
            "app.orchestration.routing_engine.resolve_cutover_state",
            return_value=SimpleNamespace(mode="control", reason="test_control"),
        ),
        patch.object(
            orchestrator,
            "_build_dual_core_input",
            AsyncMock(
                return_value=DualCoreRoutingInput(
                    intent="plan",
                    intent_confidence=0.82,
                    information_sufficient=True,
                    primary_challenge_area="execution",
                    recent_sentiment_distribution={"neutral": 2},
                    has_active_plan=True,
                    plan_health_status="healthy",
                    recent_task_feedback_distribution={"just_right": 1},
                    behavior_pattern_names=[],
                    behavior_pattern_types={},
                    behavior_pattern_details=[],
                    session_length_preference=25,
                    difficulty_preference=0.5,
                    emotional_block_detected=False,
                    procrastination_pattern=False,
                    cognitive_mode_suggested=False,
                    suggested_verbosity=None,
                    current_guidance=None,
                    routing_profile={},
                    adaptive_adjustments={},
                    cognitive_load=0.81,
                )
            ),
        ),
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="hybrid",
                reason="legacy route",
                risk_level="medium",
                confidence=0.7,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=user_context_payload,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.82,
            ),
            information_sufficient=True,
            stream_callback=AsyncMock(),
        )

    assert updated.reason.endswith("dual_core:execution_first")
    assert user_context_payload["aurora_stage39_modes"]["cogload_route_mode"] == "shadow"
    assert state.context_data["stage39_cognitive_load_shadow_delta"]["mode_changed"] is True
    assert state.context_data["stage39_cognitive_load_shadow_delta"]["cognitive_load"] == 0.81


@pytest.mark.asyncio
async def test_apply_dual_core_routing_uses_aurora_projection_for_active_cohort(orchestrator):
    orchestrator.dual_core_router.route.return_value = DualCoreDecision(
        mode="execution_first",
        reason="legacy route",
        cognitive_adjustments=[],
        execution_constraints=[],
    )
    state = SimpleNamespace(context_data={"plan_metadata": {}})

    with patch(
        "app.orchestration.routing_engine.resolve_cutover_state",
        return_value=SimpleNamespace(mode="active", reason="active_cohort_selected"),
    ), patch(
        "app.orchestration.routing_engine.route_dual_core_via_aurora",
        return_value=SimpleNamespace(
            projected_decision=DualCoreDecision(
                mode="cognitive_first",
                reason="aurora active route",
                cognitive_adjustments=["先支持"],
                execution_constraints=[],
            ),
            transition_decision=SimpleNamespace(
                decision_type="stay",
                decision_basis=SimpleNamespace(value="behavioral_signal"),
                impact_class=SimpleNamespace(value="medium"),
            ),
        ),
    ):
        updated = await orchestrator._apply_dual_core_routing(
            route_decision=RouteDecision(
                execution_mode="langgraph",
                reason="complex plan flow",
                risk_level="medium",
                confidence=0.8,
            ),
            state=state,
            active_db=None,
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.91,
            ),
            information_sufficient=False,
            stream_callback=AsyncMock(),
        )

    assert updated.execution_mode == "direct"
    assert updated.reason.endswith("dual_core:cognitive_first")
    assert state.context_data["dual_core_decision"]["mode"] == "cognitive_first"
    assert state.context_data["aurora_cutover_state"]["mode"] == "active"
    assert state.context_data["plan_metadata"]["dual_core_source"] == "aurora"
    orchestrator.dual_core_router.route.assert_not_called()
