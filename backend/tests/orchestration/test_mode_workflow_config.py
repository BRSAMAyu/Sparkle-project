from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_STUDY_PLAN,
)
from app.orchestration.mode_workflow_config import get_workflow_config


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
