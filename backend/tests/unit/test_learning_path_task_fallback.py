from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.llm_fallback_utils import safe_llm_json_call
from app.tools.plan_tools import GenerateTasksForPlanTool
from app.tools.schemas import GenerateTasksForPlanParams


@pytest.mark.asyncio
async def test_safe_llm_json_call_parses_fenced_json_array(monkeypatch):
    async def _fake_chat(messages, **kwargs):
        return """
这里是结果：
```json
[
  {
    "title": "复习大学物理",
    "description": "梳理关键概念",
    "type": "learning",
    "estimated_minutes": 25,
    "priority": 2
  }
]
```
"""

    monkeypatch.setattr("app.services.llm_fallback_utils.llm_service.chat", _fake_chat)

    result = await safe_llm_json_call([{"role": "user", "content": "return json"}], fallback=[])

    assert isinstance(result, list)
    assert result[0]["title"] == "复习大学物理"


@pytest.mark.asyncio
async def test_generate_tasks_tool_uses_deterministic_fallback_when_llm_returns_none(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()
    prerequisite_id = uuid4()
    target_id = uuid4()

    fake_plan = SimpleNamespace(
        id=plan_id,
        user_id=user_id,
        name="学习路径：经典力学",
        description="计划描述",
        subject="经典力学",
        source="learning_path",
        source_metadata={"path_node_ids": [str(prerequisite_id), str(target_id)]},
    )

    fake_rows = [
        SimpleNamespace(id=prerequisite_id, name="大学物理"),
        SimpleNamespace(id=target_id, name="经典力学"),
    ]
    fake_result = SimpleNamespace(all=lambda: fake_rows)
    fake_db = SimpleNamespace(
        execute=AsyncMock(return_value=fake_result),
        rollback=AsyncMock(),
    )

    monkeypatch.setattr("app.tools.plan_tools.PlanService.get_by_id", AsyncMock(return_value=fake_plan))
    monkeypatch.setattr(
        "app.tools.plan_tools.PersonaAwarePlanner.build_constraints",
        AsyncMock(return_value=None),
    )
    fake_rag_result = SimpleNamespace(fused_context="")
    monkeypatch.setattr(
        "app.orchestration.graph_rag.GraphRAGRetriever.retrieve",
        AsyncMock(return_value=fake_rag_result),
    )

    created_tasks = [
        SimpleNamespace(
            id=uuid4(),
            title="补齐前置知识：大学物理",
            type=SimpleNamespace(value="LEARNING"),
            estimated_minutes=25,
            priority=2,
            description="desc",
        ),
        SimpleNamespace(
            id=uuid4(),
            title="建立 经典力学 核心概念框架",
            type=SimpleNamespace(value="LEARNING"),
            estimated_minutes=35,
            priority=3,
            description="desc",
        ),
    ]
    monkeypatch.setattr("app.tools.plan_tools.TaskService.create", AsyncMock(side_effect=created_tasks))

    tool = GenerateTasksForPlanTool()
    monkeypatch.setattr(tool, "_generate_tasks_with_llm", AsyncMock(return_value=None))

    result = await tool.execute(
        GenerateTasksForPlanParams(
            plan_id=str(plan_id),
            topic="经典力学",
            difficulty="medium",
            task_count=2,
        ),
        user_id=str(user_id),
        db_session=fake_db,
    )

    assert result.success is True
    assert len(result.data["tasks"]) == 2
    assert result.data["tasks"][0]["title"].startswith("补齐前置知识")
    assert fake_db.execute.await_count >= 1
