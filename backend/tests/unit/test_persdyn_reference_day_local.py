"""V3-FIX-221（persdyn 余族）红绿测：reference_day 与日窗端点切用户本地日。

定界（wt507 211 同族，列级钟源沿 V3-FIX-37 实录）：Task.due_date 是客户端
给到的到期日（无时刻成分，墙上钟日界语义）。PersDynAttractorService 的
``reference_day = reference_time.date()``（:146 build_current_observation，
:166/:359 同源派生）是 UTC date，``_build_observation_for_day`` 里
``due_date < reference_day``（:414）把墙上语义 due_date 落在 UTC 日网格，
且日窗端点 ``_end_exclusive(reference_day)``/``_start_of_day`` 同源——
对 StudyRecord.created_at / Task.created_at / completed_at /
FocusSession.end_time / Scene.time_end / EpisodicMemory.occurred_at 这些
UTC 存储列切的是 UTC 日界，随上海 ±8h 漂移。

修法（全承 time_utils 教义）：reference_day 改 ``local_date(reference_time,
tz)``（tz 沿 207/211 先例——PushPreference.timezone 标量直查 + 缺省
Asia/Shanghai）；日窗端点对 UTC 存储列换算回 UTC 瞬间
``local_midnight_as_utc_naive(day, tz)``（两侧同钟，DB 预过滤与内存窗一
致）。辅助函数 tz 形参缺省 "UTC"——既有直接调用（含既有单测）行为逐位
不变。冻结钟：NOW_LATE = 2026-09-25 20:00 UTC（上海本地今日 = 09-26）：
- plan 任务 due 09-25（本地昨日）未完成：应计 overdue（修前 09-25<09-25
  为假漏计 → plan_adherence 误报满分）；
- 本地今日（上海 09-26 09:00 = 09-26 01:00Z）创建并完成的任务：应计入
  reference 日的完成率（修前日窗端点 09-26 00:00Z 把它整窗漏掉）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.persdyn_attractor_service import PersDynAttractorService

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


@pytest.mark.asyncio
async def test_overdue_plan_task_follows_user_local_reference_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海凌晨（本地 09-26 04:00）：本地昨日（09-25）到期的未完成 plan 任务必须计 overdue。

    修前 reference_day=09-25（UTC date）：``due 09-25 < 09-25`` 为假漏计
    → plan_adherence=1.0；修后 reference_day=本地 09-26 → 1 个 plan 任务
    全逾期 → plan_adherence=0.0。
    """
    monkeypatch.setattr("app.services.persdyn_attractor_service._utcnow", lambda: NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=uuid4(),
            title="wt513 plan due local-yesterday",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            created_at=dt.datetime(2026, 9, 22, 9, 0),
            due_date=dt.date(2026, 9, 25),
            estimated_minutes=30,
        )
    )
    await db_session.commit()

    observation = await PersDynAttractorService(db_session).build_current_observation(user_id=user.id, now=NOW_LATE)

    assert observation["plan_adherence"] == 0.0, (
        f"due 09-25（本地昨日）的未完成 plan 任务应计 overdue：修前 reference_day=UTC date 09-25 漏计："
        f"{observation}"
    )


@pytest.mark.asyncio
async def test_reference_day_window_keeps_local_today_completion(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """本地今日（上海 09-26 09:00 = 09-26 01:00Z）创建并完成的任务应计入 reference 日完成率。

    修前日窗端点 ``_end_exclusive(09-25 UTC)=09-26 00:00Z`` 把 09-26 01:00Z
    的创建/完成整窗漏掉 → tasks_7d 空 → completion_rate 落 0.5 缺省；
    修后端点换算本地日界（09-26 16:00Z）→ 1 任务 1 完成 → 1.0。
    """
    monkeypatch.setattr("app.services.persdyn_attractor_service._utcnow", lambda: NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add(
        Task(
            user_id=user.id,
            title="wt513 done local-today",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            created_at=dt.datetime(2026, 9, 26, 1, 0),  # 上海 09-26 09:00 = 本地今日上午
            completed_at=dt.datetime(2026, 9, 26, 2, 0),  # 上海 09-26 10:00 = 本地今日
            estimated_minutes=30,
        )
    )
    await db_session.commit()

    observation = await PersDynAttractorService(db_session).build_current_observation(user_id=user.id, now=NOW_LATE)

    assert observation["completion_rate"] == 1.0, (
        f"本地今日创建并完成的任务应计入 reference 日窗：修前 UTC 日窗端点 09-26 00:00Z 漏计 → "
        f"缺省 0.5：{observation}"
    )
