"""V3-FIX-251（面 3/3：aurora）红绿测：兜底合成钟 +8h 硬编码切 push_preference tz。

定界（wt519 V3-FIX-233 卡同族余量）：``AuroraRuntimeV1Service``
（aurora/runtime_v1/service.py:67/:1281）``CHINA_TIMEZONE =
timezone(timedelta(hours=8))`` 硬编码兜底钟——请求无时间戳候选时
``_request_timestamp_in_china_time`` 合成 ``datetime.now(+8h)``，
``_is_sleep_guard_window`` 再以 +8h 墙钟读「小时」判睡眠窗（23-06）：
非 +8 用户在宿主无关的假墙上被误激活/漏激活睡眠守卫。

修法（口径）：兜底合成钟改 push_preference tz 解析（缺省 Asia/Shanghai），
睡眠窗以同 tz 本地墙钟读数。客户端时间戳协议口径不变（naive 仍按 +8h
墙钟挂 tz，aware/epoch 照常换算）；LLM 请求路径协议零改动。

冻结钟（双冻结钟族单冻结即成——兜底钟直接消费 now(tz)）：冻结当前瞬间
=09-25 20:00Z：+8h 墙上=09-26 04:00（窗内，守卫激活）；UTC 墙上=20:00
（窗外）：
- UTC 用户（db tz 通道）：修前 +8h 视角 04:00 误激活 sleep_guard → 红；
  修后本地 20:00 不激活 → 绿；
- 缺省（无偏好 → Asia/Shanghai，控制组）：04:00 窗内激活，修前修后一致
  （恒绿，证明走用户时区通道而非统一偏移）。
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.dashboard import DashboardReadout
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.user import PushPreference, User

FROZEN_INSTANT = dt.datetime(2026, 9, 25, 20, 0, tzinfo=dt.UTC)


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结服务模块 datetime：now(tz) 返回冻结瞬间在 tz 的墙上表达。"""

    class _FrozenDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            if tz is not None:
                return FROZEN_INSTANT.astimezone(tz)
            return FROZEN_INSTANT.replace(tzinfo=None)

    monkeypatch.setattr("app.aurora.runtime_v1.service.datetime", _FrozenDatetime)


class _CapturingDecisionLoop:
    def __init__(self) -> None:
        self.readouts: list[DashboardReadout] = []

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        self.readouts.append(readout)
        return AuroraDecision(action="wait")


class _StubSelfModelService:
    async def get_readout_summary(self, **kwargs: Any) -> dict[str, Any]:
        return {}


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


async def _plan_turn(db: AsyncSession, user: User) -> dict[str, Any]:
    decision_loop = _CapturingDecisionLoop()
    service = AuroraRuntimeV1Service(
        decision_loop=decision_loop,
        self_model_service=_StubSelfModelService(),
    )
    await service.plan_turn(
        active_db=db,
        user_id=str(user.id),
        surface="aurora_planning",
        conversation_id="conv-sleep-tz",
        request_id="req-sleep-tz",
        user_message="我还想再聊一会儿计划。",
        # 无任何时间戳候选：走兜底合成钟（本卡修面）。
        request_extra_context={"sprint_policy": {"sleep_guard_hint": "晚间不追加新难点。"}},
        conversation_context={},
        user_context_payload={},
    )
    return decision_loop.readouts[0].request_extra_context


@pytest.mark.asyncio
async def test_plan_turn_fallback_clock_follows_user_timezone(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 用户本地 20:00 非睡眠窗：修前 +8h 视角 04:00 误激活 sleep_guard。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")

    context = await _plan_turn(db_session, user)

    assert "sleep_guard_active" not in context, (
        "UTC 用户兜底合成钟应按本地墙钟 20:00 判窗（非 23-06 睡眠窗，不激活守卫）；"
        "修前 +8h 硬编码把同一瞬间切到 09-26 04:00 误激活"
    )


@pytest.mark.asyncio
async def test_plan_turn_fallback_clock_default_shanghai_control(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组：无偏好（缺省 Asia/Shanghai）本地 04:00 在窗内，守卫激活（修前修后一致）。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone=None)

    context = await _plan_turn(db_session, user)

    assert context.get("sleep_guard_active") is True, (
        "Asia/Shanghai（缺省）用户同一瞬间本地 09-26 04:00 在睡眠窗内，守卫应激活"
        "（控制组，证明走用户时区通道而非统一偏移）"
    )
    assert context.get("sleep_guard_hint") == "晚间不追加新难点。"
