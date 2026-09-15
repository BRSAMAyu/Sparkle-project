import pytest

from app.orchestration.sufficiency_checker import SufficiencyChecker, SufficiencyStatus


@pytest.mark.asyncio
async def test_sufficiency_llm_fallback_disabled_keeps_rule_path():
    checker = SufficiencyChecker(strict_mode=False)
    result = await checker.check(
        intent="create_plan",
        extracted_entities={"plan_title": "冲刺计划", "plan_type": "sprint"},
        conversation_context=[],
        user_message="帮我做个计划",
        use_llm_fallback=False,
    )
    assert result.status == SufficiencyStatus.SUFFICIENT


@pytest.mark.asyncio
async def test_sufficiency_llm_fallback_plan_intent_needs_clarification(monkeypatch):
    checker = SufficiencyChecker(strict_mode=False)

    async def mock_refine(intent: str, user_message: str) -> bool:
        return False

    async def mock_question(intent: str, user_message: str) -> str:
        return "请补充目标考试时间和每天可投入时长。"

    monkeypatch.setattr(checker, "_llm_refinement", mock_refine)
    monkeypatch.setattr(checker, "_generate_clarification", mock_question)

    result = await checker.check(
        intent="create_plan",
        extracted_entities={"plan_title": "冲刺计划", "plan_type": "sprint"},
        conversation_context=[],
        user_message="帮我做个计划",
        use_llm_fallback=True,
    )
    assert result.status == SufficiencyStatus.NEED_CLARIFICATION
    assert result.clarification_text == "请补充目标考试时间和每天可投入时长。"


@pytest.mark.asyncio
async def test_sufficiency_llm_fallback_non_plan_intent_skips_llm(monkeypatch):
    checker = SufficiencyChecker(strict_mode=False)

    called = {"v": False}

    async def mock_refine(intent: str, user_message: str) -> bool:
        called["v"] = True
        return False

    monkeypatch.setattr(checker, "_llm_refinement", mock_refine)
    result = await checker.check(
        intent="knowledge_query",
        extracted_entities={"query": "牛顿第二定律"},
        conversation_context=[],
        user_message="解释牛顿第二定律",
        use_llm_fallback=True,
    )
    assert result.status == SufficiencyStatus.SUFFICIENT
    assert called["v"] is False


@pytest.mark.asyncio
async def test_sufficiency_checker_breaks_repeated_clarification_loop():
    checker = SufficiencyChecker(strict_mode=False)

    result1 = await checker.check(
        intent="create_task",
        extracted_entities={},
        conversation_context=[],
        tracking_key="user-1:session-1:create_task",
    )
    result2 = await checker.check(
        intent="create_task",
        extracted_entities={},
        conversation_context=[],
        tracking_key="user-1:session-1:create_task",
    )

    assert result1.status == SufficiencyStatus.NEED_CLARIFICATION
    assert result2.status == SufficiencyStatus.SUFFICIENT
    assert result2.recommended_action == "proceed"
    assert result2.clarification_questions == []
