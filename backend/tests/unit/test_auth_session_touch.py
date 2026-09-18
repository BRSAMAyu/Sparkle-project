"""Regression tests for AuthSessionService (A1: touch must not revive revoked sessions)."""

from __future__ import annotations

from datetime import timedelta, datetime, UTC
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.dml import Insert as InsertBase

from app.services import auth_session_service as mod
from app.services.auth_session_service import auth_session_service


class _CaptureDB:
    def __init__(self, last_active_at: object = None) -> None:
        self.statements: list[object] = []
        self._last_active_at = last_active_at

    async def execute(self, stmt: object) -> object:
        self.statements.append(stmt)
        if isinstance(stmt, Select):
            result = MagicMock()
            # 支持 touch_session freshness-skip 的 .first() 读取：
            # 返回 (last_active_at,) 或 None（无行）
            if self._last_active_at is None:
                result.first.return_value = None
            else:
                result.first.return_value = (self._last_active_at,)
            result.scalar_one.return_value = None
            return result
        return None

    async def flush(self) -> None:
        return None


class _FakeCache:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)

    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.set_calls.append((key, value, ttl))


def _first_insert(db) -> object:
    """freshness-skip 会在 upsert 前先发 SELECT，这里取第一条真正的 upsert 语句。"""
    for stmt in db.statements:
        if isinstance(stmt, InsertBase):
            return stmt
    raise AssertionError("no upsert statement captured")


def _on_conflict_updates(stmt: object) -> dict:
    assert isinstance(stmt, InsertBase)
    post = getattr(stmt, "_post_values_clause", None)
    assert post is not None and type(post).__name__ == "OnConflictDoUpdate"
    return dict(post.update_values_to_set)


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch) -> tuple[_CaptureDB, _FakeCache]:
    db = _CaptureDB()
    cache = _FakeCache()
    monkeypatch.setattr(mod, "cache_service", cache)
    return db, cache


@pytest.mark.asyncio
async def test_touch_from_payload_does_not_reset_revocation(capture):
    """A1: touch 只更新元数据，不得复位 is_active/revoked_at 或删除撤销标记。"""
    db, cache = capture

    await auth_session_service.touch_from_payload(
        db,
        request=None,
        user_id="user-1",
        payload={"sid": "sess-1", "type": "access", "jti": "jti-1"},
    )

    updates = _on_conflict_updates(_first_insert(db))
    assert "last_active_at" in updates
    assert "is_active" not in updates, "touch must not re-activate the session row"
    assert "revoked_at" not in updates, "touch must not clear the revocation timestamp"
    assert not cache.deleted, "touch must not delete the session_revoked redis marker"


@pytest.mark.asyncio
async def test_upsert_session_keeps_reactivation_semantics(capture):
    """A1 对照：登录/刷新的 upsert 仍允许复位撤销状态并清除标记。"""
    db, cache = capture

    await auth_session_service.upsert_session(
        db,
        user_id="user-1",
        session_id="sess-1",
        request=None,
    )

    updates = _on_conflict_updates(_first_insert(db))
    assert updates.get("is_active") is True
    assert "revoked_at" in updates
    assert cache.deleted == [f"{mod.SESSION_REVOKED_PREFIX}sess-1"]


def test_pg_insert_construct_used():
    """确保服务确实走 postgres upsert（防测试对象漂移）。"""
    stmt = pg_insert(mod.UserSession).values(user_id="u", session_id="s")
    assert isinstance(stmt, InsertBase)


@pytest.mark.asyncio
async def test_touch_freshness_skip_skips_recent_touch(capture):
    """restore-storm 防护：SESSION_TOUCH_MIN_INTERVAL 窗口内的重复 touch 直接跳过，
    不发 upsert（消除恢复风暴下 user_sessions 行锁排队与写放大）。"""
    db, _ = capture
    db._last_active_at = datetime.now(UTC).replace(tzinfo=None)  # 刚刚活跃过
    db.statements.clear()

    await auth_session_service.touch_session(db, user_id="user-1", session_id="sess-1", request=None)

    assert not [s for s in db.statements if isinstance(s, InsertBase)], (
        "freshness 窗口内的 touch 不得发出 upsert"
    )


@pytest.mark.asyncio
async def test_touch_stale_session_still_touches(capture):
    """窗口外的会话照常 touch（活跃度元数据保持准确）。"""
    db, _ = capture
    stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=mod.SESSION_TOUCH_MIN_INTERVAL + 1)
    db._last_active_at = stale

    await auth_session_service.touch_session(db, user_id="user-1", session_id="sess-1", request=None)

    assert [s for s in db.statements if isinstance(s, InsertBase)], "窗口外的 touch 必须写库"
