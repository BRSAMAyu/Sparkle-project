"""RB-06 follow-up（P3 清扫）：流路径共享会话上的中途 commit 审计处置。

R1 RB-06 已修 session_state_mixin；R2-09 移交了同族坐标
``context_builder.py``（_build_full_context 内持久化用户消息时中途 commit）。
本波全仓审计又确认 ``persistence_layer._persist_assistant_message``（助手消息
落盘）同样在 gRPC 流的共享 ``active_db`` 上中途 commit——破坏"一轮一事务"
原子性（用户消息已提交而后续任何环节失败时，外层 agent_grpc_service 的
rollback 无法回滚它）。

处置与 RB-06 同法：``commit()`` → ``flush()``。提交所有权在
``app/services/agent_grpc_service.py``（stream 结束统一 commit、异常 rollback，
见 :354-399）；flush 后由调用方统一提交，PK 由 flush 分配，写 lane 语义不变。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.persistence_layer import PersistenceLayerMixin


class _RecordingSession:
    """假 session：记录 add/flush/commit/rollback 调用序列。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add(self, obj) -> None:
        self.calls.append(("add", obj))

    async def flush(self) -> None:
        self.calls.append(("flush",))

    async def commit(self) -> None:
        self.calls.append(("commit",))

    async def rollback(self) -> None:
        self.calls.append(("rollback",))


def _assert_flush_not_commit(session: _RecordingSession) -> None:
    ops = [c[0] for c in session.calls]
    assert "flush" in ops, "必须 flush 使调用方（agent_grpc_service）统一提交"
    assert "commit" not in ops, "共享会话上禁止中途 commit（RB-06/R2-09 同族）"


@pytest.mark.asyncio
async def test_persist_user_message_uses_flush_not_commit() -> None:
    """R2-09：_build_full_context 用户消息落盘走 flush。"""
    mixin = object.__new__(ContextBuilderMixin)
    session = _RecordingSession()
    await mixin._persist_user_message(
        active_db=session,
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        user_message="你好",
        request_id="req-1",
    )
    _assert_flush_not_commit(session)


@pytest.mark.asyncio
async def test_persist_user_message_rolls_back_on_failure() -> None:
    mixin = object.__new__(ContextBuilderMixin)

    class _BoomSession(_RecordingSession):
        async def flush(self) -> None:
            self.calls.append(("flush",))
            raise RuntimeError("boom")

    session = _BoomSession()
    # 异常必须被吞掉（非致命路径），且触发 rollback 清理
    await mixin._persist_user_message(
        active_db=session,
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        user_message="你好",
        request_id="req-1",
    )
    ops = [c[0] for c in session.calls]
    assert "rollback" in ops
    assert "commit" not in ops


@pytest.mark.asyncio
async def test_persist_assistant_message_independent_session_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """B-01/NBP-1 后契约：助手消息落盘改用独立 session 自持提交（共享 gRPC 流
    session 可能已被本轮更早异常毒化，复用会陪葬）——共享 active_db 全程不被
    触碰，独立 session 内 flush 分配 PK + commit；写 lane 照常触发。"""
    import app.orchestration.persistence_layer as pl

    lane_calls: list[dict] = []

    class _FakeLane:
        @staticmethod
        def enqueue_from_session(**kwargs) -> None:
            lane_calls.append(kwargs)

    class _PersistSession:
        def __init__(self) -> None:
            self.calls: list[tuple] = []

        def add(self, obj) -> None:
            self.calls.append(("add", obj))

        async def get(self, model, pk):
            return None

        async def flush(self) -> None:
            self.calls.append(("flush",))

        async def commit(self) -> None:
            self.calls.append(("commit",))

        async def __aenter__(self) -> "_PersistSession":
            return self

        async def __aexit__(self, *exc) -> bool:
            return False

    persist_sessions: list[_PersistSession] = []

    class _FakeSessionLocal:
        def __call__(self) -> _PersistSession:
            session = _PersistSession()
            persist_sessions.append(session)
            return session

    monkeypatch.setattr(pl, "MemoryInferredWriteLaneService", _FakeLane)
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", _FakeSessionLocal())
    mixin = object.__new__(PersistenceLayerMixin)
    mixin._coerce_session_uuid = staticmethod(lambda sid: uuid4())  # type: ignore[attr-defined]
    # _persist_assistant_message 通过模块级 llm_service 取默认模型，改打桩
    monkeypatch.setattr(pl, "llm_service", SimpleNamespace(default_model="unit-model"))

    shared = _RecordingSession()
    await PersistenceLayerMixin._persist_assistant_message(
        mixin,
        active_db=shared,  # type: ignore[arg-type]
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        full_response="回复内容",
    )
    # 共享流 session 不被触碰（RB-06 审计目标的强化形态：写与提交所有权
    # 全在独立 session，提交所有权在 AsyncSessionLocal 上下文内）
    assert shared.calls == []
    ops = [c[0] for c in persist_sessions[0].calls]
    assert "flush" in ops, "独立 session 必须 flush 分配 assistant_message_id"
    assert "commit" in ops, "独立 session 自持提交（消息与会话头同事务）"
    assert lane_calls, "flush 后写 lane 仍必须被触发（assistant_message_id 可用）"


@pytest.mark.asyncio
async def test_persist_assistant_message_rolls_back_shared_session_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """独立 session 写入失败时，异常被吞（非致命路径）且共享 session 被 rollback。"""
    import app.orchestration.persistence_layer as pl

    class _FakeLane:
        @staticmethod
        def enqueue_from_session(**kwargs) -> None:
            raise RuntimeError("lane boom")

    class _PersistSession:
        async def get(self, model, pk):
            return None

        def add(self, obj) -> None:
            pass

        async def flush(self) -> None:
            pass

        async def __aenter__(self) -> "_PersistSession":
            return self

        async def __aexit__(self, *exc) -> bool:
            return False

    class _FakeSessionLocal:
        def __call__(self) -> _PersistSession:
            return _PersistSession()

    monkeypatch.setattr(pl, "MemoryInferredWriteLaneService", _FakeLane)
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", _FakeSessionLocal())
    mixin = object.__new__(PersistenceLayerMixin)
    mixin._coerce_session_uuid = staticmethod(lambda sid: uuid4())  # type: ignore[attr-defined]
    monkeypatch.setattr(pl, "llm_service", SimpleNamespace(default_model="unit-model"))

    shared = _RecordingSession()
    await PersistenceLayerMixin._persist_assistant_message(
        mixin,
        active_db=shared,  # type: ignore[arg-type]
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        full_response="回复内容",
    )
    ops = [c[0] for c in shared.calls]
    assert "rollback" in ops
    assert "commit" not in ops
