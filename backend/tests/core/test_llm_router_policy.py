from app.core.agent_profiles import AgentRole
from app.core.llm_router import llm_router


def test_tool_execution_uses_policy_backed_registered_model():
    selection = llm_router.select_model(AgentRole.TOOL_EXECUTION)
    assert selection.model_key in {"mimo_pro", "dashscope_chat", "deepseek_chat"}


def test_science_agent_no_longer_points_to_removed_model_key():
    selection = llm_router.select_model(AgentRole.SCIENCE_AGENT)
    assert selection.model_key in {"dashscope_reason", "mimo_pro", "deepseek_reason"}
