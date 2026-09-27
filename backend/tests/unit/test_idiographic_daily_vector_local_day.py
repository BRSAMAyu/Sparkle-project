"""V3-FIX-320（修1）红绿测：idiographic 每日行为向量键控统一用户本地日。

定界（wt604 普查 §3.1-5，列级钟源逐一核实）：
- ``FocusSession.end_time``：naive ``DateTime`` 列，客户端本地墙上时间直存
  （models/focus.py:38-39，V3-FIX-37 定界）→ ``.date()`` 即用户本地日；
- ``Task.completed_at`` / ``StudyRecord.created_at``：naive ``DateTime`` 列 +
  服务端 ``_utcnow`` 写入（task_service/execution_service 写点、time_utils
  docstring 点名）→ ``.date()`` 是 UTC 日，不是用户本地日。

修前 ``_load_behavior_daily_aggregates``（:448-521）：窗口端点
``_day_start(UTC 日)`` naive 零点，focus 按**墙钟日**键控、task/study 按
**UTC 日**键控——上海 00:00-08:00（= 前日 16:00-24:00Z）事件里 focus 落
本地今日、task/study 落 UTC「昨日」，同一日向量两钟分裂错桶。

修法（承 293 已裁决契约 + time_utils 教义，对齐 persdyn V3-FIX-221 先例）：
日网格与键控统一用户本地日——tz 沿 PushPreference.timezone 标量直查（缺省
Asia/Shanghai）；墙钟列窗口走 ``local_midnight_wall``（同钟零点）、键取
``end_time.date()``；UTC 列窗口走 ``local_midnight_as_utc_naive``、键取
``local_date(value, tz)``。冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海
本地 = 09-26 01:00，正落 00:00-08:00 错桶窗）：
- 墙钟 end_time 09-26 01:00 的专注 + UTC 17:00Z 的任务/学习记录必须同落
  本地今日 09-26 的向量（修前 grid 末日是 UTC 09-25：focus 键 09-26 落网
  格外、task/study 键 09-25 落「昨日」桶）；
- UTC 控制组（tz=UTC，同钟自洽）：修前修后行为逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.idiographic_association_service import IdiographicAssociationService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
LOCAL_TODAY = dt.date(2026, 9, 26)  # 上海本地今日（NOW_LATE 所属用户日）


async def _seed_user(
    db: AsyncSession, *, timezone: str | None = None
) -> User:
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


async def _seed_local_today_events(db: AsyncSession, user_id, *, wall_today: dt.date, utc_instant: dt.datetime) -> None:
    """同一用户本地日的一组事件：专注（墙钟列）+ 任务完成/学习记录（UTC 列）。

    ``wall_today``：专注 end_time 的客户端墙上日（= 用户本地日）；
    ``utc_instant``：任务完成与学习记录的 UTC 瞬间（同一本地日内）。
    全部取预估=实际的 30 分钟任务，task_accuracy_daily = 1.0。
    """
    node = KnowledgeNode(name=f"wt610-node-{uuid4().hex[:8]}")
    db.add(node)
    await db.flush()
    db.add_all(
        [
            FocusSession(
                user_id=user_id,
                start_time=dt.datetime.combine(wall_today, dt.time(0, 30)),
                end_time=dt.datetime.combine(wall_today, dt.time(1, 0)),
                duration_minutes=30,
                status=FocusStatus.COMPLETED,
            ),
            Task(
                user_id=user_id,
                title="wt610 local-day task",
                type=TaskType.LEARNING,
                status=TaskStatus.COMPLETED,
                estimated_minutes=30,
                actual_minutes=30,
                completed_at=utc_instant,
            ),
            StudyRecord(
                user_id=user_id,
                node_id=node.id,
                study_minutes=30,
                mastery_delta=0.1,
                created_at=utc_instant,
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_daily_vectors_key_focus_and_task_study_on_same_user_local_day(
    db_session: AsyncSession,
):
    """上海 00:00-08:00 窗：focus 与 task/study 必须同落用户本地今日的向量。

    修前：日网格按 UTC 日（末日 09-25）；focus 按墙钟日键控 → 09-26 的专注
    落在网格外；task/study 按 UTC 日键控 → 09-25 桶。三者分裂、错桶。
    修后：统一用户本地日 → 全部落 09-26 向量，09-25 桶为空。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    # 专注墙钟 end = 09-26 01:00（= 09-25 17:00Z）；任务/学习 UTC = 09-25 17:00Z
    await _seed_local_today_events(
        db_session,
        user.id,
        wall_today=LOCAL_TODAY,
        utc_instant=dt.datetime(2026, 9, 25, 17, 0),
    )

    service = IdiographicAssociationService(db_session, now_factory=lambda: NOW_LATE)
    vectors = await service._build_daily_vectors(user.id, NOW_LATE)

    today_vec = vectors.get(LOCAL_TODAY)
    assert today_vec is not None, (
        f"日网格末日应为用户本地今日 {LOCAL_TODAY}（修前为 UTC 日 09-25，focus 键 09-26 落网格外）："
        f"grid 末日={max(vectors) if vectors else None}"
    )
    dims = today_vec["dims"]
    assert dims["focus_duration_daily"] == 0.5, (
        f"墙钟 09-26 01:00 的专注（30min）应计入本地今日向量：{dims}"
    )
    assert dims["task_accuracy_daily"] == 1.0, (
        f"UTC 09-25 17:00Z 完成的任务应按本地日计入今日向量：{dims}"
    )
    assert dims["session_frequency_daily"] == 1.0, (
        f"UTC 09-25 17:00Z 的学习记录应按本地日计入今日向量：{dims}"
    )
    assert today_vec["active_event_count"] == 32, (
        f"今日向量活跃事件数应含 task(1)+focus(30)+study(1)=32：{today_vec}"
    )
    assert vectors[dt.date(2026, 9, 25)]["active_event_count"] == 0, (
        "本地昨日（09-25）向量不应吸收上海 00:00-08:00 的事件"
    )


@pytest.mark.asyncio
async def test_daily_vectors_utc_user_unchanged(db_session: AsyncSession):
    """UTC 控制组（同钟自洽）：tz=UTC 用户键控/窗口修前修后逐位不变。"""
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_local_today_events(
        db_session,
        user.id,
        wall_today=dt.date(2026, 9, 25),
        utc_instant=dt.datetime(2026, 9, 25, 17, 0),
    )

    service = IdiographicAssociationService(db_session, now_factory=lambda: NOW_LATE)
    vectors = await service._build_daily_vectors(user.id, NOW_LATE)

    today_vec = vectors.get(dt.date(2026, 9, 25))
    assert today_vec is not None
    dims = today_vec["dims"]
    assert dims["focus_duration_daily"] == 0.5
    assert dims["task_accuracy_daily"] == 1.0
    assert dims["session_frequency_daily"] == 1.0
    assert today_vec["active_event_count"] == 32
    assert vectors[dt.date(2026, 9, 24)]["active_event_count"] == 0
