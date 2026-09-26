"""V3-FIX-243 红绿测：checkpoint 触发日游标 +8h 硬编码切 push_preference tz。

定界（wt519 V3-FIX-233 卡同文件余量，233 只收 _lagging_tasks/_plan_total_days，
触发游标需 scan 循环 per-user tz 通道另立）：``plan_day_number``
（checkpoint_nudge_service.py:1220）的
``local_today = today or (datetime.now(UTC)+timedelta(hours=8)).date()`` 与
``local_start = (created_at.replace(tzinfo=UTC)+timedelta(hours=8)).date()``
均按 +8h 硬编码切——``scan_and_send_checkpoint_nudges`` 的触发判等
（``checkpoint["day"] != today_day``）随之错日：非 +8 用户 checkpoint
提前/错后一整天触发。

修法：scan 循环内按 plan.user_id 的 PushPreference.timezone 标量直查
（缺省 Asia/Shanghai），``today=local_date(utcnow(), tz)`` 传入
``plan_day_number``；created_at 起始日按同 tz ``local_date`` 换算。
冻结钟（沿 233 双冻结钟族）：冻结 NOW=09-25 20:00Z + created_at=09-18
15:00Z（+8h 墙上 09-18 23:00 不跨日，UTC 侧同日）——

- 上海日游标 = (09-26 − 09-18)+1 = **9**（与旧 +8h 行为逐位一致）；
- UTC 用户日游标 = (09-25 − 09-18)+1 = **8**（修前 +8h 算 9）。

checkpoint 落 day 8：UTC 用户修前不触发（游标 9≠8）→ 红；修后当日触发。
checkpoint 落 day 9 的上海缺省用户为控制组（修前修后一致，证明走用户
时区通道而非统一偏移）。
"""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.plan import Plan, PlanType
from app.models.user import PushPreference, User
from app.services.checkpoint_nudge_service import plan_day_number, scan_and_send_checkpoint_nudges

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；+8h 墙上日 = 2026-09-26
CREATED_MID = dt.datetime(2026, 9, 18, 15, 0)  # naive UTC；+8h 墙上 09-18 23:00（不跨日）


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结模块 datetime（修前 +8h 面走 datetime.now(UTC)）与 utcnow（修后通道）。"""
    real_utc = dt.UTC

    class _FrozenDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return NOW_LATE.replace(tzinfo=tz if tz is not None else None)

    monkeypatch.setattr("app.services.checkpoint_nudge_service.datetime", _FrozenDatetime)
    monkeypatch.setattr("app.services.checkpoint_nudge_service.utcnow", lambda: NOW_LATE, raising=False)
    monkeypatch.setattr("app.services.checkpoint_nudge_service.UTC", real_utc, raising=False)


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


def test_plan_day_number_follows_resolved_timezone(monkeypatch: pytest.MonkeyPatch):
    """UTC 用户：游标 (09-25 − 09-18)+1 = 8；上海缺省 9（与旧 +8h 行为一致的控制组）。"""
    _freeze_clocks(monkeypatch)
    plan = SimpleNamespace(created_at=CREATED_MID)

    assert plan_day_number(plan, timezone_name="UTC") == 8, (
        "UTC 用户 checkpoint 日游标应按本地日 (09-25 − 09-18)+1=8；" "修前 +8h 硬编码把 today 切到 09-26 算 9"
    )
    assert (
        plan_day_number(plan, timezone_name="Asia/Shanghai") == 9
    ), "Asia/Shanghai 用户日游标 (09-26 − 09-18)+1=9（与旧 +8h 行为一致的控制组）"


def _plan_for(user_id, *, checkpoint_day: int) -> Plan:
    return Plan(
        id=uuid4(),
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        description=json.dumps(
            {"strategy": {"checkpoints": [{"day": checkpoint_day, "description": "Day N 晚：做20题自测"}]}},
            ensure_ascii=False,
        ),
        subject="计算机网络",
        is_active=True,
        created_at=CREATED_MID,
    )


async def _seed_user(db: AsyncSession, *, timezone: str | None) -> User:
    user = User(
        username=f"wt531-{uuid4().hex[:8]}",
        email=f"wt531-{uuid4().hex[:8]}@test.local",
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
async def test_scan_triggers_on_utc_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户 checkpoint 落 day 8（本地今日 09-25）：修前 +8h 游标 9 错过当日触发。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    session = ChatSession(id=uuid4(), user_id=user.id, is_active=True, last_message_at=NOW_LATE)
    plan = _plan_for(user.id, checkpoint_day=8)
    db_session.add_all([session, plan])
    await db_session.commit()

    redis = _FakeRedis()
    result = await scan_and_send_checkpoint_nudges(db=db_session, redis=redis, today=None)

    assert result["triggered"] == 1, (
        "UTC 用户本地今日=09-25，checkpoint day 8 应当日触发；" "修前 +8h 硬编码把游标切到 09-26（day 9）错过触发"
    )


@pytest.mark.asyncio
async def test_scan_shanghai_default_user_control_matches_legacy_plus8(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组：无偏好（缺省 Asia/Shanghai）用户 checkpoint day 9，修前修后一致触发。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone=None)
    session = ChatSession(id=uuid4(), user_id=user.id, is_active=True, last_message_at=NOW_LATE)
    plan = _plan_for(user.id, checkpoint_day=9)
    db_session.add_all([session, plan])
    await db_session.commit()

    redis = _FakeRedis()
    result = await scan_and_send_checkpoint_nudges(db=db_session, redis=redis, today=None)

    assert result["triggered"] == 1, (
        "Asia/Shanghai（缺省）用户日游标 (09-26 − 09-18)+1=9，checkpoint day 9 触发"
        "（控制组，证明走用户时区通道而非统一偏移）"
    )
