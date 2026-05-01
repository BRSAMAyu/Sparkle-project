from app.orchestration.prompts import build_conversation_memory_fragment, build_system_prompt


def _conversation_messages() -> list[dict[str, str]]:
    return [
        {"role": "user", "content": "我最头疼的是 TCP 状态机，三次握手还行。"},
        {"role": "assistant", "content": "我们先拆状态和迁移。"},
        {"role": "user", "content": "目标是今晚能做对连接管理选择题。"},
        {"role": "assistant", "content": "可以。"},
        {"role": "user", "content": "OSI 模型闭卷复述已经完成了。"},
        {"role": "assistant", "content": "收到。"},
    ]


def test_conversation_memory_fragment_extracts_key_points_without_raw_dump() -> None:
    fragment = build_conversation_memory_fragment({"messages": _conversation_messages()})

    assert "本轮对话中用户已提及：" in fragment
    assert "- 困难：TCP状态机" in fragment
    assert "- 目标：今晚能做对连接管理选择题" in fragment
    assert "- 已完成：OSI模型闭卷复述" in fragment
    assert "我最头疼的是 TCP 状态机" not in fragment
    assert "助手" not in fragment


def test_conversation_memory_fragment_requires_enough_history() -> None:
    fragment = build_conversation_memory_fragment({"messages": _conversation_messages()[:3]})

    assert fragment == ""


def test_build_system_prompt_injects_conversation_memory_fragment() -> None:
    prompt = build_system_prompt(
        user_context={"preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5}},
        conversation_history={"messages": _conversation_messages()},
    )

    assert "## 对话记忆片段" in prompt
    assert "- 困难：TCP状态机" in prompt
    assert "- 已完成：OSI模型闭卷复述" in prompt
