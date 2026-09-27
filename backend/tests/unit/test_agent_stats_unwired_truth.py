"""
V3-FIX-330 红→绿测：/agent-stats/* 读侧在写侧未接线时必须如实标 unavailable

背景（v3-output/WT624-TRUTH/baseline.md F5）：agent_execution_stats 表全仓零生产
写入方（record_agent_execution 无调用者），此前四个数据端点在表存在且为空时把
结构性零当测量值返回（success=True 的 0 次执行/0% 成功率，无任何标记），仅当
表缺失才置 degraded。修复后：写侧接线前，读侧一律如实返回
degraded=True + data_status="unavailable" + unavailable_reason="write_side_unwired"；
/agent-types 为静态目录（非测量值），语义不受影响。
"""

from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.agent_stats import router
from app.models.agent_stats import (
    AgentExecutionStats,  # noqa: F401 — 登记 Base.metadata，确保测试库建表（空表=生产「有表无写入」形态）
)
from app.models.user import User

app = FastAPI()
app.include_router(router, prefix="/api/v1")

def _assert_unavailable(data: dict, label: str) -> None:
    """断言读侧如实标注：写侧未接线，数值为不可用占位而非测量值。"""
    assert data.get("degraded") is True, f"{label} 缺少 degraded 标记"
    assert data.get("data_status") == "unavailable", f"{label} 缺少 data_status 标记"
    assert data.get("unavailable_reason") == "write_side_unwired", f"{label} 缺少 unavailable_reason 标记"


@pytest.fixture(name="agent_stats_client")
async def agent_stats_client_fixture(db_session):
    user = User(
        id=uuid4(),
        username=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _get_json(client: AsyncClient, path: str) -> dict[str, Any]:
    response = await client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text}"
    body: dict[str, Any] = response.json()
    assert body["success"] is True
    return cast(dict[str, Any], body["data"])


@pytest.mark.usefixtures("agent_stats_client")
async def test_user_overview_reports_unavailable_when_write_side_unwired(agent_stats_client):
    """表存在但零写入时不得把结构性零冒充测量值，必须标 unavailable。"""
    data = await _get_json(agent_stats_client, "/api/v1/agent-stats/user/overview?days=30")
    _assert_unavailable(data, "user/overview")


async def test_overview_alias_reports_unavailable_when_write_side_unwired(agent_stats_client):
    data = await _get_json(agent_stats_client, "/api/v1/agent-stats/overview?days=7")
    _assert_unavailable(data, "overview 别名")


async def test_top_agents_reports_unavailable_when_write_side_unwired(agent_stats_client):
    data = await _get_json(agent_stats_client, "/api/v1/agent-stats/user/top-agents")
    _assert_unavailable(data, "top-agents")


async def test_performance_reports_unavailable_when_write_side_unwired(agent_stats_client):
    data = await _get_json(agent_stats_client, "/api/v1/agent-stats/performance?days=7")
    _assert_unavailable(data, "performance")


async def test_agent_types_catalog_remains_static_metadata(agent_stats_client):
    """/agent-types 是静态目录非测量值，不随 unavailable 语义降级。"""
    data = await _get_json(agent_stats_client, "/api/v1/agent-stats/agent-types")
    assert data["agent_types"]  # 静态目录仍在
    assert data["total_count"] > 0
    assert "data_status" not in data
