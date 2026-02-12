from app.orchestration.chat_modes import CHAT_MODE_EXPERT_AUTO, CHAT_MODE_STUDY_PLAN
from app.orchestration.expert_strategy import ExpertStrategyV1, parse_selected_experts
from app.orchestration.expert_strategy_v2 import ExpertStrategyV2


def test_parse_selected_experts_supports_csv_and_json() -> None:
    assert parse_selected_experts("deep_analyst,code_agent") == ["deep_analyst", "code_agent"]
    assert parse_selected_experts('["deep_analyst", "code_agent"]') == ["deep_analyst", "code_agent"]
    assert parse_selected_experts(["deep_analyst", "code_agent"]) == ["deep_analyst", "code_agent"]


def test_strategy_v1_explicit_unavailable_fallback() -> None:
    decision = ExpertStrategyV1.route(
        message="请帮我分析这个问题",
        chat_mode="expert::unknown_expert",
        user_preferences={},
        user_context={},
    )
    assert decision.routing_strategy == "explicit_expert_fallback"
    assert decision.selected_experts
    assert decision.fallback_reason is not None


def test_strategy_v2_routes_and_emits_metadata() -> None:
    decision = ExpertStrategyV2.route(
        message="请给我一个分步骤的学习计划，并说明为什么这样安排。",
        chat_mode=CHAT_MODE_EXPERT_AUTO,
        user_preferences={},
        user_context={},
    )

    assert decision.selected_experts
    assert decision.policy_id.startswith("expert_strategy_v2:")
    metadata = decision.to_metadata()
    for key in (
        "selected_experts",
        "routing_strategy",
        "fallback_reason",
        "route_confidence",
        "expert_entry_source",
        "policy_id",
        "complexity_score",
        "complexity_tier",
    ):
        assert key in metadata


def test_strategy_v2_study_plan_pack_policy_id() -> None:
    decision = ExpertStrategyV2.route(
        message="请给我一个12周学习计划，按里程碑拆解并给验收标准。",
        chat_mode=CHAT_MODE_STUDY_PLAN,
        user_preferences={},
        user_context={},
    )
    assert decision.policy_id == "expert_strategy_v2:study_plan_v1"
