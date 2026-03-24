from app.core.unified_intent_router import IntentRoutingResult, UnifiedIntentRouter, UnifiedIntentType


def test_skip_llm_assist_for_short_follow_up_chat():
    router = UnifiedIntentRouter()
    result = IntentRoutingResult(
        primary_intent=UnifiedIntentType.CHAT,
        confidence=0.5,
        routing_layer="rule",
        execution_mode="direct",
    )

    should_skip = router._should_skip_llm_assist(
        message="基于刚才的解释，再换个更简单的说法。",
        rule_result=result,
        conversation_history=[{"role": "assistant", "content": "上一轮解释"}],
    )

    assert should_skip is True


def test_do_not_skip_llm_assist_for_explicit_task_request():
    router = UnifiedIntentRouter()
    result = IntentRoutingResult(
        primary_intent=UnifiedIntentType.CHAT,
        confidence=0.5,
        routing_layer="rule",
        execution_mode="direct",
    )

    should_skip = router._should_skip_llm_assist(
        message="帮我创建一个明天晚上 8 点提醒我的任务。",
        rule_result=result,
        conversation_history=[{"role": "assistant", "content": "上一轮解释"}],
    )

    assert should_skip is False
