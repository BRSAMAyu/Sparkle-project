"""V3-FIX-323（修1）红绿测：metacognition 每日准确率序列键控用户本地日。

定界（wt610 修 320 时遗留址）：``build_daily_accuracy_series`` 的行时间
``recorded_at`` 来自 ``TheaterPrediction.generated_at`` / ``Task.completed_at``
——naive ``DateTime`` 列 + 服务端 ``_utcnow`` 写入（UTC 钟列），修前
``recorded_at.date()`` / ``reference_time.date()`` 是 **UTC 日**键控；而唯一
消费方 idiographic ``_build_daily_vectors``（V3-FIX-320 已修）的日网格是
**用户本地日**——上海 00:00-08:00（= 前日 16:00-24:00Z）的预测记录落 UTC
「昨日」桶，与网格错位一日，metacognition_accuracy 维残差 ≤1 日。

修法（承 293/320 已裁决契约）：tz 沿 PushPreference.timezone 标量直查
（缺省 Asia/Shanghai），窗口端点与行键控统一 ``local_date(value, tz)``。
冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海本地 = 09-26 01:00）：
- 上海本地今日（09-26 00:30 = 09-25 16:30Z）的预测必须落 09-26 键（修前落
  UTC 09-25 桶）；
- 本地昨日（09-25 04:00 = 09-24 20:00Z）的预测必须落 09-25 键（修前落
  09-24 桶）；
- UTC 控制组（tz=UTC，同钟自洽）：修前修后键控逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.theater_prediction import TheaterPrediction
from app.models.user import PushPreference, User
from app.services.metacognition_service import MetacognitionService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
LOCAL_TODAY = dt.date(2026, 9, 26)
LOCAL_YESTERDAY = dt.date(2026, 9, 25)

ACC_TODAY = 0.9  # predicted 0.8 / actual 0.9 → bias 0.1 → accuracy 0.9
ACC_YESTERDAY = 1.0  # predicted 0.5 / actual 0.5 → bias 0 → accuracy 1.0


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt613-{uuid4().hex[:8]}",
        email=f"wt613-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_prediction(
    db: AsyncSession,
    user_id,
    *,
    generated_at: dt.datetime,
    predicted: float,
    actual: float,
) -> None:
    """一条 TheaterPrediction：completion/mastery 两个收集器各自产一行同值样本。

    ``_collect_completion_bias_rows``（0-1 口径）与 ``_collect_mastery_bias_rows``
    （0-100 口径）扫同一批行——把两侧 bias 幅度对齐（mastery 差额按 completion
    差额 ×100 缩放），同日桶均值即单值，断言对收集器组成不敏感。
    """
    db.add(
        TheaterPrediction(
            prediction_id=f"wt613-{uuid4().hex[:12]}",
            user_id=user_id,
            topic="wt613 local-day series",
            target_name="数据结构期中",
            target_resolution_mode="manual",
            generated_at=generated_at,
            selected_prediction={
                "estimated_completion_rate": predicted,
                "estimated_mastery": 80.0,
            },
            accuracy_summary={
                "predicted_completion_rate": predicted,
                "actual_completion_rate": actual,
                "predicted_mastery": 80.0 - (actual - predicted) * 100.0,
                "actual_mastery": 80.0,
            },
        )
    )
    await db.commit()


async def _seed_local_window_predictions(db: AsyncSession, user_id) -> None:
    """同一上海本地窗内的两条预测（UTC 日键控下会各错位一日）。"""
    await _seed_prediction(
        db,
        user_id,
        generated_at=dt.datetime(2026, 9, 25, 16, 30),  # 上海 09-26 00:30（UTC 日 09-25）
        predicted=0.8,
        actual=0.9,
    )
    await _seed_prediction(
        db,
        user_id,
        generated_at=dt.datetime(2026, 9, 24, 20, 0),  # 上海 09-25 04:00（UTC 日 09-24）
        predicted=0.5,
        actual=0.5,
    )


@pytest.mark.asyncio
async def test_daily_accuracy_series_keys_on_user_local_day(
    db_session: AsyncSession,
):
    """上海 00:00-08:00 窗：预测记录必须按用户本地日键控。"""
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_local_window_predictions(db_session, user.id)

    series = await MetacognitionService(db_session, redis=None).build_daily_accuracy_series(
        user.id, now=NOW_LATE
    )

    assert series.get(LOCAL_TODAY) == ACC_TODAY, (
        f"上海 09-26 00:30（=09-25 16:30Z）的预测应落本地今日 {LOCAL_TODAY} 键"
        f"（修前落 UTC 日 09-25 桶）：{series}"
    )
    assert series.get(LOCAL_YESTERDAY) == ACC_YESTERDAY, (
        f"上海 09-25 04:00（=09-24 20:00Z）的预测应落本地昨日 {LOCAL_YESTERDAY} 键"
        f"（修前落 UTC 日 09-24 桶）：{series}"
    )


@pytest.mark.asyncio
async def test_daily_accuracy_series_defaults_to_market_tz_without_preference(
    db_session: AsyncSession,
):
    """无 PushPreference 的用户按缺省 Asia/Shanghai 口径键控。"""
    user = await _seed_user(db_session, timezone=None)
    await _seed_local_window_predictions(db_session, user.id)

    series = await MetacognitionService(db_session, redis=None).build_daily_accuracy_series(
        user.id, now=NOW_LATE
    )

    assert series.get(LOCAL_TODAY) == ACC_TODAY, (
        f"无偏好用户按缺省 Asia/Shanghai：本地今日 {LOCAL_TODAY} 应有值：{series}"
    )
    assert series.get(LOCAL_YESTERDAY) == ACC_YESTERDAY


@pytest.mark.asyncio
async def test_daily_accuracy_series_utc_user_unchanged(db_session: AsyncSession):
    """UTC 控制组（同钟自洽）：键控修前修后逐位不变。"""
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_local_window_predictions(db_session, user.id)

    series = await MetacognitionService(db_session, redis=None).build_daily_accuracy_series(
        user.id, now=NOW_LATE
    )

    assert series.get(dt.date(2026, 9, 25)) == ACC_TODAY
    assert series.get(dt.date(2026, 9, 24)) == ACC_YESTERDAY
    assert LOCAL_TODAY not in series, "UTC 用户的本地日=UTC 日，09-26 不应出现在键中"
