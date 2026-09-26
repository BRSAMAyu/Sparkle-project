"""V3-FIX-37（stats 时区债）红绿测：stats 日界 naive-UTC 错切 → 用户本地日对齐。

定界实录（主市场 Asia/Shanghai = UTC+8）：
- ``FocusSession.start_time`` 存**客户端本地墙上时间 naive**：mobile
  ``focus_repository.dart:78`` ``startTime.toIso8601String()``（本地 DateTime、
  无时区后缀）→ 后端 ``FocusService._to_utc_naive`` 对 naive 原样入库；
- ``StudyRecord.created_at`` / ``Task.completed_at`` 存 **UTC naive**（服务端
  ``time_utils.utcnow`` / ``task_service._utcnow``）；
- 而聚合窗口全部用 naive-UTC 日界切（``api/v1/statistics.py:48/:251`` 与
  ``focus_service._utcnow`` 面）：UTC+8 本地 00:00–08:00 的会话被切进「昨天」，
  晨间专注被 heatmap 上界整段排除 → streak 误报 0。

红测冻结 NOW = 2026-09-25 23:30 UTC（上海本地 = 2026-09-26 07:30）：
- 本地今日（09-26）晨间 06:30 的 FocusSession（墙上时间 naive 入库）；
- UTC 09-25 23:00 完成的 Task / 22:00 的 StudyRecord（= 本地 09-26 07:00/06:00，
  UTC naive 入库）。

修前：``/stats/daily`` focus_sessions=0（上界 09-26T00:00 UTC 排除）、
``/stats/activity/heatmap`` 末日=09-25（UTC 今日）、focus today/heatmap/streak
全按 UTC 日报 0。修后：全部按用户本地日（09-26）命中。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.statistics as statistics_module
import app.services.focus_service as focus_service_module
from app.api.v1.statistics import get_daily_stats, get_learning_heatmap
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.focus_service import FocusService

NOW = datetime(2026, 9, 25, 23, 30)  # naive UTC；Asia/Shanghai 本地 = 2026-09-26 07:30
LOCAL_TODAY = "2026-09-26"


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结两端聚合时钟（statistics._utcnow 修前不存在，raising=False 让红落在行为上）。"""
    monkeypatch.setattr(statistics_module, "_utcnow", lambda: NOW, raising=False)
    monkeypatch.setattr(focus_service_module, "_utcnow", lambda: NOW, raising=False)


async def _seed_user(db: AsyncSession) -> User:
    user = User(
        username=f"wt487-{uuid4().hex[:8]}",
        email=f"wt487-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _morning_session(user_id) -> FocusSession:
    # 本地（上海）2026-09-26 06:30 晨间专注，墙上时间 naive 入库（mobile 真实写法）
    return FocusSession(
        user_id=user_id,
        start_time=datetime(2026, 9, 26, 6, 30),
        end_time=datetime(2026, 9, 26, 7, 15),
        duration_minutes=45,
        status=FocusStatus.COMPLETED,
    )


async def test_daily_counts_local_morning_focus_session(db_session: AsyncSession, frozen_clock: None):
    """跨 UTC 日界：上海晨间 06:30 会话属于本地今日 → /stats/daily 必须计入。"""
    user = await _seed_user(db_session)
    db_session.add(_morning_session(user.id))
    await db_session.commit()

    result = await get_daily_stats(current_user=user, db=db_session)

    assert result["focus_sessions"] == 1, (
        f"上海晨间会话（本地 09-26 06:30，存墙上时间）应计入本地今日；"
        f"修前按 UTC 日界（今日=09-25、上界 09-26T00:00）整段排除：{result['focus_sessions']}"
    )


async def test_activity_heatmap_buckets_by_user_local_day(db_session: AsyncSession, frozen_clock: None):
    """UTC naive 入库的 Task/StudyRecord 也必须按用户本地日归属与标注末日。"""
    user = await _seed_user(db_session)
    node = KnowledgeNode(name=f"tz-node-{uuid4().hex[:6]}", importance_level=3)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    # UTC 09-25 23:00 完成（= 上海本地 09-26 07:00），带 StudyRecord → 分钟走 study 侧
    linked_task = Task(
        user_id=user.id,
        title="晨间听力",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=45,
        actual_minutes=40,
        status=TaskStatus.COMPLETED,
        completed_at=datetime(2026, 9, 25, 23, 0),
        knowledge_node_id=node.id,
    )
    db_session.add(linked_task)
    await db_session.commit()
    await db_session.refresh(linked_task)
    db_session.add(
        StudyRecord(
            user_id=user.id,
            node_id=node.id,
            task_id=linked_task.id,
            study_minutes=35,
            mastery_delta=1.0,
            record_type="task_complete",
            created_at=datetime(2026, 9, 25, 22, 0),
        )
    )
    await db_session.commit()

    result = await get_learning_heatmap(days=7, user_id=None, current_user=user, db=db_session)

    last = result[-1]
    assert last["date"] == LOCAL_TODAY, (
        f"heatmap 末日应为用户本地今日 {LOCAL_TODAY}（NOW=UTC 09-25 23:30 上海已是 09-26）；"
        f"修前按 UTC 今日标 09-25：{last['date']}"
    )
    assert last["minutes"] == 35.0, f"study 分钟应归属本地今日：{last}"
    assert last["tasks_completed"] == 1, f"完成任务数应归属本地今日：{last}"


async def test_focus_stats_use_user_local_day(db_session: AsyncSession, frozen_clock: None):
    """focus today/heatmap/streak 三面同证：本地晨间会话不再被 UTC 日界吞掉。"""
    user = await _seed_user(db_session)
    db_session.add(_morning_session(user.id))
    await db_session.commit()

    today_stats = await FocusService.get_today_stats(db_session, user.id)
    assert (
        today_stats["total_minutes"] == 45
    ), f"today 分钟应按本地日=45；修前 UTC 日界（窗口 [09-25, 09-26)）排除晨间会话：{today_stats}"
    assert str(today_stats["today_date"]).startswith(
        LOCAL_TODAY
    ), f"today_date 应为本地今日 {LOCAL_TODAY}；修前报 UTC 今日 09-25：{today_stats['today_date']}"

    heatmap = await FocusService.get_heatmap_data(db_session, user.id, days=3)
    assert heatmap.get(LOCAL_TODAY) == 45.0, (
        f"focus heatmap 应含本地今日键 {LOCAL_TODAY}=45（mobile 以本地 DateTime.now() 日键取数）；"
        f"修前窗口上界 09-25T23:30 UTC 整段排除：{heatmap}"
    )

    streak = await FocusService._calculate_current_streak(db_session, user.id)
    assert streak == 1, f"本地今日有会话 → streak 至少 1；修前按 UTC 日判 09-25 无会话 → 误报 0：{streak}"


async def test_focus_weekly_monthly_windows_align_local_wall_clock(db_session: AsyncSession, frozen_clock: None):
    """周/月窗口同钟对齐：本地晨间会话落入按本地日推周一/月初的窗口。"""
    user = await _seed_user(db_session)
    db_session.add(_morning_session(user.id))
    await db_session.commit()

    weekly = await FocusService.get_weekly_stats(db_session, user.id)
    assert weekly["total_minutes"] == 45, f"本地今日（周六 09-26）晨间会话应落在本地周窗（周一 09-21 起）：{weekly}"
    assert weekly["streak_days"] == 1

    monthly = await FocusService.get_monthly_stats(db_session, user.id)
    assert monthly["total_minutes"] == 45, f"本地今日晨间会话应落在本地月窗（09-01 起）：{monthly}"
