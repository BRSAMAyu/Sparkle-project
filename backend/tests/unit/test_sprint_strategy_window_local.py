"""V3-FIX-221（推送余族）红绿测：SprintStrategy 提醒窗与 hours_left 切用户本地日。

定界（wt507 207 同族，列级钟源沿 V3-FIX-37 实录）：Task.due_date 是客户端
给到的到期日（无时刻成分，墙上钟日界语义）。SprintStrategy（strategy.py）
should_trigger 的提醒窗 ``due_date <= deadline_threshold.date()`` 且
``>= now.date()`` 双端都是 UTC date，get_context_data 的下界 ``>= now.date()``
同源——上海凌晨（UTC 尚在前日）下界早开一日把本地昨日到期（已过期）任务
拉回提醒窗（过期任务多推）；上海日间 base 72h 截止端落在 UTC 16:00-24:00
时上界早收一日把最后一日本地到期任务漏在窗外（漏推）。payload 的
``hours_left`` 再把墙上 due_date 23:59:59 与 UTC now 直减，多出 8 小时。

修法：窗端点改用户本地日 ``local_date(instant, valid_timezone_name(policy
.timezone))``（推送面 tz 的天然通道是 policy.timezone，engine.py 由
push_preference 缺省 Asia/Shanghai 装配）；hours_left 用同一墙钟的本地
now。冻结钟：NOW_SMALL_HOURS = 2026-09-24 18:00 UTC（上海 = 09-25 02:00，
pressure_tolerance=0 → 窗 72h）：证漏推面（due 09-28 修前上界 09-27 漏）、
多推面（due 09-24 本地昨日修前在下界内）、payload 面（hours_left 修前 29
修后 21）；本地今日（09-25）到期为双版皆触发的控制组。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.personalization.profiles import PushPolicyProfile
from app.services.push_strategies.strategy import SprintStrategy

NOW_SMALL_HOURS = dt.datetime(2026, 9, 24, 18, 0)  # naive UTC；上海本地 = 2026-09-25 02:00


def _policy() -> PushPolicyProfile:
    return PushPolicyProfile(
        daily_cap=3,
        min_interval_minutes=120,
        pressure_tolerance=0.0,  # base 72h 窗
        memory_urgency_threshold=0.5,
        curiosity_frequency="daily",
        silent_during_focus=False,
        active_hours=[],
        timezone="Asia/Shanghai",
        preference_version=1,
    )


async def _seed_user(db: AsyncSession) -> User:
    user = User(
        username=f"wt513-{uuid4().hex[:8]}",
        email=f"wt513-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_pending_due(db: AsyncSession, user_id, due: dt.date) -> None:
    db.add(
        Task(
            user_id=user_id,
            title=f"wt513 sprint due {due.isoformat()}",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            due_date=due,
            estimated_minutes=20,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_sprint_window_keeps_last_local_day_within_horizon(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海凌晨（本地 09-25 02:00）：72h 地平线内最后一天（本地 09-28）到期的待办必须触发提醒。

    修前上界 ``deadline_threshold.date()``=09-27（UTC date）：due 09-28 被
    漏在窗外 → 不触发（提醒窗晨间漏推）。
    """
    monkeypatch.setattr("app.services.push_strategies.strategy._utcnow", lambda: NOW_SMALL_HOURS)
    user = await _seed_user(db_session)
    await _seed_pending_due(db_session, user.id, dt.date(2026, 9, 28))

    triggered = await SprintStrategy(db_session).should_trigger(user, _policy())

    assert triggered is True, "due 09-28 在 72h 窗内（上海本地窗 [09-25, 09-28]）：修前上界 UTC date 09-27 把它漏推"


@pytest.mark.asyncio
async def test_sprint_window_excludes_local_yesterday_due(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海凌晨：本地昨日（09-24）到期（已过期）的待办不应拉回「即将到期」提醒窗。

    修前下界 ``now.date()``=09-24（UTC date）：due 09-24 落在窗内 → 触发
    （过期任务多推）；修后下界=本地今日 09-25 → 不触发。
    """
    monkeypatch.setattr("app.services.push_strategies.strategy._utcnow", lambda: NOW_SMALL_HOURS)
    user = await _seed_user(db_session)
    await _seed_pending_due(db_session, user.id, dt.date(2026, 9, 24))

    triggered = await SprintStrategy(db_session).should_trigger(user, _policy())

    assert triggered is False, "修前下界 UTC date 09-24 把本地昨日到期的过期任务拉回提醒窗（多推）"


@pytest.mark.asyncio
async def test_sprint_window_still_triggers_for_local_today_due(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组：本地今日（09-25）到期的待办双版都触发（防「修成空窗」假绿）。"""
    monkeypatch.setattr("app.services.push_strategies.strategy._utcnow", lambda: NOW_SMALL_HOURS)
    user = await _seed_user(db_session)
    await _seed_pending_due(db_session, user.id, dt.date(2026, 9, 25))

    triggered = await SprintStrategy(db_session).should_trigger(user, _policy())

    assert triggered is True, "本地今日到期的待办必须仍在 72h 提醒窗内"


@pytest.mark.asyncio
async def test_context_hours_left_uses_local_wall_now(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """payload hours_left 必须按同一墙钟的本地 now 计：due 09-25 在上海 09-25 02:00 应余 ~22h。

    修前墙上 23:59:59 直减 UTC now（09-24 18:00）= 29h——比用户真实剩余
    时间多 8 小时。
    """
    monkeypatch.setattr("app.services.push_strategies.strategy._utcnow", lambda: NOW_SMALL_HOURS)
    user = await _seed_user(db_session)
    await _seed_pending_due(db_session, user.id, dt.date(2026, 9, 25))

    context = await SprintStrategy(db_session).get_context_data(user)

    assert context, f"due 09-25 应命中本地窗并产出 payload：{context}"
    assert (
        context["hours_left"] == 21
    ), f"hours_left 应按本地墙钟 now（09-25 02:00）计为 21；修前直减 UTC now 得 29：{context}"
