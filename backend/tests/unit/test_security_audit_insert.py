"""AUDIT-INSERT-Fix · security_audit_logs 落库与降级回归（COLDSTART 双可靠性项之二）.

活栈根因（/tmp/fastapi_engine.log 实证，每条安全事件全灭）::

    NotNullViolationError: null value in column "id" of relation
    "security_audit_logs" violates not-null constraint

表 DDL（baseline cc9383c4c29f）无 server_default、模型无 Python 侧 default →
``_record_security_event`` 的 INSERT 缺 id 必然失败；旧失败分支还
``db.rollback()`` 整个请求事务（把同事务已 flush 的 LoginAttempt 一并吞掉）。

本文件双向钉死：
- INSERT 成功：模型 id 有客户端默认值，无显式 id 的 INSERT 落库成功；
- 失败降级：插入失败只回滚 SAVEPOINT——外层事务完好（LoginAttempt 存活）、
  完整事件 JSON 以 ``[SecurityAuditFallback]`` 落日志（留痕不静默）；
- Redis 实时监控面失败不拖垮已落库的审计行。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.security_monitor import SecurityEvent, SecurityEventType, SecurityMonitor, ThreatLevel
from app.models.audit_log import SecurityAuditLog
from app.models.base import Base
from app.models.user import LoginAttempt


@pytest_asyncio.fixture
async def audit_session(tmp_path):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        f"sqlite+aiosqlite:////{tmp_path / 'audit_insert.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _make_monitor() -> SecurityMonitor:
    monitor = SecurityMonitor()
    monitor.redis = AsyncMock()
    return monitor


def _make_event(**overrides) -> SecurityEvent:
    payload = {
        "event_type": SecurityEventType.LOGIN_FAILED,
        "ip_address": "203.0.113.9",
        "threat_level": ThreatLevel.MEDIUM,
        "details": {"username": "alice", "success": False},
    }
    payload.update(overrides)
    return SecurityEvent(**payload)


@pytest.mark.asyncio
async def test_insert_succeeds_with_generated_id(audit_session):
    """修复核心：无显式 id 的 INSERT 成功（id 由客户端默认值在 flush 时生成）。"""
    row = SecurityAuditLog(
        event_type="login_failed",
        threat_level="medium",
        details={"username": "alice"},
    )
    audit_session.add(row)
    await audit_session.flush()

    assert row.id is not None, "SecurityAuditLog.id 必须有 Python 侧默认值"
    count = len((await audit_session.execute(select(SecurityAuditLog.id))).all())
    assert count == 1


@pytest.mark.asyncio
async def test_record_security_event_persists_and_mirrors_redis(audit_session):
    monitor = _make_monitor()
    event = _make_event()
    await monitor._record_security_event(event, audit_session)

    rows = (await audit_session.execute(select(SecurityAuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "login_failed"
    assert rows[0].threat_level == "medium"
    monitor.redis.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_insert_failure_degrades_without_poisoning_outer_transaction(audit_session):
    """插入失败（flush 抛 IntegrityError）只回滚 SAVEPOINT：
    外层已 flush 的 LoginAttempt 存活，完整事件 JSON 落日志留痕。"""
    from sqlalchemy.exc import IntegrityError

    # 外层事务先 flush 一行业务数据（对应 record_login_attempt 的真实序列）
    attempt = LoginAttempt(username="alice", ip_address="203.0.113.9", success=False)
    audit_session.add(attempt)
    await audit_session.flush()

    async def _boom():
        raise IntegrityError(
            "INSERT INTO security_audit_logs ...", {}, Exception("NOT NULL check failed")
        )

    logs: list[str] = []
    from loguru import logger

    original_flush = audit_session.flush
    audit_session.flush = _boom  # 只打断审计插入那一次 flush
    sink_id = logger.add(lambda message: logs.append(str(message)), level="WARNING")
    try:
        monitor = _make_monitor()
        event = _make_event()
        await monitor._record_security_event(event, audit_session)
    finally:
        audit_session.flush = original_flush
        logger.remove(sink_id)

    # 审计行没进来，但外层事务未被 rollback 毒化
    audit_rows = (await audit_session.execute(select(SecurityAuditLog))).scalars().all()
    assert audit_rows == []
    await audit_session.commit()
    kept = (await audit_session.execute(select(LoginAttempt))).scalars().all()
    assert len(kept) == 1, "SAVEPOINT 修复后外层业务行必须存活"

    # 降级留痕：完整事件 JSON 进日志（非静默）
    assert any("[SecurityAuditFallback]" in line for line in logs), logs
    assert any("login_failed" in line for line in logs), logs


@pytest.mark.asyncio
async def test_malformed_event_degrades_without_raising(audit_session):
    """事件本身残缺（event_type=None）：构造即失败也走降级，不外抛打断调用方，
    外层事务不受影响。"""
    attempt = LoginAttempt(username="bob", ip_address="203.0.113.10", success=True)
    audit_session.add(attempt)
    await audit_session.flush()

    logs: list[str] = []
    from loguru import logger

    sink_id = logger.add(lambda message: logs.append(str(message)), level="WARNING")
    try:
        monitor = _make_monitor()
        bad_event = _make_event(event_type=None)  # type: ignore[arg-type] — 故意残缺
        await monitor._record_security_event(bad_event, audit_session)
    finally:
        logger.remove(sink_id)

    assert any("[SecurityAuditFallback]" in line for line in logs), logs
    await audit_session.commit()
    kept = (await audit_session.execute(select(LoginAttempt))).scalars().all()
    assert len(kept) == 1


@pytest.mark.asyncio
async def test_redis_failure_does_not_lose_audit_row(audit_session):
    """Redis 实时监控面失败：审计行（已 flush）不受影响，仅 WARNING。"""
    monitor = _make_monitor()
    monitor.redis.setex = AsyncMock(side_effect=ConnectionError("redis down"))

    event = _make_event()
    await monitor._record_security_event(event, audit_session)

    rows = (await audit_session.execute(select(SecurityAuditLog))).scalars().all()
    assert len(rows) == 1, "审计行已落事务，Redis 故障不得回滚它"


@pytest.mark.asyncio
async def test_id_default_is_unique_per_row(audit_session):
    ids = set()
    for _ in range(3):
        row = SecurityAuditLog(event_type="data_access", threat_level="low")
        audit_session.add(row)
        await audit_session.flush()
        ids.add(row.id)
    assert len(ids) == 3
