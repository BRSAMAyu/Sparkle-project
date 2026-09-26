"""V3-FIX-221（planning_compiler 余族）红绿测：deadline_days 切用户本地日。

定界（wt499 209 同族）：``_derive_deadline_days``（planning_strategy_compiler.py:538）
``(target - _utcnow().date()).days``——target 是 vision/plan_context 给到
的到期日（无时刻成分，墙上钟日界语义），右值是 UTC date：上海晨间（UTC
尚在前日）deadline_days 偏一日（target=本地今日 算成 1，plan_horizon/
feasibility 联动失真）。编译器是纯同步面（无 db 通道），修法：compile()
增 ``today: date | None`` 形参（调用方有 tz 通道时可显式传入），缺省回落
``local_date(_utcnow(), DEFAULT_USER_TIMEZONE)``——与族先例「缺省回落主
市场 Asia/Shanghai」一致，去 UTC date 依赖。冻结钟：NOW_MORNING =
2026-09-24 20:00 UTC（上海 = 09-25 04:00）：target=09-25（本地今日）的
deadline_days 应为 0，修前 (09-25 - 09-24).days = 1。
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.orchestration.planning_strategy_compiler import PlanningStrategyCompiler

NOW_MORNING = dt.datetime(2026, 9, 24, 20, 0)  # naive UTC；上海本地 = 2026-09-25 04:00


def test_deadline_days_counts_local_today_target_as_zero(monkeypatch: pytest.MonkeyPatch):
    """上海晨间：本地今日（09-25）到期的 target，deadline_days 应为 0 而非 1。"""
    monkeypatch.setattr("app.orchestration.planning_strategy_compiler._utcnow", lambda: NOW_MORNING)

    compiled = PlanningStrategyCompiler().compile(
        situation_brief={"vision": {"target_date": "2026-09-25"}},
    )

    assert compiled.deadline_days == 0, (
        f"target=本地今日（09-25）deadline_days 应为 0；修前右值 UTC date 09-24 算出 1（晨间偏一日）："
        f"{compiled.deadline_days}"
    )


def test_deadline_days_honors_explicit_today(monkeypatch: pytest.MonkeyPatch):
    """显式 today 形参（调用方 tz 通道）：本地明日 target → 1；本地昨日 target → 0（max 钳 0）。"""
    monkeypatch.setattr("app.orchestration.planning_strategy_compiler._utcnow", lambda: NOW_MORNING)
    compiler = PlanningStrategyCompiler()

    tomorrow = compiler.compile(
        situation_brief={"vision": {"target_date": "2026-09-27"}},
        today=dt.date(2026, 9, 26),
    )
    overdue = compiler.compile(
        situation_brief={"vision": {"target_date": "2026-09-25"}},
        today=dt.date(2026, 9, 26),
    )

    assert tomorrow.deadline_days == 1, f"显式 today=09-26、target=09-27 应为 1：{tomorrow.deadline_days}"
    assert overdue.deadline_days == 0, f"已过期 target 钳 0：{overdue.deadline_days}"


def test_deadline_days_none_when_no_target():
    """无 target_date 时保持 None（签名外行为零改动）。"""
    compiled = PlanningStrategyCompiler().compile(situation_brief={"vision": {}})

    assert compiled.deadline_days is None
