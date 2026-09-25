"""R2-D（H6）红绿测：goal_router 进度投影单一化。

缺陷（修前）：两处进度投影各自用 ``or`` 取值，真值塌缩导致两类问题——
- ``_progress_payload``（原 :314）：``(goal.progress if goal else None) or (plan.progress if plan else None) or 0``，
  goal.progress=0.0（刚建目标的合法进度）被当成缺失，静默落到 plan.progress；
- ``_plan_health_payload``（原 :608）：``(plan.progress if plan else None) or (goal.progress if goal else None)``，
  优先级与上面相反（plan 优先），且同样存在 0.0 塌缩——同一个 goal-detail 响应里
  ``progress.overall`` 与 ``plan_health.phase_health`` 可能来自不同实体。

修复后口径（单一投影函数 ``_projected_progress``）：
- **goal 优先**，goal.progress 为 None 才回退 plan.progress（回退语义见
  ``_resolve_goal``：goal-detail 主实体是 goal，home 卡无目标时才以活跃计划兜底，
  「进度走到哪」语义归属于 goal）；
- 显式 ``is not None`` 判空，0.0 不再被误判为缺失；
- 两处消费点同源，``overall`` 与 ``phase_health`` 恒出自同一实体同一值。

红测关键例：goal.progress=0.0、plan.progress=0.5——修前 overall=0.5（塌缩）、
phase_health=0.5（plan 优先），断言两者均应为 0.0（goal 同源）即红。
"""

from __future__ import annotations

from app.api.v1.experience.goal_router import _plan_health_payload, _progress_payload
from app.models.goal import Goal
from app.models.plan import Plan


def _counts() -> dict[str, int]:
    return {"total": 0, "completed": 0, "paused": 0, "stuck": 0}


def test_goal_zero_progress_wins_over_plan() -> None:
    """goal.progress=0.0 是合法值：overall 与 phase_health 均须同源取 goal，不塌缩到 plan。"""
    goal = Goal(progress=0.0, mastery=0.4)
    plan = Plan(progress=0.5, mastery_level=0.6)

    overall = _progress_payload(goal=goal, plan=plan, task_counts=_counts())["overall"]
    phase_health = _plan_health_payload(goal=goal, plan=plan, task_counts=_counts()).phase_health

    assert overall == 0.0, f"overall 应取 goal.progress=0.0（修前 or 塌缩到 plan 的 0.5）：{overall}"
    assert phase_health == 0.0, f"phase_health 应取 goal.progress=0.0（修前 plan 优先取 0.5）：{phase_health}"
    assert overall == phase_health, "两处投影必须同源一致"


def test_goal_none_progress_falls_back_to_plan() -> None:
    """goal.progress=None → 回退 plan.progress，两处同源取 0.5。"""
    goal = Goal(progress=None, mastery=0.4)
    plan = Plan(progress=0.5, mastery_level=0.6)

    overall = _progress_payload(goal=goal, plan=plan, task_counts=_counts())["overall"]
    phase_health = _plan_health_payload(goal=goal, plan=plan, task_counts=_counts()).phase_health

    assert overall == 0.5
    assert phase_health == 0.5
    assert overall == phase_health


def test_goal_zero_progress_without_plan_is_zero() -> None:
    """无 plan 时 goal.progress=0.0 不得丢给 0 再误判——投影即 0.0。"""
    goal = Goal(progress=0.0, mastery=0.4)

    overall = _progress_payload(goal=goal, plan=None, task_counts=_counts())["overall"]
    phase_health = _plan_health_payload(goal=goal, plan=None, task_counts=_counts()).phase_health

    assert overall == 0.0
    assert phase_health == 0.0


def test_both_none_projects_zero() -> None:
    """goal/plan 皆 None → 两处投影均回 0（空态行为保持）。"""
    overall = _progress_payload(goal=None, plan=None, task_counts=_counts())["overall"]
    phase_health = _plan_health_payload(goal=None, plan=None, task_counts=_counts()).phase_health

    assert overall == 0.0
    assert phase_health == 0.0
