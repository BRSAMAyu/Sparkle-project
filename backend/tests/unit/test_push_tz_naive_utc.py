"""P1-B 推送链 naive-UTC 回归（daily-flow R2 · DF-9 下游）。

背景：带 PushPreference 行的用户在智能推送循环里 14/14 全崩——
PushService._check_frequency_cap 把 tz-aware 的 utc_start_of_day 绑定到
TIMESTAMP WITHOUT TIME ZONE 的 push_histories.created_at 上，asyncpg 抛
DataError（can't subtract offset-naive and offset-aware datetimes），被
process_all_users 捕获为 ERROR 后跳过该用户 → 实测账号 3 天 0 通知。
无偏好行用户在 _check_frequency_cap 入口提前 return，反而不触发——
这正是"通道有产出（2h 56 用户）但偏好行用户全灭"的分叉点。

项目规范：naive UTC 是 DB canonical 形态（app/core/time_utils），
本修复与 d9210935（memory 写入 naive-UTC 归一化）同款模式。

测试环境是 SQLite（其绑定处理器会静默吞掉 aware 偏移，无法天然复现），
因此给会话 execute 挂"PG 严格绑定守卫"：任何 aware datetime 绑定参数
一律抛 asyncpg 真实 DataError（生产同签名），忠实复现 PG 上的崩溃路径。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from asyncpg.exceptions import DataError as AsyncpgDataError
from sqlalchemy import select

from app.models.notification import Notification, PushHistory
from app.models.user import PushPreference, User
from app.services.personalization.profiles import PushPolicyProfile
from app.services.push_service import PushService

TEST_TZ = "Asia/Shanghai"


# ---------------------------------------------------------------------------
# 夹具与工具
# ---------------------------------------------------------------------------


async def _make_user(db_session, *, with_preference: bool) -> User:
    user = User(
        username=f"push_tz_{uuid4().hex[:8]}",
        email=f"push_tz_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()  # 生成 user.id
    if with_preference:
        # 复刻生产分叉点：push_preferences 表里有行的用户
        user.push_preference = PushPreference(user_id=user.id)
        db_session.add(user.push_preference)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def install_pg_strict_execute(db_session, sink: list | None = None) -> None:
    """PG 严格绑定守卫：aware datetime 绑定参数 → 生产同签名 DataError。

    生产栈（asyncpg + TIMESTAMP WITHOUT TIME ZONE）对 aware 绑定参数抛
    DataError；SQLite 不会。该守卫把测试环境拉到 PG 的严格度上。
    """
    original_execute = db_session.execute

    async def strict_execute(query: Any, *args: Any, **kwargs: Any):
        try:
            compiled = query.compile()
            params = compiled.params or {}
        except Exception:
            params = {}
        for value in params.values():
            if isinstance(value, datetime):
                if sink is not None:
                    sink.append(value)
                if value.tzinfo is not None:
                    raise AsyncpgDataError(
                        f"invalid input for query argument: {value!r} "
                        "(can't subtract offset-naive and offset-aware datetimes)"
                    )
        return await original_execute(query, *args, **kwargs)

    db_session.execute = strict_execute  # type: ignore[method-assign]


def _shanghai_midnight_utc_window() -> tuple[datetime, datetime]:
    """调用前后各取一次"今日上海零点"的 UTC 形态，容忍跨零点竞态。"""
    def _one() -> datetime:
        now_utc = datetime.now(UTC)
        local_now = now_utc.astimezone(ZoneInfo(TEST_TZ))
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(UTC).replace(tzinfo=None)

    return _one(), _one()


# ---------------------------------------------------------------------------
# 红线 1：频控查询必须绑定 naive UTC（生产 14/14 崩溃点）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_frequency_cap_binds_naive_utc_start_of_day(db_session, monkeypatch):
    """_check_frequency_cap 的日上限查询必须用 naive UTC 参数绑定 created_at。

    修复前：绑定 tz-aware utc_start_of_day → asyncpg DataError（生产 14/14）。
    """
    user = await _make_user(db_session, with_preference=True)
    assert user.push_preference is not None
    assert user.push_preference.last_push_time is None

    policy = PushPolicyProfile(
        daily_cap=3,
        min_interval_minutes=120,
        pressure_tolerance=0.5,
        memory_urgency_threshold=0.5,
        curiosity_frequency="daily",
        silent_during_focus=False,
        active_hours=[],
        timezone=TEST_TZ,
        preference_version=1,
    )

    sink: list[datetime] = []
    install_pg_strict_execute(db_session, sink)

    # 不抛 DataError 即修复；且绑定参数必须是 naive UTC、语义等于"今日上海零点"
    capped = await PushService(db_session)._check_frequency_cap(user, policy)

    assert capped is False, "无当日推送记录时不应触发频控"
    assert len(sink) == 1, "日上限查询应恰好绑定一个 datetime 参数"
    bound = sink[0]
    assert bound.tzinfo is None, (
        "绑定到 TIMESTAMP WITHOUT TIME ZONE 列的参数必须是 naive UTC "
        f"（canonical 形态），实际为 aware: {bound!r}"
    )
    expected_before, expected_after = _shanghai_midnight_utc_window()
    assert bound in (expected_before, expected_after), (
        f"naive 参数语义应为今日({TEST_TZ})零点换算的 UTC：{bound!r} "
        f"不在 [{expected_before!r}, {expected_after!r}] 中"
    )


# ---------------------------------------------------------------------------
# 红线 2：修复后频控语义不受影响——只数"今日"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_frequency_cap_counts_only_today_pushes(db_session):
    """修复后的日上限查询：数今日（上海时区）推送数，昨日记录不计入。"""
    user = await _make_user(db_session, with_preference=True)

    start_of_today_utc, _ = _shanghai_midnight_utc_window()
    today_row = start_of_today_utc + timedelta(minutes=1)
    yesterday_row = start_of_today_utc - timedelta(minutes=1)

    for i, created_at in enumerate([today_row] * 3 + [yesterday_row]):
        history = PushHistory(
            user_id=user.id,
            trigger_type="sprint",
            content_hash=f"hash-{i}",
            status="sent",
        )
        history.created_at = created_at
        db_session.add(history)
    await db_session.commit()

    policy = PushPolicyProfile(
        daily_cap=3,
        min_interval_minutes=120,
        pressure_tolerance=0.5,
        memory_urgency_threshold=0.5,
        curiosity_frequency="daily",
        silent_during_focus=False,
        active_hours=[],
        timezone=TEST_TZ,
        preference_version=1,
    )
    service = PushService(db_session)

    assert await service._check_frequency_cap(user, policy) is True, "今日 3 条应触顶（昨日 1 条不计）"

    policy.daily_cap = 4
    assert await service._check_frequency_cap(user, policy) is False, "上限调到 4 后今日 3 条不应触顶"


# ---------------------------------------------------------------------------
# 红线 3：带偏好行用户的完整推送流程不崩且产出通知（14/14 复现场景）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_flow_user_with_preference_row_produces_notification(
    db_session, monkeypatch
):
    """复现 DF-9/P1-B 的 14/14 场景：push_preferences 有行的用户走完整
    智能推送循环（真实 _check_frequency_cap），必须不崩且产出通知。

    修复前：频控查询抛 DataError → process_all_users 捕获记 errors →
    该用户被跳过（生产日志 'Error processing push for user' ×14）。
    """
    user = await _make_user(db_session, with_preference=True)

    async def _true(self, *args, **kwargs):
        return True

    async def _false(self, *args, **kwargs):
        return False

    async def _content(self, user, explicit_prefs, trigger_type, trigger_data):
        return {"title": "Sparkle 提醒", "body": "该复习今天的冲刺任务了"}

    # 与 DF-9 测试（test_push_default_coverage）同款打点，唯独 _check_frequency_cap
    # 保持真实实现——它正是生产崩溃点
    monkeypatch.setattr(PushService, "_is_active_time", _true)
    monkeypatch.setattr(PushService, "_check_schedule_and_quiet_hours", _false)
    monkeypatch.setattr(PushService, "_generate_push_content", _content)
    monkeypatch.setattr(PushService, "_aurora_push_opt_in_enabled", _true)

    from app.services.push_strategies import (
        CuriosityStrategy,
        EmptyCapsuleStrategy,
        InactivityStrategy,
        MemoryStrategy,
        SprintStrategy,
    )

    async def _should_trigger(self, user_obj, policy):
        return user_obj.id == user.id

    async def _no_trigger(self, user_obj, policy):
        return False

    monkeypatch.setattr(InactivityStrategy, "should_trigger", _should_trigger)
    monkeypatch.setattr(SprintStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(MemoryStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(EmptyCapsuleStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(CuriosityStrategy, "should_trigger", _no_trigger)

    install_pg_strict_execute(db_session)

    service = PushService(db_session)
    summary = await service.process_all_users()

    assert summary["errors"] == 0, (
        f"带偏好行用户的推送评估不允许出错（生产 14/14 崩溃签名）：{summary}"
    )
    assert summary["triggered"] >= 1 and summary["sent"] >= 1

    notifications = (
        (await db_session.execute(select(Notification).where(Notification.user_id == user.id)))
        .scalars()
        .all()
    )
    assert notifications, "触发推送必须产出站内通知（实测账号 3 天 0 通知的回归）"

    assert user.push_preference is not None
    last_push_time = user.push_preference.last_push_time
    assert last_push_time is not None, "推送后必须回写 last_push_time（频控 cooldown 依赖）"
    assert last_push_time.tzinfo is None, (
        "last_push_time 写入必须是 naive UTC（canonical），aware 值在 PG 上"
        f"会在 flush 时抛同类 DataError：{last_push_time!r}"
    )

    histories = (
        (await db_session.execute(select(PushHistory).where(PushHistory.user_id == user.id)))
        .scalars()
        .all()
    )
    assert histories, "推送必须落 push_histories（频控数据源）"


# ---------------------------------------------------------------------------
# 红线 4：无偏好行用户路径不受影响（对照组，生产通道有产出的那 56 用户）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_flow_user_without_preference_row_still_works(db_session, monkeypatch):
    """对照组：无偏好行用户（走合成默认路径）的推送流程保持可用。"""
    user = await _make_user(db_session, with_preference=False)
    assert user.push_preference is None

    async def _true(self, *args, **kwargs):
        return True

    async def _false(self, *args, **kwargs):
        return False

    async def _content(self, user_obj, explicit_prefs, trigger_type, trigger_data):
        return {"title": "Sparkle 提醒", "body": "该复习今天的冲刺任务了"}

    monkeypatch.setattr(PushService, "_is_active_time", _true)
    monkeypatch.setattr(PushService, "_check_schedule_and_quiet_hours", _false)
    monkeypatch.setattr(PushService, "_generate_push_content", _content)
    monkeypatch.setattr(PushService, "_aurora_push_opt_in_enabled", _true)

    from app.services.push_strategies import (
        CuriosityStrategy,
        EmptyCapsuleStrategy,
        InactivityStrategy,
        MemoryStrategy,
        SprintStrategy,
    )

    async def _should_trigger(self, user_obj, policy):
        return user_obj.id == user.id

    async def _no_trigger(self, user_obj, policy):
        return False

    monkeypatch.setattr(InactivityStrategy, "should_trigger", _should_trigger)
    monkeypatch.setattr(SprintStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(MemoryStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(EmptyCapsuleStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(CuriosityStrategy, "should_trigger", _no_trigger)

    install_pg_strict_execute(db_session)

    summary = await PushService(db_session).process_all_users()

    assert summary["errors"] == 0
    assert summary["sent"] >= 1
    notifications = (
        (await db_session.execute(select(Notification).where(Notification.user_id == user.id)))
        .scalars()
        .all()
    )
    assert notifications
