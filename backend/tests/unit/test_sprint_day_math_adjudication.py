"""V3-FIX-326 裁决红绿测：冲刺 day 数学 = 创建锚定的 UTC 日期脊柱（三调用点统一）。

裁决（wt618，2026-09-27）：`_plan_current_day` / dashboard
`_derive_initial_days_left`+`_current_day_index` / plans API
`_initial_days_for_today`+`_today_day_index` 统一到
``app/core/sprint_day_math``——plan.created_at 是 naive-UTC 存储
（wt615 五环锚链 + wt618 live PG 独立复核），``.date()`` 直取 UTC 日历日；
V3-FIX-314 的「本地墙上钟存储」论证翻案、读法保留；wt615 的
「UTC→本地换算」方案否决（JOURNEY 脊柱在上海本地日框架只有 6 天，
day7 永不可达——day6 门 [] 病征同根）。

红侧（本文件对**被否决替代**的可证伪性）：
- 若回退 221 的 ``_as_local_date``（UTC→本地换算）：created 上海本地日
  = 09-23 → 脊柱 6 → today 09-28 时 current=6 → ``test_day7_gate_pin``
  红（day7 门必失败，即裁决排除的分支）。
- 若实现读成本地墙上钟框架：``sprint_spine_days`` 返回 6 →
  ``test_spine_is_utc_calendar_anchored`` 红。
- 统一前三处公式各自为政（221→314 漂移的根因）：``app.core.sprint_day_math``
  模块为本裁决新增，统一前 import 即红。

冻结锚（live PG + state 文件实测，2026-09-27 取证）：
JOURNEY 计划 7917e864 created=2026-09-22 21:15:30.064186（naive-UTC）、
target_date=2026-09-29、用户 tz=Asia/Shanghai；day1–day7 模板
order_index=N*1000/day:N tag；day1–6 门实际跑在 UTC 09-22 22:37 /
09-23 06:09 / 09-24 00:02 / 09-25 00:00 / 09-26 00:18 / 09-27 00:26
（=上海 06:37/14:09/08:02/08:00/08:18/08:26，逐日与 state 文件
dayN_run_date=UTC 日一致）；day7 门明晨（上海 09-28 08:00 窗）要求
day:7 入 /tasks/today——``test_day7_gate_pin`` 即该门的常驻回归钉。
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.api.v1.plans import _derived_today_day, _initial_days_for_today, _today_day_index
from app.core.sprint_day_math import sprint_current_day, sprint_spine_days
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.daily_task_selection_service import _is_today_relevant, _plan_current_day
from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService

# JOURNEY 计划 7917e864 实测锚（naive-UTC 存储）。
PLAN_CREATED_AT = datetime(2026, 9, 22, 21, 15, 30, 64186)
PLAN_TARGET = date(2026, 9, 29)


def _journey_plan() -> Plan:
    return Plan(
        name="离散数学期末 7 天冲刺：及格冲 70+",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        priority=PlanPriority.HIGH,
        target_date=PLAN_TARGET,
        created_at=PLAN_CREATED_AT,
    )


def _journey_tasks(user_id=None, plan_id=None) -> list[Task]:
    return [
        Task(
            user_id=user_id or uuid4(),
            plan_id=plan_id,
            title=f"Day {day} · 冲刺",
            type=TaskType.LEARNING,
            estimated_minutes=60,
            status=TaskStatus.PENDING,
            tags=[f"day:{day}"],
            order_index=day * 1000,
        )
        for day in range(1, 8)
    ]


def test_spine_is_utc_calendar_anchored():
    """脊柱长度锚创建 UTC 日历日：created 09-22 21:15Z + target 09-29 = 7。

    被否决的本地日框架（上海 created 本地日 09-23）会给 6——红侧分支。
    """
    assert sprint_spine_days(PLAN_TARGET, PLAN_CREATED_AT) == 7
    # date 输入（日界语义）原样透传。
    assert sprint_spine_days(PLAN_TARGET, date(2026, 9, 22)) == 7
    # 脊柱非正（target 未晚于创建 UTC 日）→ None（调用方各自回落）。
    assert sprint_spine_days(date(2026, 9, 22), PLAN_CREATED_AT) is None
    assert sprint_spine_days(None, PLAN_CREATED_AT) is None
    assert sprint_spine_days(PLAN_TARGET, None) is None


def test_day6_gate_pin():
    """day6 门（09-27，上海 08:26 实测窗）：current=6，day:6 入面、day:7 不入。"""
    plan = _journey_plan()
    assert _plan_current_day(plan, date(2026, 9, 27), "Asia/Shanghai") == 6
    day6 = _journey_tasks()[5]
    day7 = _journey_tasks()[6]
    assert _is_today_relevant(day6, date(2026, 9, 27), plan=plan, tz_name="Asia/Shanghai") is True
    assert _is_today_relevant(day7, date(2026, 9, 27), plan=plan, tz_name="Asia/Shanghai") is False


def test_day7_gate_pin():
    """day7 门（明晨 09-28 上海 08:00 窗）：current=7，day:7 必入 /tasks/today 面。

    这是裁决的常驻回归钉：回退 221 的 UTC→本地换算会把 created 推成
    09-23 → 脊柱 6 → current=6 → day:7 被排除 → 门失败（红侧分支）。
    """
    plan = _journey_plan()
    assert _plan_current_day(plan, date(2026, 9, 28), "Asia/Shanghai") == 7
    day7 = _journey_tasks()[6]
    assert _is_today_relevant(day7, date(2026, 9, 28), plan=plan, tz_name="Asia/Shanghai") is True


def test_night_window_convention_pin():
    """夜间窗约定边界冻结：UTC 16–24 点创建的计划在本地次日 0–8 点 +1。

    created 09-22 21:15Z（上海 09-23 05:15）的本地创建日 09-23 读数=2
    （脊柱按 UTC 钟推进的既定约定，非 defect；13.1% 面量化见裁决注记）。
    若未来此断言翻红，说明有人把本族改吃了另一只钟——须回裁决重议而非顺手改。
    """
    assert sprint_current_day(PLAN_TARGET, PLAN_CREATED_AT, date(2026, 9, 23)) == 2
    assert _plan_current_day(_journey_plan(), date(2026, 9, 23), "Asia/Shanghai") == 2


def test_three_call_sites_agree_on_journey_shape():
    """三调用点同一计划同日必同值（221→314 漂移的根因封死）。"""
    plan = _journey_plan()  # 无 strategy JSON 描述 → plans API 落脊柱推算
    tasks = _journey_tasks()
    service = ExamSprintDashboardService(MagicMock())

    for today, expected in ((date(2026, 9, 27), 6), (date(2026, 9, 28), 7)):
        # daily task selection 面。
        assert _plan_current_day(plan, today, "Asia/Shanghai") == expected
        # dashboard 面：initial(spine) - days_left + 1，max_task_day 截断不触发。
        initial = service._derive_initial_days_left(plan=plan, goal_model={}, tasks=tasks)
        assert initial == 7
        days_left = service._days_left(PLAN_TARGET, fallback=initial, today=today)
        assert service._current_day_index(initial_days_left=initial, days_left=days_left, tasks=tasks) == expected
        # plans API 面：/today 端点游标与 highlights 派生日。
        assert _initial_days_for_today(plan, tasks) == 7
        assert _today_day_index(plan, tasks, today) == expected
        assert _derived_today_day(plan, tasks, [expected], today) == expected


def test_spine_fallbacks_preserved():
    """各面既有优先链不因统一而变：goal_model / strategy 元数据优先于脊柱。"""
    plan = _journey_plan()
    tasks = _journey_tasks()
    service = ExamSprintDashboardService(MagicMock())
    # dashboard：goal_model.days_left 优先。
    assert service._derive_initial_days_left(plan=plan, goal_model={"days_left": 5}, tasks=tasks) == 5
    # plans API：strategy JSON 的 total_days 优先。
    plan.description = '{"strategy": {"total_days": 5}}'
    assert _initial_days_for_today(plan, tasks) == 5
