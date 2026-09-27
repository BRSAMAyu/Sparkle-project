"""V3-FIX-319（user_activity_service 跨钟 max）红绿测。

定界（V3-FIX-297 同款病的新址，WT604 普查 §3.1-3）：
- ``FocusSession.end_time`` 存客户端本地墙上时间 naive（mobile 发本地 ISO 串、
  无时区后缀——focus_repository.dart / V3-FIX-37 定界；``models/focus.py:39``
  纯 naive ``DateTime`` 列，无服务端 utcnow 写点）；
- ``ChatMessage.created_at``（``models/chat.py:70`` ``default=datetime.utcnow``）
  与 ``Task.completed_at``（``task_service.py:716`` ``_utcnow()``）存 **UTC naive**；
- ``get_last_activity_snapshot`` 修前把三列 naive 直值 ``max()``：UTC+8 用户
  墙上钟值显得比真实绝对时刻「新」8 小时（上海 00:00-08:00 的会话绝对只到
  前日 16:00-24:00Z）——``last_activity_at`` 被墙钟列夺魁且返回墙上钟原样，
  唯一消费面 ``aurora.runtime_v1`` comeback 阶梯以 ``now - last_activity_at``
  差值消费该值（绝对时刻语义），静默时长被低估 → 活跃判定延迟 ~8h。

修法（沿 V3-FIX-297 先例）：
- 墙上钟列先经 ``time_utils.wall_clock_to_utc_naive`` 按用户时区换算成绝对
  UTC naive，再与 UTC 列同钟 max；返回值同为绝对 UTC naive。
- 时区来源：``push_preference.timezone`` 标量直查、缺省/非法回落 Asia/Shanghai
  （state_aggregator._user_timezone 同款，规避 async lazy-load）。

冻结钟（沿 test_state_aggregator_local_clock 双冻结钟族）：
- NOW = 2026-09-25 18:30 naive-UTC = 上海 2026-09-26 02:30（缺陷窗
  00:00-08:00 内）；UTC 用户同钟控制组钉住「边界确由用户时区驱动、非硬编码
  平移」。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, MessageRole
from app.models.focus import FocusSession, FocusStatus
from app.models.user import PushPreference, User
from app.services.user_activity_service import UserActivityService

pytestmark = pytest.mark.asyncio

NOW = dt.datetime(2026, 9, 25, 18, 30)  # naive UTC；上海本地 = 2026-09-26 02:30（缺陷窗）


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt609-{uuid4().hex[:8]}",
        email=f"wt609-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_focus(db: AsyncSession, user_id, *, end: dt.datetime) -> None:
    db.add(
        FocusSession(
            user_id=user_id,
            # start_time/end_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=end - dt.timedelta(hours=1),
            end_time=end,
            duration_minutes=60,
            status=FocusStatus.COMPLETED,
        )
    )
    await db.commit()


async def _seed_chat(db: AsyncSession, user_id, *, at: dt.datetime) -> None:
    db.add(
        ChatMessage(
            user_id=user_id,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="hi",
            created_at=at,  # created_at 是 UTC 存储列（models/chat.py default=utcnow）
        )
    )
    await db.commit()


async def test_focus_only_snapshot_returns_absolute_utc_shanghai(db_session: AsyncSession):
    """上海用户只有 focus：返回值必须是换算后的绝对 UTC 瞬间，而非墙上钟原样。

    墙上钟 09-26 01:00（缺陷窗内）绝对只到 09-25T17:00Z；修前 naive 原样返回
    09-26 01:00——NOW=18:30 时 ``now - last_activity_at`` 为负（被消费面钳到
    0 分钟），用户被误判「刚刚活跃」，唤醒/召回判定延迟 ~8h。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 26, 1, 0))

    snapshot = await UserActivityService(db_session).get_last_activity_snapshot(user.id)

    assert snapshot.last_focus_session_at == dt.datetime(2026, 9, 25, 17, 0), (
        f"墙上钟列应按用户时区换算成绝对 UTC naive（09-26 01:00 上海 = 09-25T17:00Z）；"
        f"修前返回墙上钟原样：{snapshot.last_focus_session_at}"
    )
    assert snapshot.last_activity_at == dt.datetime(2026, 9, 25, 17, 0)
    # 消费面语义（aurora comeback 差值）：NOW 距真实活跃 1.5h，不得为负
    assert NOW - snapshot.last_activity_at == dt.timedelta(hours=1, minutes=30)


async def test_cross_clock_max_picks_newest_absolute_moment_shanghai(db_session: AsyncSession):
    """上海用户：chat 09-25T18:00Z 应压过墙上钟 09-26 01:00（绝对 09-25T17:00Z）。

    修前 max() 直比 naive 选了墙上钟 09-26 01:00——比真实最新的 chat 时刻
    「新」7 小时，跨钟夺魁。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 26, 1, 0))
    await _seed_chat(db_session, user.id, at=dt.datetime(2026, 9, 25, 18, 0))

    snapshot = await UserActivityService(db_session).get_last_activity_snapshot(user.id)

    assert snapshot.last_activity_at == dt.datetime(2026, 9, 25, 18, 0), (
        f"max 应按绝对时刻选 chat 09-25T18:00Z（墙上钟 01:00 绝对只到 17:00Z）；"
        f"修前 naive 直比选了墙上钟：{snapshot.last_activity_at}"
    )


async def test_task_completion_utc_participates_unchanged(db_session: AsyncSession):
    """UTC 列（Task.completed_at）参与 max 的行为修前修后一致（同钟面不回归）。"""
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    from app.models.task import Task, TaskStatus, TaskType

    db_session.add(
        Task(
            user_id=user.id,
            title="t",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.COMPLETED,
            completed_at=dt.datetime(2026, 9, 25, 10, 0),  # UTC 存储（task_service._utcnow 写点）
        )
    )
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 26, 1, 0))
    await db_session.commit()

    snapshot = await UserActivityService(db_session).get_last_activity_snapshot(user.id)

    assert snapshot.last_task_completion_at == dt.datetime(2026, 9, 25, 10, 0)
    # focus 绝对 17:00Z > task 10:00Z → 换算后的 focus 胜出
    assert snapshot.last_activity_at == dt.datetime(2026, 9, 25, 17, 0)


async def test_utc_user_control_unchanged(db_session: AsyncSession):
    """UTC 用户控制组：墙上钟=UTC 钟同钟，赢家与返回值修前修后一致（钉住时区驱动面）。"""
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 25, 17, 0))
    await _seed_chat(db_session, user.id, at=dt.datetime(2026, 9, 25, 18, 0))

    snapshot = await UserActivityService(db_session).get_last_activity_snapshot(user.id)

    assert snapshot.last_activity_at == dt.datetime(2026, 9, 25, 18, 0)
