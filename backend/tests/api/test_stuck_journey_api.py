"""POST /api/v1/experience/stuck-journey/* API 测试（J-05）。

红测先行：证明 base 667001e6 上「我卡住了」没有统一恢复旅程面
（三入口只拼模板 prompt 进 chat，无真实 context 断言、无单问选择、
无纠正反馈环）。目标契约在本文件冻结：

- start：三面（home/goal/action）可达，payload.context 全部来自真源
  读取（Goal/Task 行原样投影：标题/状态/停滞天数/近期失败计数），
  question 恒 ≤1（最多先问一个高价值问题）或直接 act 出主 intervention；
- 差异化：不同真实 context → 不同问句（引擎 IG 选择，非固定问卷）；
- answer：branch_key 直传 → 收敛到主 intervention（≤2 轮进 proposal）；
- correct：「不是这个原因」落库（反馈环），纠正后同 context 再次
  start 的主判断改变（不静默丢弃）；非法 friction_type 拒绝。

零 mock 冒充：db 用 sqlite 内存基座种真实行，引擎走 A-03 真源。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.experience.stuck_journey_router import router as stuck_journey_router
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


class _FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _build_app(session: AsyncSession, user_id) -> FastAPI:
    app = FastAPI()
    # router 自带 /experience 前缀（goal_router 同款），不再重复挂前缀。
    app.include_router(stuck_journey_router)

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser(user_id)
    return app


async def _make_user(db_session: AsyncSession) -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


_NOW = datetime(2026, 9, 25, 10, 0, 0)


async def _seed_goal_with_plan(
    db_session: AsyncSession, user_id, *, title: str = "两周内完成线代一轮复习"
) -> Goal:
    goal = Goal(
        user_id=user_id,
        title=title,
        goal_type="exam",
        status="active",
        is_primary=True,
        progress=0.25,
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(user_id=user_id, goal_id=goal.id, name="线代复习冲刺", type=PlanType.SPRINT)
    db_session.add(plan)
    await db_session.flush()
    goal.plan_id = plan.id
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


async def _seed_task(
    db_session: AsyncSession,
    user_id,
    plan_id,
    *,
    title: str,
    status: TaskStatus,
    updated_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> Task:
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=25,
        status=status,
        updated_at=updated_at or _NOW,
        completed_at=completed_at,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def _post(app: FastAPI, path: str, json: dict) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(path, json=json)
    return resp


@pytest.mark.asyncio
async def test_start_on_action_surface_projects_real_task_context(db_session):
    """action 面：payload.context 携带真实任务行投影（标题/状态/停滞天数）。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    task = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="线代第三章特征值练习",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    app = _build_app(db_session, user.id)

    resp = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(task.id)},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["version"]
    assert payload["surface"] == "action"
    ctx = payload["context"]
    # 真实 context 断言：来自 db 行，不是模板占位。
    assert ctx["task"]["id"] == str(task.id)
    assert ctx["task"]["title"] == "线代第三章特征值练习"
    assert ctx["task"]["status"] == TaskStatus.IN_PROGRESS.value
    assert ctx["goal"]["title"] == "两周内完成线代一轮复习"
    assert ctx["days_since_progress"] >= 5
    # 单问出口：question 至多一个；question/主 intervention 二者必有其一。
    assert payload["question"] is None or isinstance(payload["question"], dict)
    if payload["question"] is not None:
        assert payload["question"]["branch_options"]
    assert payload["receipt"]["decision_reason"]


@pytest.mark.asyncio
async def test_start_on_goal_surface_anchors_seeded_goal(db_session):
    """goal 面：context 锚定传入 goal 的真实标题。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id, title="考研英语阅读刷题")
    app = _build_app(db_session, user.id)

    resp = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "goal", "goal_id": str(goal.id)},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["surface"] == "goal"
    assert payload["context"]["goal"]["title"] == "考研英语阅读刷题"
    assert payload["context"]["goal"]["id"] == str(goal.id)


@pytest.mark.asyncio
async def test_recent_failure_count_read_from_real_task_rows(db_session):
    """近期失败计数来自真源（近期 stuck/abandoned 任务行），不伪造。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    task = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="概率论第二章习题",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    for i, status in enumerate([TaskStatus.STUCK, TaskStatus.ABANDONED, TaskStatus.STUCK]):
        await _seed_task(
            db_session,
            user.id,
            goal.plan_id,
            title=f"失败任务 {i}",
            status=status,
            updated_at=_NOW - timedelta(days=1 + i),
        )
    app = _build_app(db_session, user.id)

    resp = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(task.id)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    failures = payload["context"]["recent_failures"]
    assert failures["count"] == 3
    assert "失败任务 0" in failures["titles"]
    # 失败新鲜（1-2 天前）→ 技能族证据充分 → 直接 act 出主 intervention。
    assert payload["question"] is None
    assert payload["main_intervention"] is not None
    assert payload["main_intervention"]["friction_type"] == "skill"


@pytest.mark.asyncio
async def test_question_selection_differs_by_real_context(db_session):
    """差异化：停滞+失败 → q_tried_and_checked；空 context → 根分裂问。
    问句选择由 context 驱动（A-03 IG），不是固定问卷。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    stalled = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="复变函数第四章作业",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    for i in range(3):
        await _seed_task(
            db_session,
            user.id,
            goal.plan_id,
            title=f"卡住任务 {i}",
            status=TaskStatus.STUCK,
            # 失败也在 5 天前：停滞天数不被新鲜活动重置，
            # entry(0.8) vs skill(1.0)/difficulty(0.6) 证据竞争 → 单问出口。
            updated_at=_NOW - timedelta(days=6 + i),
        )
    app = _build_app(db_session, user.id)

    rich = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(stalled.id)},
    )
    assert rich.status_code == 200
    rich_payload = rich.json()
    assert rich_payload["question"] is not None

    # 空 context（无 goal 无 task 的新用户）走引擎根分裂问。
    empty_user = await _make_user(db_session)
    empty_app = _build_app(db_session, empty_user.id)
    bare = await _post(empty_app, "/experience/stuck-journey/start", {"surface": "home"})
    assert bare.status_code == 200
    bare_payload = bare.json()

    assert bare_payload["question"] is not None
    assert rich_payload["question"]["question_id"] == "q_tried_and_checked"
    assert bare_payload["question"]["question_id"] == "q_direction_vs_push"


@pytest.mark.asyncio
async def test_answer_turn_converges_to_main_intervention(db_session):
    """answer：branch_key 直传 → ≤2 轮收敛到主 intervention（proposal）。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    stalled = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="数据结构图论专题",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    for i in range(3):
        await _seed_task(
            db_session,
            user.id,
            goal.plan_id,
            title=f"卡住任务 {i}",
            status=TaskStatus.STUCK,
            updated_at=_NOW - timedelta(days=6 + i),
        )
    app = _build_app(db_session, user.id)

    start = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(stalled.id)},
    )
    question = start.json()["question"]
    assert question is not None

    resp = await _post(
        app,
        "/experience/stuck-journey/answer",
        {
            "surface": "action",
            "task_id": str(stalled.id),
            "question_id": question["question_id"],
            "branch_key": question["branch_options"][0]["key"],
        },
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["question"] is None  # 单问上限：答后不再追问
    intervention = payload["main_intervention"]
    assert intervention["type"]
    assert intervention["nominated"]
    assert intervention["friction_type"] not in ("", "unknown")


@pytest.mark.asyncio
async def test_correction_changes_subsequent_judgment(db_session):
    """纠正反馈环：act 出口纠正主判断后，同 context 再次 start 主判断改变，
    且纠正记录落库（不静默丢弃）。"""
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    stalled = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="操作系统进程调度",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    app = _build_app(db_session, user.id)

    first = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(stalled.id)},
    )
    first_payload = first.json()
    primary_type = first_payload["friction_type"]
    assert primary_type not in ("", "unknown")
    assert first_payload["main_intervention"]["type"]

    corrected = await _post(
        app,
        "/experience/stuck-journey/correct",
        {
            "surface": "action",
            "task_id": str(stalled.id),
            "friction_type": primary_type,
        },
    )
    assert corrected.status_code == 200, corrected.text
    correction_payload = corrected.json()
    assert correction_payload["correction_id"]
    # 纠正后立即重派生：主判断不再是被纠正的类型（反馈环生效）。
    after = correction_payload["journey"]
    assert after["friction_type"] != primary_type
    assert after["receipt"]["correction_active"] is True

    # 后续 start 同样改变（纠正进入反馈环，影响后续判断）。
    second = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(stalled.id)},
    )
    second_payload = second.json()
    assert second_payload["friction_type"] != primary_type
    assert second_payload["receipt"]["active_corrections"] >= 1


@pytest.mark.asyncio
async def test_correction_rejects_invalid_friction_type(db_session):
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    app = _build_app(db_session, user.id)

    resp = await _post(
        app,
        "/experience/stuck-journey/correct",
        {"surface": "home", "friction_type": "not_a_type"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_rejects_unknown_surface(db_session):
    pytest.importorskip("app.services.stuck_journey_service")
    user = await _make_user(db_session)
    app = _build_app(db_session, user.id)

    resp = await _post(app, "/experience/stuck-journey/start", {"surface": "settings"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# V3-FIX-51 · 旅程提名的「建议非执行」契约锁（决策两面守卫不对称的声明式处置）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_intervention_declares_recommendation_delivery(db_session):
    """旅程面 main_intervention 恒带 ``delivery="recommendation"``（类型面锁）。

    chat 面决策经 A-02 结构守卫（能力/权限/分配事实）后才有 ``selected``；
    旅程面提名不经该守卫——同一摩擦类型两面结论可合法不同（A-08 p03 双输
    反例）。本契约把差异**声明化**（非静默）：旅程提名是「建议，非执行承诺」，
    执行发生在客户端动作面（各有其守卫）。消费方据此区分两面语义。
    """
    pytest.importorskip("app.services.stuck_journey_service")
    from app.services.stuck_journey_service import JOURNEY_INTERVENTION_DELIVERY

    assert JOURNEY_INTERVENTION_DELIVERY == "recommendation"

    user = await _make_user(db_session)
    goal = await _seed_goal_with_plan(db_session, user.id)
    stalled = await _seed_task(
        db_session,
        user.id,
        goal.plan_id,
        title="英语真题阅读精读",
        status=TaskStatus.IN_PROGRESS,
        updated_at=_NOW - timedelta(days=6),
    )
    for i in range(3):
        await _seed_task(
            db_session,
            user.id,
            goal.plan_id,
            title=f"卡住任务 {i}",
            status=TaskStatus.STUCK,
            updated_at=_NOW - timedelta(days=6 + i),
        )
    app = _build_app(db_session, user.id)

    start = await _post(
        app,
        "/experience/stuck-journey/start",
        {"surface": "action", "task_id": str(stalled.id)},
    )
    assert start.status_code == 200, start.text
    payload = start.json()
    assert payload["main_intervention"] is None or payload["main_intervention"]["delivery"] == "recommendation"

    question = payload["question"]
    if question is not None:
        answered = await _post(
            app,
            "/experience/stuck-journey/answer",
            {
                "surface": "action",
                "task_id": str(stalled.id),
                "question_id": question["question_id"],
                "branch_key": question["branch_options"][0]["key"],
            },
        )
        assert answered.status_code == 200, answered.text
        intervention = answered.json()["main_intervention"]
        assert intervention is not None
        assert intervention["delivery"] == "recommendation"
