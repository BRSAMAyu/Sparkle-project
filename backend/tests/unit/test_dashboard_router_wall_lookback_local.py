"""V3-FIX-211（dashboard_router 墙钟余族）红绿测：FocusSession 窗口端点切用户本地墙上钟。

定界（V3-FIX-37 双存储钟实录 + 本卡逐列核）：
- ``FocusSession.start_time`` 存客户端本地墙上时间 naive（墙上钟列）；
- ``Task.completed_at`` / ``Task.created_at`` / ``User.created_at`` 是服务端
  ``_utcnow`` 写入的 UTC 存储列。
- ``dashboard_router._GrowthExperienceDashboardBuilder`` 修前把
  ``_compute_lookback`` 的 UTC 瞬间 ``since`` 同时喂两类列：
  * ``_time_distribution``（:140）/``_plan_stability``（:245）直比
    ``start_time``——窗口端点在本地日界附近随时刻漂移 ±8h（V3-FIX-208
    同族）：UTC+8 晚间漏计 7 天前上午会话、晨间多计 8 天前深夜会话；
  * ``_efficiency_metrics`` / ``_knowledge_changes`` 比 UTC 列，无跨钟，
    本卡保持 UTC 瞬间不变（控制组钉住）。
- 修法：新增 ``_wall_lookback``——老用户取 ``local_midnight_wall(today -
  LOOKBACK_DAYS)``（V3-FIX-208 先例；勿用 local_midnight_as_utc_naive——
  那是 UTC 存储列的换算），新用户分支（注册 <7d）取注册时刻换算成的用户
  本地墙上钟 naive（保持「自注册起」语义同钟；UTC 存储的注册瞬间直比墙上
  钟列对西半球用户会漏计注册后头几个小时的会话）。

冻结钟三面（沿 test_growth_dashboard_focus_window_local 冻结钟族）：
- NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：证漏计面——
  7 天前（09-18）本地上午的完成/中断会话必须计入，修前被
  ``>= 09-18 12:00``（UTC 瞬间直比）排除；
- 新用户面：America/New_York 用户（UTC-4）注册瞬间 09-25 00:00Z，注册后
  2 小时的会话（NY 墙上 09-24 22:00）必须计入，修前被
  ``>= 09-25 00:00``（UTC naive 直比）排除。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.experience import dashboard_router
from app.models.focus import FocusSession, FocusStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00


def _freeze(monkeypatch: pytest.MonkeyPatch, now: dt.datetime) -> None:
    monkeypatch.setattr(dashboard_router, "_utcnow", lambda: now)


async def _seed_user(
    db: AsyncSession,
    *,
    timezone: str | None = None,
    created_at: dt.datetime | None = None,
) -> User:
    user = User(
        username=f"wt507-{uuid4().hex[:8]}",
        email=f"wt507-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    if created_at is not None:
        user.created_at = created_at
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_session(
    db: AsyncSession,
    user_id,
    *,
    start: dt.datetime,
    minutes: int,
    status: FocusStatus = FocusStatus.COMPLETED,
) -> FocusSession:
    session = FocusSession(
        user_id=user_id,
        # start_time 是客户端本地墙上钟列（无时区后缀 naive）
        start_time=start,
        end_time=start + dt.timedelta(minutes=minutes),
        duration_minutes=minutes,
        status=status,
    )
    db.add(session)
    await db.commit()
    return session


async def _build(db: AsyncSession, monkeypatch: pytest.MonkeyPatch, user: User) -> dict:
    builder = dashboard_router._GrowthExperienceDashboardBuilder(db)

    async def _fake_snapshot(self, user_id, *, user):  # noqa: ANN001
        return {}

    async def _empty_narrative(user_id):  # noqa: ANN001
        return {}

    monkeypatch.setattr(dashboard_router.GrowthDashboardService, "build_snapshot", _fake_snapshot)
    monkeypatch.setattr(builder, "_weekly_narrative", _empty_narrative)
    return await builder.build(user.id, user=user)


async def test_week_ago_morning_sessions_count_at_shanghai_evening(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晚间（本地 09-25 20:00）：7 天前本地上午的会话必须计入回看窗口。

    修前 since = UTC now − 7d = 09-18 12:00 直比墙上钟列：09-18 08:30 的
    50 分钟完成会话与 09-18 07:00 的 15 分钟中断会话被漏计；UTC 列窗口
    （completed_at 效率面）保持不变（控制组）。
    """
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai", created_at=dt.datetime(2026, 5, 1, 0, 0))
    # 7 天前（09-18）本地上午——正确窗口（本地零点 09-18 00:00 起）内
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 18, 8, 30), minutes=50)
    await _seed_session(
        db_session, user.id, start=dt.datetime(2026, 9, 18, 7, 0), minutes=15, status=FocusStatus.INTERRUPTED
    )
    # 8 天前深夜——两个窗口都应排除（防窗口被修得过宽）
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 17, 23, 0), minutes=40)
    # 本地昨日（09-24）上午——两个窗口都应计入（防「修成全排」假绿）
    await _seed_session(
        db_session, user.id, start=dt.datetime(2026, 9, 24, 9, 0), minutes=20, status=FocusStatus.INTERRUPTED
    )
    # UTC 列控制组：completed_at 09-20 06:00Z 在两版窗口内，效率面必须不变
    db_session.add(
        Task(
            user_id=user.id,
            title="wt507 efficiency control",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            completed_at=dt.datetime(2026, 9, 20, 6, 0),
            estimated_minutes=30,
        )
    )
    await db_session.commit()

    payload = await _build(db_session, monkeypatch, user)

    distribution = {item["category"]: item["hours"] for item in payload["time_distribution"]}
    assert distribution.get("unassigned") == 1.4, (
        f"上海晚间窗口起点应为本地零点 09-18 00:00：50+15+20 分钟计入（该查询不滤状态、"
        f"09-17 23:00 不计）；修前起点=09-18 12:00 把 7 天前上午两个会话漏计（只剩 20 分钟）："
        f"{payload['time_distribution']}"
    )
    assert (
        payload["plan_stability"]["interruptions"] == 2
    ), f"plan_stability 同钟修复：09-18 07:00 中断会话应计入；修前被漏计：{payload['plan_stability']}"
    assert (
        payload["efficiency_metrics"]["tasks_completed"] == 1
    ), f"UTC 存储列窗口保持 UTC 瞬间，不应被本卡改动：{payload['efficiency_metrics']}"


async def test_new_user_lookback_translates_registration_to_user_wall(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """新用户分支：注册时刻换算成用户本地墙上钟，注册后数小时的会话必须计入。

    America/New_York（UTC-4）用户 09-25 00:00Z 注册（NY 本地 09-24 20:00），
    NY 墙上 09-24 22:00（= 09-25 02:00Z，注册后 2 小时）的会话：修前
    since=注册瞬间 UTC naive 直比墙上钟列 → 09-24 22:00 < 09-25 00:00 被
    漏计；修后注册瞬间换算为 NY 墙上 09-24 20:00 → 计入。
    """
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(
        db_session,
        timezone="America/New_York",
        created_at=dt.datetime(2026, 9, 25, 0, 0),
    )
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 24, 22, 0), minutes=25)

    payload = await _build(db_session, monkeypatch, user)

    distribution = {item["category"]: item["hours"] for item in payload["time_distribution"]}
    assert distribution.get("unassigned") == 0.4, (
        f"新用户回看起点应换算成用户本地墙上钟（NY 09-24 20:00），注册后 2 小时的会话应计入；"
        f"修前 since=09-25 00:00（UTC naive）直比墙上钟列把它漏计：{payload['time_distribution']}"
    )
