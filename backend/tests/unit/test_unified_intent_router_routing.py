from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType


def test_determine_execution_mode_high_risk_forces_direct():
    router = UnifiedIntentRouter()
    mode = router._determine_execution_mode(
        message="请删除所有任务",
        intent=UnifiedIntentType.TASK,
        confidence=0.9,
    )
    assert mode == "direct"


def test_determine_execution_mode_complex_plan_uses_langgraph():
    router = UnifiedIntentRouter()
    mode = router._determine_execution_mode(
        message="帮我制定学习计划，然后分三步执行",
        intent=UnifiedIntentType.PLAN,
        confidence=0.8,
    )
    assert mode == "langgraph"


def test_determine_execution_mode_special_intent_uses_direct():
    router = UnifiedIntentRouter()
    mode = router._determine_execution_mode(
        message="帮我翻译这段话",
        intent=UnifiedIntentType.TRANSLATION,
        confidence=0.95,
    )
    assert mode == "direct"


def test_determine_execution_mode_default_direct():
    router = UnifiedIntentRouter()
    mode = router._determine_execution_mode(
        message="你好",
        intent=UnifiedIntentType.CHAT,
        confidence=0.7,
    )
    assert mode == "direct"


def test_assess_risk_level_high_medium_low():
    router = UnifiedIntentRouter()
    high = router._assess_risk_level(message="clear all tasks", intent=UnifiedIntentType.CHAT)
    medium = router._assess_risk_level(message="帮我创建任务", intent=UnifiedIntentType.TASK)
    low = router._assess_risk_level(message="今天天气如何", intent=UnifiedIntentType.CHAT)

    assert high == "high"
    assert medium == "medium"
    assert low == "low"
