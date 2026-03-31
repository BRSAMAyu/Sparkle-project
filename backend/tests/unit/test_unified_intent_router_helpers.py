from __future__ import annotations

from app.core.unified_intent_router import IntentRoutingResult, UnifiedIntentRouter, UnifiedIntentType


def test_build_context_string_uses_recent_window_and_truncates_content():
    router = UnifiedIntentRouter(context_window_size=2)

    context = router._build_context_string(
        [
            {"role": "system", "content": "ignored"},
            {"role": "assistant", "content": "A" * 250},
            {"role": "user", "content": "latest question"},
        ]
    )

    lines = context.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("1. [assistant]: ")
    assert lines[0].endswith("A" * 200)
    assert "ignored" not in context
    assert lines[1] == "2. [user]: latest question"


def test_should_skip_llm_assist_for_empty_message():
    router = UnifiedIntentRouter()
    result = IntentRoutingResult(primary_intent=UnifiedIntentType.CHAT, confidence=0.9)

    should_skip = router._should_skip_llm_assist(
        message="   ",
        rule_result=result,
        conversation_history=[{"role": "assistant", "content": "previous"}],
    )

    assert should_skip is True


def test_should_not_skip_llm_assist_when_rule_confidence_is_low():
    router = UnifiedIntentRouter()
    result = IntentRoutingResult(primary_intent=UnifiedIntentType.CHAT, confidence=0.49)

    should_skip = router._should_skip_llm_assist(
        message="换个角度解释一下",
        rule_result=result,
        conversation_history=[{"role": "assistant", "content": "previous"}],
    )

    assert should_skip is False


def test_should_not_skip_llm_assist_for_complex_follow_up():
    router = UnifiedIntentRouter()
    result = IntentRoutingResult(primary_intent=UnifiedIntentType.CHAT, confidence=0.8)

    should_skip = router._should_skip_llm_assist(
        message="先总结一下这题，然后给我一个三步复习方案。",
        rule_result=result,
        conversation_history=[{"role": "assistant", "content": "previous"}],
    )

    assert should_skip is False


def test_is_advisory_plan_query_distinguishes_consulting_from_explicit_planning():
    router = UnifiedIntentRouter()

    assert router._is_advisory_plan_query("Python 和 Go 我应该先学哪个？")
    assert not router._is_advisory_plan_query("帮我制定一个 Python 学习计划")


def test_map_fuzzy_intent_covers_known_aliases_and_falls_back_to_chat():
    router = UnifiedIntentRouter()

    assert router._map_fuzzy_intent("behavior summary") == UnifiedIntentType.COGNITIVE_PRISM
    assert router._map_fuzzy_intent("translation request") == UnifiedIntentType.TRANSLATION
    assert router._map_fuzzy_intent("未知分类") == UnifiedIntentType.CHAT


def test_extract_context_version_prefers_realtime_tasks_version():
    router = UnifiedIntentRouter()

    version = router._extract_context_version(
        {
            "realtime_versions": {"tasks": "task-v3"},
            "context_version": "context-v1",
        }
    )

    assert version == "task-v3"


def test_extract_context_version_falls_back_to_context_version():
    router = UnifiedIntentRouter()

    version = router._extract_context_version({"context_version": "context-v7"})

    assert version == "context-v7"


def test_determine_execution_mode_for_advisory_plan_stays_direct():
    router = UnifiedIntentRouter()

    mode = router._determine_execution_mode(
        message="考研数学和专业课我应该先学哪个？",
        intent=UnifiedIntentType.PLAN,
        confidence=0.95,
    )

    assert mode == "direct"


def test_determine_execution_mode_for_multi_intent_uses_langgraph():
    router = UnifiedIntentRouter()

    mode = router._determine_execution_mode(
        message="先解释这个概念，再帮我整理一个复习任务",
        intent=UnifiedIntentType.MULTI_INTENT,
        confidence=0.9,
    )

    assert mode == "langgraph"


def test_determine_execution_mode_for_high_confidence_error_diagnosis_uses_langgraph():
    router = UnifiedIntentRouter()

    mode = router._determine_execution_mode(
        message="帮我分析这道错题为什么错了",
        intent=UnifiedIntentType.ERROR_DIAGNOSIS,
        confidence=0.85,
    )

    assert mode == "langgraph"
