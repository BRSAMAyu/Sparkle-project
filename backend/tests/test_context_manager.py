import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.context_manager import CognitiveContext, ContextOrchestrator
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext


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
        m.setattr(orchestrator, "_get_error_profile", AsyncMock(return_value={"summary": {"total_errors": 5}, "recent": []}))
        m.setattr(
            orchestrator,
            "_get_task_profile",
            AsyncMock(
                return_value={
                    "tasks": [{"id": str(uuid.uuid4()), "title": "Test Task", "priority": 1, "due_date": None, "type": "study"}],
                    "focus": {"focus_minutes": 120},
                }
            ),
        )
        m.setattr(orchestrator, "_get_user_metrics", AsyncMock(return_value={"level": 5}))
        m.setattr(orchestrator, "_get_community_profile", AsyncMock(return_value={"active_group_count": 1}))

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
    assert redis_client.setex.called


@pytest.mark.asyncio
async def test_context_orchestrator_uses_isolated_sessions_for_service_backed_helpers():
    shared_db = AsyncMock()
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    orchestrator = ContextOrchestrator(shared_db, redis_client)

    created_sessions = [object(), object(), object(), object(), object()]
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

        await orchestrator.get_user_context(str(uuid.uuid4()))

    assert len(service_dbs["profile"]) == 1
    assert len(service_dbs["error"]) == 1
    assert len(service_dbs["user"]) == 1
    assert service_dbs["profile"][0] in issued_sessions
    assert service_dbs["error"][0] in issued_sessions
    assert service_dbs["user"][0] in issued_sessions
    assert all(db is not shared_db for db in service_dbs["profile"] + service_dbs["error"] + service_dbs["user"])
