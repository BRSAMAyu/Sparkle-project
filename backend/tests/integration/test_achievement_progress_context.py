from unittest.mock import AsyncMock

import pytest

from app.core.context_manager import ContextOrchestrator
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.orchestration.prompts import build_system_prompt


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.values.pop(key, None)


@pytest.mark.asyncio
async def test_achievement_progress_event_reaches_chat_context(db_session, test_user) -> None:
    redis = _FakeRedis()
    await ContextOrchestrator.record_achievement_progress_event(
        redis,
        {
            "event_type": "achievement.progress",
            "user_id": str(test_user.id),
            "achievement_id": "study_100hours",
            "achievement_name": "百小时学习",
            "progress_percent": 75,
            "timestamp": "2026-04-26T10:00:00",
        },
    )

    orchestrator = ContextOrchestrator(db_session, redis)
    profile_context = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.0,
            active_learning_subjects=[],
            weak_spots=[],
            recent_mastery_changes=[],
        ),
        cognitive_summary=CognitiveSummary(),
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr(orchestrator, "_get_profile_context", AsyncMock(return_value=profile_context))
        m.setattr(orchestrator, "_get_error_profile", AsyncMock(return_value={"summary": {}, "recent": []}))
        m.setattr(orchestrator, "_get_task_profile", AsyncMock(return_value={"tasks": [], "focus": {}}))
        m.setattr(orchestrator, "_get_user_metrics", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_community_profile", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_social_context_v1", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_achievement_context", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_calendar_context", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_capsule_preferences", AsyncMock(return_value={}))
        m.setattr(
            "app.core.context_manager.MemoryService.get_recent_episodic",
            AsyncMock(return_value=[]),
        )

        context = await orchestrator.get_user_context(str(test_user.id), force_refresh=True)

    assert context.achievement_summary["recent_progress_events"][0]["achievement_name"] == "百小时学习"
    assert context.achievement_summary["recent_progress_events"][0]["progress_percent"] == 75

    prompt = build_system_prompt(
        user_context=context.model_dump(mode="json"),
        conversation_history={"messages": []},
    )
    assert "百小时学习 刚推进到 75%" in prompt
