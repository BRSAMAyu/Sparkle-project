"""V3-FIX-250（写侧面 2）红绿测：replan 端点 today 比对/派生切用户本地日。

定界（wt519 V3-FIX-233 同族写侧/比对侧余量，250 登记面 2）：
``replan_plan`` 的 ``today = date.today()``（api/v1/plans.py:1352）是宿
主机本地日，流入三处：

1. ``explicit_target <= today`` 422 拒绝判定（上海凌晨显式重锚「本地今
   日」被误放行）；
2. ``previous_target >= today`` 幂等判定（上海凌晨「昨天到期」计划被误
   判 target_date_still_valid——晨间偏一日的续期漏窗）；
3. ``_derive_replan_target(plan, tasks, today)`` 新终点派生（写侧：新
   target_date 落库值整体偏移）。

修法：沿 233 同款——端点有 db 通道，``today`` 切
``_user_local_today(db, user_id)``（PushPreference.timezone 标量直查，
缺省 Asia/Shanghai）。冻结钟（沿双冻结钟族）：冻结 NOW=09-25 20:00Z
（上海本地今日=09-26、UTC 用户本地今日=09-25）+ 冻结宿主机
date.today()=09-25（UTC 宿主钟）。**写侧语义差异如实标注**：修前上海
用例新终点=09-28（宿主机日 09-25 + 跨度 3），修后=09-29（本地今日
09-26 + 跨度 3）——落库值平移一天，属修目标本身，非回归。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.plans import PlanReplanRequest, replan_plan
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00
SPAN_DAYS = 3  # 未完成任务 day:1..day:3 → 未完成日跨度 3 天


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.plans.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机钟（UTC 宿主此刻真实值）

    monkeypatch.setattr("app.api.v1.plans.date", _FrozenDate)


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt526-{uuid4().hex[:8]}",
        email=f"wt526-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_expired_plan(db: AsyncSession, user: User, *, target: dt.date) -> Plan:
    plan = Plan(
        user_id=user.id,
        name=f"wt526-replan-{uuid4().hex[:6]}",
        type=PlanType.SPRINT,
        target_date=target,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    for day in range(1, SPAN_DAYS + 1):
        db.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"wt526 day-{day}",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                order_index=day,
                tags=[f"day:{day}"],
                estimated_minutes=20,
            )
        )
    await db.commit()
    return plan


@pytest.mark.asyncio
async def test_replan_target_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海用户凌晨 replan 过期计划（target 09-24）：新终点=本地今日 09-26+3=09-29。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    plan = await _seed_expired_plan(db_session, user, target=dt.date(2026, 9, 24))

    resp = await replan_plan(plan_id=plan.id, request_body=None, current_user=user, db=db_session)

    assert resp["replanned"] is True
    assert resp["new_target_date"] == "2026-09-29", (
        "replan 新终点应按用户本地日（09-26）+未完成跨度 3 = 09-29 落库；"
        "修前 date.today()=宿主机日 09-25，写 09-28（写侧语义差异：落库终点平移一天，修目标本身）"
    )
    assert resp["days_shifted"] == 5  # 09-24 → 09-29


@pytest.mark.asyncio
async def test_replan_target_utc_user_keeps_utc_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户（tz 通道控制组）：本地今日=09-25，新终点=09-25+3=09-28。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    plan = await _seed_expired_plan(db_session, user, target=dt.date(2026, 9, 24))

    resp = await replan_plan(plan_id=plan.id, request_body=None, current_user=user, db=db_session)

    assert resp["replanned"] is True
    assert (
        resp["new_target_date"] == "2026-09-28"
    ), "UTC 用户本地今日仍 09-25，新终点应=09-28（控制组，证明走用户时区通道而非统一 +8h）"


@pytest.mark.asyncio
async def test_replan_idempotency_judged_on_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海用户凌晨：target=09-25（==宿主机日、<本地今日）应判过期并重锚，非 no-op。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    plan = await _seed_expired_plan(db_session, user, target=dt.date(2026, 9, 25))

    resp = await replan_plan(plan_id=plan.id, request_body=None, current_user=user, db=db_session)

    assert resp["replanned"] is True, (
        "上海用户本地今日已 09-26，target 09-25 已过期：previous_target>=today 应按用户本地日"
        "判定为假并重锚（修前 09-25>=09-25 误判 target_date_still_valid no-op——晨间偏一日续期漏窗）"
    )
    assert resp["new_target_date"] == "2026-09-29"


@pytest.mark.asyncio
async def test_replan_explicit_target_rejected_on_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海用户凌晨显式重锚「本地今日 09-26」：应 422（非严格未来），不得误放行。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    plan = await _seed_expired_plan(db_session, user, target=dt.date(2026, 9, 24))

    with pytest.raises(HTTPException) as exc_info:
        await replan_plan(
            plan_id=plan.id,
            request_body=PlanReplanRequest(target_date=dt.date(2026, 9, 26), note=""),
            current_user=user,
            db=db_session,
        )

    assert exc_info.value.detail == "PLAN_TARGET_DATE_MUST_BE_FUTURE", (
        "上海用户本地今日已 09-26：explicit_target=09-26 应被 422 拒绝"
        "（修前 09-26>宿主机日 09-25 误放行，把「今天」写成本计划终点）"
    )
