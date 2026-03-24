import pytest

from app.schemas.intent import IntentParseRequest, IntentType
from app.services.multi_intent_service import MultiIntentService


@pytest.mark.asyncio
async def test_multi_intent_service_falls_back_to_heuristics_when_llm_unavailable(monkeypatch):
    service = MultiIntentService(db=None)

    async def _fake_parse_with_llm(messages):
        return None

    monkeypatch.setattr(service, "_parse_with_llm", _fake_parse_with_llm)

    result = await service.parse_intents(
        IntentParseRequest(message="帮我创建一个复习任务，然后解释一下矩阵乘法")
    )

    assert result.is_multi_intent is True
    assert len(result.intents) == 2
    assert result.intents[0].type == IntentType.TASK_MANAGEMENT
    assert result.intents[1].type == IntentType.KNOWLEDGE_QUERY


@pytest.mark.asyncio
async def test_multi_intent_service_heuristics_keep_single_intent_for_simple_message(monkeypatch):
    service = MultiIntentService(db=None)

    async def _fake_parse_with_llm(messages):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(service, "_parse_with_llm", _fake_parse_with_llm)

    result = await service.parse_intents(
        IntentParseRequest(message="提醒我明天上午九点复习线性代数")
    )

    assert result.is_multi_intent is False
    assert len(result.intents) == 1
    assert result.intents[0].type in {IntentType.TASK_MANAGEMENT, IntentType.TIME_PLANNING}
