"""V3-FIX-233（checkpoint_nudge 面）红绿测：+8h 硬编码改 push_preference tz 解析。

定界（233 登记面 6，行为变化点）：checkpoint_nudge_service 用硬编码
+8h 偏移代替时区解析——
- ``_lagging_tasks``（:750）：``task.due_date <= (datetime.now(UTC)+
  timedelta(hours=8)).date()``（非 push_preference 口径：UTC 用户被错切
  成上海日，负偏移时区反向错切）；
- ``_plan_total_days``（:737，同流同缺陷兄弟面）：``local_start=
  (plan.created_at.replace(tzinfo=UTC)+timedelta(hours=8)).date()``——
  expected_completion_rate 的总天数随硬编码漂移。

修法：tz 沿 207/211/221 先例——PushPreference.timezone 解析（缺省
Asia/Shanghai）进 ``_build_checkpoint_progress_context``，``_lagging_tasks``
的「今日」改 ``local_date(utcnow(), tz)``、``_plan_total_days`` 的
created_at 改 ``local_date(created_at, tz)``。**行为变化点（如实标注）**：
时区≠Asia/Shanghai 的用户 lagging/expected 天数从 +8h 硬编码切真实
tz（Asia/Shanghai 用户逐位不变）。冻结钟（沿双冻结钟族）：冻结
NOW=09-25 20:00Z + 冻结宿主机钟：
- UTC 用户：due 09-26 任务不是 lagging（本地今日=09-25），修前 +8h 把
  今天切到 09-26 误报 lagging；plan created 09-18 20:00Z → 总天数 9，
  修前 +8h 算 8；
- Asia/Shanghai（缺省）：due 09-26 是 lagging、总天数 8——与旧 +8h 行为
  逐位一致（控制组）。
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.task import Task, TaskStatus, TaskType
from app.services.checkpoint_nudge_service import CheckpointNudgeService

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；+8h 墙上日 = 2026-09-26


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结模块 datetime（修前 +8h 面走 datetime.now(UTC)）与 utcnow（修后通道）。"""
    real_utc = dt.UTC

    class _FrozenDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return NOW_LATE.replace(tzinfo=tz if tz is not None else None)

    monkeypatch.setattr("app.services.checkpoint_nudge_service.datetime", _FrozenDatetime)
    monkeypatch.setattr(
        "app.services.checkpoint_nudge_service.utcnow", lambda: NOW_LATE.replace(tzinfo=None), raising=False
    )
    monkeypatch.setattr("app.services.checkpoint_nudge_service.UTC", real_utc, raising=False)


def _task_due(day: int) -> Task:
    return Task(
        user_id=uuid4(),
        title=f"wt519 due {day}",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, day),
        estimated_minutes=20,
    )


def test_lagging_tasks_follow_resolved_timezone(monkeypatch: pytest.MonkeyPatch):
    """UTC 用户：due 09-26（UTC 本地明日）不误报 lagging；上海缺省保持 lagging。"""
    _freeze_clocks(monkeypatch)
    service = CheckpointNudgeService.__new__(CheckpointNudgeService)  # 纯方法面，不触 db/redis
    task = _task_due(26)

    utc_picked = service._lagging_tasks(tasks=[task], checkpoint_day=1, tz_name="UTC")
    assert utc_picked == [], (
        f"UTC 用户本地今日=09-25，due 09-26 不应 lagging；修前硬编码 +8h 把今日切到 09-26 误报：{utc_picked}"
    )

    shanghai_picked = service._lagging_tasks(tasks=[task], checkpoint_day=1, tz_name="Asia/Shanghai")
    assert shanghai_picked == [task], (
        f"Asia/Shanghai 用户本地今日=09-26，due 09-26 应 lagging（与旧 +8h 行为一致的控制组）：{shanghai_picked}"
    )

    overdue = _task_due(24)
    assert service._lagging_tasks(tasks=[overdue], checkpoint_day=1, tz_name="UTC") == [overdue], (
        "UTC 用户本地昨日到期任务仍应 lagging（overdue 控制组）"
    )


def test_plan_total_days_follow_resolved_timezone(monkeypatch: pytest.MonkeyPatch):
    """UTC 用户：created 09-18 20:00Z（UTC 本地起始 09-18）→ 总天数 9；上海缺省 8。"""
    _freeze_clocks(monkeypatch)
    service = CheckpointNudgeService.__new__(CheckpointNudgeService)
    plan = SimpleNamespace(
        created_at=dt.datetime(2026, 9, 18, 20, 0),  # naive UTC；上海本地 09-19 04:00，UTC 本地 09-18
        target_date=dt.date(2026, 9, 26),
    )

    assert service._plan_total_days(plan=plan, tasks=[], tz_name="UTC") == 9, (
        "UTC 用户 plan 总天数应按本地起始 09-18 算 9；修前硬编码 +8h 把起始切到 09-19 算 8"
    )
    assert service._plan_total_days(plan=plan, tasks=[], tz_name="Asia/Shanghai") == 8, (
        "Asia/Shanghai 用户 plan 总天数应按本地起始 09-19 算 8（与旧 +8h 行为一致的控制组）"
    )
