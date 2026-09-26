"""B-01（CHAT-VISIBLE，V13 实测）红证：WS/gRPC 主链轮次落库必须同时建立
``chat_sessions`` 头行。

复现路径（v3-output/V13/REPORT.md B-01）：新号注册 → 完成画像引导 → 跳过建模
访谈 → 主聊天发送首条 WS 消息。引擎把 USER/ASSISTANT 行写进 ``chat_messages``
（``context_builder._persist_user_message`` /
``persistence_layer._persist_assistant_message``），但整条链无人写
``chat_sessions``：网关 Redis persister（``chat_history_persister.go`` 的
``chatSessionUpsertSQL``）是 WS 路径唯一的 session 头写入者，而
``CHAT_PERSISTER_ENABLED`` 默认 false（engine 是 single authoritative
writer，gateway setup.go:208 / config.go:562）→ ``chat_sessions`` 永远缺行 →
网关 ``GET /api/v1/chat/sessions``（``getRecentSessionsFromDB`` 只读该表）
返回空 → 移动端重启后拿不到 conversationId，历史永不可达。

本测试在真实 sqlite 引擎上验证：轮次持久化（user + assistant 两个落库点）
之后——
1. ``chat_sessions`` 头行存在（session 列表可发现的充要条件）；
2. ``chat_messages`` 行引用同一 session_id（历史可回放的充要条件）；
3. 幂等：同 session 第二轮不重复建头；
4. legacy label（零 UUID 降级）保持既有语义：不建头、不报错。
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.persistence_layer import PersistenceLayerMixin

SESSION_ID = str(uuid.uuid4())


def _build_engine_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _make_schema(engine) -> None:
    from app.db.session import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _bare_context_builder_mixin() -> ContextBuilderMixin:
    return object.__new__(ContextBuilderMixin)


def _bare_persistence_layer_mixin() -> PersistenceLayerMixin:
    """裸 PersistenceLayerMixin，绑定 ChatOrchestrator 的 _coerce_session_uuid
    语义（uuid5 fallback），与生产组合一致。"""
    mixin = object.__new__(PersistenceLayerMixin)
    # `_coerce_session_uuid` 已是 @staticmethod（单参）：旧双参 lambda
    # `_coerce(mixin, sid)` 触发 TypeError，被 _persist_assistant_message 宽
    # except 吞成 persist 全失败。对齐判例直绑 staticmethod 契约。
    mixin._coerce_session_uuid = staticmethod(ChatOrchestrator._coerce_session_uuid)  # type: ignore[method-assign]
    return mixin


@pytest.mark.asyncio
async def test_user_turn_persistence_creates_session_header() -> None:
    """B-01 主断言：_persist_user_message 落库后 chat_sessions 头必须存在。

    修复前：只有 chat_messages 行（V13 DB 铁证：消息 4 行 / sessions 0 行）。
    """
    engine, sessionmaker = _build_engine_sessionmaker()
    await _make_schema(engine)
    user_id = uuid.uuid4()
    mixin = _bare_context_builder_mixin()

    async with sessionmaker() as db:
        await mixin._persist_user_message(
            active_db=db,
            user_id=str(user_id),
            session_id=SESSION_ID,
            user_message="7天后考离散数学，最弱图论，每天2小时",
            request_id="req-b01-1",
        )
        await db.flush()

        header = (
            await db.execute(select(ChatSession).where(ChatSession.id == uuid.UUID(SESSION_ID)))
        ).scalar_one_or_none()
        assert header is not None, (
            "B-01 红证：WS 轮次用户消息落库后 chat_sessions 头缺失——"
            "sessions 列表永远为空，移动端重启后历史不可达"
        )
        assert str(header.user_id) == str(user_id)
        assert header.is_active is True
        assert header.last_message_at is not None

        msg = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == uuid.UUID(SESSION_ID))
            )
        ).scalar_one()
        assert msg.role == MessageRole.USER
        assert str(msg.user_id) == str(user_id)

    await engine.dispose()


@pytest.mark.asyncio
async def test_assistant_turn_persistence_creates_session_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B-01 收尾断言：_persist_assistant_message 的独立 session 同样幂等补建头。

    该路径自带提交（既有语义：共享流 session 可能被更早异常毒化），头行
    必须与 assistant 行同事务落地，避免任何「有消息无会话」的孤儿态。
    """
    import app.db.session as dbs
    import app.orchestration.persistence_layer as pl

    engine, sessionmaker = _build_engine_sessionmaker()
    await _make_schema(engine)

    # _persist_assistant_message 通过模块级 AsyncSessionLocal 自建 session——
    # 打桩到本测试的内存引擎（StaticPool 共享连接）。
    monkeypatch.setattr(dbs, "AsyncSessionLocal", sessionmaker)
    lane_probe = MagicMock(return_value=None)
    monkeypatch.setattr(
        pl.MemoryInferredWriteLaneService, "enqueue_from_session", lane_probe
    )
    monkeypatch.setattr(
        pl.MemoryInferredWriteLaneService, "enqueue_from_chat_turn", lane_probe
    )
    monkeypatch.setattr(pl, "llm_service", MagicMock(default_model="unit-model"))

    user_id = uuid.uuid4()
    mixin = _bare_persistence_layer_mixin()

    async with sessionmaker() as shared_db:
        await mixin._persist_assistant_message(
            active_db=shared_db,
            user_id=str(user_id),
            session_id=SESSION_ID,
            full_response="我按你的反馈把策略收紧了一版，你确认后我就开始生成任务卡。",
        )

    async with sessionmaker() as db:
        header = (
            await db.execute(select(ChatSession).where(ChatSession.id == uuid.UUID(SESSION_ID)))
        ).scalar_one_or_none()
        assert header is not None, "B-01 红证：assistant 落库后 chat_sessions 头缺失"
        assert header.is_active is True

        msg = (
            await db.execute(
                select(ChatMessage)
                .where(
                    ChatMessage.session_id == uuid.UUID(SESSION_ID),
                    ChatMessage.role == MessageRole.ASSISTANT,
                )
            )
        ).scalar_one()
        assert msg.content.startswith("我按你的反馈")

    await engine.dispose()


@pytest.mark.asyncio
async def test_session_header_is_idempotent_across_turns() -> None:
    """同一 session 连续两轮：头行只有一条，不重复建头。"""
    engine, sessionmaker = _build_engine_sessionmaker()
    await _make_schema(engine)
    user_id = uuid.uuid4()
    mixin = _bare_context_builder_mixin()

    async with sessionmaker() as db:
        for i, text in enumerate(("第一轮", "第二轮")):
            await mixin._persist_user_message(
                active_db=db,
                user_id=str(user_id),
                session_id=SESSION_ID,
                user_message=text,
                request_id=f"req-b01-{i}",
            )
            await db.flush()

        headers = (
            (await db.execute(select(ChatSession).where(ChatSession.id == uuid.UUID(SESSION_ID))))
            .scalars()
            .all()
        )
        assert len(headers) == 1, "幂等性破坏：同 session 出现多头"
        assert headers[0].is_active is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_label_session_skips_header() -> None:
    """legacy label（非 UUID）→ 零 UUID 降级 → 不建头（跨用户 PK，保持既有语义）。"""
    engine, sessionmaker = _build_engine_sessionmaker()
    await _make_schema(engine)
    user_id = uuid.uuid4()
    mixin = _bare_context_builder_mixin()

    async with sessionmaker() as db:
        await mixin._persist_user_message(
            active_db=db,
            user_id=str(user_id),
            session_id="df-d2-s1",
            user_message="legacy label 消息",
            request_id="req-b01-4",
        )
        await db.flush()

        headers = (await db.execute(select(ChatSession))).scalars().all()
        assert headers == [], "零 UUID 降级不应产生头行（PK 跨用户冲突风险）"
        msg = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == uuid.UUID(int=0))
            )
        ).scalar_one()
        assert msg.content == "legacy label 消息"

    await engine.dispose()
