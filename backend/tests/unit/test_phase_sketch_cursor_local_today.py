"""V3-FIX-251（面 2/3：phase_sketch）红绿测：phase 排程游标宿主机钟切用户本地日。

定界（wt519 V3-FIX-233 卡同族余量）：``PhaseSketchService.materialize_sketch``
（phase_sketch_service.py:105）``cursor = date.today()`` 读宿主机本地日，
phase estimated_start/estimated_end 网格整体随宿主机钟漂移——UTC 宿主上
服务上海用户，phase 排程起点错一日。

修法：materialize_sketch 按 user_id 的 PushPreference.timezone 标量直查
（缺省 Asia/Shanghai），``cursor = local_date(utcnow(), tz)``。

冻结钟（沿双冻结钟族）：冻结宿主机 date.today()=09-25 + 冻结
NOW=09-25 20:00Z（上海本地今日=09-26、UTC 用户本地今日=09-25）：
- 上海（缺省）：phases[0].estimated_start = 09-26（修前 09-25，红）；
- UTC 用户（tz 通道控制组）：09-25（修前修后一致，恒绿）。
"""

from __future__ import annotations

import datetime as dt
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PushPreference, User
from app.orchestration.discovery_manager import DiscoveryManager
from app.orchestration.phase_sketch_service import PhaseSketchService
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.planning_artifact_service import PlanningArtifactService

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机钟（UTC 宿主此刻真实值）

    # 修前通道（宿主机 date.today()）在修后模块已无 date 导入，raising=False
    # 保持双冻结钟族口径：红测阶段冻结宿主机钟，修后该冻结为无害空转。
    monkeypatch.setattr("app.orchestration.phase_sketch_service.date", _FrozenDate, raising=False)
    monkeypatch.setattr("app.orchestration.phase_sketch_service.utcnow", lambda: NOW_LATE, raising=False)


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "wt531-tz-test"


async def _materialize_phases(db: AsyncSession, user_id) -> list:
    """沿 test_phase_d_full_flow 的既有链路：discovery → compass 审批 → sketch → materialize。"""
    fake_bus = FakeEventBus()
    discovery = DiscoveryManager(db, fake_bus)
    started = await discovery.start_discovery(
        user_id=user_id,
        initial_message="我想在1年内把机器学习真正学扎实，并完成职业转型。",
    )
    await discovery.process_discovery_turn(
        user_id=user_id,
        session_id=started["session_id"],
        user_message="我现在有一些 Python 基础，但数学一般，工作很忙，每天1小时，过去试过几次但坚持不好。",
    )
    finalized = await discovery.finalize_discovery(
        user_id=user_id,
        session_id=started["session_id"],
        plan_overrides={"name": "ML Growth"},
    )
    compass_review = await GlobalCompassManager(db, fake_bus).present_compass_for_review(
        plan_card_id=UUID(finalized["plan_card_id"]),
        user_id=user_id,
    )
    approved_compass = await GlobalCompassManager(db, fake_bus).user_approve_compass(
        artifact_id=UUID(compass_review["artifact_id"]),
        user_id=user_id,
        edits={"values": ["career", "mastery"]},
    )
    dossier = await PlanningArtifactService(db, fake_bus).get_artifact(UUID(finalized["dossier_artifact_id"]))
    sketch = await PhaseSketchService(db, fake_bus).generate_sketch(
        plan_card_id=UUID(finalized["plan_card_id"]),
        compass=approved_compass,
        dossier=dossier,
        user_id=user_id,
    )
    return await PhaseSketchService(db, fake_bus).materialize_sketch(
        plan_card_id=UUID(finalized["plan_card_id"]),
        sketch=sketch,
        user_id=user_id,
    )


@pytest.mark.asyncio
async def test_materialize_cursor_follows_market_default_local_day(
    db_session: AsyncSession, test_user, monkeypatch: pytest.MonkeyPatch
):
    """上海（缺省）用户：phase 起点按本地今日 09-26 起格；修前宿主机日 09-25 起格。"""
    _freeze_clocks(monkeypatch)
    phases = await _materialize_phases(db_session, test_user.id)

    assert phases, "materialize_sketch 应产出 phase 卡"
    assert (phases[0].metadata_ or {}).get("estimated_start") == "2026-09-26", (
        "phase 排程游标应按主市场本地今日（09-26）起格；"
        "修前 date.today()=宿主机日 09-25（行为变化点：排程网格平移一天，修目标本身）"
    )
    # timeline "1年" → 首 phase 8 周：estimated_end = 09-26 + 8*7 - 1 = 11-20
    assert (phases[0].metadata_ or {}).get("estimated_end") == "2026-11-20"
    assert (phases[1].metadata_ or {}).get("estimated_start") == "2026-11-21"


@pytest.mark.asyncio
async def test_materialize_cursor_utc_user_control(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """控制组：UTC 用户 phase 起点按本地今日 09-25（修前修后一致，恒绿）。"""
    _freeze_clocks(monkeypatch)
    user = User(
        username=f"wt531-{uuid4().hex[:8]}",
        email=f"wt531-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(PushPreference(user_id=user.id, timezone="UTC"))
    await db_session.commit()

    phases = await _materialize_phases(db_session, user.id)

    assert phases
    assert (phases[0].metadata_ or {}).get(
        "estimated_start"
    ) == "2026-09-25", "UTC 用户本地今日=09-25，phase 排程应从 09-25 起格（控制组，证明走用户时区通道而非统一平移）"
