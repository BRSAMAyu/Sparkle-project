"""V3-FIX-211（两处未定界面收口）红绿测：weekly_stats 周窗墙钟域换算 + behavior_pattern 用户本地日。

两处定界结论（本卡完成，录台账 V3-FIX-211 行）：

1. ``weekly_stats_service.get_weekly_summary``（:74 focus 窗）：窗口端点由
   调用方传入——weekly_digest_service / weekly_synthesis_service 均为
   ``_utcnow()`` 派生的 UTC 滚动瞬间。同一对端点直比
   ``StudyRecord.created_at`` / ``Task.updated_at``（UTC 存储列）无跨钟，
   而 ``FocusSession.start_time`` 是客户端本地墙上钟列——不换算时专注计数
   随市场时区漂移 ±8h。修法：focus 查询的端点换算成同一真实区间的用户本地
   墙上 naive（周期语义零改动；如产品要把周窗对齐本地日界需连同调用方
   周期语义一起拍板，非本卡面）。
   冻结窗 [09-18 12:00Z, 09-25 12:00Z]（上海墙上 [09-18 20:00, 09-25 20:00]）：
   墙上 09-25 15:00（=07:00Z，真实窗内）的会话必须计入，修前墙上值直比
   UTC 端点把它漏在窗外。

2. ``behavior_pattern_service.analyze_focus_decay``（:96-99 唯一调用方）：
   ``_get_daily_focus_average`` 的日窗端点是 naive 零点形状（与墙上钟列同
   域），但 ``date`` 来源是 ``date.today()``=宿主机本地日——既非 UTC 亦非
   用户时区。生产调用面为空（celery scan_behavior_patterns 只调
   analyze_planning_optimism），零风险收口：today 改用户本地日。
   冻结 NOW=09-25 20:00Z（上海本地今日=09-26）+ 冻结宿主机 date.today()=
   09-25：墙上 09-26 03:00 的会话属本地今日，修前宿主机日窗把它漏在窗外
   → 今日均值 0 → 误报 Focus Decay。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.analytics import behavior_pattern_service as bps_module
from app.services.analytics.behavior_pattern_service import BehaviorPatternService
from app.services.analytics.weekly_stats_service import WeeklyStatsService

WINDOW_START = dt.datetime(2026, 9, 18, 12, 0)  # naive UTC；上海墙上 = 09-18 20:00
WINDOW_END = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海墙上 = 09-25 20:00
NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt507-{uuid4().hex[:8]}",
        email=f"wt507-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_session(db: AsyncSession, user_id, *, start: dt.datetime, minutes: int) -> None:
    db.add(
        FocusSession(
            user_id=user_id,
            # start_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=start,
            end_time=start + dt.timedelta(minutes=minutes),
            duration_minutes=minutes,
            status=FocusStatus.COMPLETED,
        )
    )
    await db.commit()


async def test_weekly_summary_focus_window_translated_to_user_wall(
    db_session: AsyncSession,
):
    """墙上 09-25 15:00（=07:00Z，真实窗内）的会话必须计入周窗专注统计。

    修前墙上值直比 UTC 端点：09-25 15:00 > 端点 09-25 12:00 被漏在窗外；
    修后端点换算成上海墙上 [09-18 20:00, 09-25 20:00] → 计入。UTC 列
    （Task.updated_at 完成数）保持原端点（控制组）。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 25, 15, 0), minutes=30)
    # 窗外控制：墙上 09-26 01:00（=09-25 17:00Z，窗后）不计
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 26, 1, 0), minutes=45)
    db_session.add(
        Task(
            user_id=user.id,
            title="wt507 weekly control",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            updated_at=dt.datetime(2026, 9, 21, 6, 0),
            completed_at=dt.datetime(2026, 9, 21, 6, 0),
            estimated_minutes=20,
        )
    )
    await db_session.commit()

    stats = await WeeklyStatsService(db_session).get_weekly_summary(str(user.id), WINDOW_START, WINDOW_END)

    assert stats["focus_duration_minutes"] == 30, (
        f"周窗 focus 查询端点应换算成用户本地墙上域（上海墙上 09-18 20:00 起）；"
        f"修前墙上 09-25 15:00 直比 UTC 端点 09-25 12:00 被漏计：{stats}"
    )
    assert stats["focus_sessions_count"] == 1, f"窗后会话（墙上 09-26 01:00）不应计入：{stats}"
    assert stats["tasks_completed"] == 1, f"UTC 存储列保持原端点，不应被本卡改动：{stats}"


async def test_focus_decay_uses_user_local_today_not_host_date(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """focus_decay 的「今日」必须取用户本地日，而非宿主机本地日。

    冻结 NOW=09-25 20:00Z（上海本地今日=09-26）且冻结宿主机 date.today()
    返回 09-25：墙上 09-26 03:00（本地今日凌晨）的 50 分钟会话修前落在
    宿主机日窗之外 → 今日均值 0 → 误报 Focus Decay；修后三日各 50 分钟，
    无衰减模式。
    """
    monkeypatch.setattr("app.services.analytics.behavior_pattern_service._utcnow", lambda: NOW_LATE)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)

    monkeypatch.setattr(bps_module, "date", _FrozenDate)

    async def _no_publish(event_type, payload, stream="sparkle_events"):  # noqa: ANN001
        return None

    monkeypatch.setattr(bps_module.event_bus, "publish", _no_publish)

    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    # 不放 09-25 的会话：宿主机日窗（09-25）必须为空才能证误报面
    for start in (dt.datetime(2026, 9, 26, 3, 0), dt.datetime(2026, 9, 24, 9, 0), dt.datetime(2026, 9, 23, 9, 0)):
        await _seed_session(db_session, user.id, start=start, minutes=50)

    pattern = await BehaviorPatternService(db_session).analyze_focus_decay(user.id)

    assert pattern is None, (
        f"用户本地日三日窗 [09-26:50, 09-25:0, 09-24:50] 不满足衰减判据（50 < 0.7*50 为假），"
        f"不应产生 Focus Decay 模式；修前 today=date.today()（宿主机 09-25）把本地今日 09-26 03:00 "
        f"会话漏计 → stats=[0, 50, 50] 误报：{pattern}"
    )
