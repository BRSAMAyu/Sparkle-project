from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.orchestration.context_focus import ContextFocusResolver
from app.orchestration.prompts import build_system_prompt
from app.services.embedding_service import embedding_service
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_context_focus_resolver_prefers_emotional_focus_without_plan_action() -> None:
    resolver = ContextFocusResolver()

    decision = resolver.resolve(
        user_message="我最近好崩溃，完全学不进去",
        route_intent="chat",
        plan_context={"plan_title": "高数复习"},
        cognitive_insights={"has_cognitive_patterns": True, "pattern_count": 2},
    )

    assert decision.focus_mode == "emotional_focus"
    assert decision.section_weights["plan_context"] == "minimal"
    assert decision.section_weights["cognitive_prism"] == "full"


def test_build_system_prompt_uses_briefing_and_hides_irrelevant_plan_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "current_query": "给我讲一下矩阵乘法",
            "context_focus": {
                "focus_mode": "knowledge_focus",
                "focus_reason": "route:knowledge",
                "section_weights": {
                    "user_context": "medium",
                    "plan_context": "low",
                    "cognitive_prism": "off",
                    "preferences": "medium",
                    "goals": "low",
                    "episodic": "low",
                    "task_summary": "off",
                },
                "section_caps": {"goals": 2, "episodic": 1, "next_actions": 1, "active_plans": 1},
                "briefing_candidates": ["本轮优先聚焦知识解释，减少无关画像噪声"],
                "semantic_gating_enabled": True,
                "route_intent": "knowledge",
            },
            "context_briefing_note": "当前重点：只解释矩阵乘法，减少无关计划信息",
        },
        conversation_history={"messages": []},
        plan_context={"plan_title": "英语冲刺计划", "goal": "提升英语成绩"},
    )

    assert prompt.startswith("你是 Sparkle") is False
    assert "## 本轮关键上下文摘要" in prompt
    assert "矩阵乘法" in prompt
    assert "英语冲刺计划" not in prompt


@pytest.mark.asyncio
async def test_context_pack_semantic_gating_filters_irrelevant_memory(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUSING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SEMANTIC_GATING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_BRIEFING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)

    async def fake_batch_embeddings(texts: list[str], text_type: str = "document") -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            if "矩阵" in text or "线代" in text:
                vectors.append([1.0, 0.0])
            elif "英语" in text:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.2, 0.2])
        return vectors

    monkeypatch.setattr(embedding_service, "batch_embeddings", fake_batch_embeddings)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="math_style",
        pref_value={"value": "喜欢先看矩阵乘法例题"},
        evidence_refs=[{"type": "event", "id": "evt_math"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="english_style",
        pref_value={"value": "英语阅读时喜欢先背单词"},
        evidence_refs=[{"type": "event", "id": "evt_english"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="线代矩阵专项",
        status="active",
        evidence_refs=[{"type": "event", "id": "goal_math"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="英语阅读专项",
        status="active",
        evidence_refs=[{"type": "event", "id": "goal_english"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="昨天复盘了矩阵乘法错题",
        source_type="analysis",
        source_id="epi_math",
        occurred_at=_utcnow(),
        importance_score=0.8,
        tags=["math"],
        evidence_refs=[{"type": "event", "id": "epi_math"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="上周做了英语阅读训练",
        source_type="analysis",
        source_id="epi_english",
        occurred_at=_utcnow(),
        importance_score=0.6,
        tags=["english"],
        evidence_refs=[{"type": "event", "id": "epi_english"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"learning": {"preferences": 200, "goals": 200, "episodic": 200}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(
        user_id=user_id,
        intent="learning",
        query_text="给我讲一下矩阵乘法",
        focus_mode="knowledge_focus",
        route_intent="knowledge",
    )

    assert "math_style" in pack.preferences
    assert "english_style" not in pack.preferences
    assert any("线代矩阵专项" in goal["title"] for goal in pack.goals)
    assert all("英语" not in goal["title"] for goal in pack.goals)
    assert pack.context_focus is not None
    assert pack.context_focus["focus_mode"] == "knowledge_focus"
    assert pack.context_briefing_note
