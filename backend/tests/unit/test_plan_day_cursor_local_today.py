"""V3-FIX-233（plans API 面）红绿测：plan day 游标（days_left）切用户本地日。

定界（wt513 221/209 同族余量，233 登记面 3）：``_derived_today_day``
（api/v1/plans.py:385）与 ``_today_day_index``（:499）的
``days_left = max((plan.target_date - date.today()).days, 0)`` 是宿主机
钟——上海晨间 plan day 游标偏一日，/today 与 plan 详情 day_highlights
的「当天」派生随之漂移。

修法（沿 221 planning_strategy_compiler 先例）：两函数增 ``today`` 形参
（有 tz 通路的调用方显式传入——get_plan/get_plan_today 端点
PushPreference.timezone 标量直查），缺省
``local_date(utcnow(), DEFAULT_USER_TIMEZONE)`` 去宿主机 date.today()
依赖。冻结钟（沿双冻结钟族）：冻结 NOW=09-25 20:00Z（主市场本地今日
=09-26）+ 冻结宿主机 date.today()=09-25：
- target 09-26、initial 7 天计划：本地今日应为 Day 8（days_left=0），
  修前宿主机 09-25 算出 days_left=1 → Day 7；
- 显式 today=09-25（UTC 用户语义）应得 Day 7（参数通道钉测）。
"""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import pytest

from app.api.v1.plans import _derived_today_day, _today_day_index

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _plan_stub(target_date: dt.date) -> SimpleNamespace:
    return SimpleNamespace(
        target_date=target_date,
        description=json.dumps({"strategy": {"actual_days_left": 7}}),
        created_at=dt.datetime(2026, 9, 19, 20, 0),
        source_metadata={},
    )


def _task_stub(day: int) -> SimpleNamespace:
    return SimpleNamespace(order_index=day * 1000, tags=[], status="pending")


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.plans.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    monkeypatch.setattr("app.api.v1.plans.date", _FrozenDate)


def test_day_cursor_defaults_to_market_local_day(monkeypatch: pytest.MonkeyPatch):
    """缺省钟：上海本地今日（09-26）到期的 7 天计划应派生 Day 8 而非 Day 7。"""
    _freeze_clocks(monkeypatch)
    plan = _plan_stub(dt.date(2026, 9, 26))

    assert _derived_today_day(plan, [], []) == 8, (
        "plan 详情 day_highlights 游标应按主市场本地日派生 Day 8（days_left=0）；"
        "修前 date.today()=宿主机日 09-25 算出 days_left=1 → Day 7"
    )
    assert _today_day_index(plan, [_task_stub(8)]) == 8, (
        "/today 游标应按主市场本地日派生 Day 8（max_task_day=8 不截断）；"
        "修前 date.today()=宿主机日 09-25 算出 days_left=1 → Day 7"
    )


def test_day_cursor_explicit_today_param(monkeypatch: pytest.MonkeyPatch):
    """显式 today 形参（tz 通路调用方）：UTC 用户本地今日 09-25 应回落 Day 7。"""
    _freeze_clocks(monkeypatch)
    plan = _plan_stub(dt.date(2026, 9, 26))

    assert _derived_today_day(plan, [], [], today=dt.date(2026, 9, 25)) == 7, (
        "显式 today=09-25（UTC 用户）应派生 Day 7（days_left=1）——today 形参未贯通"
    )
    assert _today_day_index(plan, [_task_stub(8)], today=dt.date(2026, 9, 25)) == 7, (
        "显式 today=09-25（UTC 用户）应派生 Day 7——today 形参未贯通"
    )
