"""V3-FIX-250（写侧面 3）红绿测：archive 提前完成天数切用户本地日。

定界（wt519 V3-FIX-233 同族余量，250 登记面 3；209 同族 days 面写侧/
事件面）：``archive_plan_state`` 的
``days_ahead = (plan.target_date - date.today()).days``
（api/v1/plans.py:1588）以宿主机本地日计「提前完成天数」，流入
SPRINT_AHEAD 成就事件（days_ahead>0 才触发）——UTC 宿主上服务上海
用户，按本地日历已到终点日仍被记「提前 1 天」。

修法：沿 233 同款——``today`` 切 ``_user_local_today(db, user_id)``
（PushPreference.timezone 标量直查，缺省 Asia/Shanghai）。冻结钟（沿
双冻结钟族）：冻结 NOW=09-25 20:00Z（上海本地今日=09-26、UTC 用户本
地今日=09-25）+ 冻结宿主机 date.today()=09-25（UTC 宿主钟）：

- 上海用户：终点 09-26、本地今日 09-26 → days_ahead=0，SPRINT_AHEAD
  不得触发（修前 09-26-09-25=1 误触发——事件面语义差异如实标注：修前
  该场景发 sprint_ahead(days_ahead=1)，修后不发，属修目标本身）；
- UTC 用户（tz 通道控制组）：本地今日仍 09-25 → days_ahead=1，
  SPRINT_AHEAD 触发且 days_ahead=1（修前修后一致——证明走用户时区通
  道而非统一偏移）。
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.plans import archive_plan_state
from app.models.plan import Plan, PlanType
from app.models.user import PushPreference, User
from app.services.achievement_engine import AchievementEvent

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00
TARGET = dt.date(2026, 9, 26)  # 冲刺终点（= 上海用户本地今日）


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.plans.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机钟（UTC 宿主此刻真实值）

    monkeypatch.setattr("app.api.v1.plans.date", _FrozenDate)


def _capture_achievement_events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, dict]]:
    events: list[tuple[Any, dict]] = []

    async def _capture(self, user_id, event, **kwargs):  # noqa: ANN001
        events.append((event, kwargs))

    async def _no_daily_first(self, user_id, db):  # noqa: ANN001
        return None

    monkeypatch.setattr("app.services.achievement_engine.AchievementEngine.process_event", _capture)
    monkeypatch.setattr("app.services.achievement_engine.AchievementEngine.check_daily_first", _no_daily_first)
    return events


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt526-{uuid4().hex[:8]}",
        email=f"wt526-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_finished_sprint(db: AsyncSession, user: User) -> Plan:
    plan = Plan(
        user_id=user.id,
        name=f"wt526-sprint-{uuid4().hex[:6]}",
        type=PlanType.SPRINT,
        target_date=TARGET,
        progress=1.0,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@pytest.mark.asyncio
async def test_archive_days_ahead_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海用户本地终点日（09-26 04:00）归档：days_ahead=0，SPRINT_AHEAD 不触发。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    plan = await _seed_finished_sprint(db_session, user)
    events = _capture_achievement_events(monkeypatch)

    await archive_plan_state(plan_id=plan.id, current_user=user, db=db_session)

    ahead = [kwargs for event, kwargs in events if event == AchievementEvent.SPRINT_AHEAD]
    assert ahead == [], (
        "上海用户本地今日已 09-26（=终点日）：days_ahead 应=0、SPRINT_AHEAD 不触发"
        "（修前 date.today()=宿主机日 09-25，误发 sprint_ahead(days_ahead=1)——"
        "事件面语义差异：修前发/修后不发，修目标本身）"
    )


@pytest.mark.asyncio
async def test_archive_days_ahead_utc_user_keeps_utc_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户（tz 通道控制组）：本地今日=09-25，days_ahead=1，SPRINT_AHEAD 触发。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    plan = await _seed_finished_sprint(db_session, user)
    events = _capture_achievement_events(monkeypatch)

    await archive_plan_state(plan_id=plan.id, current_user=user, db=db_session)

    ahead = [kwargs for event, kwargs in events if event == AchievementEvent.SPRINT_AHEAD]
    assert len(ahead) == 1 and ahead[0].get("days_ahead") == 1, (
        "UTC 用户本地今日仍 09-25（提前终点日 1 天）：应触发 sprint_ahead(days_ahead=1)"
        "（控制组，证明走用户时区通道而非统一 +8h）"
    )
