"""F-7（wt324 实测 major·阻断 U-05 Goal 屏验收）：current_goal_id 必须落在 goal 空间。

缺陷链（v3-output/WT324-SIMEVIDENCE/REPORT.md §四 F-7）：
multi-goal 看板的 plan 回退快照以 ``plan.id`` 冒充 goal id，激活链经
``PUT /users/me`` / ``POST /user/settings`` 把 **plan_id** 写进
``user_settings.current_goal_id``；app 再以其请求
``GET /experience/goal-detail/{id}`` → 404（「目标详情加载失败」，重启复现）。

本回归三面：
1. 写侧纠偏（激活链存真正的 goal_id）：settings 写入口收到本人 plan_id 时
   纠偏为该 plan 的 goal_id；
2. 读侧自愈（存量错数据不改库）：库中已落的 plan_id 在 settings / me 读取时
   投影为真正的 goal_id，且不回写库；
3. 端到端：纠偏后的 id 请求 goal-detail 必须 200（plan_id 直连仍 404，
   404 语义本身不变——修的是喂给它的 id）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models.task_document  # noqa: F401 — goal-detail 依赖表需注册进 metadata
from app.api.deps import get_current_user
from app.api.v1.experience.goal_router import router as goal_router
from app.api.v1.user_settings import router as user_settings_router
from app.api.v1.users import router as users_router
from app.aurora.runtime_v1.models import GoalWorldGraphSnapshot  # noqa: F401 — 同上
from app.db.session import get_db
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.user import User
from app.models.user_settings import UserSettings


@pytest.fixture
def client(db_session: AsyncSession, test_user: User):
    app = FastAPI()
    app.include_router(users_router, prefix="/users")
    app.include_router(user_settings_router)
    app.include_router(goal_router)

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def goal_and_plan(db_session: AsyncSession, test_user: User) -> tuple[Goal, Plan]:
    goal = Goal(user_id=test_user.id, title="期末拿 A", goal_type="exam", status="active")
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(
        user_id=test_user.id,
        goal_id=goal.id,
        name="期末冲刺计划",
        type=PlanType.SPRINT,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(goal)
    await db_session.refresh(plan)
    return goal, plan


async def _write_plan_id_into_settings(db_session: AsyncSession, user_id, plan_id) -> None:
    """绕过服务层，直接模拟存量错数据（wt324 实测：库里已是 plan_id）。"""
    record = UserSettings(user_id=user_id, current_goal_id=str(plan_id))
    db_session.add(record)
    await db_session.commit()


async def _settings_row(db_session: AsyncSession, user_id) -> UserSettings:
    row = (
        await db_session.execute(
            select(UserSettings).where(
                UserSettings.user_id == user_id,
                UserSettings.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    return row


# ---------------------------------------------------------------------------
# 1. 写侧纠偏：激活链把 plan_id 交给 settings 时必须落真正的 goal_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_write_remaps_plan_id_to_goal_id(db_session, test_user, goal_and_plan, client):
    goal, plan = goal_and_plan

    response = client.post("/user/settings", json={"current_goal_id": str(plan.id)})

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] == str(goal.id)
    row = await _settings_row(db_session, test_user.id)
    assert row.current_goal_id == str(goal.id), "激活链必须存 goal 空间的 id"


@pytest.mark.asyncio
async def test_users_me_write_remaps_plan_id_to_goal_id(db_session, test_user, goal_and_plan, client):
    goal, plan = goal_and_plan

    response = client.put("/users/me", json={"current_goal_id": str(plan.id)})

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] == str(goal.id)
    row = await _settings_row(db_session, test_user.id)
    assert row.current_goal_id == str(goal.id)


@pytest.mark.asyncio
async def test_settings_write_keeps_real_goal_id_untouched(db_session, test_user, goal_and_plan, client):
    goal, _plan = goal_and_plan

    response = client.post("/user/settings", json={"current_goal_id": str(goal.id)})

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] == str(goal.id)


@pytest.mark.asyncio
async def test_settings_write_allows_clearing_to_null(db_session, test_user, goal_and_plan, client):
    _goal, _plan = goal_and_plan

    response = client.post("/user/settings", json={"current_goal_id": None})

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] is None


# ---------------------------------------------------------------------------
# 2. 读侧自愈：存量 plan_id 读取时投影为 goal_id，不回写库（不改库）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_read_corrects_legacy_plan_id_without_db_write(db_session, test_user, goal_and_plan, client):
    _goal, plan = goal_and_plan
    await _write_plan_id_into_settings(db_session, test_user.id, plan.id)

    response = client.get("/user/settings")

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] == str(_goal.id), "读取必须纠偏到 goal 空间"
    row = await _settings_row(db_session, test_user.id)
    assert row.current_goal_id == str(plan.id), "读侧纠偏不得回写库（不改库原则）"


@pytest.mark.asyncio
async def test_users_me_read_corrects_legacy_plan_id(db_session, test_user, goal_and_plan, client):
    goal, plan = goal_and_plan
    await _write_plan_id_into_settings(db_session, test_user.id, plan.id)

    response = client.get("/users/me")

    assert response.status_code == 200, response.text
    assert response.json()["current_goal_id"] == str(goal.id)


@pytest.mark.asyncio
async def test_read_passes_through_goal_id_and_arbitrary_values(db_session, test_user, goal_and_plan, client):
    """goal id 原样、悬空值不吞（lenient：不因竞态/外部数据损坏而清空选择）。"""
    goal, _plan = goal_and_plan
    dangling = str(uuid4())
    await _write_plan_id_into_settings(db_session, test_user.id, uuid4())
    row = await _settings_row(db_session, test_user.id)
    row.current_goal_id = dangling
    await db_session.commit()

    response = client.get("/user/settings")
    assert response.status_code == 200
    assert response.json()["current_goal_id"] == dangling

    row.current_goal_id = str(goal.id)
    await db_session.commit()
    response = client.get("/user/settings")
    assert response.status_code == 200
    assert response.json()["current_goal_id"] == str(goal.id)


# ---------------------------------------------------------------------------
# 3. 端到端：纠偏后的 id 请求 goal-detail 200；plan_id 直连仍 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_goal_detail_200_with_corrected_goal_id(db_session, test_user, goal_and_plan, client):
    goal, plan = goal_and_plan
    await _write_plan_id_into_settings(db_session, test_user.id, plan.id)

    corrected = client.get("/user/settings").json()["current_goal_id"]
    assert corrected == str(goal.id)

    detail = client.get(f"/experience/goal-detail/{corrected}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["goal"]["id"] == str(goal.id)


@pytest.mark.asyncio
async def test_goal_detail_with_raw_plan_id_still_404(db_session, test_user, goal_and_plan, client):
    """404 语义不因本修放宽：喂 plan_id 依旧 404，修的是 settings 读侧喂出来的 id。"""
    _goal, plan = goal_and_plan

    detail = client.get(f"/experience/goal-detail/{plan.id}")
    assert detail.status_code == 404
