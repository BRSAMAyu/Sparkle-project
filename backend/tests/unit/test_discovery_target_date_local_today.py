"""V3-FIX-251（面 1/3：discovery）红绿测：target_date 网格 × 宿主机钟切用户本地日。

定界（wt519 V3-FIX-233 卡同族余量）：``DiscoveryManager._build_plan_create``
（discovery_manager.py:381）SPRINT/GROWTH 推断
``timeline <= (date.today()+timedelta(days=120))`` 与
``_extract_timeline_date``（:480-486）``date.today()+days/weeks/months*30/years``
派生的用户可见 target_date 起点网格均读宿主机本地日——UTC 宿主上服务
上海用户，相对时长（"30天"）的 target_date 落错一日网格。

修法：``finalize_discovery`` 按 user_id 的 PushPreference.timezone 标量直查
（缺省 Asia/Shanghai）换算本地日显式传 today；``_build_plan_create`` /
``_extract_timeline_date`` 增 today 形参，未传时回落主市场 Asia/Shanghai
本地日（docstring 注明口径）。

冻结钟（沿双冻结钟族）：冻结宿主机 date.today()=09-25（UTC 宿主此刻
真实值）+ 冻结 NOW=09-25 20:00Z（上海本地今日=09-26、UTC 用户本地
今日=09-25）：
- 上海（缺省）：timeline "30天" → target 10-26（修前 10-25，红）；
  ISO "2027-01-24" 边界 → SPRINT（修前宿主机 cutoff 2027-01-23 判 GROWTH，红）；
- UTC 用户（tz 通道控制组）：timeline "30天" → target 10-25（修前修后一致，
  恒绿——证明走用户时区通道而非统一平移）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanType
from app.models.user import PushPreference, User
from app.orchestration.discovery_manager import DiscoveryManager, DiscoveryState

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机钟（UTC 宿主此刻真实值）

    monkeypatch.setattr("app.orchestration.discovery_manager.date", _FrozenDate)
    monkeypatch.setattr("app.orchestration.discovery_manager.utcnow", lambda: NOW_LATE, raising=False)


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "wt531-tz-test"


@pytest.mark.asyncio
async def test_build_plan_create_relative_days_grid_follows_market_default_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """timeline "30天"：主市场本地今日 09-26 + 30 = target 10-26；修前宿主机日写 10-25。"""
    _freeze_clocks(monkeypatch)
    manager = DiscoveryManager(db_session, FakeEventBus())
    state = DiscoveryState(goal_statement="在30天内学好机器学习", timeline="30天")

    plan_in = manager._build_plan_create(state, {})

    assert plan_in.target_date == dt.date(2026, 10, 26), (
        "相对时长 target_date 应按主市场本地今日（09-26）+30=10-26 起格；"
        "修前 date.today()=宿主机日 09-25 写 10-25（行为变化点：落库值平移一天，修目标本身）"
    )
    assert plan_in.type == PlanType.SPRINT


@pytest.mark.asyncio
async def test_build_plan_create_iso_boundary_inference_follows_market_default_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """ISO 边界 2027-01-24：上海本地 cutoff（09-26+120=2027-01-24）→ SPRINT；修前宿主机 cutoff 01-23 判 GROWTH。"""
    _freeze_clocks(monkeypatch)
    manager = DiscoveryManager(db_session, FakeEventBus())
    state = DiscoveryState(goal_statement="在2027-01-24前学好", timeline="2027-01-24")

    plan_in = manager._build_plan_create(state, {})

    assert plan_in.type == PlanType.SPRINT, (
        "SPRINT/GROWTH 推断 cutoff 应按主市场本地今日 09-26+120=2027-01-24；"
        "修前宿主机日 09-25+120=2027-01-23 把边界日误判 GROWTH"
    )
    assert plan_in.target_date == dt.date(2027, 1, 24)


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
async def test_finalize_discovery_utc_user_target_date_control(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组：UTC 用户 timeline "30天" → 本地今日 09-25+30 = target 10-25（修前修后一致）。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    manager = DiscoveryManager(db_session, FakeEventBus())
    started = await manager.start_discovery(
        user_id=user.id,
        initial_message="我想在30天内学好机器学习，为了完成职业转型。",
    )
    await manager.process_discovery_turn(
        user_id=user.id,
        session_id=started["session_id"],
        user_message="我现在在职，基础还可以，但时间有限，每天1小时，之前试过自学但总是坚持不下来。",
    )
    finalized = await manager.finalize_discovery(
        user_id=user.id,
        session_id=started["session_id"],
        plan_overrides={"name": "UTC Control"},
    )
    plan = await db_session.get(Plan, finalized["plan_id"])

    assert plan is not None
    assert plan.target_date == dt.date(2026, 10, 25), (
        "UTC 用户本地今日=09-25，timeline 30天 应写 target=10-25" "（控制组，证明走用户时区通道而非统一平移）"
    )
    assert plan.type == PlanType.SPRINT
