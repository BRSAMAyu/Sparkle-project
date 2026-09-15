from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.omnibar_service import OmniBarService


@pytest.mark.asyncio
async def test_dispatch_task_allows_lowercase_task_type(monkeypatch):
    service = OmniBarService(AsyncMock())
    user_id = uuid4()

    async def fake_classify(_text: str):
        return {
            "type": "TASK",
            "data": {
                "title": "今晚复习线性代数 30 分钟",
                "type": "learning",
                "estimated_minutes": 30,
                "priority": 2,
            },
        }

    create_mock = AsyncMock(return_value=SimpleNamespace(id=uuid4(), title="今晚复习线性代数 30 分钟"))
    monkeypatch.setattr(service, "_classify_intent", fake_classify)
    monkeypatch.setattr("app.services.omnibar_service.TaskService.create", create_mock)

    result = await service.dispatch(user_id=user_id, text="提醒我今晚复习线性代数 30 分钟")

    assert result["action_type"] == "TASK"
    assert create_mock.await_count == 1
    created = create_mock.await_args.kwargs["obj_in"]
    assert created.type.value == "LEARNING"


@pytest.mark.asyncio
async def test_dispatch_task_falls_back_to_chat_with_error_payload(monkeypatch):
    service = OmniBarService(AsyncMock())
    user_id = uuid4()

    async def fake_classify(_text: str):
        return {
            "type": "TASK",
            "data": {"title": "创建失败任务", "type": "learning"},
        }

    monkeypatch.setattr(service, "_classify_intent", fake_classify)
    monkeypatch.setattr("app.services.omnibar_service.TaskService.create", AsyncMock(side_effect=RuntimeError("boom")))

    result = await service.dispatch(user_id=user_id, text="提醒我做件事")

    assert result["action_type"] == "CHAT"
    assert "error" in result["data"]


@pytest.mark.asyncio
async def test_dispatch_task_uses_rule_fallback_when_llm_returns_chat(monkeypatch):
    service = OmniBarService(AsyncMock())
    user_id = uuid4()

    create_mock = AsyncMock(return_value=SimpleNamespace(id=uuid4(), title="今晚复习线性代数 30 分钟"))
    monkeypatch.setattr("app.services.llm_fallback_utils.omnibar_llm.json_call", AsyncMock(return_value={"type": "CHAT"}))
    monkeypatch.setattr("app.services.omnibar_service.TaskService.create", create_mock)

    result = await service.dispatch(user_id=user_id, text="提醒我今晚复习线性代数 30 分钟")

    assert result["action_type"] == "TASK"
    assert create_mock.await_count == 1
    created = create_mock.await_args.kwargs["obj_in"]
    assert created.estimated_minutes == 30
    assert created.type.value == "LEARNING"
