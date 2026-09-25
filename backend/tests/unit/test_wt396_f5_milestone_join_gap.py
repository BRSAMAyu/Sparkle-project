"""wt396 F5（J-08 轮3）· 里程碑↔任务位置 join 错位 —— 红绿契约锁.

轮3判据（v3-output/WT391-HUNT-R3 REPORT F5）：``_milestones_face`` 把 wizard
里程碑列表与按 ``created_at`` 序的里程碑任务行做**位置 join**（无 id 关联）；
``goals.py`` 建目标时里程碑任务创建失败被 ``except Exception: pass`` 吞掉 →
天然制造缺位 → 后续里程碑全部顺延错位一位（达成状态归属错误）。

修法口径（卡面）：
1. 创建面：任务创建失败不再静默吞——响应 ``warning`` 带补偿清单标记（目标
   创建本身不阻塞，设计意图保留）；同时把 wizard 里程碑 id 持久化到任务标签
   （``goal_milestone:<id>``），为轨迹面提供 id 关联。
2. 轨迹面：join 稳健化——id 标签精确关联 > 标题匹配（存量数据回退）> 显式
   gap 标注（缺失位 ``task=None`` 且 ``gap=True``，绝不顺延错位）；未匹配的
   里程碑任务行仍走尾部「任务行即事实」段，不丢失。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User

pytestmark = pytest.mark.asyncio

_WIZARD_3 = [
    {"id": "m1", "title": "里程碑一", "description": "d1"},
    {"id": "m2", "title": "里程碑二", "description": "d2"},
    {"id": "m3", "title": "里程碑三", "description": "d3"},
]


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _seed_goal_plan_tasks(
    db_session: AsyncSession,
    *,
    milestones: list[dict],
    task_specs: list[dict],  # {"title", "tags", "status"}
) -> tuple[Goal, list[Task]]:
    """goals.py 创建流同构：goal metadata 带 wizard 里程碑 + plan + 里程碑任务行。"""
    user = User(
        username=f"wt396f5_{uuid4().hex[:10]}",
        email=f"wt396f5_{uuid4().hex[:10]}@t.example",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.flush()
    goal = Goal(
        user_id=user.id,
        title="wt396 F5 轨迹目标",
        goal_type="skill",
        status="active",
        metadata_payload={
            "creation_wizard": {
                "motivation": "wt396 F5",
                "milestones": milestones,
                "created_at": _naive_now().isoformat(),
            }
        },
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(user_id=user.id, goal_id=goal.id, name="wt396 F5 计划", type=PlanType.GROWTH)
    db_session.add(plan)
    await db_session.flush()
    goal.plan_id = plan.id
    db_session.add(goal)
    tasks: list[Task] = []
    for spec in task_specs:
        task = Task(
            user_id=user.id,
            plan_id=plan.id,
            title=spec["title"],
            type=TaskType.LEARNING,
            estimated_minutes=25,
            tags=spec["tags"],
            status=spec.get("status", TaskStatus.PENDING),
        )
        db_session.add(task)
        tasks.append(task)
    await db_session.commit()
    for task in tasks:
        await db_session.refresh(task)
    return goal, tasks


# ---------------------------------------------------------------------------
# 轨迹面：中间里程碑任务缺失 → 显式 gap，绝不顺延错位（轮3探针 A 的 DB 口径）
# ---------------------------------------------------------------------------


async def test_missing_middle_milestone_task_is_gap_not_misattributed(db_session):
    """3 里程碑、第 2 个任务创建失败（缺失）→ m2 显式 gap；m3 关联它自己的任务.

    修前（位置 join）：m2 错配 m3 的任务且 reached=True；m3 反而 reached=False。
    """
    from app.services.goal_trajectory_service import build_goal_trajectory

    goal, tasks = await _seed_goal_plan_tasks(
        db_session,
        milestones=_WIZARD_3,
        task_specs=[
            {"title": "里程碑一", "tags": ["goal_first_step"], "status": TaskStatus.PENDING},
            # m2 任务创建失败被吞 → 只有 m1/m3 的任务行
            {"title": "里程碑三", "tags": ["goal_milestone"], "status": TaskStatus.COMPLETED},
        ],
    )
    trajectory = await build_goal_trajectory(db_session, user_id=goal.user_id, goal_id=goal.id)
    faces = {f["milestone_id"]: f for f in trajectory["milestones"]}

    m2 = faces["m2"]
    assert m2["task_id"] is None, "缺失位的 m2 不得顺延错配下一个里程碑的任务"
    assert m2["reached"] is False, "m2 自己的任务不存在，绝不能因顺延而显示已达成"
    assert m2.get("gap") is True, "缺失位必须显式 gap 标注（诚实呈现而非错位归属）"

    m3 = faces["m3"]
    assert m3["task_id"] == str(tasks[1].id), "m3 必须关联它自己的任务行"
    assert m3["reached"] is True, "m3 的任务真实完成 → reached=True"

    m1 = faces["m1"]
    assert m1["task_id"] == str(tasks[0].id) and m1["reached"] is False

    # 价值叙事不因错位虚增
    assert trajectory["value_summary"]["milestones_reached"] == 1


async def test_full_alignment_and_surplus_tasks_unchanged(db_session):
    """无缺失时 3↔3 对齐与修前等价；超出 wizard 列表的任务行走尾部事实段."""
    from app.services.goal_trajectory_service import build_goal_trajectory

    goal, tasks = await _seed_goal_plan_tasks(
        db_session,
        milestones=_WIZARD_3,
        task_specs=[
            {"title": "里程碑一", "tags": ["goal_first_step"], "status": TaskStatus.COMPLETED},
            {"title": "里程碑二", "tags": ["goal_milestone"], "status": TaskStatus.PENDING},
            {"title": "里程碑三", "tags": ["goal_milestone"], "status": TaskStatus.PENDING},
            {"title": "额外里程碑任务", "tags": ["goal_milestone"], "status": TaskStatus.PENDING},
        ],
    )
    trajectory = await build_goal_trajectory(db_session, user_id=goal.user_id, goal_id=goal.id)
    faces = trajectory["milestones"]
    by_id = {f["milestone_id"]: f for f in faces}
    assert by_id["m1"]["task_id"] == str(tasks[0].id) and by_id["m1"]["reached"] is True
    assert by_id["m2"]["task_id"] == str(tasks[1].id)
    assert by_id["m3"]["task_id"] == str(tasks[2].id)
    # 第 4 个任务行不在 wizard 列表内 → 尾部「任务行即事实」段（milestone_id=None）
    trailing = [f for f in faces if f["milestone_id"] is None]
    assert len(trailing) == 1 and trailing[0]["task_id"] == str(tasks[3].id)
    assert all(f.get("gap") is not True for f in faces), "无缺失时不得出现 gap 标注"


async def test_id_tag_join_beats_title_for_new_goals(db_session):
    """新目标（创建面写入 ``goal_milestone:<id>`` 标签）→ id 精确关联优先于标题.

    标题被用户改过时仍能正确关联；缺失位照旧显式 gap。
    """
    from app.services.goal_trajectory_service import build_goal_trajectory

    goal, tasks = await _seed_goal_plan_tasks(
        db_session,
        milestones=_WIZARD_3,
        task_specs=[
            {"title": "里程碑一", "tags": ["goal_first_step", "goal_milestone:m1"], "status": TaskStatus.PENDING},
            # m2 缺失
            {"title": "用户已改名", "tags": ["goal_milestone", "goal_milestone:m3"], "status": TaskStatus.COMPLETED},
        ],
    )
    trajectory = await build_goal_trajectory(db_session, user_id=goal.user_id, goal_id=goal.id)
    faces = {f["milestone_id"]: f for f in trajectory["milestones"]}
    assert faces["m3"]["task_id"] == str(tasks[1].id) and faces["m3"]["reached"] is True
    assert faces["m2"].get("gap") is True and faces["m2"]["task_id"] is None
    assert faces["m1"]["task_id"] == str(tasks[0].id)


# ---------------------------------------------------------------------------
# 创建面：任务创建失败不再静默吞（补偿清单进 warning）+ 里程碑 id 持久化到标签
# ---------------------------------------------------------------------------


async def test_goal_creation_task_failure_surfaces_warning_and_persists_milestone_ids(
    db_session, monkeypatch
):
    """第 2 个里程碑任务创建失败 → 目标仍创建（设计意图），但响应 warning 带
    补偿标记；成功创建的任务行携带 ``goal_milestone:<id>`` id 标签."""
    from fastapi import FastAPI

    import app.api.v1.goals as goals_api
    from app.schemas.task import TaskCreate
    from app.services.task_service import TaskService

    user = User(
        username=f"wt396f5c_{uuid4().hex[:10]}",
        email=f"wt396f5c_{uuid4().hex[:10]}@t.example",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()

    app = FastAPI()
    app.include_router(goals_api.router, prefix="/api/v1/goals")

    async def _override_get_db():
        yield db_session

    async def _override_get_current_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    real_create = TaskService.create
    calls: list[str] = []

    async def _spying_create(db, obj_in: TaskCreate, *, user_id):
        calls.append(list(obj_in.tags or [])[0])
        if len(calls) == 2:
            raise RuntimeError("simulated milestone task creation failure (wt396 F5 red)")
        return await real_create(db, obj_in, user_id)

    monkeypatch.setattr(TaskService, "create", _spying_create)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/goals",
            json={
                "goal_type": "skill",
                "title": "wt396 F5 创建目标",
                "motivation": "补偿清单红测",
                "milestones": [
                    {"id": "m1", "title": "里程碑一"},
                    {"id": "m2", "title": "里程碑二"},
                    {"id": "m3", "title": "里程碑三"},
                ],
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["first_task_id"] is not None, "第一个任务创建成功必须暴露 first_task_id"

    # 补偿清单：失败不再静默（响应面如实携带标记）
    assert body["warning"], "里程碑任务创建失败必须在 warning 显式呈现（不得 except: pass 静默吞）"
    assert "milestone_task_creation_failed" in body["warning"]

    # id 关联持久化：成功任务行携带 goal_milestone:<id> 标签（轨迹面 id join 的根基）
    from sqlalchemy import select

    rows = (
        (await db_session.execute(select(Task).where(Task.user_id == user.id).order_by(Task.created_at.asc())))
        .scalars()
        .all()
    )
    assert len(rows) == 2, "m2 任务失败，m1/m3 两个任务成功"
    assert "goal_milestone:m1" in (rows[0].tags or []), "首步任务必须携带里程碑 id 标签"
    assert "goal_first_step" in (rows[0].tags or [])
    assert "goal_milestone:m3" in (rows[1].tags or []), "里程碑任务必须携带里程碑 id 标签"


async def test_goal_creation_happy_path_persists_milestone_ids(db_session):
    """无失败时全部任务携带 ``goal_milestone:<id>`` 标签（存量 join 兼容的根基面）."""
    from fastapi import FastAPI

    import app.api.v1.goals as goals_api

    user = User(
        username=f"wt396f5h_{uuid4().hex[:10]}",
        email=f"wt396f5h_{uuid4().hex[:10]}@t.example",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()

    app = FastAPI()
    app.include_router(goals_api.router, prefix="/api/v1/goals")

    async def _override_get_db():
        yield db_session

    async def _override_get_current_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/goals",
            json={
                "goal_type": "skill",
                "title": "wt396 F5 全量目标",
                "milestones": [
                    {"id": "m1", "title": "里程碑一"},
                    {"id": "m2", "title": "里程碑二"},
                ],
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["warning"] is None

    from sqlalchemy import select

    rows = (
        (await db_session.execute(select(Task).where(Task.user_id == user.id).order_by(Task.created_at.asc())))
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert "goal_milestone:m1" in (rows[0].tags or [])
    assert "goal_milestone:m2" in (rows[1].tags or [])
