from app.core.agent_profiles import AgentRole, TaskType
from app.core.llm_router import ModelProvider, llm_router


def test_tool_execution_uses_policy_backed_registered_model():
    selection = llm_router.select_model(AgentRole.TOOL_EXECUTION)
    assert selection.model_key in {
        "xiaomi_standard_thinking",
        "dashscope_standard_thinking",
        "dashscope_chat",
        "deepseek_chat",
    }
    assert selection.config.tier.value in {"standard", "plus"}


def test_science_agent_no_longer_points_to_removed_model_key():
    selection = llm_router.select_model(AgentRole.SCIENCE_AGENT)
    assert selection.model_key in {"dashscope_reason", "mimo_pro", "deepseek_reason"}


def test_reviewer_can_avoid_generation_provider():
    selection = llm_router.select_model(
        AgentRole.REVIEWER,
        TaskType.REVIEW,
        avoid_providers=[ModelProvider.DEEPSEEK],
    )
    assert selection.config.provider != ModelProvider.DEEPSEEK


def test_siliconflow_free_model_registered_in_free_tier():
    selection = llm_router.select_specific_model("siliconflow_free", agent_role=AgentRole.ROUTER)
    assert selection.config.provider == ModelProvider.SILICONFLOW
    assert selection.config.tier.value == "free"


def test_balanced_mode_prefers_standard_for_generation():
    selection = llm_router.select_model(
        AgentRole.GENERATION,
        TaskType.STANDARD_RESPONSE,
        reasoning_mode="balanced",
    )
    assert selection.config.tier.value == "standard"


def test_max_is_not_auto_selected_in_deep_mode():
    selection = llm_router.select_model(
        AgentRole.DEEP_ANALYST,
        TaskType.DEEP_REASONING,
        reasoning_mode="deep",
    )
    assert selection.config.tier.value in {"plus", "pro"}


def test_deep_mode_standard_chat_still_prefers_standard_tier():
    selection = llm_router.select_model(
        AgentRole.GENERATION,
        TaskType.STANDARD_RESPONSE,
        reasoning_mode="deep",
    )
    assert selection.config.tier.value == "standard"
