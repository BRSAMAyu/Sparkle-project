"""V3-FIX-293 + V3-FIX-294：连胜引擎用户本地日界 + 冻结续签 max/longest 同步 红绿测.

背景（wt573 定位 / wt576 二轮独立复现，双场景均真实引擎 + 冻结模块级 ``_utcnow``
+ sqlite 内存库；台账行 grep "V3-FIX-293"/"V3-FIX-294"）：

F2 / V3-FIX-293（P2）——连胜日界用 UTC 日且丢弃调用方传入的本地 activity_date：
- ``achievement_engine._update_streak_stats`` 原 :2034 ``today = _utcnow().date()``，
  而唯一显式调用方 ``api/v1/accountability.py`` 打卡端点按用户本地日去重后把
  ``activity_date=today_start.date()``（用户本地打卡日）透传进 kwargs——引擎全函数
  不读，静默丢弃；
- 场景 A（误烧冻结卡）：上海用户本地连续两日打卡（周日 00:30 / 周一 23:40 本地），
  UTC 日差=2 → 冻结卡 1→0 误烧 + 用户没缺的本地日被写成假 FROZEN 行落库；
- 场景 B（白嫖续签）：本地整缺一日（周一 23:50 打卡后整个周二不活动、周三 06:00
  再打卡），UTC 日差恰=1 → 免费 +1，既不烧卡也不记 MISSED；
- 契约依据：V3-FIX-37/wt559 已裁决「用户本地日」为本仓统计/连胜语义基准。

F3 / V3-FIX-294（P2）——冻结续签分支不同步 max_streak/longest_streak：
- 原 :2098-2103 冻结分支只做 ``freeze_charges -= days_missed`` 与
  ``current_streak += 1``，对照 delta==1 正常分支的完整簿记（max/total/longest
  +start/end）缺三样；冻结桥接出 current=31 而 longest=30，随后断签
  （current 归 1 不回填纪录）→ 31 天真实纪录永久丢成 30；
- 消费方：排行榜 ``longest_streak × WEIGHT_STREAK``（leaderboard_service）、
  streak_signal_processor:43/:52。

**历史数据口径声明（HUMAN_INBOX，不属本卡）**：本修复只改变「今后写入」的日界
口径（stats.last_activity_date 与 user_streak_days.day 全部落用户本地日）。修复
前已落库的 UTC 日界历史行（user_streak_days 中 UTC 日期的 active/frozen/missed
行、stats.last_activity_date 的 UTC 日期值）**不被本修复重释或回填**——修后首
次事件与紧邻的历史 UTC 行做 delta 运算时可能仍产生一次跨口径误判（如历史行是
UTC 日期、新事件是本地日期，二者相差可达 1 日），该数据修复属用户面，由集成后
主会话登记 HUMAN_INBOX 处理。本文件测试的种子一律按**修后引擎自身会写出的形状**
（用户本地日）播种，不伪造历史 UTC 行口径、不断言历史行为契约。

时钟注入模式：monkeypatch 模块级 ``app.services.achievement_engine._utcnow``
（沿 test_growth_streak_local_clock.py / test_dashboard_router_wall_lookback_local.py
先例），用可变 holder 在同一测试内推进冻结钟，驱动真实引擎多步打卡序列。
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.services.achievement_engine as achievement_engine_module
from app.core.cache import cache_service
from app.models.achievement import UserStreakDay, UserStreakStats
from app.models.base import Base
from app.models.user import PushPreference, User
from app.services.achievement_engine import AchievementEngine, AchievementEvent
from app.services.streak_quality import StreakQualityService

# wt576 场景钟（2026-09-27=周日，2026-09-28=周一；UTC+8 = 上海本地）
SCENARIO_A_NOW_1 = "2026-09-26T16:30:00"  # 上海周日 00:30 —— 本地打卡日 09-27
SCENARIO_A_NOW_2 = "2026-09-28T15:40:00"  # 上海周一 23:40 —— 本地打卡日 09-28
SCENARIO_B_NOW_1 = "2026-09-28T15:50:00"  # 上海周一 23:50 —— 本地打卡日 09-28
SCENARIO_B_NOW_2 = "2026-09-29T22:00:00"  # 上海周三 06:00 —— 本地打卡日 09-30


class _QualityOkStub:
    """高质量日形态：质量块不干扰连胜主断言（无 WEAK、无里程碑递归）。"""

    quality_score = 0.9
    is_quality_day = True


async def _fake_compute_quality(self, user_id, target_date=None):  # noqa: ARG001
    return _QualityOkStub()


async def _fake_quality_streak(self, user_id, target_date=None):  # noqa: ARG001
    return 0


@pytest.fixture
def isolated_quality(monkeypatch):
    """钉住质量服务与 cache，隔离外部副作用（沿 test_streak_weak_persistence）。"""
    monkeypatch.setattr(StreakQualityService, "compute_quality", _fake_compute_quality)
    monkeypatch.setattr(StreakQualityService, "quality_streak", _fake_quality_streak)
    monkeypatch.setattr(cache_service, "set", AsyncMock())
    monkeypatch.setattr(cache_service, "get", AsyncMock(return_value=None))


@pytest.fixture
def frozen_clock(monkeypatch):
    """冻结引擎模块级 _utcnow，返回可推进的 holder（真实引擎直驱）。

    holder 值为 naive-UTC ISO 串（与时区无关的绝对时刻），注入时解析回
    datetime——引擎对 _utcnow() 的消费面既有 ``.date()``（日界）也有原值
    落库（last_freeze_used_at），须返回 datetime 保持形状。
    """
    from datetime import datetime

    holder = {"now": "2026-09-28T12:00:00"}

    def _frozen() -> datetime:
        return datetime.fromisoformat(holder["now"])

    monkeypatch.setattr(achievement_engine_module, "_utcnow", _frozen)
    return holder


@pytest_asyncio.fixture(name="streak_db")
async def streak_db_fixture():
    """sqlite 内存库 + 全量相关表（users/push_preferences/user_streak_stats/user_streak_days）。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    User.__table__,
                    PushPreference.__table__,
                    UserStreakStats.__table__,
                    UserStreakDay.__table__,
                ],
            )
        )

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_factory
    await engine.dispose()


async def _make_user(session: AsyncSession, username: str, timezone: str | None = None) -> User:
    """建用户；timezone=None 时不建 PushPreference（走缺省回退），否则显式钉时区。"""
    user = User(username=username, email=f"{username}@example.com", hashed_password="hashed", photon_balance=0)
    session.add(user)
    await session.flush()  # 先取 user.id（无 Python 侧默认值）
    if timezone is not None:
        session.add(PushPreference(user_id=user.id, timezone=timezone))
        await session.flush()
    return user


async def _checkin(
    session: AsyncSession,
    user_id: Any,
    event_type: str = AchievementEvent.DAILY_CHECKIN,
    **kwargs: Any,
) -> None:
    """真实引擎直驱一次打卡（_update_streak_stats 是本卡修复面；kwargs 原样透传）。"""
    engine_svc = AchievementEngine(session)
    await engine_svc._update_streak_stats(user_id, event_type, **kwargs)


async def _streak_day_map(session: AsyncSession, user_id: Any) -> dict[date, str]:
    rows = (
        await session.execute(
            select(UserStreakDay.day, UserStreakDay.status).where(
                UserStreakDay.user_id == user_id, UserStreakDay.deleted_at.is_(None)
            )
        )
    ).all()
    return {day: (status.value if hasattr(status, "value") else status) for day, status in rows}


async def _stats(session: AsyncSession, user_id: Any) -> UserStreakStats:
    return (await session.execute(select(UserStreakStats).where(UserStreakStats.user_id == user_id))).scalar_one()


def _advance_clock(holder: dict, iso: str) -> None:
    holder["now"] = iso


def _as_day(value: Any) -> Any:
    """last_activity_date 列是 DateTime：sqlite/PG 往返后可能回读 datetime(午夜)。

    断言统一归一到 date 再比（引擎自身经 _coerce_activity_date 同款口径）。
    """
    from datetime import datetime

    return value.date() if isinstance(value, datetime) else value


# ========== F2 / V3-FIX-293 场景 A：本地连续日不得误烧冻结卡 ==========


@pytest.mark.asyncio
async def test_scenario_a_consecutive_local_days_do_not_burn_freeze(streak_db, frozen_clock, isolated_quality):
    """上海用户本地连续日打卡：冻结卡不得 1→0、不得落假 FROZEN 行.

    修复前实录（wt576 红）：两日本地连续（09-27/09-28），UTC 日差 2 →
    "used 1 freeze charges" + user_streak_days 落 ('2026-09-27','frozen') 假行。
    """
    engine, session_factory = streak_db
    async with session_factory() as session:
        user = await _make_user(session, "shanghai_a")
        # 调用方口径（accountability.py:1448）：显式透传用户本地打卡日。
        _advance_clock(frozen_clock, SCENARIO_A_NOW_1)
        await _checkin(session, user.id, activity_date=date(2026, 9, 27), source="accountability_checkin")

        _advance_clock(frozen_clock, SCENARIO_A_NOW_2)
        await _checkin(session, user.id, activity_date=date(2026, 9, 28), source="accountability_checkin")

        stats = await _stats(session, user.id)
        assert stats.current_streak == 2
        assert stats.freeze_charges == 1, "本地连续日不得烧冻结卡（修前 1→0）"
        assert _as_day(stats.last_activity_date) == date(2026, 9, 28), "last_activity_date 须落用户本地日"

        days = await _streak_day_map(session, user.id)
        assert days == {
            date(2026, 9, 27): "active",
            date(2026, 9, 28): "active",
        }, "user_streak_days 全链路本地日：无 09-26 UTC 行、无假 FROZEN 行（修前 ('2026-09-27','frozen')）"


# ========== F2 / V3-FIX-293 场景 B：本地整缺一日不得白嫖续签 ==========


@pytest.mark.asyncio
async def test_scenario_b_missed_local_day_breaks_streak_without_charge(streak_db, frozen_clock, isolated_quality):
    """本地整缺一日且无冻结卡：断签归 1，不得 UTC delta=1 白嫖 +1.

    修复前实录（wt576 红）：周一 23:50 打卡、整个周二不活动、周三 06:00 再打卡，
    UTC 日差恰 1 → current 5→6 免费续签。
    """
    engine, session_factory = streak_db
    async with session_factory() as session:
        user = await _make_user(session, "shanghai_b")
        # 真实引擎建立本地日 09-28 的 ACTIVE 日行，再把计数器钉到 wt576 场景 B
        # 前置态（current=5、冻结卡耗尽）——种子=修后引擎自身会写出的本地日形状。
        _advance_clock(frozen_clock, SCENARIO_B_NOW_1)
        await _checkin(session, user.id, activity_date=date(2026, 9, 28), source="accountability_checkin")

        stats = await _stats(session, user.id)
        stats.current_streak = 5
        stats.max_streak = 5
        stats.longest_streak = 5
        stats.total_checkin_days = 5
        # 场景前提：冻结卡已耗尽
        stats.freeze_charges = 0
        await session.flush()

        # 整个本地周二（09-29）不活动 → 周三（09-30）06:00 打卡
        _advance_clock(frozen_clock, SCENARIO_B_NOW_2)
        await _checkin(session, user.id, activity_date=date(2026, 9, 30), source="accountability_checkin")

        stats = await _stats(session, user.id)
        assert stats.current_streak == 1, "本地整缺一日必须断签（修前白嫖 5→6）"
        assert _as_day(stats.last_activity_date) == date(2026, 9, 30)

        days = await _streak_day_map(session, user.id)
        assert days[date(2026, 9, 29)] == "missed", "真缺的本地日须落 MISSED 行（修前无行/ACTIVE）"
        assert days[date(2026, 9, 30)] == "active"


@pytest.mark.asyncio
async def test_scenario_b_missed_local_day_with_charge_freeze_bridges(streak_db, frozen_clock, isolated_quality):
    """本地整缺一日且有冻结卡：走冻结桥接（烧卡+FROZEN 行），不得免费续签.

    修复前实录（红）：UTC delta=1 直进连续分支——卡不烧、缺日无 FROZEN 行、
    计数白嫖 +1。
    """
    engine, session_factory = streak_db
    async with session_factory() as session:
        user = await _make_user(session, "shanghai_b2")
        _advance_clock(frozen_clock, SCENARIO_B_NOW_1)
        await _checkin(session, user.id, activity_date=date(2026, 9, 28), source="accountability_checkin")

        stats = await _stats(session, user.id)
        stats.current_streak = 5
        stats.max_streak = 5
        stats.longest_streak = 5
        stats.total_checkin_days = 5
        stats.freeze_charges = 1
        await session.flush()

        _advance_clock(frozen_clock, SCENARIO_B_NOW_2)
        await _checkin(session, user.id, activity_date=date(2026, 9, 30), source="accountability_checkin")

        stats = await _stats(session, user.id)
        assert stats.freeze_charges == 0, "真缺的本地日必须烧卡桥接（修前白嫖不烧卡）"
        assert stats.current_streak == 6
        assert _as_day(stats.last_activity_date) == date(2026, 9, 30)

        days = await _streak_day_map(session, user.id)
        assert days[date(2026, 9, 29)] == "frozen", "被冻结桥接的缺日须落 FROZEN 行"
        assert days[date(2026, 9, 30)] == "active"


# ========== F2 / V3-FIX-293 回退口径：无 activity_date 时用户本地日 ==========


@pytest.mark.asyncio
async def test_fallback_without_activity_date_uses_default_user_local_day(streak_db, frozen_clock, isolated_quality):
    """无 activity_date 透传时：缺省 Asia/Shanghai 用户本地日，不静默回 UTC 日.

    修复前实录（红）：NOW=09-28 17:00Z（上海 09-29 01:00）按 UTC 日 09-28 判
    delta=0 早退——连续日丢失。修后按本地日 09-29 正常续签。
    """
    engine, session_factory = streak_db
    async with session_factory() as session:
        user = await _make_user(session, "fallback_default")  # 无 PushPreference 行
        seed_day = date(2026, 9, 28)
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=3,
                max_streak=3,
                longest_streak=3,
                total_checkin_days=3,
                last_activity_date=seed_day,
            )
        )
        await session.flush()

        _advance_clock(frozen_clock, "2026-09-28T17:00:00")  # 上海 09-29 01:00
        await _checkin(session, user.id)  # 不传 activity_date（NODE_MASTERED/TASK_COMPLETED 等调用面形状）

        stats = await _stats(session, user.id)
        assert stats.current_streak == 4, "缺省回退=用户本地日（上海 09-29），delta=1 连续（修前 delta=0 早退）"
        assert _as_day(stats.last_activity_date) == date(2026, 9, 29)

        days = await _streak_day_map(session, user.id)
        assert days == {date(2026, 9, 29): "active"}, "user_streak_days 落本地日 09-29（修前落 UTC 日 09-28）"


@pytest.mark.asyncio
async def test_fallback_explicit_timezone_rows_drive_resolution(streak_db, frozen_clock, isolated_quality):
    """显式 PushPreference 时区驱动回退：上海行续签、UTC 行不误跳日（对照控制组）."""
    engine, session_factory = streak_db
    async with session_factory() as session:
        shanghai_user = await _make_user(session, "tz_shanghai", timezone="Asia/Shanghai")
        utc_user = await _make_user(session, "tz_utc", timezone="UTC")
        for target in (shanghai_user, utc_user):
            session.add(
                UserStreakStats(
                    user_id=target.id,
                    current_streak=3,
                    max_streak=3,
                    longest_streak=3,
                    total_checkin_days=3,
                    last_activity_date=date(2026, 9, 28),
                )
            )
        await session.flush()

        _advance_clock(frozen_clock, "2026-09-28T17:00:00")  # 上海 09-29 01:00 / UTC 09-28 17:00
        await _checkin(session, shanghai_user.id)
        await _checkin(session, utc_user.id)

        shanghai_stats = await _stats(session, shanghai_user.id)
        assert shanghai_stats.current_streak == 4, "上海用户按本地日 09-29 续签"
        assert _as_day(shanghai_stats.last_activity_date) == date(2026, 9, 29)
        shanghai_days = await _streak_day_map(session, shanghai_user.id)
        assert shanghai_days == {date(2026, 9, 29): "active"}

        utc_stats = await _stats(session, utc_user.id)
        assert utc_stats.current_streak == 3, "UTC 用户本地日仍 09-28：delta=0 同日去重，不误跳（时区驱动证据）"
        assert _as_day(utc_stats.last_activity_date) == date(2026, 9, 28)
        utc_days = await _streak_day_map(session, utc_user.id)
        # delta==0 分支本就 upsert 当日 ACTIVE 行（引擎既有语义）：UTC 用户的
        # 「今日」仍钉在 09-28（不漂到上海本地日 09-29）——时区驱动证据。
        assert utc_days == {date(2026, 9, 28): "active"}, "UTC 用户同日去重：日行落其本地日 09-28"


# ========== F3 / V3-FIX-294：冻结续签同步 max/longest/total ==========


@pytest.mark.asyncio
async def test_freeze_bridge_syncs_max_longest_and_survives_break(streak_db, frozen_clock, isolated_quality):
    """冻结桥接续签须与正常路径同口径簿记；随后断签不得丢 31 天纪录.

    修复前实录（wt576 红）：seed current=max=longest=30 → 冻结桥接后
    current=31 而 max=longest=total=30；断签后 31 天纪录永久丢失。
    """
    engine, session_factory = streak_db
    async with session_factory() as session:
        user = await _make_user(session, "freeze_max")
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=30,
                max_streak=30,
                longest_streak=30,
                total_checkin_days=30,
                freeze_charges=1,
                last_activity_date=date(2026, 9, 26),
                longest_streak_start=date(2026, 8, 28),
            )
        )
        await session.flush()

        _advance_clock(frozen_clock, "2026-09-28T12:00:00")
        await _checkin(session, user.id, activity_date=date(2026, 9, 28))

        stats = await _stats(session, user.id)
        assert stats.current_streak == 31
        assert stats.freeze_charges == 0
        assert stats.max_streak == 31, "冻结续签须同步 max_streak（修后红线：修前恒 30）"
        assert stats.longest_streak == 31, "冻结续签须同步 longest_streak（排行榜 longest_streak×WEIGHT_STREAK 消费方）"
        assert stats.total_checkin_days == 31, "冻结续签与正常路径同口径：total_checkin_days 同步 +1"
        assert _as_day(stats.longest_streak_end) == date(2026, 9, 28)
        assert _as_day(stats.last_activity_date) == date(2026, 9, 28)

        days = await _streak_day_map(session, user.id)
        assert days[date(2026, 9, 27)] == "frozen"
        assert days[date(2026, 9, 28)] == "active"

        # 断签：冻结已耗尽 + 再缺 4 日 → current 归 1，但 31 天纪录必须保全
        _advance_clock(frozen_clock, "2026-10-03T12:00:00")
        await _checkin(session, user.id, activity_date=date(2026, 10, 3))

        stats = await _stats(session, user.id)
        assert stats.current_streak == 1
        assert stats.longest_streak == 31, "断签不得回填/吞掉冻结桥接出的 31 天纪录（修后该纪录才有机会存在）"
        assert stats.max_streak == 31
