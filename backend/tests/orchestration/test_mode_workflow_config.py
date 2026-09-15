from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_STUDY_PLAN,
)
from app.orchestration.mode_workflow_config import get_workflow_config
from app.services.custom_expert_service import CUSTOM_EXPERT_PREFIX


def test_mode_configs_exist_and_are_sequential():
    for mode in [CHAT_MODE_DEEP_ANALYSIS, CHAT_MODE_STUDY_PLAN, CHAT_MODE_ERROR_DIAGNOSIS]:
        config = get_workflow_config(mode)
        assert config is not None
        assert config.collaboration_mode == "sequential"
        assert len(config.collaboration_agents) >= 2
        assert len(config.collaboration_order) >= 2
        assert all("agent" in step for step in config.collaboration_order)


def test_error_diagnosis_defaults_to_confirmation_gate():
    config = get_workflow_config(CHAT_MODE_ERROR_DIAGNOSIS)
    assert config is not None
    assert config.tool_policy.get("allow_record_error_without_confirmation") is False


def test_team_mode_preserves_custom_expert_ids_and_final_agents():
    mode = (
        'team::{"agents":["deep_analyst","'
        + CUSTOM_EXPERT_PREFIX
        + '12345678-1234-5678-1234-567812345678"],'
        '"final_agents":["'
        + CUSTOM_EXPERT_PREFIX
        + '12345678-1234-5678-1234-567812345678"],'
        '"mode":"debate"}'
    )
    config = get_workflow_config(mode)
    assert config is not None
    assert config.collaboration_mode == "debate"
    assert any(agent.startswith(CUSTOM_EXPERT_PREFIX) for agent in config.required_agents)
    assert any(agent.startswith(CUSTOM_EXPERT_PREFIX) for agent in config.answer_agents)
