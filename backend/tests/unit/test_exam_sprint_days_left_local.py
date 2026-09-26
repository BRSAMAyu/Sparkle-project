"""V3-FIX-233（exam_sprint 面）红绿测：dashboard days_left 切用户本地日。

定界（wt513 221/209 同族余量，233 登记面 5）：``_days_left`` 的
``max((target_date - date.today()).days, 0)``（exam_sprint_dashboard_
service.py:375）是宿主机钟——上海晨间 days_left/current_day_index 偏一
日（daily_task_selection._plan_current_day 沿其约定）。

修法（沿 221 planning_strategy_compiler 先例）：``_days_left`` 增
``today`` 形参（get_dashboard 有 db 通路——PushPreference.timezone 标量
直查显式传入），缺省 ``local_date(utcnow(), DEFAULT_USER_TIMEZONE)`` 去
宿主机 date.today() 依赖。冻结钟（沿双冻结钟族）：冻结 NOW=09-25
20:00Z（主市场本地今日=09-26）+ 冻结宿主机 date.today()=09-25：
- target 09-26（本地今日）：days_left 应为 0（修前宿主机 09-25 算 1）；
- target 09-25（本地昨日）：双版都 0（max(…,0) 控制组）；
- 显式 today=09-25（UTC 用户语义）对 target 09-26 应算 1（参数通道钉测）。
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock

import pytest

from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.exam_sprint_dashboard_service.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    monkeypatch.setattr("app.services.exam_sprint_dashboard_service.date", _FrozenDate)


def test_days_left_defaults_to_market_local_day(monkeypatch: pytest.MonkeyPatch):
    _freeze_clocks(monkeypatch)
    service = ExamSprintDashboardService(AsyncMock())

    assert service._days_left(dt.date(2026, 9, 26), fallback=6) == 0, (
        "target=本地今日（09-26）days_left 应为 0；修前 date.today()=宿主机日 09-25 算出 1"
    )
    assert service._days_left(dt.date(2026, 9, 25), fallback=6) == 0, "target=本地昨日双版都钳 0（控制组）"
    assert service._days_left(None, fallback=6) == 6, "无 target 走 fallback，不受钟影响（控制组）"


def test_days_left_explicit_today_param(monkeypatch: pytest.MonkeyPatch):
    _freeze_clocks(monkeypatch)
    service = ExamSprintDashboardService(AsyncMock())

    assert service._days_left(dt.date(2026, 9, 26), fallback=6, today=dt.date(2026, 9, 25)) == 1, (
        "显式 today=09-25（UTC 用户）对 target 09-26 应算 1——today 形参未贯通"
    )
