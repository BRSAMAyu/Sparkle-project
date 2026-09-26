"""V3-FIX-221（daily_task 余族）红绿测：select_tasks 的「今日」切用户本地日。

定界（wt507 211 同族，列级钟源沿 V3-FIX-37 实录）：``select_tasks`` 的
``today = date.today()``（daily_task_selection_service.py:117）是宿主机
本地日——既非 UTC 亦非用户时区。它流入：
- ``_is_today_relevant``（:40-43）：``completed_at.date()==today``（UTC
  存储列取 UTC date）与 ``due_date<=today``（墙上钟 due_date）；
- ``include_completed_today`` 过滤（:152）：同款 ``completed_at.date()``；
- ``score_candidate``（:208 缺省同为 ``date.today()``）→ ``_deadline_score``
  的 days_to_due（209 同族派生量）。

修法：today 改 ``local_date(utcnow(), tz)``（tz 沿 207/211 先例——
PushPreference.timezone 标量直查 + valid_timezone_name 缺省
Asia/Shanghai）；completed_at/created_at 这类 UTC 存储列比本地日一律先
``local_date(value, tz)`` 换算（score_candidate 无 db 通道，缺省回落主
市场本地日，去宿主机钟依赖）。冻结钟（沿双冻结钟族）：冻结 NOW=09-25
20:00Z（上海本地今日=09-26）+ 冻结宿主机 date.today()=09-25：
- due 09-26（本地今日）的待办必须 today-relevant，修前 09-26<=09-25 为假
  被排除（漏）；days_to_due 应为 0（修前 1）；
- completed_at=09-25 02:00Z（上海 09-25 10:00=本地昨日）的已完成任务不应
  混进「今日」，修前 UTC date 09-25==宿主机日 09-25 被误留（多）；
- due 09-25（本地昨日）的待办双版都 relevant（控制组）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.daily_task_selection_service import DailyTaskSelectionService

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt513-{uuid4().hex[:8]}",
        email=f"wt513-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结 UTC 钟与宿主机 date.today()（沿 211 冻结宿主机日族）。

    utcnow 在修前模块里尚不存在（red 跑 date.today() 面），raising=False
    允许补种；修后模块名由 time_utils 导入，补丁照常覆盖。
    """
    monkeypatch.setattr("app.services.daily_task_selection_service.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    monkeypatch.setattr("app.services.daily_task_selection_service.date", _FrozenDate)


@pytest.mark.asyncio
async def test_today_relevant_and_completed_filter_follow_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海凌晨（本地 09-26 04:00）：today 面按用户本地日 09-26 切。

    - due 09-26（本地今日）待办必须入选（修前被 09-26<=09-25 排除）；
    - 本地昨日（上海 09-25 10:00）完成的任务不得以「今日已完成」混入
      （修前 UTC date==宿主机日 双双 09-25 被误留）；
    - due 09-25（本地昨日）待办仍 relevant（控制组）。
    """
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add_all(
        [
            Task(
                user_id=user.id,
                title="wt513 due local-today",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=dt.date(2026, 9, 26),
                estimated_minutes=20,
            ),
            Task(
                user_id=user.id,
                title="wt513 due local-yesterday control",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=dt.date(2026, 9, 25),
                estimated_minutes=20,
            ),
            Task(
                user_id=user.id,
                title="wt513 completed local-yesterday",
                type=TaskType.LEARNING,
                status=TaskStatus.COMPLETED,
                completed_at=dt.datetime(2026, 9, 25, 2, 0),  # 上海 09-25 10:00 = 本地昨日
                estimated_minutes=20,
            ),
        ]
    )
    await db_session.commit()

    selections = await DailyTaskSelectionService(db_session).select_tasks(
        user_id=user.id,
        limit=10,
        include_completed_today=True,
        only_today_relevant=True,
    )

    titles = [item.task.title for item in selections]
    assert (
        "wt513 due local-today" in titles
    ), f"本地今日（09-26）到期的待办必须 today-relevant；修前 today=宿主机日 09-25 把它排除：{titles}"
    assert "wt513 completed local-yesterday" not in titles, (
        f"本地昨日（上海 09-25 10:00）完成的任务不得按「今日已完成」混入；"
        f"修前 completed_at UTC date==宿主机日 09-25 被误留：{titles}"
    )
    assert "wt513 due local-yesterday control" in titles, f"本地昨日到期待办仍须 relevant（控制组）：{titles}"


@pytest.mark.asyncio
async def test_days_to_due_signal_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """days_to_due（209 同族派生量）：本地今日（09-26）到期的任务应为 0 而非 1。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add(
        Task(
            user_id=user.id,
            title="wt513 due local-today",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            due_date=dt.date(2026, 9, 26),
            estimated_minutes=20,
        )
    )
    await db_session.commit()

    selections = await DailyTaskSelectionService(db_session).select_tasks(user_id=user.id, limit=5)

    target = next(item for item in selections if item.task.title == "wt513 due local-today")
    assert target.signals["days_to_due"] == 0, (
        f"本地今日到期 days_to_due 应为 0；修前 today=宿主机日 09-25 算出 1（deadline 文案随之失真）："
        f"{target.signals}"
    )
    assert (
        target.reason is not None and "due today" in target.reason
    ), f"days==0 应给「due today」理由（修前 days==1 无 deadline 理由）：{target.reason}"
