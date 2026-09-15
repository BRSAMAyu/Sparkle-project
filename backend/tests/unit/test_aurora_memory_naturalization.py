from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.user import User
from app.orchestration.prompts import build_system_prompt
from app.orchestration.response_builder import ResponseBuilderMixin
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_memory_prompt_renders_structured_natural_reference_context() -> None:
    occurred_at = (_utcnow() - timedelta(days=3)).isoformat()
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5},
            "episodic_memories": [
                {
                    "id": f"memory-{idx}",
                    "summary": f"memory-{idx}",
                    "source_type": "chat_turn",
                    "occurred_at": occurred_at,
                    "confidence": 0.82,
                    "user_confirmed": True,
                }
                for idx in range(6)
            ],
        },
        conversation_history={"messages": []},
    )

    assert "【近期相关记忆】" in prompt
    assert "memory_1:" in prompt
    assert "content: memory-0" in prompt
    assert "time_ago: 3天前" in prompt
    assert "source: 你告诉我的" in prompt
    assert "confidence: 0.82" in prompt
    assert "user_confirmed: true" in prompt
    assert "content: memory-4" in prompt
    assert "memory-5" not in prompt
    assert "自然带入相关事实" in prompt
    assert "用户否认后停止引用该记忆" in prompt


def test_memory_reference_receipt_only_when_response_uses_memory() -> None:
    receipt = ResponseBuilderMixin._build_memory_reference_receipt(
        full_response="明天考高数的话，今晚先收一个最小复习闭环就好。",
        user_context_payload={
            "episodic_memories": [
                {
                    "id": "mem-gaoshu",
                    "summary": "明天考高数",
                    "source_type": "chat_turn",
                    "occurred_at": (_utcnow() - timedelta(days=1)).isoformat(),
                    "confidence": 0.9,
                    "user_confirmed": True,
                }
            ]
        },
        context_data={},
        response_id="resp-1",
    )

    assert receipt is not None
    assert receipt["receipt_type"] == "memory_reference_receipt"
    assert receipt["memory_reference_outcome"] == "pending"
    assert receipt["used_count"] == 1
    referenced = receipt["referenced_memories"][0]
    assert referenced["id"] == "mem-gaoshu"
    assert referenced["content"] == "明天考高数"
    assert referenced["confidence"] == pytest.approx(0.9)

    empty_receipt = ResponseBuilderMixin._build_memory_reference_receipt(
        full_response="我们先看这道题的条件。",
        user_context_payload={
            "episodic_memories": [
                {
                    "id": "mem-gaoshu",
                    "summary": "明天考高数",
                    "source_type": "chat_turn",
                }
            ]
        },
        context_data={},
        response_id="resp-2",
    )
    assert empty_receipt is None


@pytest.mark.asyncio
async def test_memory_reference_outcome_adjusts_future_reference_confidence(db_session) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user_id,
        summary="明天考高数",
        source_type="chat_turn",
        source_id="turn-1",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["exam"],
        evidence_refs=[{"type": "chat_turn", "id": "turn-1"}],
        confidence=0.8,
    )

    corrected = await service.record_memory_reference_outcome(
        kind="episodic",
        memory_id=record.id,
        user_id=user_id,
        outcome="corrected",
        response_id="resp-1",
        reason="user said this was wrong",
    )
    assert corrected["memory_reference_outcome"] == "corrected"
    assert corrected["confidence"] == pytest.approx(0.7)
    assert corrected["correction_count"] == 1

    denied = await service.record_memory_reference_outcome(
        kind="episodic",
        memory_id=record.id,
        user_id=user_id,
        outcome="denied",
        response_id="resp-2",
        reason="not my exam",
    )
    assert denied["memory_reference_outcome"] == "denied"
    assert denied["confidence"] == pytest.approx(0.6)
    assert denied["correction_count"] == 2
