"""GOAL-ROUTER：goal 域路由遮蔽死代码——注册面与形状面回归（红→绿）。

遮蔽机制（v3-output/GOAL-ROUTER/REPORT.md）：
``app/api/v1/router.py`` 的 ``_include_experience_routers()`` 对
``experience/*_router.py`` 逐个调用 ``_include_router_if_new()``：只要 incoming
router 与已注册路由存在**任一** ``(path, methods)`` 重叠，整个 router 被拒绝
注册。``experience_readouts``（先于 closeout 动态挂载）持有
``GET /experience/goal-detail/{goal_id}``，与 ``experience/goal_router.py`` 的
同路径 GET 冲突 → goal_router 整体（含 mobile 正在调用的
``PUT /experience/goal-detail/{goal_id}/criteria-status``）从未生效。

消费链（裁决依据，shape 对照见 REPORT）：
- mobile goal 详情屏 ``goal_detail_provider.dart`` 按 goal_router 的
  ``GoalDetailPayload`` 形状解析，并调用 criteria-status PUT；
- mobile home 仪表盘卡 ``experience_repository.getGoalDetail('current')`` 按
  readouts 形状解析（active/plan/progress/next_task/goal_graph/...）。

裁决 = 方案 (a)：goal_router 成为该路径唯一所有者，GET 返回**超集形状**
（goal 屏契约字段 + home 卡兼容字段 + 'current' 别名解析），PUT 随之生效；
readouts 不再注册 GET（防止再次遮蔽本文件即为守卫）。
"""

from __future__ import annotations

from typing import Any, get_type_hints
from unittest.mock import AsyncMock
from uuid import uuid4

GOAL_DETAIL_PATH = "/experience/goal-detail/{goal_id}"
CRITERIA_PUT_PATH = "/experience/goal-detail/{goal_id}/criteria-status"

# mobile goal 详情屏 GoalDetailData.fromJson 依赖的顶层键
# （mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart）。
MOBILE_GOAL_SCREEN_KEYS = {
    "goal",
    "minimum_acceptance_criteria",
    "plan_health",
    "current_phase",
    "todays_minimal_next_step",
    "knowledge_bottlenecks",
    "accountability_status",
    "related_sources",
    "strategy_belief",
}
# mobile home 仪表盘卡 GoalDetailSnapshot.fromJson 依赖的顶层键
# （mobile/lib/features/experience/data/experience_models.dart）。
MOBILE_HOME_CARD_KEYS = {
    "active",
    "plan",
    "progress",
    "next_task",
    "goal_graph",
    "why_this_matters",
    "updated_at",
}


def _api_routes() -> dict[tuple[str, frozenset[str]], Any]:
    from app.api.v1.router import api_router

    return {
        (route.path, frozenset(route.methods)): route
        for route in api_router.routes
        if getattr(route, "methods", None)
    }


# ---------------------------------------------------------------------------
# 注册面：goal 域端点必须由 goal_router（closeout 动态挂载）提供
# ---------------------------------------------------------------------------
class TestRouteRegistration:
    def test_criteria_status_put_is_registered(self) -> None:
        """mobile confirmMinimumCriteria 调用的 PUT 必须真实存在（修复前 405）。"""
        routes = _api_routes()
        assert (CRITERIA_PUT_PATH, frozenset({"PUT"})) in routes

    def test_goal_detail_get_is_served_by_goal_router(self) -> None:
        """GET goal-detail 的 handler 必须来自 goal_router（而非 readouts 抢注）。"""
        route = _api_routes()[(GOAL_DETAIL_PATH, frozenset({"GET"}))]
        module = getattr(route.endpoint, "__module__", "")
        assert "goal_router" in module, f"goal-detail GET 由 {module} 提供，goal_router 仍被遮蔽"

    def test_readouts_no_longer_registers_goal_detail(self) -> None:
        """readouts 不得再注册同路径 GET——否则 goal_router 会被再次整体遮蔽。"""
        from app.api.v1 import experience_readouts

        readout_paths = {route.path for route in experience_readouts.router.routes}
        assert not any("goal-detail" in path for path in readout_paths)

    def test_goal_router_fully_registered(self) -> None:
        """goal_router 的每条路由都必须出现在 api_router（不允许部分遮蔽）。"""
        from app.api.v1.experience import goal_router

        routes = _api_routes()
        for route in goal_router.router.routes:
            key = (route.path, frozenset(route.methods))
            assert key in routes, f"goal_router 路由被遮蔽：{key}"


# ---------------------------------------------------------------------------
# 形状面：单一端点必须同时满足两个 mobile 消费方的契约（超集）
# ---------------------------------------------------------------------------
class TestResponseShapeSuperset:
    def test_response_model_covers_goal_screen_contract(self) -> None:
        route = _api_routes()[(GOAL_DETAIL_PATH, frozenset({"GET"}))]
        model = getattr(route, "response_model", None)
        fields = set(getattr(model, "model_fields", {}) or {})
        assert fields >= MOBILE_GOAL_SCREEN_KEYS, f"缺少 goal 详情屏契约字段：{MOBILE_GOAL_SCREEN_KEYS - fields}"

    def test_response_model_covers_home_card_contract(self) -> None:
        route = _api_routes()[(GOAL_DETAIL_PATH, frozenset({"GET"}))]
        model = getattr(route, "response_model", None)
        fields = set(getattr(model, "model_fields", {}) or {})
        assert fields >= MOBILE_HOME_CARD_KEYS, f"缺少 home 卡兼容字段：{MOBILE_HOME_CARD_KEYS - fields}"


# ---------------------------------------------------------------------------
# 运行面：response_model 层验证（NBP-2 教训——直调 handler 不经过 FastAPI 的
# response_model 校验路径，「单测绿/运行红」）。closeout 动态加载机制是本域
# 注册的真正生效路径，注册面与运行面必须都绿才算端点健康。
# ---------------------------------------------------------------------------
class TestResponseModelRuntime:
    def _closeout_experience_routes(self) -> list[Any]:
        """api_router 中由 closeout 动态加载（experience/*_router.py）提供的路由。"""
        from app.api.v1.router import api_router

        return [
            route
            for route in api_router.routes
            if getattr(route.endpoint, "__module__", "").startswith("app.api.v1.experience_closeout_")
        ]

    def test_every_closeout_experience_model_is_fully_defined(self) -> None:
        """closeout 动态加载的 experience 路由，其 response/body pydantic 模型必须完全定义。

        根因守卫（NBP-2）：动态加载 exec 前未注册 sys.modules 时，pydantic v2 对
        ``from __future__ import annotations`` 的字符串前向引用按 ``cls.__module__``
        查 sys.modules 落空 → 模型 ``__pydantic_complete__=False`` → 首次响应校验
        触发 model_rebuild 失败 → 运行时 500（注册面单测全绿，本测试专防）。
        """
        from pydantic import BaseModel

        checked = 0
        for route in self._closeout_experience_routes():
            model = getattr(route, "response_model", None)
            if isinstance(model, type) and issubclass(model, BaseModel):
                assert model.__pydantic_complete__, (
                    f"{route.path} 的 response_model {model.__module__}.{model.__name__} "
                    "未完全定义——运行时 response 校验必 500"
                )
                checked += 1
            for hint in get_type_hints(route.endpoint).values():
                if isinstance(hint, type) and issubclass(hint, BaseModel):
                    assert hint.__pydantic_complete__, (
                        f"{route.path} 的请求体模型 {hint.__module__}.{hint.__name__} 未完全定义——运行时必 500"
                    )
        assert checked >= 1, "closeout experience 路由枚举为空——挂载机制回归"

    def test_goal_detail_get_via_testclient_returns_superset(self, monkeypatch) -> None:
        """TestClient 全栈（路由→依赖→handler→response_model 校验）打 goal-detail。

        NBP-2 前此测试 500（``GoalDetailPayload is not fully defined``）；直调
        handler 的组装单测测不到 response_model 校验层，故必须走 HTTP 面。
        """
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from uuid import uuid4

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.api.deps import get_current_user
        from app.api.v1.router import api_router
        from app.db.session import get_db

        goal = _goal_mock(uuid4(), plan_id=None)
        task = _task_mock()

        async def _fake_active_goal(db, user_id, goal_id="current"):
            assert goal_id in {"current", "active"}
            return goal

        async def _fake_next_task(db, *, user_id, plan_id=None):
            return task

        async def _noop(*args, **kwargs):
            return None

        async def _empty_graph(*args, **kwargs):
            return {}

        # 数据面依赖通过 endpoint.__globals__（closeout exec 模块命名空间）注入：
        # 生效路由的 handler 就住在该命名空间，包内直调模块的对象替换不了它。
        route = _api_routes()[(GOAL_DETAIL_PATH, frozenset({"GET"}))]
        handler_globals = route.endpoint.__globals__
        monkeypatch.setattr(handler_globals["_readouts"], "_active_goal", _fake_active_goal)
        monkeypatch.setitem(handler_globals, "_load_plan", _noop)
        monkeypatch.setitem(handler_globals, "_todays_next_task", _fake_next_task)
        monkeypatch.setitem(handler_globals, "_load_graph_payload", _empty_graph)
        monkeypatch.setattr(handler_globals["_readouts"], "_active_plan", _noop)
        monkeypatch.setattr(
            handler_globals["_readouts"],
            "_task_counts",
            AsyncMock(return_value={"total": 4, "completed": 1, "paused": 1, "stuck": 0}),
        )
        monkeypatch.setattr(
            handler_globals["_readouts"],
            "_goal_graph_summary",
            AsyncMock(return_value={"active": False, "nodes": [], "edges": [], "focus_suggestions": []}),
        )
        monkeypatch.setitem(
            handler_globals,
            "_accountability_status",
            AsyncMock(return_value=handler_globals["AccountabilityStatusPayload"]()),
        )
        monkeypatch.setitem(handler_globals, "_related_sources", AsyncMock(return_value=[]))
        monkeypatch.setitem(handler_globals, "_strategy_belief_payload", AsyncMock(return_value=None))

        app = FastAPI()
        app.include_router(api_router)

        async def _override_get_db():
            yield MagicMock(spec=AsyncSession)

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/experience/goal-detail/current")

        assert response.status_code == 200, f"goal-detail 运行面断裂：{response.status_code} {response.text[:300]}"
        data = response.json()
        assert set(data) >= MOBILE_GOAL_SCREEN_KEYS
        assert set(data) >= MOBILE_HOME_CARD_KEYS
        assert data["goal"]["title"] == "数据结构期中冲刺"
        assert data["todays_minimal_next_step"]["task_id"] == str(task.id)
        assert data["next_task"]["id"] == str(task.id)
        assert data["active"] is True
        assert data["minimum_acceptance_criteria"]["thresholds"], "达标线载荷缺失"


# ---------------------------------------------------------------------------
# 功能面：组装逻辑（handler 级，mock 依赖，不触库）
# ---------------------------------------------------------------------------
def _goal_mock(goal_id, plan_id=None):
    goal = AsyncMock()
    goal.id = goal_id
    goal.plan_id = plan_id
    goal.title = "数据结构期中冲刺"
    goal.goal_type = "exam"
    goal.status = "active"
    goal.priority = "high"
    goal.mastery = 0.42
    goal.progress = 0.6
    goal.target_date = None
    goal.minimum_acceptance_criteria = {
        "description": "期中不低于 85 分",
        "status": "pending_confirmation",
        "thresholds": [{"label": "模拟卷 >= 85 分", "met": True}],
    }
    return goal


def _task_mock():
    task = AsyncMock()
    task.id = uuid4()
    task.title = "复习第 3 章"
    task.type = AsyncMock(value="review")
    task.status = AsyncMock(value="pending")
    task.priority = 2
    task.order_index = 0
    task.created_at = None
    task.due_date = None
    task.knowledge_node_id = None
    task.estimated_minutes = 25
    return task


class TestHandlerAssembly:
    async def test_current_alias_builds_superset_payload(self, monkeypatch) -> None:
        """'current' 别名（home 卡用法）解析主目标并返回超集载荷。"""
        from app.api.v1.experience import goal_router

        goal = _goal_mock(uuid4(), plan_id=None)
        task = _task_mock()

        async def _fake_active_goal(db, user_id, goal_id="current"):
            assert goal_id in {"current", "active"}
            return goal

        async def _fake_next_task(db, *, user_id, plan_id=None):
            return task

        async def _noop(*args, **kwargs):
            return None

        async def _empty_graph(*args, **kwargs):
            return {}

        monkeypatch.setattr(goal_router._readouts, "_active_goal", _fake_active_goal)
        monkeypatch.setattr(goal_router, "_load_plan", _noop)
        monkeypatch.setattr(goal_router._readouts, "_active_plan", _noop)
        monkeypatch.setattr(
            goal_router._readouts,
            "_task_counts",
            AsyncMock(return_value={"total": 4, "completed": 1, "paused": 1, "stuck": 0}),
        )
        monkeypatch.setattr(goal_router, "_todays_next_task", _fake_next_task)
        monkeypatch.setattr(goal_router, "_load_graph_payload", _empty_graph)
        monkeypatch.setattr(
            goal_router._readouts,
            "_goal_graph_summary",
            AsyncMock(return_value={"active": False, "nodes": [], "edges": [], "focus_suggestions": []}),
        )
        monkeypatch.setattr(
            goal_router,
            "_accountability_status",
            AsyncMock(return_value=goal_router.AccountabilityStatusPayload()),
        )
        monkeypatch.setattr(goal_router, "_related_sources", AsyncMock(return_value=[]))
        monkeypatch.setattr(goal_router, "_strategy_belief_payload", AsyncMock(return_value=None))

        payload = await goal_router.get_goal_detail(
            goal_id="current", db=AsyncMock(), current_user=AsyncMock(id=uuid4())
        )

        data = payload.model_dump()
        assert set(data) >= MOBILE_GOAL_SCREEN_KEYS
        assert set(data) >= MOBILE_HOME_CARD_KEYS
        # goal 屏契约：今日一步与 SSOT 同源
        assert data["todays_minimal_next_step"]["task_id"] == str(task.id)
        # home 卡兼容：next_task 与 todays_minimal_next_step 来自同一次取数
        assert data["next_task"]["id"] == str(task.id)
        assert data["active"] is True
        assert data["goal"]["title"] == "数据结构期中冲刺"

    async def test_explicit_uuid_miss_returns_404(self, monkeypatch) -> None:
        """显式 UUID 查无此目标 → 404（goal 详情屏语义）；home 的 current 不受影响。"""
        import pytest
        from fastapi import HTTPException

        from app.api.v1.experience import goal_router

        async def _fake_load_goal(db, *, goal_id, user_id):
            return None

        monkeypatch.setattr(goal_router, "_load_goal", _fake_load_goal)
        with pytest.raises(HTTPException) as exc_info:
            await goal_router.get_goal_detail(
                goal_id=str(uuid4()), db=AsyncMock(), current_user=AsyncMock(id=uuid4())
            )
        assert exc_info.value.status_code == 404

    async def test_draft_criteria_fallback_keeps_home_card_lines(self, monkeypatch) -> None:
        """无达标线的目标回退草案达标线——home 卡 criteria 行不回归为空。"""
        from app.api.v1.experience import goal_router

        goal = _goal_mock(uuid4())
        goal.minimum_acceptance_criteria = None
        task = _task_mock()

        async def _fake_active_goal(db, user_id, goal_id="current"):
            return goal

        async def _noop(*args, **kwargs):
            return None

        async def _empty_graph(*args, **kwargs):
            return {}

        monkeypatch.setattr(goal_router._readouts, "_active_goal", _fake_active_goal)
        monkeypatch.setattr(goal_router, "_load_plan", _noop)
        monkeypatch.setattr(goal_router._readouts, "_active_plan", _noop)
        monkeypatch.setattr(
            goal_router._readouts,
            "_task_counts",
            AsyncMock(return_value={"total": 0, "completed": 0, "paused": 0, "stuck": 0}),
        )
        monkeypatch.setattr(goal_router, "_todays_next_task", AsyncMock(return_value=task))
        monkeypatch.setattr(goal_router, "_load_graph_payload", _empty_graph)
        monkeypatch.setattr(
            goal_router._readouts,
            "_goal_graph_summary",
            AsyncMock(return_value={"active": False, "nodes": [], "edges": [], "focus_suggestions": []}),
        )
        monkeypatch.setattr(
            goal_router,
            "_accountability_status",
            AsyncMock(return_value=goal_router.AccountabilityStatusPayload()),
        )
        monkeypatch.setattr(goal_router, "_related_sources", AsyncMock(return_value=[]))
        monkeypatch.setattr(goal_router, "_strategy_belief_payload", AsyncMock(return_value=None))

        payload = await goal_router.get_goal_detail(
            goal_id="current", db=AsyncMock(), current_user=AsyncMock(id=uuid4())
        )
        criteria = payload.model_dump()["minimum_acceptance_criteria"]
        assert criteria["thresholds"], "草案达标线回退缺失，home 卡达标线行会退化为空"
        assert all(item["label"] for item in criteria["thresholds"])
