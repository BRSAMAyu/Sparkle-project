"""V3-FIX-259：StreakDayStatus.WEAK 四层断链的 engine 写面与 wire 契约红绿测.

背景（wt534 B-06 实体真源审计 §2.1 / 台账 V3-FIX-259）：
- 迁移 f2b3c4d5e6f7 建的 PG 原生枚举 streakdaystatus 只有 3 值（active/frozen/
  missed，无 weak），而引擎 ``achievement_engine._update_streak_stats`` 在质量
  分 <0.4 时活体写 ``StreakDayStatus.WEAK``——迁移库上该写入触发 enum DataError，
  被外层 ``except Exception`` 以 debug 级静默吞掉：质量加权连胜静默死亡，
  且失败 flush 让会话进入 PendingRollback 毒化态，殃及同事务后续全部操作；
- wire 侧 ``StreakDayRecord.status`` 是无约束 ``str`` 且 docstring 值集过时
  （"active | frozen | missed"），与实现 4 值不符，OpenAPI 无法约束值集。

测试策略：
1. engine 写面：在 sqlite 上用 3 值 CHECK 约束镜像"迁移建库"形状（原生枚举
   无 weak 的语义等价物），断言 WEAK 写失败 (a) 不再静默——WARNING 日志 +
   Prometheus 计数器增量；(b) 不投毒会话——savepoint 回滚后外层连胜事务
   （stats + ACTIVE 行）存活、后续查询可用。注释标红行为为修复前实录。
2. wire 契约：``StreakDayRecord.status`` 收敛为 ``StreakDayStatus`` 枚举，
   值集与后端 StrEnum 精确对齐（含 weak），OpenAPI schema 声明完整值集。
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.cache import cache_service
from app.core.metrics import REGISTRY
from app.models.achievement import StreakDayStatus, UserStreakDay, UserStreakStats
from app.models.base import Base
from app.models.user import User
from app.schemas.achievement import StreakDayRecord
from app.services.achievement_engine import AchievementEngine, AchievementEvent, _utcnow
from app.services.streak_quality import StreakQualityService

PERSIST_FAILURE_COUNTER = "sparkle_streak_quality_status_persist_failures_total"

# 迁移建库形状镜像：user_streak_days.status 三值 CHECK（等价于 PG 原生枚举
# 无 'weak'——写入即约束违约，flush 抛 DBAPIError）。
STREAK_DAYS_3_VALUE_DDL = """
CREATE TABLE user_streak_days (
    user_id VARCHAR(36) NOT NULL,
    day DATE NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'frozen', 'missed')),
    used_freeze BOOLEAN NOT NULL DEFAULT 0,
    source_event VARCHAR(50),
    id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    PRIMARY KEY (user_id, day)
)
"""


class _QualityStub:
    """低质量日形态：quality_score=0.2 → 引擎应落 StreakDayStatus.WEAK。"""

    quality_score = 0.2
    is_quality_day = False


async def _fake_compute_quality(self, user_id, target_date=None):  # noqa: ARG001
    return _QualityStub()


async def _fake_quality_streak(self, user_id, target_date=None):  # noqa: ARG001
    return 0


@pytest.fixture
def quality_low_day(monkeypatch):
    """把质量服务钉在低质量日形态，隔离 cache 副作用。"""
    monkeypatch.setattr(StreakQualityService, "compute_quality", _fake_compute_quality)
    monkeypatch.setattr(StreakQualityService, "quality_streak", _fake_quality_streak)
    monkeypatch.setattr(cache_service, "set", AsyncMock())
    monkeypatch.setattr(cache_service, "get", AsyncMock(return_value=None))


@pytest.fixture
def capture_loguru():
    """按仓内范式捕获 loguru（tests/unit/test_v3_fix62 同款 sink）。"""
    records: list = []
    sink_id = logger.add(lambda m: records.append(m.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


@pytest_asyncio.fixture(name="migrated_shape_db")
async def migrated_shape_db_fixture():
    """3 值 CHECK 镜像库：除 user_streak_days 走 raw DDL 外全量建 metadata 表。"""
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[User.__table__, UserStreakStats.__table__],
            )
        )
        await conn.execute(text(STREAK_DAYS_3_VALUE_DDL))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_factory

    await engine.dispose()


def _counter_value() -> float:
    return REGISTRY.get_sample_value(PERSIST_FAILURE_COUNTER) or 0.0


@pytest.mark.asyncio
async def test_engine_weak_write_failure_not_silent_and_session_survives(
    migrated_shape_db, quality_low_day, capture_loguru
):
    """WEAK 写失败必须：WARNING 日志 + 计数器递增 + 会话不投毒.

    修复前实录（红）：仅 debug 级 "Quality streak calculation skipped"，
    计数器不存在/不增，且失败 flush 后同会话任何查询抛 PendingRollbackError。
    """
    engine, session_factory = migrated_shape_db
    before = _counter_value()
    async with session_factory() as session:
        user = User(username="weakuser", email="weak@example.com", hashed_password="hashed", photon_balance=0)
        session.add(user)
        await session.flush()  # 先取 user.id（无 Python 侧默认值）
        # 锚定引擎 UTC 时钟（本地 date.today() 跨午夜会与引擎 today 错位成 delta=0）
        yesterday = _utcnow().date() - timedelta(days=1)
        # 昨日已活跃（delta==1 连续路径）——首日/当日分支会提前 return，
        # 只有连续路径会走到质量块（WEAK 落库点）。
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=1,
                max_streak=1,
                longest_streak=1,
                total_checkin_days=1,
                last_activity_date=yesterday,
            )
        )
        await session.flush()

        engine_svc = AchievementEngine(session)
        # 连续路径：stats.current_streak=2 + 落今日 ACTIVE 行（三值枚举可写），
        # 随后质量块尝试落 WEAK → 被 CHECK/枚举拒绝。
        await engine_svc._update_streak_stats(user.id, AchievementEvent.DAILY_CHECKIN)

        weak_rows = (
            await session.execute(select(func.count()).select_from(UserStreakDay))
        ).scalar_one()
        assert weak_rows == 1, "仅今日 ACTIVE 行应存活；WEAK 行被约束拒绝"

        stats = (
            await session.execute(select(UserStreakStats).where(UserStreakStats.user_id == user.id))
        ).scalar_one()
        assert stats is not None and stats.current_streak == 2, "savepoint 回滚不得波及外层连胜事务"

        statuses = [row[0] for row in await session.execute(select(UserStreakDay.status))]
        assert statuses == ["active"]

        warnings = [
            r
            for r in capture_loguru
            if r["level"].name == "WARNING" and "streak" in r["message"].lower()
        ]
        assert warnings, "WEAK 写失败不得停留在 debug 级静默：必须有 WARNING 日志"

    assert _counter_value() > before, "WEAK 写失败必须递增 Prometheus 计数器"


@pytest.mark.asyncio
async def test_engine_weak_write_persists_on_capable_db(db_session):
    """枚举齐备（迁移后形状）时 WEAK 真实落库，语义=弱连胜日.

    sqlite 的 Enum 映射为含 4 值 CHECK 的 VARCHAR（模型值集），等价迁移修复后
    的 PG 枚举形态：WEAK 行直接可写。
    """
    user = User(username="weakcapable", email="weakcap@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.flush()

    engine_svc = AchievementEngine(db_session)
    await engine_svc._upsert_streak_day(user.id, date(2026, 9, 25), StreakDayStatus.WEAK, source_event="daily_checkin")

    row = (
        await db_session.execute(
            select(UserStreakDay).where(UserStreakDay.user_id == user.id, UserStreakDay.day == date(2026, 9, 25))
        )
    ).scalar_one()
    assert row.status == StreakDayStatus.WEAK
    assert row.source_event == "daily_checkin"


# ========== wire 契约 ==========


def test_streak_wire_value_set_alignment():
    """mobile 契约面：后端值集固定 4 值，wire 与 StrEnum 精确对齐."""
    assert {s.value for s in StreakDayStatus} == {"active", "weak", "frozen", "missed"}


def test_streak_day_record_wire_schema_documents_full_value_set():
    """status 收敛为枚举：weak 可下发，OpenAPI 值集描述与实现一致.

    修复前实录（红）：status 为无约束 str，schema 仅有过时 docstring
    "active | frozen | missed"，无枚举约束、无 weak。
    """
    record = StreakDayRecord(day=date(2026, 9, 25), status=StreakDayStatus.WEAK)
    assert record.model_dump(mode="json")["status"] == "weak"

    schema = StreakDayRecord.model_json_schema()
    status_schema = json.dumps(schema["properties"]["status"])
    for value in ("active", "weak", "frozen", "missed"):
        assert value in status_schema, f"wire schema 值集缺 {value!r}：{status_schema}"

    enums = [
        set(definition["enum"])
        for definition in schema.get("$defs", {}).values()
        if "enum" in definition
    ]
    assert {"active", "weak", "frozen", "missed"} in enums, "status 必须以枚举约束下发值集"


def test_streak_day_record_rejects_out_of_set_status():
    """值集外状态在 wire 出口被拒（不再静默透传未知串到端上）."""
    with pytest.raises(Exception):
        StreakDayRecord.model_validate({"day": "2026-09-25", "status": "supercharged"})
