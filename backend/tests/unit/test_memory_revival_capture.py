"""MR-1 记忆捕获主路径复活（memory-revival round2）。

多端实测（memory-rag-seedlib-eval MR-1）："WS 纯聊天轮 0 记忆落库"。
代码梳理确认 assistant 消息持久化 → ``enqueue_from_session`` → 推断 lane
的接线在标准轮 happy path 上是通的（RB-06 测试覆盖 persist→enqueue wiring），
真正的机制性死点是：规则候选器对"显式记忆口令 + 陈述事实"类句子
（如"我最喜欢的电影是《星际穿越》，帮我记住这个。"）返回 None——
既无工作记忆条目、也无固化对象，"帮我记住"产品承诺整链失活。

本文件红绿锁定：显式记忆口令必须产生候选并写入 episodic LTM。
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

EVAL_MOVIE_MESSAGE = "我最喜欢的电影是《星际穿越》，帮我记住这个。"


async def _create_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _create_user_turn(db_session, user_id, session_id, content: str) -> ChatMessage:
    message = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.USER,
        content=content,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest.mark.asyncio
async def test_explicit_memory_command_yields_candidate(db_session):
    """红：显式记忆口令句此前被规则候选器完全丢弃（extract_candidate → None）。"""
    service = MemoryInferredWriteLaneService(db_session)
    candidate = service.extract_candidate(
        user_id=uuid4(),
        user_message=EVAL_MOVIE_MESSAGE,
        assistant_message="好的，我记住了。",
        evidence_token="turn_movie_red",
    )
    assert candidate is not None, (
        "显式记忆口令（帮我记住/记下来）必须产生推断候选，" "否则工作记忆与固化链无事可做（MR-1 死点）"
    )
    assert candidate.subject_type in {"self", "commitment", "person_mention", "relationship"}


@pytest.mark.asyncio
async def test_explicit_memory_command_writes_episodic_ltm_row(db_session, monkeypatch):
    """红：标准聊天轮（enqueue_from_session 路径，user_message=None 从库补读）
    一轮后 episodic_memories 必须有 inferred_extraction 写入。"""
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
    monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

    user = await _create_user(db_session)
    session_id = uuid4()
    user_turn = await _create_user_turn(db_session, user.id, session_id, EVAL_MOVIE_MESSAGE)

    service = MemoryInferredWriteLaneService(db_session)
    # enqueue_from_session 语义：user_message=None → 从 chat_messages 回读最新用户轮
    candidate = await service.process_chat_turn(
        user_id=user.id,
        session_id=session_id,
        user_message=None,
        assistant_message="好的，我记住了。",
        user_message_id=None,
        assistant_message_id=None,
    )

    assert candidate is not None, "显式记忆口令一轮后必须产出候选"
    rows = (
        (
            await db_session.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user.id,
                    EpisodicMemory.source_lane == "inferred_extraction",
                    EpisodicMemory.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1, f"显式记忆口令一轮后 episodic_memories 应有 1 行写入，实际 {len(rows)}"
    assert "星际穿越" in rows[0].summary
    assert rows[0].evidence_token == str(user_turn.id)


@pytest.mark.asyncio
async def test_explicit_memory_command_still_respects_user_disabled(db_session, monkeypatch):
    """护栏：显式口令 fallback 不得绕过用户记忆关闭开关。"""
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
    monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

    from app.models.user_memory_settings import UserMemorySettings

    user = await _create_user(db_session)
    db_session.add(
        UserMemorySettings(
            user_id=user.id,
            enabled=False,
            allow_episodic=False,
        )
    )
    await db_session.commit()

    session_id = uuid4()
    await _create_user_turn(db_session, user.id, session_id, EVAL_MOVIE_MESSAGE)

    service = MemoryInferredWriteLaneService(db_session)
    await service.process_chat_turn(
        user_id=user.id,
        session_id=session_id,
        user_message=EVAL_MOVIE_MESSAGE,
        assistant_message="好的，我记住了。",
        user_message_id=str(uuid4()),
        assistant_message_id=None,
    )
    rows = (await db_session.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == user.id))).scalars().all()
    assert len(rows) == 0, "用户关闭记忆时显式口令也不得落库"


@pytest.mark.asyncio
async def test_explicit_memory_command_not_duplicated(db_session, monkeypatch):
    """护栏：同一 evidence_token 重复触发不得写两行（semantic/evidence 去重仍生效）。"""
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
    monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

    user = await _create_user(db_session)
    session_id = uuid4()
    user_turn = await _create_user_turn(db_session, user.id, session_id, EVAL_MOVIE_MESSAGE)

    service = MemoryInferredWriteLaneService(db_session)
    for _ in range(2):
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=EVAL_MOVIE_MESSAGE,
            assistant_message="好的，我记住了。",
            user_message_id=str(user_turn.id),
            assistant_message_id=None,
        )

    rows = (
        (
            await db_session.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user.id,
                    EpisodicMemory.source_lane == "inferred_extraction",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1, f"重复口令必须去重，实际 {len(rows)} 行"


def test_explicit_command_fallback_respects_hard_banned_topics():
    """护栏：硬禁止话题（人格判定/负面标签）即使用户口令要求记住也不得捕获。"""
    banned_message = "帮我记住：我就是个很笨的人，我永远学不会。"
    assert MemoryInferredWriteLaneService._has_explicit_memory_command(banned_message)
    fact = MemoryInferredWriteLaneService._extract_explicit_command_fact(banned_message)
    assert fact is None, "硬禁止话题不得通过显式口令 fallback 捕获"
