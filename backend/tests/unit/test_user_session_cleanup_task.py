"""SESSION-GC — user_sessions 保留期清理任务（AUTH-DEEP A-2 末行 P2）删留边界回归。

判据（两侧都过保活期才删）：
- ``coalesce(revoked_at, last_active_at) < cutoff``
- ``last_active_at < cutoff``

覆盖三类卡面行 + 边界精度 + 分批循环：
1. 过期（revoked 且两侧均过 TTL）→ 删
2. 未过期（在用活跃）→ 留
3. 刚 revoke（revoked_at 在 TTL 内）→ 留
4. 附加类：从未 revoke 但停用超 TTL（refresh token 已过寿的死行）→ 删
"""

from __future__ import annotations

import contextlib
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.time_utils import utcnow as _utcnow
from app.models.auth_security import UserSession
from app.models.base import Base
from app.models.user import User
from app.tasks import user_session_cleanup as mod

_TABLES = [
    "users",
    "push_preferences",  # users 的 eager relationship 附属表
    "user_intervention_settings",  # 同上
    "user_sessions",
]


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables[name] for name in _TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_user(db: AsyncSession) -> User:
    user = User(
        username=f"gc_{uuid4().hex[:8]}",
        email=f"gc_{uuid4().hex[:8]}@example.com",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _row(user_id, session_id: str, *, revoked_at, last_active_at) -> UserSession:
    return UserSession(
        user_id=user_id,
        session_id=session_id,
        is_active=revoked_at is None,
        revoked_at=revoked_at,
        last_active_at=last_active_at,
    )


async def _count_remaining(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(UserSession))
    return int(result.scalar_one())


async def _remaining_session_ids(db: AsyncSession) -> set[str]:
    result = await db.execute(select(UserSession.session_id))
    return {row[0] for row in result.all()}


@pytest.mark.asyncio
async def test_three_card_classes_delete_keep_boundary(sqlite_session):
    """卡面三类行：过期删 / 活跃留 / 刚 revoke 留。"""
    db = sqlite_session
    user = await _seed_user(db)
    now = _utcnow()
    ttl = timedelta(seconds=mod.SESSION_TTL_SECONDS)

    db.add_all(
        [
            # 1) 过期：revoked 很久以前 + 停用很久以前 → 删
            _row(
                user.id,
                "revoked-expired",
                revoked_at=now - ttl - timedelta(days=1),
                last_active_at=now - ttl - timedelta(days=1),
            ),
            # 2) 未过期：在用活跃 → 留
            _row(
                user.id,
                "active-fresh",
                revoked_at=None,
                last_active_at=now - timedelta(minutes=5),
            ),
            # 3) 刚 revoke：revoked_at 在保活期内（即便 last_active 很旧）→ 留
            _row(
                user.id,
                "revoked-just-now",
                revoked_at=now - timedelta(minutes=5),
                last_active_at=now - ttl - timedelta(days=2),
            ),
        ]
    )
    await db.commit()

    deleted = await mod._cleanup_expired_user_sessions(db)

    assert deleted == 1
    assert await _remaining_session_ids(db) == {"active-fresh", "revoked-just-now"}


@pytest.mark.asyncio
async def test_stale_never_revoked_and_ttl_boundary(sqlite_session):
    """从未 revoke 的停用死行删除；TTL 边界为严格小于（界内保留/界外删除）。"""
    db = sqlite_session
    user = await _seed_user(db)
    now = _utcnow()
    ttl = timedelta(seconds=mod.SESSION_TTL_SECONDS)

    db.add_all(
        [
            # 4) 从未 revoke 但停用超 TTL（refresh token 已过寿）→ 删
            _row(
                user.id,
                "stale-never-revoked",
                revoked_at=None,
                last_active_at=now - ttl - timedelta(seconds=1),
            ),
            # 边界：保活期内最后 2s（cutoff 为任务侧时钟，严格 < 下不删）→ 留
            _row(
                user.id,
                "boundary-inside",
                revoked_at=None,
                last_active_at=now - ttl + timedelta(seconds=2),
            ),
            # 边界：revoked_at 在保活期内最后 2s（即便 last_active 很旧）→ 留
            _row(
                user.id,
                "boundary-revoked-inside",
                revoked_at=now - ttl + timedelta(seconds=2),
                last_active_at=now - ttl - timedelta(days=1),
            ),
        ]
    )
    await db.commit()

    deleted = await mod._cleanup_expired_user_sessions(db)

    assert deleted == 1
    assert await _remaining_session_ids(db) == {"boundary-inside", "boundary-revoked-inside"}


@pytest.mark.asyncio
async def test_batched_deletion_loops_multiple_batches(sqlite_session, monkeypatch):
    """分批删除：BATCH_SIZE=10 时 25 行过期数据经多批删净，未过期行原样保留。"""
    db = sqlite_session
    user = await _seed_user(db)
    monkeypatch.setattr(mod, "BATCH_SIZE", 10)
    now = _utcnow()
    ttl = timedelta(seconds=mod.SESSION_TTL_SECONDS)
    stale = now - ttl - timedelta(hours=1)

    db.add_all(
        [_row(user.id, f"expired-{i}", revoked_at=stale, last_active_at=stale) for i in range(25)]
        + [_row(user.id, f"keep-{i}", revoked_at=None, last_active_at=now - timedelta(minutes=1)) for i in range(3)]
    )
    await db.commit()
    assert await _count_remaining(db) == 28

    deleted = await mod._cleanup_expired_user_sessions(db)

    assert deleted == 25
    assert await _count_remaining(db) == 3
    remaining = await _remaining_session_ids(db)
    assert all(sid.startswith("keep-") for sid in remaining)


def _read_cleanup_counter() -> float:
    from prometheus_client import REGISTRY

    collector = REGISTRY._names_to_collectors.get("sparkle_user_sessions_cleanup_deleted_total")
    if collector is None:
        return 0.0
    return float(collector._value.get())


def test_task_wrapper_reports_success_and_increments_counter(monkeypatch):
    """任务壳：返回 success + deleted_count，并把清理行数累进 metrics 计数器。"""

    async def _fake_core(db):
        return 7

    @contextlib.contextmanager
    def _fake_ctx():
        yield object()

    monkeypatch.setattr(mod, "get_db_context", _fake_ctx)
    monkeypatch.setattr(mod, "_cleanup_expired_user_sessions", _fake_core)
    before = _read_cleanup_counter()

    result = mod.cleanup_expired_user_sessions()

    assert result == {"status": "success", "deleted_count": 7}
    assert _read_cleanup_counter() == pytest.approx(before + 7)


def test_task_wrapper_reports_error_on_failure(monkeypatch):
    """任务壳：核心清理抛错时返回 error dict（celery autoretry 仍接管重试）。"""

    async def _boom(db):
        raise RuntimeError("db down")

    @contextlib.contextmanager
    def _fake_ctx():
        yield object()

    monkeypatch.setattr(mod, "get_db_context", _fake_ctx)
    monkeypatch.setattr(mod, "_cleanup_expired_user_sessions", _boom)

    result = mod.cleanup_expired_user_sessions()

    assert result["status"] == "error"
    assert "db down" in result["message"]
