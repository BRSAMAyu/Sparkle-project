"""S7 单一事实源回归 ·「今日任务」判定（批1-A 信任地基）。

AUDIT S7 / TRIAGE §1.2 / DECISIONS D10：home 快照（experience_readouts
goal-detail → next_task）、goal 详情（experience/goal_router goal-detail →
todays_minimal_next_step）与指挥台对「今天有没有待执行任务」此前各自取数、
各自判定（readouts 无 today 过滤且含 PAUSED；goal_router 无 today 过滤但排
除 PAUSED），同一目标状态下两屏可以一个说有任务、一个说没有。

修复裁决：引擎侧由 app/services/goal_today_view.py 唯一导出「今日任务」判
定（纯判定 + SQL 条件 + 取数），两个消费面全部改引用。客户端日期过滤仅作
展示分组（mobile/lib/features/home/presentation/providers/task_board_provider.dart
注释同步声明同一口径）。

本文件先于实现编写（TDD 红证）：实现落地前 import 失败即红。
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import sqlite

from app.models.task import Task, TaskStatus

TODAY = dt.date(2026, 9, 22)
TOMORROW = TODAY + dt.timedelta(days=1)


def _task(status: TaskStatus, due: dt.date | None, priority: int = 0) -> Task:
    """构造脱离会话的 Task 实例（纯判定层不依赖 DB）。"""
    return Task(
        user_id=uuid4(),
        plan_id=uuid4(),
        title=f"task-{status.value}-{due}",
        type="LEARNING",
        estimated_minutes=25,
        status=status,
        priority=priority,
        due_date=due,
    )


# ---------------------------------------------------------------------------
# 1. 纯判定：两消费面在同一任务集合上对「今日有无任务」结论必须一致
# ---------------------------------------------------------------------------
SCENARIOS: list[tuple[str, list[Task], bool]] = [
    ("今天到期且待执行", [_task(TaskStatus.PENDING, TODAY)], True),
    ("今天到期且进行中", [_task(TaskStatus.IN_PROGRESS, TODAY)], True),
    ("今天到期但已暂停（旧 readouts 口径会误判为有）",
     [_task(TaskStatus.PAUSED, TODAY)], True),
    ("今天到期但已完成（待执行=0）", [_task(TaskStatus.COMPLETED, TODAY)], False),
    ("今天到期但已放弃", [_task(TaskStatus.ABANDONED, TODAY)], False),
    ("只在未来到期", [_task(TaskStatus.PENDING, TOMORROW)], False),
    ("无到期日（旧两口径都会误判为有）", [_task(TaskStatus.PENDING, None)], False),
    ("混合：未来任务+今日完成", [_task(TaskStatus.PENDING, TOMORROW),
                                  _task(TaskStatus.COMPLETED, TODAY)], False),
    ("空集合", [], False),
]


def test_ssot_module_exists_and_exports_contract():
    from app.services import goal_today_view as gtv

    for name in (
        "TODAY_ACTIVE_STATUSES",
        "todays_task_condition",
        "pick_todays_next_task",
        "has_todays_task",
        "todays_task_payload",
        "fetch_todays_next_task",
    ):
        assert hasattr(gtv, name), f"SSOT 模块缺少契约成员: {name}"


@pytest.mark.parametrize("name,tasks,expected", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_home_and_goal_surfaces_agree_on_today_verdict(name, tasks, expected):
    """同一 goal 状态下，home 快照口径与 goal 详情口径判定一致且符合语义。"""
    from app.api.v1.experience import goal_router
    from app.api.v1.experience_readouts import _next_task_payload_verdict
    from app.services import goal_today_view as gtv

    picked = gtv.pick_todays_next_task(tasks, TODAY)
    goal_payload = goal_router._next_step_payload(picked)
    home_payload = gtv.todays_task_payload(picked)

    assert (picked is not None) is expected, name
    assert goal_router._todays_step_exists(picked) is expected, name
    assert _next_task_payload_verdict(home_payload) is expected, name
    assert gtv.has_todays_task(tasks, TODAY) is expected, name

    # 两消费面必须从同一判定的同一结果出发（结构上不可各说各话）
    assert goal_payload.task_id == (str(picked.id) if picked else None)
    assert (home_payload or {}).get("id") == (str(picked.id) if picked else None)


def test_pick_prefers_in_progress_then_priority():
    from app.services import goal_today_view as gtv

    low = _task(TaskStatus.PENDING, TODAY, priority=1)
    high = _task(TaskStatus.PENDING, TODAY, priority=9)
    active = _task(TaskStatus.IN_PROGRESS, TODAY, priority=0)
    picked = gtv.pick_todays_next_task([low, high, active], TODAY)
    assert picked is active


# ---------------------------------------------------------------------------
# 2. SQL 条件是纯判定的唯一镜像（防两处定义漂移）
# ---------------------------------------------------------------------------
def _status_params(params: dict) -> set:
    """收集编译参数里的状态值（兼容 in_ 展开参数与整体 list 两种编译形态）。"""
    values: set = set()
    for key, value in params.items():
        if not str(key).startswith("status_"):
            continue
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


def test_condition_matches_pure_predicate():
    from app.services import goal_today_view as gtv

    cond = gtv.todays_task_condition(TODAY)
    stmt = select(Task.id).where(cond)
    compiled = stmt.compile(dialect=sqlite.dialect())
    params = compiled.params

    assert params.get("due_date_1") == TODAY
    assert _status_params(params) == set(gtv.TODAY_ACTIVE_STATUSES)
    # 排除软删
    assert "deleted_at" in str(compiled)


@pytest.mark.asyncio
async def test_surface_queries_both_filter_by_ssot_condition(monkeypatch):
    """两消费面的实际 DB 查询必须携带同一 SSOT 条件（today + 状态集）。

    「今天」是两消费面各自时钟源（goal_router 的 ``datetime.now(UTC)`` 与
    experience_readouts 的 ``_utcnow``）在调用期求值的运行期事实，SSOT 条件
    本身由 goal_today_view.todays_task_condition 唯一定义。本测试固定两个时
    钟源后再断言查询参数等于固定日期——保留原断言语义（today 过滤 + 状态
    集 + 排除软删），同时不依赖墙钟：原版本把运行期参数与硬编码 2026-09-22
    裸比且无时钟控制，UTC 日期滚过 09-22（2026-09-23 00:00 UTC）后恒红
    （时间炸弹，wt338 REPORT §二诊断）。
    """
    from datetime import UTC

    from app.api.v1 import experience_readouts
    from app.api.v1.experience import goal_router
    from app.services.goal_today_view import TODAY_ACTIVE_STATUSES

    fixed_now = dt.datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC)

    class _FrozenDatetime(dt.datetime):
        """替身：与真实 datetime 同型（.date() 可用），仅 now 固定。"""

        @staticmethod
        def now(tz=None):  # type: ignore[override]
            return fixed_now

    monkeypatch.setattr(goal_router, "datetime", _FrozenDatetime)
    monkeypatch.setattr(
        experience_readouts, "_utcnow", lambda: fixed_now.replace(tzinfo=None)
    )

    captured: dict[str, object] = {}

    class _Result:
        def scalar_one_or_none(self):
            return None

    async def _fake_execute(stmt, *args, **kwargs):
        captured["stmt"] = stmt
        return _Result()

    db = AsyncMock()
    db.execute = _fake_execute
    db_id, plan_id = uuid4(), uuid4()

    await goal_router._todays_next_task(db, user_id=db_id, plan_id=plan_id)
    goal_stmt = captured.pop("stmt")

    await experience_readouts._next_task(db, db_id, plan_id=plan_id)
    readouts_stmt = captured.pop("stmt")

    for stmt in (goal_stmt, readouts_stmt):
        compiled = stmt.compile(dialect=sqlite.dialect())
        params = compiled.params
        due_values = {v for k, v in params.items() if "due_date" in k}
        assert due_values == {TODAY}, (
            "消费面查询未按 SSOT 过滤 today（due_date 条件缺失）"
        )
        assert _status_params(params) == set(TODAY_ACTIVE_STATUSES)
        assert "deleted_at" in str(compiled)


# ---------------------------------------------------------------------------
# 3. 取数层端到端（conftest 内存 SQLite，非业务库）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fetch_todays_next_task_filters_today(db_session):
    from app.models.plan import Plan
    from app.models.user import User
    from app.services import goal_today_view as gtv

    user = User(username=f"gtv_{uuid4().hex[:10]}", email=f"{uuid4().hex[:10]}@t.example", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    plan = Plan(user_id=user.id, name="gtv-plan", type="sprint")
    db_session.add(plan)
    await db_session.flush()

    past = Task(user_id=user.id, plan_id=plan.id, title="overdue", type="LEARNING",
                estimated_minutes=10, status=TaskStatus.PENDING, priority=9, due_date=TODAY - dt.timedelta(days=1))
    future = Task(user_id=user.id, plan_id=plan.id, title="future", type="LEARNING",
                  estimated_minutes=10, status=TaskStatus.PENDING, priority=9, due_date=TOMORROW)
    today_low = Task(user_id=user.id, plan_id=plan.id, title="today-low", type="LEARNING",
                     estimated_minutes=10, status=TaskStatus.PENDING, priority=1, due_date=TODAY)
    today_high = Task(user_id=user.id, plan_id=plan.id, title="today-high", type="LEARNING",
                      estimated_minutes=10, status=TaskStatus.PENDING, priority=8, due_date=TODAY)
    db_session.add_all([past, future, today_low, today_high])
    await db_session.commit()

    fetched = await gtv.fetch_todays_next_task(
        db_session, user_id=user.id, plan_id=plan.id, today=TODAY
    )
    assert fetched is not None
    assert fetched.title == "today-high"

    none_today = await gtv.fetch_todays_next_task(
        db_session, user_id=user.id, plan_id=plan.id, today=TODAY + dt.timedelta(days=3)
    )
    assert none_today is None
