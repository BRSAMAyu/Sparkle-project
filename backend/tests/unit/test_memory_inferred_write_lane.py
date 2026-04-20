import json
from datetime import timezone, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.prompts import build_system_prompt
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService, revoke_inferred_lane
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _create_user(db_session):
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
async def test_memory_inferred_extractor_precision_fixture(db_session):
    service = MemoryInferredWriteLaneService(db_session)
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "memory_inferred_cold_dataset.json"
    )
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    predicted_positive = 0
    true_positive = 0
    false_positive = 0
    user_id = uuid4()
    for index, case in enumerate(cases):
        candidate = service.extract_candidate(
            user_id=user_id,
            user_message=case["user_message"],
            assistant_message="好的，我会按这个节奏继续帮你安排。",
            evidence_token=f"turn_{index}",
        )
        if candidate is not None:
            predicted_positive += 1
        if case["label"] == "positive" and candidate is not None:
            true_positive += 1
        if case["label"] == "negative" and candidate is not None:
            false_positive += 1

    precision = true_positive / predicted_positive if predicted_positive else 0.0
    assert false_positive == 0
    assert precision >= 0.9


@pytest.mark.asyncio
async def test_memory_inferred_write_lane_respects_feature_flag(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)

    user = await _create_user(db_session)
    session_id = uuid4()
    user_turn = await _create_user_turn(
        db_session,
        user.id,
        session_id,
        "最近我在整理线代错题，明天要把特征值这章再复习一遍。",
    )

    service = MemoryInferredWriteLaneService(db_session)
    candidate = await service.process_chat_turn(
        user_id=user.id,
        session_id=session_id,
        user_message=user_turn.content,
        assistant_message="好的，我会帮你按这个节奏排。",
        user_message_id=str(user_turn.id),
        assistant_message_id=str(uuid4()),
    )

    assert candidate is not None
    result = await db_session.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == user.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_memory_inferred_revoke_hides_from_prompt_read_path(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)

    user = await _create_user(db_session)
    session_id = uuid4()
    text = "这周我要赶论文 ddl，今晚先把提纲补完。"
    user_turn = await _create_user_turn(db_session, user.id, session_id, text)

    service = MemoryInferredWriteLaneService(db_session)
    candidate = await service.process_chat_turn(
        user_id=user.id,
        session_id=session_id,
        user_message=text,
        assistant_message="收到，我会按 ddl 优先级继续帮你收紧计划。",
        user_message_id=str(user_turn.id),
        assistant_message_id=str(uuid4()),
    )
    assert candidate is not None

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack_before = await builder.build(user.id, intent="chat", query_text="继续帮我安排今晚进度")
    prompt_before = build_system_prompt(pack_before.to_prompt_context(), "History")
    assert candidate.candidate_text in prompt_before

    record = (
        await db_session.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user.id,
                EpisodicMemory.source_lane == "inferred_extraction",
            )
        )
    ).scalar_one()
    await MemoryService(db_session).retract_memory(
        kind="episodic",
        memory_id=record.id,
        user_id=user.id,
        reason="user_revoked_ai_auto_memory",
    )
    await db_session.refresh(record)
    assert record.revoked_at is not None
    assert record.retracted_at is None

    pack_after = await builder.build(user.id, intent="chat", query_text="继续帮我安排今晚进度")
    prompt_after = build_system_prompt(pack_after.to_prompt_context(), "History")
    assert candidate.candidate_text not in prompt_after


@pytest.mark.asyncio
async def test_memory_inferred_kill_switch_only_revokes_inferred_lane(db_session):
    user = await _create_user(db_session)
    memory_service = MemoryService(db_session)

    inferred = await memory_service.create_episodic_memory(
        user_id=user.id,
        summary="最近在准备教资考试",
        source_type="chat",
        source_id=str(uuid4()),
        source_lane="inferred_extraction",
        occurred_at=_utcnow(),
        importance_score=0.95,
        confidence=0.95,
        tags=["stage16:auto_memory"],
        evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
        evidence_token=str(uuid4()),
        decay_policy="7d",
        semantic_key="auto-memory",
        emit_system_update=False,
    )
    explicit = await memory_service.create_episodic_memory(
        user_id=user.id,
        summary="用户手动保存的经历",
        source_type="analysis",
        source_id="manual",
        occurred_at=_utcnow(),
        importance_score=0.8,
        tags=["manual"],
        evidence_refs=[{"type": "event", "id": "evt_manual"}],
        emit_system_update=False,
    )

    revoked = await revoke_inferred_lane(db_session, user_id=user.id, reason="stage16_test")
    assert revoked == 1

    await db_session.refresh(inferred)
    await db_session.refresh(explicit)
    assert inferred.revoked_at is not None
    assert explicit.revoked_at is None
    assert explicit.retracted_at is None
