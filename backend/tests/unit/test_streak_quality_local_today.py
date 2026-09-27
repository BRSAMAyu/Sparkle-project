"""V3-FIX-320（修3）红绿测：streak_quality「今日」切用户本地日（293 契约）。

定界（wt604 普查 §3.1-8，列级钟源核实）：
- ``StudyRecord.created_at`` / ``Task.completed_at``：naive 列 + 服务端
  ``_utcnow`` 写入 → UTC 存储列，日窗端点须换算成本地日界的 UTC 瞬间；
- ``Task.due_date`` / ``UserStreakDay.day``：``Date`` 列，墙上钟日界语义
  （客户端本地日），与「今日」直接可比；
- ``UserStreakStats.last_activity_date`` 等 streak 列：UTC naive（297
  docstring 定界），achievement_engine V3-FIX-293 已裁连胜日界=用户本地日
  （``_resolve_streak_activity_date``，push_preference.timezone 标量直查、
  缺省 Asia/Shanghai）。

修前 ``streak_quality`` 三处「今日」缺省 ``_utcnow().date()``（UTC 日），
日窗端点 ``_day_bounds`` 是 UTC 日零点——与 293 契约分裂：上海 00:00-08:00
（= 前日 16:00-24:00Z）时 build_payload/quality_streak/weekly_quality_trend
把「昨日」当今日，两面各说各话。

修法：缺省「今日」= ``local_date(_utcnow(), tz)``（tz 沿 PushPreference.
timezone 标量直查，缺省 Asia/Shanghai，293 同款）；UTC 存储列的日窗端点
换算 ``local_midnight_as_utc_naive(day, tz)``（两侧同钟）；Date 列比较
保持本地日直比。冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海本地 =
09-26 01:00）：本地今日（09-26）凌晨的学习记录必须计入「今日质量」
（修前被记到 UTC 09-25 的「今日」头上）；UTC 控制组修前修后行为逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.user import PushPreference, User
from app.services.streak_quality import StreakQualityService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt610-{uuid4().hex[:8]}",
        email=f"wt610-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_study(
    db: AsyncSession, user_id, *, created_at: dt.datetime, minutes: int, mastery: float
) -> None:
    node = KnowledgeNode(name=f"wt610-node-{uuid4().hex[:8]}")
    db.add(node)
    await db.flush()
    db.add(
        StudyRecord(
            user_id=user_id,
            node_id=node.id,
            study_minutes=minutes,
            mastery_delta=mastery,
            created_at=created_at,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_streak_quality_today_follows_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海 00:00-08:00：「今日质量」= 本地今日（09-26）的学习记录。

    种两天的记录：本地昨日（09-25 18:00 上海 = 10:00Z）只学 10 分钟（不构成
    质量日）；本地今日（09-26 07:00 上海 = 前日 23:00Z）学 90 分钟（质量日）。
    修后「今日」= 09-26：今日质量只含 90 分钟、quality_streak=1、周趋势末日
    09-26。修前「今日」= UTC 09-25：两天记录全进同一窗（100 分钟）→ 红。
    """
    monkeypatch.setattr("app.services.streak_quality._utcnow", lambda: NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_study(
        db_session,
        user.id,
        created_at=dt.datetime(2026, 9, 25, 10, 0),  # 上海 09-25 18:00 = 本地昨日
        minutes=10,
        mastery=0.05,
    )
    await _seed_study(
        db_session,
        user.id,
        created_at=dt.datetime(2026, 9, 25, 23, 0),  # 上海 09-26 07:00 = 本地今日
        minutes=90,
        mastery=0.2,
    )

    payload = await StreakQualityService(db_session).build_payload(user.id)

    today_quality = payload["today_quality"]
    assert today_quality["effective_minutes"] == 90, (
        f"「今日质量」应只含本地今日（09-26）的 90 分钟"
        f"（修前 UTC 日窗把昨日 10 分钟也并入 = 100）：{today_quality}"
    )
    assert today_quality["is_quality_day"] is True
    assert payload["quality_streak"] == 1, (
        "质量连胜应从本地今日起算：昨日（10 分钟）不是质量日，连胜=1"
    )
    trend = payload["weekly_quality_trend"]
    assert trend[-1]["date"] == "2026-09-26", (
        f"周趋势末日应为用户本地今日 09-26（修前 UTC 日 09-25）：{trend[-1]['date']}"
    )
    assert trend[-1]["breakdown"]["effective_minutes"] == 90


@pytest.mark.asyncio
async def test_streak_quality_utc_user_unchanged(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 控制组（同钟自洽）：「今日」与日窗修前修后逐位不变。"""
    monkeypatch.setattr("app.services.streak_quality._utcnow", lambda: NOW_LATE)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_study(
        db_session,
        user.id,
        created_at=dt.datetime(2026, 9, 25, 17, 0),  # UTC 今日 17:00
        minutes=90,
        mastery=0.2,
    )

    payload = await StreakQualityService(db_session).build_payload(user.id)

    assert payload["today_quality"]["effective_minutes"] == 90
    assert payload["today_quality"]["is_quality_day"] is True
    assert payload["quality_streak"] == 1
    trend = payload["weekly_quality_trend"]
    assert trend[-1]["date"] == "2026-09-25"
    assert trend[-1]["breakdown"]["effective_minutes"] == 90
