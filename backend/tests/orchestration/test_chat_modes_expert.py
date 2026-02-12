from app.orchestration.chat_modes import (
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_EXPERT_PREFIX,
    CHAT_MODE_STANDARD,
    extract_expert_id,
    is_expert_chat_mode,
    normalize_chat_mode,
)


def test_normalize_chat_mode_supports_expert_values():
    assert normalize_chat_mode("expert_auto") == CHAT_MODE_EXPERT_AUTO
    assert normalize_chat_mode("expert::math_agent") == "expert::math_agent"
    assert normalize_chat_mode("unknown_mode") == CHAT_MODE_STANDARD
    assert normalize_chat_mode("") == CHAT_MODE_STANDARD


def test_expert_chat_mode_detection_and_extraction():
    explicit_mode = f"{CHAT_MODE_EXPERT_PREFIX}code_agent"
    assert is_expert_chat_mode("expert_auto") is True
    assert is_expert_chat_mode(explicit_mode) is True
    assert extract_expert_id(explicit_mode) == "code_agent"
    assert extract_expert_id("standard") is None
