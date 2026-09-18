"""FT-LAT-2: 会话首条消息（空历史）的简单消息短路单元测试。

Before FT-LAT-2 the router unconditionally fell through to the Layer-3 LLM
classify call whenever conversation history was empty, so the very first
message of every session paid an extra serial LLM round trip before a single
token was streamed. After FT-LAT-2, empty history no longer forces the LLM:
the same light-message guards (chat intent, confidence floor, length cap,
complexity scan, action keywords) decide, so simple greetings short-circuit
while complex/action messages still get LLM assist.
"""

import asyncio

from app.core.unified_intent_router import IntentRoutingResult, UnifiedIntentRouter, UnifiedIntentType


def _chat_rule_result() -> IntentRoutingResult:
    return IntentRoutingResult(
        primary_intent=UnifiedIntentType.CHAT,
        confidence=0.5,
        routing_layer="rule",
        execution_mode="direct",
    )


def test_simple_first_message_skips_llm_assist_without_history():
    router = UnifiedIntentRouter()

    should_skip = router._should_skip_llm_assist(
        message="你好，简单介绍下你能做什么",
        rule_result=_chat_rule_result(),
        conversation_history=[],
    )

    assert should_skip is True


def test_route_uses_fast_path_for_simple_first_message_without_llm():
    """短路路径不调用规划（Layer-3 LLM 辅助分类）。"""
    router = UnifiedIntentRouter()
    llm_calls: list[int] = []

    async def _spy_llm_classify(message, conversation_history, rule_hints):
        llm_calls.append(1)
        return rule_hints

    router._llm_classify = _spy_llm_classify

    async def _run():
        return await router.route(
            message="你好，简单介绍下你能做什么",
            user_id="user",
            session_id="session",
            payload={},
            conversation_history=[],
        )

    result = asyncio.run(_run())

    assert llm_calls == []
    assert result.primary_intent == UnifiedIntentType.CHAT
    assert result.execution_mode == "direct"
    assert result.routing_layer == "rule_fast_path"
    assert (result.context_signals or {}).get("llm_assist_skipped") is True


def test_complex_first_message_still_uses_llm_assist():
    router = UnifiedIntentRouter()

    complex_message = (
        "我想深入理解一下微积分里的极限、导数和积分这三个概念到底有什么内在联系，"
        "然后你能不能帮我把这些概念放到物理学的运动学场景里再完整地讲一遍，"
        "最好再顺便对比一下高中数学和大学数学在讲法与侧重点上的差别。"
    )

    assert router._is_complex_intent(complex_message) is True
    should_skip = router._should_skip_llm_assist(
        message=complex_message,
        rule_result=_chat_rule_result(),
        conversation_history=[],
    )

    assert should_skip is False


def test_action_first_message_still_skips_to_direct_but_flags_no_complexity():
    """带动作词的简单首条消息：动作词守卫生效（不交给 LLM 猜意图，走直答由下游
    sufficiency/tool_planning 兜底），这里断言守卫返回 False。"""
    router = UnifiedIntentRouter()

    should_skip = router._should_skip_llm_assist(
        message="帮我创建一个今晚复习英语单词的任务",
        rule_result=_chat_rule_result(),
        conversation_history=[],
    )

    assert should_skip is False


def test_empty_history_no_longer_forces_llm_assist():
    """回归断言：空历史本身不再强制 LLM 辅助分类。"""
    router = UnifiedIntentRouter()

    should_skip = router._should_skip_llm_assist(
        message="在吗？",
        rule_result=_chat_rule_result(),
        conversation_history=[],
    )

    assert should_skip is True
