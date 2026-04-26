import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.context_manager import CognitiveContext, ContextOrchestrator
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext


def test_calendar_context_serializes_exam_and_class_events() -> None:
    event = SimpleNamespace(
        title="高数考试",
        start_time=datetime(2026, 4, 26, 14, 0, tzinfo=UTC),
        end_time=datetime(2026, 4, 26, 15, 30, tzinfo=UTC),
        is_all_day=False,
        source="manual",
        task_id=None,
        plan_id=None,
        source_metadata={},
    )

    serialized = ContextOrchestrator._serialize_busy_calendar_events([event])

    assert serialized[0]["kind"] == "exam"
    assert serialized[0]["start"] == "14:00"
    assert serialized[0]["end"] == "15:30"


@pytest.mark.asyncio
async def test_context_orchestrator_aggregation(db_session):
    redis_client = AsyncMock()
    redis_client.get.return_value = None

    orchestrator = ContextOrchestrator(db_session, redis_client)

    profile_context = ProfileContext(
        preferences={"depth": "high"},
        preference_version=7,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.82,
            active_learning_subjects=["math"],
            weak_spots=[],
            recent_mastery_changes=[],
        ),
        cognitive_summary=CognitiveSummary(),
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr(orchestrator, "_get_profile_context", AsyncMock(return_value=profile_context))
        m.setattr(
            orchestrator, "_get_error_profile", AsyncMock(return_value={"summary": {"total_errors": 5}, "recent": []})
        )
        m.setattr(
            orchestrator,
            "_get_task_profile",
            AsyncMock(
                return_value={
                    "tasks": [
                        {
                            "id": str(uuid.uuid4()),
                            "title": "Test Task",
                            "priority": 1,
                            "due_date": None,
                            "type": "study",
                        }
                    ],
                    "focus": {"focus_minutes": 120},
                }
            ),
        )
        m.setattr(orchestrator, "_get_user_metrics", AsyncMock(return_value={"level": 5}))
        m.setattr(orchestrator, "_get_community_profile", AsyncMock(return_value={"active_group_count": 1}))
        m.setattr(
            orchestrator,
            "_get_social_context_v1",
            AsyncMock(return_value={"mention_count": 1, "summary_lines": ["最近 7 天提到过 1 位学习相关人物。"]}),
        )
        m.setattr(
            orchestrator,
            "_get_achievement_context",
            AsyncMock(
                return_value={
                    "recent_unlocks": [{"achievement_id": "streak_7", "name": "七日连胜"}],
                    "in_progress_achievements": [
                        {"achievement_id": "study_100hours", "name": "百小时学习", "progress": 0.62}
                    ],
                    "total_achievement_score": 3.6,
                }
            ),
        )
        m.setattr(
            orchestrator,
            "_get_calendar_context",
            AsyncMock(
                return_value={
                    "upcoming_deadlines": [{"title": "热力学计划复盘"}],
                    "time_blocks_today": [{"start": "19:00", "end": "21:00"}],
                    "workload_density": "medium",
                    "exam_urgency": {"days_left": 12, "urgent": True},
                }
            ),
        )
        m.setattr(
            orchestrator,
            "_get_capsule_preferences",
            AsyncMock(
                return_value={
                    "favorite_count": 3,
                    "content_depth_preference": "deep",
                    "subject_affinity": ["computer_networks"],
                    "recent_notes": ["keep the rigorous examples"],
                }
            ),
        )
        m.setattr(
            "app.core.context_manager.MemoryService.get_recent_episodic",
            AsyncMock(
                return_value=[
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        summary="上次你备考计算机网络，传输层不错但子网划分薄弱。",
                        subject_type="learning_profile",
                        source_type="chat_turn",
                        occurred_at=None,
                        tags=["aurora"],
                    )
                ]
            ),
        )

        user_id = str(uuid.uuid4())
        context = await orchestrator.get_user_context(user_id)

    assert isinstance(context, CognitiveContext)
    assert context.user_id == user_id
    assert context.knowledge_stats == {
        "overall_mastery": 0.82,
        "active_learning_subjects": ["math"],
        "weak_spots": [],
    }
    assert context.error_summary == {"total_errors": 5}
    assert len(context.active_tasks) == 1
    assert context.active_tasks[0]["title"] == "Test Task"
    assert context.preferences == {"depth": "high"}
    assert context.preference_version == 7
    assert context.social_context_v1["mention_count"] == 1
    assert context.achievement_summary["recent_unlocks"][0]["name"] == "七日连胜"
    assert context.calendar_context["workload_density"] == "medium"
    assert context.capsule_preferences["content_depth_preference"] == "deep"
    assert context.capsule_preferences["subject_affinity"] == ["computer_networks"]
    assert context.past_session_memory[0]["summary"].startswith("上次你备考计算机网络")
    assert redis_client.setex.called


@pytest.mark.asyncio
async def test_context_orchestrator_uses_isolated_sessions_for_service_backed_helpers():
    shared_db = AsyncMock()
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    orchestrator = ContextOrchestrator(shared_db, redis_client)

    created_sessions = [object(), object(), object(), object(), object(), object(), object(), object(), object()]
    issued_sessions: list[object] = []
    service_dbs: dict[str, list[object]] = {"profile": [], "error": [], "user": []}

    class _SessionContext:
        def __init__(self, session):
            self._session = session

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _SessionFactory:
        def __call__(self):
            session = created_sessions.pop(0)
            issued_sessions.append(session)
            return _SessionContext(session)

    class FakeProfileContextService:
        def __init__(self, db, redis):
            service_dbs["profile"].append(db)

        async def get_profile_context(self, user_id):
            return ProfileContext()

    class FakeErrorBookService:
        def __init__(self, db):
            service_dbs["error"].append(db)

        async def get_review_stats(self, user_id):
            return {}

        async def list_errors(self, user_id, params):
            return [], 0

    class FakeUserService:
        def __init__(self, db, redis):
            service_dbs["user"].append(db)

        async def get_analytics_summary(self, user_id):
            return {}

    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.core.context_manager.async_sessionmaker", lambda *args, **kwargs: _SessionFactory())
        m.setattr("app.core.context_manager.ProfileContextService", FakeProfileContextService)
        m.setattr("app.core.context_manager.ErrorBookService", FakeErrorBookService)
        m.setattr("app.core.context_manager.UserService", FakeUserService)
        m.setattr(orchestrator, "_get_task_profile", AsyncMock(return_value={"tasks": [], "focus": {}}))
        m.setattr(orchestrator, "_get_community_profile", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_social_context_v1", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_achievement_context", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_calendar_context", AsyncMock(return_value={}))
        m.setattr(orchestrator, "_get_past_session_memory", AsyncMock(return_value=[]))

        await orchestrator.get_user_context(str(uuid.uuid4()))

    assert len(service_dbs["profile"]) == 1
    assert len(service_dbs["error"]) == 1
    assert len(service_dbs["user"]) == 1
    assert service_dbs["profile"][0] in issued_sessions
    assert service_dbs["error"][0] in issued_sessions
    assert service_dbs["user"][0] in issued_sessions
    assert all(db is not shared_db for db in service_dbs["profile"] + service_dbs["error"] + service_dbs["user"])
