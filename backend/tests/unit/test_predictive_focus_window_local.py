"""V3-FIX-211（predictive_service 墙钟余族）红绿测：24h 专注窗口切墙上钟 + overdue 切本地日。

定界（V3-FIX-37 双存储钟实录 + 本卡逐列核）：
- ``_get_current_time()=datetime.now(UTC)``（:188，UTC 钟根）派生的
  ``last_24h``/``last_7d``（:888-889）在 ``_build_rule_based_next_intent`` 与
  ``_build_rule_based_realtime_next_step`` 同时喂两类列：
  * ``FocusSession.start_time``（:911/:1081）是客户端本地墙上钟列——跨钟，
    窗口端点随时刻在本地日界附近漂移 ±8h（V3-FIX-208 同族）；
  * ``Task.completed_at`` / ``StudyRecord.created_at`` 是 UTC 存储列——
    无跨钟，保持 UTC 瞬间不变（控制组钉住）。
- 同函数 ``overdue_count``（:929）用 ``due_date < now.date()``：Task.due_date
  是客户端给到的到期日（V3-FIX-37 定界：墙上钟日界语义），修前比 UTC
  date——UTC+8 晨间把「本地昨日到期」任务漏计逾期（V3-FIX-207 同族，
  同函数顺手按 207 教义收口）。

修法：focus 窗口端点 ``local_midnight_wall(today - 1d)``（本地昨日零点
naive，208 先例）；overdue 比用户本地日。冻结钟（沿 208 冻结钟族）：
- NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：证专注窗口
  漏计面——本地昨日（09-24）上午的会话必须计入「最近24小时」窗；
- NOW_MORNING = 2026-09-24 20:00 UTC（上海 = 09-25 04:00）：证 overdue
  面——本地昨日（09-24）到期的待办必须计逾期，修前 UTC date 尚是 09-24。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.predictive_service import PredictiveService

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00
NOW_MORNING = dt.datetime(2026, 9, 24, 20, 0)  # naive UTC；上海本地 = 2026-09-25 04:00


def _freeze(monkeypatch: pytest.MonkeyPatch, now: dt.datetime) -> None:
    monkeypatch.setattr(
        PredictiveService,
        "_get_current_time",
        staticmethod(lambda: now.replace(tzinfo=dt.UTC)),
    )


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


async def test_next_intent_focus_window_counts_local_yesterday_morning(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晚间（本地 09-25 20:00）：本地昨日（09-24）上午的专注必须计入 24h 窗。

    修前 last_24h = 09-24 12:00（UTC 瞬间）直比墙上钟列，09-24 08:30 的
    50 分钟会话被漏计；UTC 列（completed 24h / study 7d）两版不变（控制组）。
    """
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 24, 8, 30), minutes=50)
    db_session.add(
        Task(
            user_id=user.id,
            title="wt507 completed control",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            completed_at=dt.datetime(2026, 9, 25, 2, 0),
            estimated_minutes=30,
        )
    )
    db_session.add(
        StudyRecord(
            user_id=user.id,
            node_id=uuid4(),  # 聚合查询只按 user_id/created_at 过滤，不连节点表
            study_minutes=25,
            mastery_delta=0.1,
            created_at=dt.datetime(2026, 9, 20, 6, 0),
        )
    )
    await db_session.commit()

    forecast = await PredictiveService(db_session)._build_rule_based_next_intent(user.id)

    signals = forecast["signals"]
    assert signals["focus_minutes_last_24h"] == 50, (
        f"上海晚间 24h 专注窗应按本地昨日零点(09-24 00:00)计入 09-24 08:30 会话；"
        f"修前起点=09-24 12:00（UTC 瞬间）把它漏计：{signals}"
    )
    assert signals["completed_last_24h"] == 1, f"UTC 存储列窗口保持 UTC 瞬间，不应被本卡改动：{signals}"
    assert signals["study_records_last_7d"] == 1, f"UTC 存储列窗口保持 UTC 瞬间，不应被本卡改动：{signals}"


async def test_realtime_next_step_focus_window_counts_local_yesterday_morning(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """realtime 面（:1081）同钟修复：本地昨日上午的完整专注必须计入 24h 计数。"""
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 24, 8, 30), minutes=50)

    result = await PredictiveService(db_session)._build_rule_based_realtime_next_step(
        user.id,
        partial_text="继续推进",
        active_plan_id=None,
        surface="test",
    )

    assert result["signals"]["focus_sessions_last_24h"] == 1, (
        f"realtime 24h 专注计数应按本地昨日零点计入 09-24 08:30 会话；"
        f"修前起点=09-24 12:00（UTC 瞬间）把它漏计：{result['signals']}"
    )


async def test_overdue_count_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海晨间（本地 09-25 04:00）：本地昨日（09-24）到期的待办必须计逾期。

    修前 overdue_count 比 ``now.date()``=09-24（UTC date）：due 09-24 < 09-24
    为假，逾期任务漏计；修后比用户本地日 09-25 → 计入。本地今日（09-25）
    到期的待办两版都不计逾期（防「修成全算」假绿）。
    """
    _freeze(monkeypatch, NOW_MORNING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add_all(
        [
            Task(
                user_id=user.id,
                title="wt507 overdue yesterday-local",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=dt.date(2026, 9, 24),
                estimated_minutes=20,
            ),
            Task(
                user_id=user.id,
                title="wt507 due today-local",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=dt.date(2026, 9, 25),
                estimated_minutes=20,
            ),
        ]
    )
    await db_session.commit()

    forecast = await PredictiveService(db_session)._build_rule_based_next_intent(user.id)

    assert forecast["signals"]["overdue_count"] == 1, (
        f"overdue 应按用户本地日（09-25）切：due 09-24 计逾期、due 09-25 不计；"
        f"修前比 UTC date 09-24 把昨日到期任务漏计：{forecast['signals']}"
    )
