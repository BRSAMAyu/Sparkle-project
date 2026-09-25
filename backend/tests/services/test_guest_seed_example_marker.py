"""O1（J-01 实测，P1 诚实性红线）：guest 种子内容必须自带「示例」声明。

J-01 实测（v3/09_evidence/j01_first3 REPORT §2.3）：新访客首屏被种入未声明
演示目标（「数据结构期中冲刺」计划 + 「二叉树遍历」任务），5/5 pass 复现，
demo 与真实数据第一分钟不可区分。红线依据：forbidden_practices「不得用
mock/seed 冒充真实行为」——种子本身合法（GJ02 demo→own 升级路径依赖它），
缺的是声明。

修法（最小诚实修，不加列）：种子写入既有 ``Plan.source="example"`` 标记
（该列已存在且已被 PlanDetail/移动端 PlanModel 透传），读侧派生透传：
- /tasks/today 等 TaskDetail 序列化带 ``is_example``（由所属 plan 派生）；
- /growth/dashboard 的 active_plan_progress 带 ``is_example``；
- /goals 列表 GoalResponse 带 ``is_example``（Goal.source 同词表）。
转正（upgrade-guest）后用户新自建计划不带标记，种子行为不变。
"""

from datetime import date, timedelta

import pytest

from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.daily_task_selection_service import DailyTaskSelectionService
from app.services.guest_seed_service import seed_guest_user_data


async def _seeded_guest(db_session) -> User:
    user = User(
        username=f"guest_example_{date.today().strftime('%H%M%S')}",
        email="guest_example@test.local",
        hashed_password="hashed",
        registration_source="guest",
    )
    db_session.add(user)
    await db_session.flush()
    await seed_guest_user_data(db_session, user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_guest_seed_marks_plans_and_today_response_with_example(db_session):
    """红测①：种子用户的 plan 行与 /tasks/today 响应必须含 example 标记。"""
    from app.api.v1.tasks import _serialize_task_detail

    user = await _seeded_guest(db_session)

    # 种子产出的计划行本身带 example 来源标记（既有 Plan.source 列）。
    from sqlalchemy import select

    plans = (
        (await db_session.execute(select(Plan).where(Plan.user_id == user.id)))
        .scalars()
        .all()
    )
    assert plans, "guest seed 应产出演示计划"
    assert all(plan.source == "example" for plan in plans), (
        "O1：种子计划必须带 source=example（base 红：source 为 NULL，demo 与真实数据不可区分）"
    )

    # /tasks/today 的响应组合（DailyTaskSelectionService + _serialize_task_detail，
    # 与端点同构）必须透传 is_example。
    service = DailyTaskSelectionService(db_session, redis=None)
    selections = await service.select_tasks(
        user_id=user.id,
        limit=50,
        include_completed_today=True,
        only_today_relevant=True,
    )
    assert selections, "guest seed 应产出今日任务"
    from app.api.v1.tasks import _load_example_flags_for_tasks

    example_flags = await _load_example_flags_for_tasks(
        db_session, task_ids=[s.task.id for s in selections]
    )
    for selection in selections:
        payload = _serialize_task_detail(
            selection.task,
            bound_sources=[],
            is_example=example_flags.get(selection.task.id, False),
        )
        assert payload.get("is_example") is True, (
            "O1：/tasks/today 的种子任务响应必须带 is_example=true（base 红：无此字段）"
        )


@pytest.mark.asyncio
async def test_growth_dashboard_active_plan_and_goals_list_carry_example_marker(db_session):
    """红测①续：growth 首屏 plan 与 /goals 列表响应透传 example 标记。"""
    from app.api.v1.goals import list_goals
    from app.services.growth_dashboard_service import GrowthDashboardService

    user = await _seeded_guest(db_session)

    # growth dashboard active_plan_progress（guest 首屏 plan chip 的真源）。
    service = GrowthDashboardService(db_session)
    active_plan = await service._get_active_plan(user.id)
    if active_plan is not None:
        payload = service._serialize_active_plan(active_plan)
        assert payload is not None
        assert payload.get("is_example") is True, (
            "O1：active_plan_progress 必须带 is_example=true（guest 首屏 chip 的数据源）"
        )

    # /goals 列表：Goal.source=example 的行必须透传 is_example=true。
    db_session.add(
        Goal(
            user_id=user.id,
            title="示例目标",
            goal_type="exam",
            status="active",
            source="example",
        )
    )
    db_session.add(
        Goal(
            user_id=user.id,
            title="自建目标",
            goal_type="exam",
            status="active",
            source="manual",
        )
    )
    await db_session.commit()

    responses = await list_goals(db=db_session, current_user=user)
    by_title = {item.title: item for item in responses}
    assert by_title["示例目标"].is_example is True
    assert by_title["自建目标"].is_example is False


@pytest.mark.asyncio
async def test_upgraded_user_self_created_content_has_no_example_marker(db_session):
    """红测③：转正后新自建计划/任务不带 example 标记（种子行为不变）。"""
    from app.api.v1.tasks import _serialize_task_detail

    user = await _seeded_guest(db_session)

    # upgrade-guest 保留同一用户行；转正后自建计划（POST /plans 不设 source）。
    own_plan = Plan(
        user_id=user.id,
        name="我自己的考研计划",
        type=PlanType.SPRINT,
        target_date=date.today() + timedelta(days=30),
    )
    db_session.add(own_plan)
    await db_session.flush()
    own_task = Task(
        user_id=user.id,
        plan_id=own_plan.id,
        title="自建任务",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        status=TaskStatus.PENDING,
    )
    db_session.add(own_task)
    await db_session.commit()

    payload = _serialize_task_detail(own_task, bound_sources=[])
    assert payload.get("is_example") is False, (
        "O1：转正后自建内容不得带示例标记（badge 只属于种子内容）"
    )
