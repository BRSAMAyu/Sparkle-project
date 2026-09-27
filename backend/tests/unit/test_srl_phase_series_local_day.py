"""V3-FIX-323（修2）红绿测：SRL phase_started_at 切用户本地日网格。

定界（wt610 修 320 时遗留址）：``SRLPhaseStateRecord.phase_started_at`` 为
naive ``DateTime`` 列 + 服务端 ``_utcnow`` 写入（srl_phase_tracker_service
``_transition_state``/``force_reset`` 写点，UTC 钟）；idiographic
``_build_srl_phase_series`` 修前 ``row.phase_started_at.date()`` 取 **UTC
日**，而 V3-FIX-320 后的日网格（``start_day``/``end_day``）是 **用户本地
日**——上海 00:00-08:00（= 前日 16:00-24:00Z）发生的相位切换，其「当日取
current_score、之前取 previous_score」的分界错切到 UTC 昨日。

修法（承 293/320 已裁决契约）：分界日换 ``local_date(phase_started_at, tz)``
（tz 沿调用方已解析的 PushPreference 标量直查口径透传，缺省
Asia/Shanghai）。冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海本地 =
09-26 01:00）：上海本地今日（09-26）开始的新相位，其 09-26 向量取
current_score、09-25 向量必须仍是 previous_score（修前 09-25 已被切成
current_score）；UTC 控制组修前修后逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.user import PushPreference, User
from app.services.idiographic_association_service import IdiographicAssociationService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
LOCAL_TODAY = dt.date(2026, 9, 26)
LOCAL_YESTERDAY = dt.date(2026, 9, 25)

CURRENT_SCORE = 0.55  # PERFORMANCE
PREVIOUS_SCORE = 0.25  # FORETHOUGHT


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


async def _seed_phase_record(db: AsyncSession, user_id) -> None:
    """上海本地今日 00:30（= 09-25 16:30Z，UTC 日 09-25）开始的相位切换。"""
    db.add(
        SRLPhaseStateRecord(
            user_id=user_id,
            current_phase="PERFORMANCE",
            previous_phase="FORETHOUGHT",
            phase_started_at=dt.datetime(2026, 9, 25, 16, 30),
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_srl_phase_series_boundary_follows_user_local_day(
    db_session: AsyncSession,
):
    """上海 00:00-08:00 窗：相位分界日必须按用户本地日切。"""
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_phase_record(db_session, user.id)

    service = IdiographicAssociationService(db_session, now_factory=lambda: NOW_LATE)
    vectors = await service._build_daily_vectors(user.id, NOW_LATE)

    assert vectors[LOCAL_TODAY]["dims"]["srl_phase_signal"] == CURRENT_SCORE, (
        f"本地今日 {LOCAL_TODAY} 应取新相位 current_score：{vectors[LOCAL_TODAY]['dims']}"
    )
    assert vectors[LOCAL_YESTERDAY]["dims"]["srl_phase_signal"] == PREVIOUS_SCORE, (
        f"本地昨日 {LOCAL_YESTERDAY} 应仍是旧相位 previous_score"
        f"（修前 phase_started_at 取 UTC 日 09-25，09-25 被错切成 current_score）："
        f"{vectors[LOCAL_YESTERDAY]['dims']}"
    )


@pytest.mark.asyncio
async def test_srl_phase_series_defaults_to_market_tz_without_preference(
    db_session: AsyncSession,
):
    """无 PushPreference 的用户按缺省 Asia/Shanghai 口径切分界。"""
    user = await _seed_user(db_session, timezone=None)
    await _seed_phase_record(db_session, user.id)

    service = IdiographicAssociationService(db_session, now_factory=lambda: NOW_LATE)
    vectors = await service._build_daily_vectors(user.id, NOW_LATE)

    assert vectors[LOCAL_TODAY]["dims"]["srl_phase_signal"] == CURRENT_SCORE
    assert vectors[LOCAL_YESTERDAY]["dims"]["srl_phase_signal"] == PREVIOUS_SCORE


@pytest.mark.asyncio
async def test_srl_phase_series_utc_user_unchanged(db_session: AsyncSession):
    """UTC 控制组（同钟自洽）：分界修前修后逐位不变。"""
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_phase_record(db_session, user.id)

    service = IdiographicAssociationService(db_session, now_factory=lambda: NOW_LATE)
    vectors = await service._build_daily_vectors(user.id, NOW_LATE)

    assert vectors[dt.date(2026, 9, 25)]["dims"]["srl_phase_signal"] == CURRENT_SCORE
    assert vectors[dt.date(2026, 9, 24)]["dims"]["srl_phase_signal"] == PREVIOUS_SCORE
