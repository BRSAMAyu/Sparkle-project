"""EI-03 守卫：`get_db_context` 的异常路径不得掩盖原始异常。

历史问题：`__exit__` 用三次独立的 `asyncio.run()`（commit / rollback / close）驱动同一个
AsyncSession。一旦内层协程半途抛异常留下未提交事务，下一次 `asyncio.run` 上的 rollback
会因跨事件循环立即失败 —— 该新异常会**替换**原始异常向上抛出，真正的事故原因被掩盖。

契约：
1. 内层异常必须**原样**（同一对象）向上抛出；
2. rollback 失败仅记录日志，永不替换原始异常；
3. close 失败同样只记录日志（此时事务已终结，不应让任务结果失败）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db import session as db_session


@pytest.fixture()
def fake_session(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    session = AsyncMock()
    monkeypatch.setattr(db_session, "AsyncSessionLocal", lambda: session)
    return session


def test_original_exception_preserved_when_rollback_also_fails(
    fake_session: AsyncMock,
) -> None:
    original = ValueError("inner boom")
    fake_session.rollback = AsyncMock(side_effect=RuntimeError("attached to a different loop"))

    with pytest.raises(ValueError) as exc_info:
        with db_session.get_db_context():
            raise original

    assert exc_info.value is original, "rollback 失败不得替换/包装原始异常"
    fake_session.rollback.assert_awaited_once()


def test_original_exception_preserved_when_close_also_fails(
    fake_session: AsyncMock,
) -> None:
    original = ValueError("inner boom")
    fake_session.close = AsyncMock(side_effect=RuntimeError("loop is closed"))

    with pytest.raises(ValueError) as exc_info:
        with db_session.get_db_context():
            raise original

    assert exc_info.value is original


def test_commit_failure_triggers_rollback_and_raises_commit_error(
    fake_session: AsyncMock,
) -> None:
    commit_error = RuntimeError("integrity constraint violated")
    fake_session.commit = AsyncMock(side_effect=commit_error)

    with pytest.raises(RuntimeError) as exc_info:
        with db_session.get_db_context():
            pass

    assert exc_info.value is commit_error
    fake_session.rollback.assert_awaited_once()


def test_close_failure_on_success_path_does_not_mask_result(
    fake_session: AsyncMock,
) -> None:
    fake_session.close = AsyncMock(side_effect=RuntimeError("loop is closed"))

    with db_session.get_db_context():
        pass  # 正常完成

    fake_session.commit.assert_awaited_once()


def test_success_path_commits_and_closes(fake_session: AsyncMock) -> None:
    captured: dict[str, object] = {}

    with db_session.get_db_context() as db:
        captured["db"] = db

    assert captured["db"] is fake_session
    fake_session.commit.assert_awaited_once()
    fake_session.rollback.assert_not_awaited()
    fake_session.close.assert_awaited_once()
